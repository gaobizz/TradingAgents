"""Transcript miner: extract stated trading heuristics from public videos.

Ross Cameron narrates his own decision rules across thousands of public
recap videos — why he took or skipped a trade, what made news "good",
when he stopped for the day. This pipeline turns that spoken corpus into
a structured rule catalog that feeds the catalyst grader's taxonomy and
proposes new mechanical vetoes for the engine.

Pipeline: load transcripts → chunk → LLM-extract *explicitly stated*
rules (verbatim quote required, no inference) → dedupe/merge → emit a
markdown report + machine-readable JSON.

Transcript sources (choose one):
- ``--transcript-dir`` — a directory of ``.txt`` (filename = video id) or
  ``.json`` files (``{"video_id", "title", "text"}``), e.g. produced by
  ``yt-dlp --write-auto-sub``. Most robust; keeps fetching under the
  user's control and YouTube ToS compliance on the user's side.
- ``--videos id1,id2`` — fetches captions via the optional
  ``youtube-transcript-api`` package (``pip install youtube-transcript-api``).

Bias warning (from docs/research/why-retail-traders-lose.md): mine
red-day/loss recaps too, not only winning days — rules extracted from a
survivor's highlight reel inherit the survivorship bias the research
documents. The extractor tags rules that come from loss discussions so
the report shows the balance.

Usage:
    python -m tradingagents.strategies.ross_cameron.transcripts \
        --transcript-dir ./transcripts --out mined_rules.md --json mined_rules.json
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

CATEGORIES = (
    "stock_selection",
    "catalyst_quality",
    "entry_tactics",
    "exit_tactics",
    "risk_management",
    "psychology",
    "red_flags",
    "market_regime",
    "other",
)

EXTRACTION_PROMPT = """You are extracting a day trader's EXPLICITLY STATED rules from a video transcript.

Rules for extraction:
- Only include heuristics the speaker states as a rule, habit, or lesson ("I only trade...",
  "I never...", "the mistake I made was...", "what I look for is..."). Do NOT infer rules he
  doesn't state. Do NOT include generic filler or promotion.
- Each item needs a short imperative rule, its category, and a short VERBATIM quote from the
  transcript supporting it.
- Set "red_day": true if the surrounding discussion is about a loss, losing day, or mistake.
- Categories: {categories}

Transcript chunk (video: {video_id}):
---
{chunk}
---

Respond with ONLY a JSON array (possibly empty):
[{{"rule": "...", "category": "...", "quote": "...", "red_day": false}}]"""


@dataclass
class Transcript:
    video_id: str
    text: str
    title: str = ""


@dataclass
class MinedRule:
    rule: str
    category: str
    quote: str
    source_video: str
    red_day: bool = False
    occurrences: int = 1
    sources: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            self.category = "other"
        if not self.sources:
            self.sources = [self.source_video]


# ---------------------------------------------------------------------------
# Transcript loading
# ---------------------------------------------------------------------------
def load_transcript_dir(path: str | Path) -> list[Transcript]:
    """Load ``.txt`` (filename = video id) and ``.json`` transcripts from a dir."""
    directory = Path(path)
    transcripts: list[Transcript] = []
    for file in sorted(directory.glob("*.txt")):
        text = file.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            transcripts.append(Transcript(video_id=file.stem, text=text))
    for file in sorted(directory.glob("*.json")):
        payload = json.loads(file.read_text(encoding="utf-8", errors="replace"))
        text = str(payload.get("text", "")).strip()
        if text:
            transcripts.append(
                Transcript(
                    video_id=str(payload.get("video_id", file.stem)),
                    text=text,
                    title=str(payload.get("title", "")),
                )
            )
    return transcripts


def fetch_youtube_transcripts(video_ids: list[str], languages=("en",)) -> list[Transcript]:
    """Fetch captions for public videos via the optional youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "youtube-transcript-api is not installed; either `pip install "
            "youtube-transcript-api` or supply --transcript-dir with files "
            "you fetched yourself (e.g. via yt-dlp)."
        ) from exc

    transcripts = []
    for video_id in video_ids:
        entries = YouTubeTranscriptApi().fetch(video_id, languages=list(languages))
        text = " ".join(getattr(e, "text", "") or "" for e in entries)
        transcripts.append(Transcript(video_id=video_id, text=text))
    return transcripts


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------
def chunk_text(text: str, size: int = 8000, overlap: int = 400) -> list[str]:
    """Split on whitespace boundaries into ~size-char chunks with overlap."""
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _parse_rules(raw: str, video_id: str) -> list[MinedRule]:
    """Parse the LLM's JSON array; malformed output yields no rules, not a crash."""
    try:
        start, end = raw.index("["), raw.rindex("]") + 1
        items = json.loads(raw[start:end])
    except (ValueError, json.JSONDecodeError):
        return []
    rules = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("rule", "")).strip():
            continue
        rules.append(
            MinedRule(
                rule=str(item["rule"]).strip(),
                category=str(item.get("category", "other")).strip(),
                quote=str(item.get("quote", "")).strip(),
                source_video=video_id,
                red_day=bool(item.get("red_day", False)),
            )
        )
    return rules


def mine_transcripts(
    transcripts: list[Transcript],
    llm,
    max_chunks_per_video: int | None = None,
) -> list[MinedRule]:
    """Run LLM extraction over every chunk of every transcript.

    ``llm`` is duck-typed on langchain's ``.invoke(str)`` (the response's
    ``.content`` is used when present). A failed call skips that chunk —
    mining is best-effort by design.
    """
    rules: list[MinedRule] = []
    for transcript in transcripts:
        chunks = chunk_text(transcript.text)
        if max_chunks_per_video is not None:
            chunks = chunks[:max_chunks_per_video]
        for chunk in chunks:
            prompt = EXTRACTION_PROMPT.format(
                categories=", ".join(CATEGORIES), video_id=transcript.video_id, chunk=chunk
            )
            try:
                response = llm.invoke(prompt)
            except Exception:
                continue
            text = getattr(response, "content", response)
            if not isinstance(text, str):
                text = str(text)
            rules.extend(_parse_rules(text, transcript.video_id))
    return dedupe_rules(rules)


_NORMALIZE = re.compile(r"[^a-z0-9 ]+")


def _normalize(rule_text: str) -> str:
    return _NORMALIZE.sub("", rule_text.casefold()).strip()


def dedupe_rules(rules: list[MinedRule]) -> list[MinedRule]:
    """Merge near-identical rules; occurrence counts become evidence weight."""
    merged: dict[str, MinedRule] = {}
    for rule in rules:
        key = _normalize(rule.rule)
        if not key:
            continue
        if key in merged:
            existing = merged[key]
            existing.occurrences += 1
            existing.red_day = existing.red_day or rule.red_day
            if rule.source_video not in existing.sources:
                existing.sources.append(rule.source_video)
        else:
            merged[key] = rule
    return sorted(merged.values(), key=lambda r: (-r.occurrences, r.category, r.rule))


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
def rules_to_markdown(rules: list[MinedRule]) -> str:
    red_day_count = sum(1 for r in rules if r.red_day)
    lines = [
        "# Mined Trading Rules (transcript extraction)",
        "",
        f"{len(rules)} distinct rules; {red_day_count} sourced from loss/red-day discussions.",
        "Rules are the speaker's stated heuristics, not verified edge — candidate inputs for",
        "the catalyst taxonomy (`catalyst.py`) and engine vetoes, pending replay validation.",
        "",
    ]
    if rules and red_day_count == 0:
        lines.insert(3, "")
        lines.insert(
            4,
            "> **Survivorship warning:** no rules came from loss discussions — mine red-day "
            "recaps before trusting this catalog.",
        )
    for category in CATEGORIES:
        in_category = [r for r in rules if r.category == category]
        if not in_category:
            continue
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        for rule in in_category:
            marker = " 🔻(red-day)" if rule.red_day else ""
            evidence = f" — seen {rule.occurrences}×" if rule.occurrences > 1 else ""
            lines.append(f"- **{rule.rule}**{marker}{evidence}")
            if rule.quote:
                lines.append(f'  > "{rule.quote}" — `{", ".join(rule.sources)}`')
        lines.append("")
    return "\n".join(lines)


def rules_to_json(rules: list[MinedRule]) -> str:
    return json.dumps([asdict(r) for r in rules], indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _build_llm(provider: str, model: str):  # pragma: no cover - thin glue
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=0)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(model=model, temperature=0)
    raise ValueError(f"unsupported provider: {provider}")


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - thin glue
    parser = argparse.ArgumentParser(description="Mine stated trading rules from video transcripts")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--transcript-dir", help="directory of .txt/.json transcripts")
    source.add_argument("--videos", help="comma-separated YouTube video ids")
    parser.add_argument("--out", default="mined_rules.md", help="markdown report path")
    parser.add_argument("--json", dest="json_out", default=None, help="JSON output path")
    parser.add_argument("--provider", default="openai", choices=("openai", "anthropic"))
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--max-chunks", type=int, default=None, help="cap chunks per video (cost control)")
    args = parser.parse_args(argv)

    if args.transcript_dir:
        transcripts = load_transcript_dir(args.transcript_dir)
    else:
        transcripts = fetch_youtube_transcripts(args.videos.split(","))
    if not transcripts:
        print("no transcripts found")
        return 1

    llm = _build_llm(args.provider, args.model)
    rules = mine_transcripts(transcripts, llm, max_chunks_per_video=args.max_chunks)

    Path(args.out).write_text(rules_to_markdown(rules), encoding="utf-8")
    print(f"{len(rules)} rules → {args.out}")
    if args.json_out:
        Path(args.json_out).write_text(rules_to_json(rules), encoding="utf-8")
        print(f"json → {args.json_out}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
