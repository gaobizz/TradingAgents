"""Catalyst grader: "catalyst feel" as an explainable, graded score.

Upgrades the Five Pillars news check from a boolean to a letter grade
(A best … F worst / veto). The taxonomy encodes the catalyst hierarchy
Cameron states across Warrior Trading materials and recap videos (see
docs/research/ross-cameron-strategy.md and the transcript miner in
``transcripts.py``, whose output is used to refine these patterns):

- A: binary, high-magnitude events that reprice a company overnight —
  FDA approval/clearance, phase-3 success, buyout/merger, dollar-quantified
  major contracts.
- B: strong but less binary — earnings beats/raised guidance, positive
  early-phase data, uplisting, granted patents, megacap partnerships.
- C: real but soft — LOIs/MOUs, product launches, analyst upgrades,
  generic partnerships.
- D: fluff that moves nothing durable — conference appearances, IR
  engagements, unclassifiable PR.
- F/veto: anti-catalysts for longs — offerings/dilution, reverse splits,
  going-concern/delisting. A veto poisons the whole day for that symbol
  regardless of any good headline (the classic "good news + offering
  priced into the spike" trap), and surfaces as a dilution flag (G6).

Modifiers (score, not vibes): staleness decays the grade (fresh overnight
news is the pillar; 2-day-old news is not a gap catalyst), dollar/percent
quantification and corroborating headlines nudge it up. Every output
carries human-readable ``reasons`` so an unattended decision is auditable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

GRADES = ("F", "D", "C", "B", "A")
GRADE_RANK = {g: i for i, g in enumerate(GRADES)}

VETO_CATEGORIES = ("dilution_offering", "reverse_split", "going_concern")

# (category, base score, compiled pattern) — first match wins per headline.
# Vetoes are checked before everything else.
_VETO_PATTERNS = [
    (
        "dilution_offering",
        re.compile(
            r"offering|registered direct|at-the-market|\bATM (program|agreement|facility)"
            r"|S-[13] |424B|warrant|convertible note|dilut|securities purchase agreement"
            r"|capital raise|unit purchase",
            re.I,
        ),
    ),
    ("reverse_split", re.compile(r"reverse (stock )?split", re.I)),
    (
        "going_concern",
        re.compile(r"going concern|delisting|non-?compliance with (nasdaq|nyse)", re.I),
    ),
]

_MEGACAPS = (
    r"google|alphabet|amazon|microsoft|nvidia|apple|meta\b|tesla|openai"
    r"|pfizer|merck|eli lilly|novartis|johnson & johnson|walmart|oracle"
)

_CATEGORY_PATTERNS = [
    # --- Tier A (base 90)
    ("fda_approval", 90, re.compile(
        r"fda (grants |)approv|marketing authorization|510\(k\) clearance"
        r"|breakthrough (therapy|device) designation|emergency use authorization", re.I)),
    ("phase3_success", 90, re.compile(
        r"phase (3|III).{0,40}(positive|success|met|achiev)|primary endpoint (was |)met", re.I)),
    ("acquisition_merger", 90, re.compile(
        r"\b(to be acquired|acquisition|merger agreement|buyout|takeover|tender offer)\b", re.I)),
    ("major_contract", 90, re.compile(
        r"\$\s?\d+(\.\d+)?\s?(million|billion).{0,40}(contract|order|award|purchase)"
        r"|department of defense|government contract", re.I)),
    # --- Tier B (base 75)
    ("earnings_beat", 75, re.compile(
        r"beats (estimates|expectations)|record (revenue|quarter|sales)"
        r"|raises (full.year |)guidance|revenue (up|grows|increases) \d+", re.I)),
    ("clinical_positive", 75, re.compile(
        r"phase (1|2|I|II).{0,40}(positive|encouraging|met)|positive (topline|interim) (data|results)", re.I)),
    ("uplisting", 75, re.compile(r"uplist|approved for listing on (nasdaq|nyse)", re.I)),
    ("patent_granted", 75, re.compile(r"patent (granted|issued|awarded|allowance)", re.I)),
    ("megacap_partnership", 75, re.compile(
        rf"(partnership|collaboration|agreement) with.{{0,30}}({_MEGACAPS})", re.I)),
    # --- Tier C (base 60)
    ("loi_mou", 60, re.compile(r"letter of intent|memorandum of understanding|\bLOI\b|\bMOU\b", re.I)),
    ("product_launch", 60, re.compile(r"launch(es|ed)?\b|unveils|introduces", re.I)),
    ("analyst_upgrade", 60, re.compile(r"upgraded? to (buy|overweight|outperform)|price target (raised|increased)", re.I)),
    ("generic_partnership", 60, re.compile(r"partnership|collaboration|strategic agreement", re.I)),
    # --- Tier D (base 45)
    ("conference_pr", 45, re.compile(
        r"to (present|attend|participate)|conference|webcast|fireside chat"
        r"|investor relations|engages|retains", re.I)),
]

_FALLBACK = ("unclassified_pr", 45)

_QUANTIFIED = re.compile(r"[$€]\s?\d|\d+(\.\d+)?\s?%|\b(million|billion)\b", re.I)

FRESH_HOURS = 18.0        # overnight/pre-market window: full weight
STALE_HOURS = 48.0        # beyond this the "news" is not a gap catalyst
STALE_PENALTY_1 = 10.0    # 18-48h old
STALE_PENALTY_2 = 25.0    # older than 48h
QUANTIFIED_BONUS = 5.0
CORROBORATION_BONUS = 5.0  # 2+ headlines in the window


@dataclass(frozen=True)
class CatalystGrade:
    grade: str                    # "A".."F"
    score: float
    category: str
    headline: str
    reasons: tuple[str, ...] = ()

    def at_least(self, minimum: str) -> bool:
        return GRADE_RANK[self.grade] >= GRADE_RANK[minimum]


def meets_minimum_grade(grade: str, minimum: str) -> bool:
    return GRADE_RANK.get(grade, -1) >= GRADE_RANK.get(minimum, 99)


def _score_to_grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _classify(headline: str) -> tuple[str, float]:
    for category, pattern in _VETO_PATTERNS:
        if pattern.search(headline):
            return category, 0.0
    for category, base, pattern in _CATEGORY_PATTERNS:
        if pattern.search(headline):
            return category, base
    return _FALLBACK


def grade_headline(
    headline: str,
    published: Optional[datetime] = None,
    scan_time: Optional[datetime] = None,
) -> CatalystGrade:
    """Grade a single headline (see module docstring for the rubric)."""
    category, score = _classify(headline)
    reasons = [f"category={category}"]

    if category in VETO_CATEGORIES:
        return CatalystGrade("F", 0.0, category, headline, tuple(reasons + ["veto"]))

    if published is not None and scan_time is not None:
        age_hours = (scan_time - published).total_seconds() / 3600.0
        if age_hours > STALE_HOURS:
            score -= STALE_PENALTY_2
            reasons.append(f"stale ({age_hours:.0f}h old)")
        elif age_hours > FRESH_HOURS:
            score -= STALE_PENALTY_1
            reasons.append(f"aging ({age_hours:.0f}h old)")
        else:
            reasons.append("fresh")
    else:
        reasons.append("recency unknown")

    if _QUANTIFIED.search(headline):
        score += QUANTIFIED_BONUS
        reasons.append("quantified")

    return CatalystGrade(_score_to_grade(score), score, category, headline, tuple(reasons))


def grade_catalyst(
    headlines: list[tuple[str, Optional[datetime]]],
    scan_time: Optional[datetime] = None,
) -> CatalystGrade:
    """Grade a symbol's news window: vetoes dominate, else best headline wins."""
    if not headlines:
        return CatalystGrade("F", 0.0, "no_news", "", ("no headlines in window",))

    graded = [grade_headline(title, published, scan_time) for title, published in headlines]

    vetoes = [g for g in graded if g.category in VETO_CATEGORIES]
    if vetoes:
        veto = vetoes[0]
        return CatalystGrade(
            "F", 0.0, veto.category, veto.headline,
            veto.reasons + ("veto poisons all other headlines in window",),
        )

    best = max(graded, key=lambda g: g.score)
    if len(graded) >= 2:
        score = best.score + CORROBORATION_BONUS
        return CatalystGrade(
            _score_to_grade(score), score, best.category, best.headline,
            best.reasons + (f"corroborated by {len(graded) - 1} more headline(s)",),
        )
    return best


# ---------------------------------------------------------------------------
# Optional LLM grader (duck-typed on langchain's ``.invoke`` interface)
# ---------------------------------------------------------------------------
_LLM_RUBRIC = """You grade news catalysts for a small-cap momentum day-trading scanner.
Grade the catalyst quality of the headlines below for symbol momentum TODAY.

Rubric:
- A: binary, high-magnitude overnight repricing (FDA approval/clearance, phase-3 success,
  buyout/merger, $-quantified major contract)
- B: strong but less binary (earnings beat / raised guidance, positive early-phase data,
  uplisting, granted patent, megacap partnership)
- C: real but soft (LOI/MOU, product launch, analyst upgrade, generic partnership)
- D: fluff (conferences, IR engagements, vague or unclassifiable PR)
- F: no catalyst, stale news, or an anti-catalyst VETO (offering/dilution, reverse split,
  going concern/delisting). Any dilution headline in the set forces F.

Headlines (with age at scan time):
{headlines}

Respond with ONLY a JSON object: {{"grade": "A|B|C|D|F", "category": "<short_slug>", "reason": "<one sentence>"}}"""


def make_llm_grader(model, fallback: Callable = grade_catalyst) -> Callable:
    """Wrap an ``.invoke``-style chat model as a grader with deterministic fallback.

    The returned callable has the same signature as :func:`grade_catalyst`.
    Any model error or unparseable response falls back to the deterministic
    grader — an unattended scan must never die on a flaky LLM call.
    """
    import json as json_module

    def _grader(headlines, scan_time=None):
        deterministic = fallback(headlines, scan_time)
        # The deterministic vetoes are hard guardrails (G6) — an LLM may
        # downgrade but never override a veto or absent news, so skip the call.
        if not headlines or deterministic.category in VETO_CATEGORIES:
            return deterministic
        try:
            lines = []
            for title, published in headlines:
                if published is not None and scan_time is not None:
                    age = (scan_time - published).total_seconds() / 3600.0
                    lines.append(f"- [{age:.0f}h old] {title}")
                else:
                    lines.append(f"- [age unknown] {title}")
            response = model.invoke(_LLM_RUBRIC.format(headlines="\n".join(lines)))
            text = getattr(response, "content", response)
            if not isinstance(text, str):
                text = str(text)
            payload = json_module.loads(text[text.index("{") : text.rindex("}") + 1])
            grade = str(payload["grade"]).strip().upper()
            if grade not in GRADE_RANK:
                return deterministic
            return CatalystGrade(
                grade=grade,
                score=float({v: k for k, v in enumerate(GRADES)}.get(grade, 0)) * 25.0,
                category=str(payload.get("category", "llm")),
                headline=headlines[0][0],
                reasons=("llm: " + str(payload.get("reason", "")).strip(),),
            )
        except Exception:
            return deterministic

    return _grader
