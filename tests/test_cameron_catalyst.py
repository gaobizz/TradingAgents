"""Tests for the catalyst grader and the transcript-mining pipeline."""

import dataclasses
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from tradingagents.strategies.ross_cameron import CameronConfig
from tradingagents.strategies.ross_cameron.catalyst import (
    CatalystGrade,
    grade_catalyst,
    grade_headline,
    make_llm_grader,
    meets_minimum_grade,
)
from tradingagents.strategies.ross_cameron.screener import screen_snapshot
from tradingagents.strategies.ross_cameron.transcripts import (
    MinedRule,
    Transcript,
    chunk_text,
    dedupe_rules,
    load_transcript_dir,
    mine_transcripts,
    rules_to_markdown,
)
from tests.test_cameron_strategy import good_snapshot

CFG = CameronConfig()
SCAN = datetime(2026, 7, 9, 9, 25)
FRESH = SCAN - timedelta(hours=2)


# ---------------------------------------------------------------------------
# Deterministic grading
# ---------------------------------------------------------------------------
class TestGradeHeadline:
    def test_tier_a_fda_approval(self):
        grade = grade_headline("FDA grants approval for lead candidate", FRESH, SCAN)
        assert grade.grade == "A" and grade.category == "fda_approval"

    def test_tier_b_earnings_beat(self):
        grade = grade_headline("Q2 results: company beats estimates", FRESH, SCAN)
        assert grade.grade == "B" and grade.category == "earnings_beat"

    def test_tier_c_letter_of_intent(self):
        grade = grade_headline("Signs letter of intent with distributor", FRESH, SCAN)
        assert grade.grade == "C" and grade.category == "loi_mou"

    def test_tier_d_conference_fluff(self):
        grade = grade_headline("CEO to present at growth conference", FRESH, SCAN)
        assert grade.grade == "D" and grade.category == "conference_pr"

    def test_unclassified_pr_defaults_to_d(self):
        grade = grade_headline("Company issues corporate update", FRESH, SCAN)
        assert grade.grade == "D" and grade.category == "unclassified_pr"

    def test_offering_is_a_veto(self):
        grade = grade_headline("Prices $10 million public offering", FRESH, SCAN)
        assert grade.grade == "F" and grade.category == "dilution_offering"
        assert "veto" in grade.reasons

    def test_staleness_decays_grade(self):
        headline = "FDA grants approval for lead candidate"
        aging = grade_headline(headline, SCAN - timedelta(hours=24), SCAN)
        stale = grade_headline(headline, SCAN - timedelta(hours=72), SCAN)
        assert aging.grade == "B"   # 90 - 10
        assert stale.grade == "C"   # 90 - 25

    def test_quantified_bonus(self):
        grade = grade_headline(
            "Awarded $50 million contract from Department of Defense", FRESH, SCAN
        )
        assert grade.category == "major_contract"
        assert grade.score == 95.0 and grade.grade == "A"
        assert "quantified" in grade.reasons


class TestGradeCatalyst:
    def test_no_news_is_f(self):
        grade = grade_catalyst([], SCAN)
        assert grade.grade == "F" and grade.category == "no_news"

    def test_best_headline_wins_with_corroboration(self):
        grade = grade_catalyst(
            [
                ("Signs letter of intent with distributor", FRESH),
                ("Q2 results: company beats estimates", FRESH),
            ],
            SCAN,
        )
        assert grade.category == "earnings_beat"
        assert grade.score == 80.0  # 75 + corroboration
        assert any("corroborated" in r for r in grade.reasons)

    def test_veto_poisons_good_news(self):
        grade = grade_catalyst(
            [
                ("FDA grants approval for lead candidate", FRESH),
                ("Announces registered direct offering", FRESH),
            ],
            SCAN,
        )
        assert grade.grade == "F" and grade.category == "dilution_offering"

    def test_minimum_grade_helper(self):
        assert meets_minimum_grade("B", "C")
        assert meets_minimum_grade("C", "C")
        assert not meets_minimum_grade("D", "C")
        assert not meets_minimum_grade("", "C")


class TestScreenerGradeIntegration:
    def test_graded_snapshot_uses_grade_not_boolean(self):
        low = dataclasses.replace(good_snapshot(), catalyst_grade="D")
        assert "catalyst" in screen_snapshot(low, CFG).failed_pillars
        ok = dataclasses.replace(good_snapshot(), catalyst_grade="C")
        assert screen_snapshot(ok, CFG).passed

    def test_min_grade_is_configurable(self):
        strict = dataclasses.replace(CFG, min_catalyst_grade="B")
        snap = dataclasses.replace(good_snapshot(), catalyst_grade="C")
        assert "catalyst" in screen_snapshot(snap, strict).failed_pillars

    def test_ungraded_snapshot_falls_back_to_boolean(self):
        assert screen_snapshot(good_snapshot(), CFG).passed  # grade="" + has_news=True


# ---------------------------------------------------------------------------
# LLM grader hook
# ---------------------------------------------------------------------------
class RecordingModel:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, 0

    def invoke(self, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.reply)


class TestLLMGrader:
    HEADLINES = [("Q2 results: company beats estimates", FRESH)]

    def test_valid_llm_response_is_used(self):
        model = RecordingModel(reply='{"grade": "A", "category": "llm_beat", "reason": "huge beat"}')
        grade = make_llm_grader(model)(self.HEADLINES, SCAN)
        assert grade.grade == "A" and grade.category == "llm_beat"
        assert model.calls == 1

    def test_model_error_falls_back_to_deterministic(self):
        model = RecordingModel(error=RuntimeError("rate limited"))
        grade = make_llm_grader(model)(self.HEADLINES, SCAN)
        assert grade.grade == "B" and grade.category == "earnings_beat"

    def test_garbage_response_falls_back(self):
        model = RecordingModel(reply="not json at all")
        grade = make_llm_grader(model)(self.HEADLINES, SCAN)
        assert grade.category == "earnings_beat"

    def test_llm_cannot_override_veto(self):
        model = RecordingModel(reply='{"grade": "A", "category": "llm", "reason": "looks great"}')
        grade = make_llm_grader(model)(
            [("Announces $5M at-the-market ATM program", FRESH)], SCAN
        )
        assert grade.grade == "F" and grade.category == "dilution_offering"
        assert model.calls == 0  # veto short-circuits before any LLM call


# ---------------------------------------------------------------------------
# Transcript mining
# ---------------------------------------------------------------------------
class ScriptedLLM:
    """Returns queued replies in order; records prompts."""

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def invoke(self, prompt):
        self.prompts.append(prompt)
        return SimpleNamespace(content=self.replies.pop(0))


class TestTranscriptMining:
    def test_chunking_covers_text_with_overlap(self):
        text = " ".join(f"word{i}" for i in range(3000))
        chunks = chunk_text(text, size=5000, overlap=200)
        assert len(chunks) > 1
        assert chunks[0].startswith("word0")
        assert chunks[-1].rstrip().endswith("word2999")

    def test_load_transcript_dir(self, tmp_path):
        (tmp_path / "vid1.txt").write_text("I only trade stocks with news.")
        (tmp_path / "vid2.json").write_text(
            json.dumps({"video_id": "vid2", "title": "Red day recap", "text": "I lost because I averaged down."})
        )
        transcripts = load_transcript_dir(tmp_path)
        assert [t.video_id for t in transcripts] == ["vid1", "vid2"]
        assert transcripts[1].title == "Red day recap"

    def test_mine_extracts_validates_and_survives_garbage(self):
        reply = json.dumps(
            [
                {"rule": "Only trade stocks with a news catalyst", "category": "catalyst_quality",
                 "quote": "I only trade stocks with news", "red_day": False},
                {"rule": "Never average down", "category": "not_a_real_category",
                 "quote": "averaging down killed me", "red_day": True},
                {"category": "risk_management", "quote": "missing rule field"},
            ]
        )
        llm = ScriptedLLM([reply, "MALFORMED {{{"])
        rules = mine_transcripts(
            [Transcript("vid1", "some transcript"), Transcript("vid2", "another")], llm
        )
        assert len(rules) == 2
        by_rule = {r.rule: r for r in rules}
        assert by_rule["Never average down"].category == "other"  # invalid → other
        assert by_rule["Never average down"].red_day

    def test_dedupe_merges_and_counts(self):
        rules = [
            MinedRule("Never average down", "risk_management", "q1", "vid1"),
            MinedRule("never average down!", "risk_management", "q2", "vid2", red_day=True),
            MinedRule("Cut losses quickly", "risk_management", "q3", "vid1"),
        ]
        merged = dedupe_rules(rules)
        assert len(merged) == 2
        top = merged[0]
        assert top.rule == "Never average down"
        assert top.occurrences == 2 and top.red_day
        assert top.sources == ["vid1", "vid2"]

    def test_markdown_report_and_survivorship_warning(self):
        with_red = rules_to_markdown(
            [MinedRule("Never average down", "risk_management", "it killed me", "vid1", red_day=True)]
        )
        assert "Risk Management" in with_red and "🔻" in with_red
        assert "Survivorship warning" not in with_red

        without_red = rules_to_markdown(
            [MinedRule("Buy high of day breaks", "entry_tactics", "", "vid1")]
        )
        assert "Survivorship warning" in without_red
