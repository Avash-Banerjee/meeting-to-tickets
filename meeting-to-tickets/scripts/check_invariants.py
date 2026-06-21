"""Structural and rigor checks for the meeting-to-tickets pipeline.

Phase 1 of this file covers normalized.md. Subsequent tasks add qa.md,
clusters.md, and ticket markdown files.
"""
from __future__ import annotations

import dataclasses
import pathlib
import re
import sys
from typing import List

import yaml


REQUIRED_NORMALIZED_KEYS = {"meeting_slug", "date", "participants", "chunks", "format_warning"}


@dataclasses.dataclass(frozen=True)
class Violation:
    path: pathlib.Path
    message: str


def _split_frontmatter(text: str) -> tuple[dict | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    raw = text[4:end]
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None, text
    if not isinstance(data, dict):
        return None, text
    return data, text[end + 5 :]


def check_normalized(path: pathlib.Path) -> List[Violation]:
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)
    violations: list[Violation] = []
    if frontmatter is None:
        violations.append(Violation(path, "normalized.md has no parseable YAML frontmatter"))
        return violations

    missing = REQUIRED_NORMALIZED_KEYS - set(frontmatter.keys())
    for key in sorted(missing):
        violations.append(Violation(path, f"normalized.md frontmatter missing required key: {key}"))

    chunks = frontmatter.get("chunks")
    if not isinstance(chunks, int):
        violations.append(Violation(path, f"normalized.md `chunks` must be an integer, got {chunks!r}"))
    elif chunks > 1:
        markers = body.count("<!-- chunk ")
        if markers != chunks:
            violations.append(
                Violation(path, f"normalized.md declares chunks={chunks} but has {markers} chunk markers")
            )

    return violations


REQUIRED_QA_KEYS = {"source", "chunks_processed", "total_qa", "dropped"}


_QA_HEADER_RE = re.compile(r"^### Q\d+ — .+\(lens: .+\)$", re.MULTILINE)


def _split_qa_blocks(body: str) -> list[str]:
    headers = list(_QA_HEADER_RE.finditer(body))
    blocks: list[str] = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        blocks.append(body[start:end])
    return blocks


def check_qa(path: pathlib.Path) -> List[Violation]:
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)
    violations: list[Violation] = []
    if frontmatter is None:
        violations.append(Violation(path, "qa.md has no parseable YAML frontmatter"))
        return violations

    missing = REQUIRED_QA_KEYS - set(frontmatter.keys())
    for key in sorted(missing):
        violations.append(Violation(path, f"qa.md frontmatter missing required key: {key}"))

    # split off the Dropped section before scanning Q&A blocks
    dropped_idx = body.find("\n## Dropped")
    qa_body = body[:dropped_idx] if dropped_idx != -1 else body
    dropped_body = body[dropped_idx:] if dropped_idx != -1 else ""

    blocks = _split_qa_blocks(qa_body)
    for block in blocks:
        header_match = _QA_HEADER_RE.search(block)
        qa_id = header_match.group(0).split("—")[0].strip().split()[-1] if header_match else "?"
        if "**Quotes:**" not in block:
            violations.append(Violation(path, f"qa.md {qa_id}: missing Quotes block"))
            continue
        quotes_section = block.split("**Quotes:**", 1)[1]
        quote_lines = [ln for ln in quotes_section.splitlines() if ln.strip().startswith("- ")]
        if not quote_lines:
            violations.append(Violation(path, f"qa.md {qa_id}: Quotes block has zero quotes"))

    for line in dropped_body.splitlines():
        s = line.strip()
        if not s.startswith("- Q "):
            continue
        if " — " not in s:
            violations.append(Violation(path, f"qa.md dropped entry missing reason: {s}"))

    return violations


REQUIRED_CLUSTERS_KEYS = {"total_clusters", "unclustered_qa"}
REQUIRED_TICKET_KEYS = {"type", "priority_hint", "source_meeting", "cluster_id"}
ALLOWED_TYPES = {"feature", "task", "problem"}
ALLOWED_PRIORITIES = {"low", "medium", "high"}


_CLUSTER_HEADER_RE = re.compile(r"^## C\d+ — .+\(suggested type: ([a-z]+)\)$", re.MULTILINE)


def check_clusters(path: pathlib.Path) -> List[Violation]:
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)
    violations: list[Violation] = []
    if frontmatter is None:
        violations.append(Violation(path, "clusters.md has no parseable YAML frontmatter"))
        return violations

    missing = REQUIRED_CLUSTERS_KEYS - set(frontmatter.keys())
    for key in sorted(missing):
        violations.append(Violation(path, f"clusters.md frontmatter missing required key: {key}"))

    for m in _CLUSTER_HEADER_RE.finditer(body):
        t = m.group(1)
        if t not in ALLOWED_TYPES:
            violations.append(
                Violation(path, f"clusters.md cluster has invalid suggested type: {t!r}")
            )

    return violations


def check_ticket(path: pathlib.Path) -> List[Violation]:
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)
    violations: list[Violation] = []
    if frontmatter is None:
        violations.append(Violation(path, "ticket has no parseable YAML frontmatter"))
        return violations

    missing = REQUIRED_TICKET_KEYS - set(frontmatter.keys())
    for key in sorted(missing):
        violations.append(Violation(path, f"ticket frontmatter missing required key: {key}"))

    t = frontmatter.get("type")
    if t not in ALLOWED_TYPES:
        violations.append(Violation(path, f"ticket has invalid type: {t!r}"))

    pri = frontmatter.get("priority_hint")
    if pri not in ALLOWED_PRIORITIES:
        violations.append(Violation(path, f"ticket has invalid priority_hint: {pri!r}"))

    if "## Description" not in body:
        violations.append(Violation(path, "ticket missing Description section"))
    else:
        description = body.split("## Description", 1)[1]
        description = description.split("## ", 1)[0]
        if not re.search(r"(?m)^>\s+\S", description):
            violations.append(
                Violation(path, "ticket Description has no verbatim quote (no blockquote lines)")
            )

    if "## Acceptance criteria" not in body:
        violations.append(Violation(path, "ticket missing Acceptance criteria section"))

    return violations


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_invariants.py <meeting_folder>", file=sys.stderr)
        return 2
    folder = pathlib.Path(argv[1])
    violations: list[Violation] = []
    if (folder / "normalized.md").exists():
        violations.extend(check_normalized(folder / "normalized.md"))
    if (folder / "qa.md").exists():
        violations.extend(check_qa(folder / "qa.md"))
    if (folder / "clusters.md").exists():
        violations.extend(check_clusters(folder / "clusters.md"))
    tickets_dir = folder / "tickets"
    if tickets_dir.is_dir():
        for ticket in sorted(tickets_dir.glob("*.md")):
            violations.extend(check_ticket(ticket))
    for v in violations:
        print(f"{v.path}: {v.message}", file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
