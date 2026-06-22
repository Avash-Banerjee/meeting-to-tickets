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


REQUIRED_NORMALIZED_KEYS = {"meeting_slug", "participants", "chunks", "format_warning"}


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


# qa.md has two valid schemas:
#  - legacy direct-extractor output: chunks_processed + total_qa
#  - post-reconciler output: chunks_merged + qa_before_dedup + qa_after_dedup + walk_backs_resolved
# Both must declare `source` and `dropped`. The schema is auto-detected by
# presence of `chunks_merged` in the frontmatter.
REQUIRED_QA_KEYS_BASE = {"source", "dropped"}
REQUIRED_QA_KEYS_LEGACY = {"chunks_processed", "total_qa"}
REQUIRED_QA_KEYS_RECONCILED = {"chunks_merged", "qa_before_dedup", "qa_after_dedup", "walk_backs_resolved"}


# Allow optional trailing annotation like `[MERGED across chunks 1 and 2]` or
# `[walk-back resolved intra-chunk]` after the lens parens.
_QA_HEADER_RE = re.compile(r"^### Q\d+ — .+\(lens: [^)]+\)", re.MULTILINE)


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

    is_reconciled = "chunks_merged" in frontmatter
    required = REQUIRED_QA_KEYS_BASE | (
        REQUIRED_QA_KEYS_RECONCILED if is_reconciled else REQUIRED_QA_KEYS_LEGACY
    )
    missing = required - set(frontmatter.keys())
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

    dropped_entries = []
    for line in dropped_body.splitlines():
        s = line.strip()
        if not s.startswith("- Q "):
            continue
        dropped_entries.append(s)
        if " — " not in s:
            violations.append(Violation(path, f"qa.md dropped entry missing reason: {s}"))

    # Count cross-check: legacy uses `total_qa`, reconciled uses `qa_after_dedup`.
    declared_total = frontmatter.get("qa_after_dedup") if is_reconciled else frontmatter.get("total_qa")
    total_key = "qa_after_dedup" if is_reconciled else "total_qa"
    if isinstance(declared_total, int) and declared_total != len(blocks):
        violations.append(
            Violation(
                path,
                f"qa.md frontmatter {total_key}={declared_total} does not match {len(blocks)} Q&A blocks found",
            )
        )

    declared_dropped = frontmatter.get("dropped")
    if isinstance(declared_dropped, int) and declared_dropped != len(dropped_entries):
        violations.append(
            Violation(
                path,
                f"qa.md frontmatter dropped count={declared_dropped} does not match {len(dropped_entries)} Dropped entries found",
            )
        )

    # A reconciled qa.md must not contain a "## Walk-back coverage gaps"
    # section. If it does, the reconciler couldn't cover one or more
    # outline-declared walk-backs and the checker flags each.
    if "## Walk-back coverage gaps" in body:
        gap_section = body.split("## Walk-back coverage gaps", 1)[1]
        for line in gap_section.splitlines():
            s = line.strip()
            if s.startswith("- "):
                violations.append(
                    Violation(path, f"qa.md reconciler flagged uncovered walk-back: {s[2:]}")
                )

    return violations


def _normalize_for_provenance(text: str) -> str:
    """Collapse whitespace and unify quote variants for substring comparison."""
    # Unify curly quotes -> straight; em/en dashes pass through unchanged.
    table = {
        ord("“"): '"',  # left double curly
        ord("”"): '"',  # right double curly
        ord("‘"): "'",  # left single curly
        ord("’"): "'",  # right single curly
    }
    text = text.translate(table)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_quoted_spans(line: str) -> list[str]:
    """Return the verbatim-quoted text within a single line.

    Handles the common ticket/qa-md form:
        - `Speaker: "quoted text"`
        - `> Speaker: "quoted text"`
        - `Speaker: "quoted text with \\"inner escaped\\" quotes"`
    Curly double quotes are normalized to straight before scanning. If
    the body after the speaker prefix is wrapped in straight `"..."`,
    the outer pair is treated as the delimiter (so inner `"` or `\\"`
    are preserved as content). If no outer pair is found, the entire
    post-prefix body is returned as the span — letting the substring
    check still catch fabricated text.
    """
    body = line.translate({
        ord("“"): '"',
        ord("”"): '"',
    })
    # Strip leading blockquote / bullet markers.
    body = re.sub(r"^>\s+", "", body)
    body = re.sub(r"^-\s+", "", body)
    # Drop the speaker prefix (anything up to the first `: `).
    body = re.sub(r"^[^:]+:\s*", "", body)
    body = body.strip()
    if not body:
        return []
    # Outer-quoted form: trim the outer `"..."` and unescape `\"` -> `"`.
    if len(body) >= 2 and body[0] == '"' and body[-1] == '"':
        inner = body[1:-1]
        inner = inner.replace('\\"', '"')
        return [inner]
    return [body]


def _collect_normalized_utterances(normalized_path: pathlib.Path) -> str:
    """Return a single normalized string of all utterance text in normalized.md.

    Strips YAML frontmatter and HTML comments (e.g. `<!-- chunk 1/1 -->`,
    `<!-- t=00:42 -->`), then collapses whitespace. Quote provenance is
    checked by substring against this string.
    """
    text = normalized_path.read_text()
    _, body = _split_frontmatter(text)
    # Remove HTML comments (chunk markers and timestamp markers).
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.DOTALL)
    return _normalize_for_provenance(body)


_BLOCKQUOTE_RE = re.compile(r"^>\s+(.+)$", re.MULTILINE)


def check_quote_provenance(meeting_folder: pathlib.Path) -> List[Violation]:
    """Verify every blockquote in tickets/*.md and every Quotes-block line in
    qa.md is a substring of the normalized.md transcript.
    """
    violations: list[Violation] = []
    normalized_path = meeting_folder / "normalized.md"
    if not normalized_path.exists():
        return violations
    haystack = _collect_normalized_utterances(normalized_path)

    # ---- tickets ----
    tickets_dir = meeting_folder / "tickets"
    if tickets_dir.is_dir():
        for ticket_path in sorted(tickets_dir.glob("*.md")):
            ticket_text = ticket_path.read_text()
            _, ticket_body = _split_frontmatter(ticket_text)
            if "## Description" not in ticket_body:
                continue
            description = ticket_body.split("## Description", 1)[1]
            description = description.split("\n## ", 1)[0]
            for m in _BLOCKQUOTE_RE.finditer(description):
                # The matched group is the line content after `> `.
                spans = _extract_quoted_spans(m.group(1))
                for span in spans:
                    needle = _normalize_for_provenance(span)
                    if needle and needle not in haystack:
                        violations.append(
                            Violation(
                                ticket_path,
                                f"ticket Description quote not found in normalized.md: {span!r}",
                            )
                        )

    # ---- qa.md ----
    qa_path = meeting_folder / "qa.md"
    if qa_path.exists():
        qa_text = qa_path.read_text()
        _, qa_body = _split_frontmatter(qa_text)
        # Trim the Dropped section so its proposed-Q text doesn't get pulled
        # into the last Q-block's Quotes scan.
        dropped_idx = qa_body.find("\n## Dropped")
        scan_body = qa_body[:dropped_idx] if dropped_idx != -1 else qa_body
        # Walk each Q-block; for each, scan the Quotes section.
        for block in _split_qa_blocks(scan_body):
            header_match = _QA_HEADER_RE.search(block)
            qa_id = (
                header_match.group(0).split("—")[0].strip().split()[-1]
                if header_match
                else "?"
            )
            if "**Quotes:**" not in block:
                continue
            quotes_section = block.split("**Quotes:**", 1)[1]
            # Stop at the next bold-label or end of block.
            quotes_section = re.split(r"\n\*\*[A-Z]", quotes_section, 1)[0]
            for ln in quotes_section.splitlines():
                s = ln.strip()
                if not s.startswith("- "):
                    continue
                spans = _extract_quoted_spans(s)
                for span in spans:
                    needle = _normalize_for_provenance(span)
                    if needle and needle not in haystack:
                        violations.append(
                            Violation(
                                qa_path,
                                f"qa.md {qa_id}: quote not found in normalized.md: {span!r}",
                            )
                        )

    return violations


REQUIRED_OUTLINE_KEYS = {
    "source",
    "chunks_covered",
    "themes",
    "entities",
    "costs",
    "commitments",
    "walk_backs",
}
OUTLINE_REQUIRED_SECTIONS = ["## Themes", "## Named entities", "## Walk-backs"]


def check_outline(path: pathlib.Path) -> List[Violation]:
    """Validate the outline.md produced by `meeting-outline`. Required keys,
    presence of the three load-bearing sections, and integer counts that
    match the bullet counts inside the sections."""
    text = path.read_text()
    frontmatter, body = _split_frontmatter(text)
    violations: list[Violation] = []
    if frontmatter is None:
        violations.append(Violation(path, "outline.md has no parseable YAML frontmatter"))
        return violations

    missing = REQUIRED_OUTLINE_KEYS - set(frontmatter.keys())
    for key in sorted(missing):
        violations.append(Violation(path, f"outline.md frontmatter missing required key: {key}"))

    for required_section in OUTLINE_REQUIRED_SECTIONS:
        if required_section not in body:
            violations.append(
                Violation(path, f"outline.md missing required section: {required_section}")
            )

    # Cross-check declared counts vs actual bullet counts per section.
    def _bullet_count(section_marker: str) -> int | None:
        if section_marker not in body:
            return None
        rest = body.split(section_marker, 1)[1]
        # Stop at next H2.
        next_h2 = re.search(r"^## ", rest, re.MULTILINE)
        chunk = rest[: next_h2.start()] if next_h2 else rest
        return sum(1 for ln in chunk.splitlines() if ln.strip().startswith("- "))

    pairs = [
        ("themes", "## Themes"),
        ("entities", "## Named entities"),
        ("costs", "## Named costs"),
        ("commitments", "## Commitments"),
        ("walk_backs", "## Walk-backs"),
    ]
    for key, marker in pairs:
        declared = frontmatter.get(key)
        actual = _bullet_count(marker)
        if isinstance(declared, int) and actual is not None and declared != actual:
            violations.append(
                Violation(
                    path,
                    f"outline.md frontmatter {key}={declared} does not match {actual} bullets under {marker}",
                )
            )

    return violations


def check_qa_chunks_present(meeting_folder: pathlib.Path) -> List[Violation]:
    """When outline.md exists (new architecture), require qa-chunks/qa-N.md
    for every chunk declared in normalized.md."""
    outline_path = meeting_folder / "outline.md"
    normalized_path = meeting_folder / "normalized.md"
    if not (outline_path.exists() and normalized_path.exists()):
        return []

    norm_fm, _ = _split_frontmatter(normalized_path.read_text())
    if not isinstance(norm_fm, dict):
        return []
    chunk_count = norm_fm.get("chunks")
    if not isinstance(chunk_count, int):
        return []

    qa_chunks_dir = meeting_folder / "qa-chunks"
    violations: list[Violation] = []
    if not qa_chunks_dir.is_dir():
        violations.append(
            Violation(
                meeting_folder,
                f"qa-chunks/ directory missing (normalized.md declares {chunk_count} chunks)",
            )
        )
        return violations

    for i in range(1, chunk_count + 1):
        chunk_qa = qa_chunks_dir / f"qa-{i}.md"
        if not chunk_qa.exists():
            violations.append(
                Violation(meeting_folder, f"qa-chunks/qa-{i}.md missing for chunk {i}")
            )

    return violations


def check_walk_back_coverage(meeting_folder: pathlib.Path) -> List[Violation]:
    """When outline.md declares walk-backs, qa.md's `walk_backs_resolved`
    frontmatter must equal the number declared. The reconciler is expected
    to surface uncovered walk-backs via a `## Walk-back coverage gaps`
    section (which check_qa already flags), so this is the count-level
    second line of defense."""
    outline_path = meeting_folder / "outline.md"
    qa_path = meeting_folder / "qa.md"
    if not (outline_path.exists() and qa_path.exists()):
        return []
    outline_fm, _ = _split_frontmatter(outline_path.read_text())
    qa_fm, _ = _split_frontmatter(qa_path.read_text())
    if not (isinstance(outline_fm, dict) and isinstance(qa_fm, dict)):
        return []
    declared = outline_fm.get("walk_backs")
    resolved = qa_fm.get("walk_backs_resolved")
    if not (isinstance(declared, int) and isinstance(resolved, int)):
        return []
    if declared != resolved:
        return [
            Violation(
                meeting_folder,
                f"outline.md declares {declared} walk-backs but qa.md only resolved {resolved}",
            )
        ]
    return []


_TICKET_SECTION_HEADERS = (
    "## Business goal",
    "## Description",
    "## Acceptance criteria",
    "## Priority hint",
    "## Open questions",
    "## Evidence",
)

_SCAFFOLDING_RE = re.compile(r"\b(?:C\d+|Q\d+|chunk \d+)\b")


def check_no_internal_scaffolding_in_ticket_prose(path: pathlib.Path) -> List[Violation]:
    """Cluster ids, Q-ids, and chunk indices are internal scaffolding — they
    are allowed only in the YAML frontmatter and the `## Evidence` section.
    Flag any occurrence in user-readable prose (Business goal, Description,
    Acceptance criteria, Priority hint, Open questions)."""
    text = path.read_text()
    _, body = _split_frontmatter(text)
    violations: list[Violation] = []

    # Split body into sections at each H2. We only inspect named sections we
    # treat as user-facing; the Evidence section is exempt.
    section_positions: list[tuple[str, int, int]] = []
    matches = list(re.finditer(r"^(## .+)$", body, re.MULTILINE))
    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_positions.append((header, start, end))

    user_facing_headers = {
        "## Business goal",
        "## Description",
        "## Acceptance criteria",
        "## Priority hint",
        "## Open questions",
    }

    for header, start, end in section_positions:
        if header not in user_facing_headers:
            continue
        section_text = body[start:end]
        # Strip blockquote lines (verbatim transcript quotes — these may
        # legitimately contain "Q1" meaning calendar Q1, "C-suite", etc.)
        # before scanning for scaffolding leakage in the drafter's own prose.
        non_quote_lines = "\n".join(
            ln for ln in section_text.splitlines() if not ln.lstrip().startswith(">")
        )
        for m in _SCAFFOLDING_RE.finditer(non_quote_lines):
            token = m.group(0)
            violations.append(
                Violation(
                    path,
                    f"ticket internal scaffolding leaked into {header}: {token!r} "
                    f"(scaffolding allowed only in frontmatter and `## Evidence`)",
                )
            )

    return violations


REQUIRED_DEVREV_KEYS = {"type", "severity", "source_meeting", "source_ticket"}
ALLOWED_DEVREV_TYPES = {"feature_request", "task", "improvement", "bug"}
ALLOWED_DEVREV_SEVERITIES = {"blocker", "high", "medium", "low"}
REQUIRED_DEVREV_SECTIONS = ("## Summary", "## Acceptance criteria", "## Top evidence", "## Source")


def check_devrev_files(meeting_folder: pathlib.Path) -> List[Violation]:
    """Validate the devrev/ sibling files produced by `devrev-compactor`.

    For each devrev/*.md:
    - Frontmatter has required keys with valid enum values.
    - All four required sections are present.
    - There is a corresponding source ticket file referenced by `source_ticket`.
    - The 1:1 mapping holds: every tickets/*.md has a matching devrev/<same-name>
      (only when devrev/ exists at all — if devrev/ doesn't exist, no check fires
      because the stage is optional)."""
    devrev_dir = meeting_folder / "devrev"
    tickets_dir = meeting_folder / "tickets"
    violations: list[Violation] = []
    if not devrev_dir.is_dir():
        return violations

    devrev_files = sorted(p for p in devrev_dir.glob("*.md") if not p.name.endswith(".md.draft"))
    ticket_files = sorted(p for p in tickets_dir.glob("*.md") if not p.name.endswith(".md.draft")) if tickets_dir.is_dir() else []

    # 1:1 name parity check
    devrev_names = {p.name for p in devrev_files}
    ticket_names = {p.name for p in ticket_files}
    for name in ticket_names - devrev_names:
        violations.append(
            Violation(meeting_folder, f"devrev/ missing companion for tickets/{name}")
        )
    for name in devrev_names - ticket_names:
        violations.append(
            Violation(meeting_folder, f"devrev/{name} has no matching tickets/{name}")
        )

    # Per-file structural checks
    for p in devrev_files:
        text = p.read_text()
        frontmatter, body = _split_frontmatter(text)
        if frontmatter is None:
            violations.append(Violation(p, "devrev file has no parseable YAML frontmatter"))
            continue
        missing = REQUIRED_DEVREV_KEYS - set(frontmatter.keys())
        for key in sorted(missing):
            violations.append(Violation(p, f"devrev frontmatter missing required key: {key}"))
        t = frontmatter.get("type")
        if t not in ALLOWED_DEVREV_TYPES:
            violations.append(
                Violation(p, f"devrev frontmatter type={t!r} not in {sorted(ALLOWED_DEVREV_TYPES)}")
            )
        sev = frontmatter.get("severity")
        if sev not in ALLOWED_DEVREV_SEVERITIES:
            violations.append(
                Violation(p, f"devrev frontmatter severity={sev!r} not in {sorted(ALLOWED_DEVREV_SEVERITIES)}")
            )
        for section in REQUIRED_DEVREV_SECTIONS:
            if section not in body:
                violations.append(Violation(p, f"devrev file missing required section: {section}"))

        # source_ticket should reference a real file
        src = frontmatter.get("source_ticket")
        if isinstance(src, str):
            # Resolve relative to the devrev file's directory.
            resolved = (p.parent / src).resolve()
            if not resolved.exists():
                violations.append(
                    Violation(p, f"devrev source_ticket points to nonexistent file: {src}")
                )

    return violations


def check_ticket_cluster_counts(meeting_folder: pathlib.Path) -> List[Violation]:
    """Cross-check ticket count against clusters minus cluster-level drops."""
    violations: list[Violation] = []
    clusters_path = meeting_folder / "clusters.md"
    tickets_dir = meeting_folder / "tickets"
    if not clusters_path.exists():
        return violations
    clusters_text = clusters_path.read_text()
    frontmatter, _ = _split_frontmatter(clusters_text)
    if not isinstance(frontmatter, dict):
        return violations
    total_clusters = frontmatter.get("total_clusters")
    if not isinstance(total_clusters, int):
        return violations

    dropped_clusters = 0
    dropped_path = meeting_folder / "dropped.md"
    if dropped_path.exists():
        for line in dropped_path.read_text().splitlines():
            if re.match(r"^\s*-\s+C\d+", line):
                dropped_clusters += 1

    ticket_files = []
    if tickets_dir.is_dir():
        ticket_files = [
            p
            for p in sorted(tickets_dir.glob("*.md"))
            if not p.name.endswith(".md.draft")
        ]
    expected = total_clusters - dropped_clusters
    actual = len(ticket_files)
    if expected != actual:
        violations.append(
            Violation(
                meeting_folder,
                f"ticket count ({actual}) does not match clusters ({total_clusters}) minus dropped clusters ({dropped_clusters}); expected {expected}",
            )
        )
    return violations


def collect_qa_ids(path: pathlib.Path) -> set[str]:
    """Return the set of Q-ids declared in a qa.md file (e.g. {'Q1', 'Q2'})."""
    if not path.exists():
        return set()
    text = path.read_text()
    _, body = _split_frontmatter(text)
    ids: set[str] = set()
    for m in _QA_HEADER_RE.finditer(body):
        token = m.group(0).split("—")[0].strip().split()[-1]
        ids.add(token)
    return ids


REQUIRED_CLUSTERS_KEYS = {"total_clusters", "unclustered_qa"}
REQUIRED_TICKET_KEYS = {"type", "priority_hint", "source_meeting", "cluster_id"}
ALLOWED_TYPES = {"feature", "task", "problem"}
ALLOWED_PRIORITIES = {"low", "medium", "high"}


_CLUSTER_HEADER_RE = re.compile(r"^## C(\d+) — .+\(suggested type: ([a-z]+)\)$", re.MULTILINE)
_QA_REF_LINE_RE = re.compile(r"^\s*\*\*Q&A:\*\*\s*(.+)$", re.MULTILINE)
_QA_ID_RE = re.compile(r"Q\d+")


def _split_cluster_blocks(body: str) -> list[tuple[str, str]]:
    r"""Return [(cluster_id, block_text), ...] for each `## C\d+` block in body."""
    headers = list(_CLUSTER_HEADER_RE.finditer(body))
    blocks: list[tuple[str, str]] = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(body)
        cluster_id = f"C{m.group(1)}"
        blocks.append((cluster_id, body[start:end]))
    return blocks


def check_clusters(path: pathlib.Path, qa_ids: set[str] | None = None) -> List[Violation]:
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
        t = m.group(2)
        if t not in ALLOWED_TYPES:
            violations.append(
                Violation(path, f"clusters.md cluster has invalid suggested type: {t!r}")
            )

    if qa_ids is not None:
        for cluster_id, block in _split_cluster_blocks(body):
            qa_line_match = _QA_REF_LINE_RE.search(block)
            if qa_line_match is None:
                continue
            referenced = _QA_ID_RE.findall(qa_line_match.group(1))
            for ref in referenced:
                if ref not in qa_ids:
                    violations.append(
                        Violation(
                            path,
                            f"clusters.md {cluster_id} references unknown Q&A id: {ref}",
                        )
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

    if "type" not in missing:
        t = frontmatter.get("type")
        if t not in ALLOWED_TYPES:
            violations.append(Violation(path, f"ticket has invalid type: {t!r}"))

    if "priority_hint" not in missing:
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
    else:
        ac_section = body.split("## Acceptance criteria", 1)[1]
        ac_section = ac_section.split("\n## ", 1)[0]
        ac_lines = [
            ln.strip()
            for ln in ac_section.splitlines()
            if re.match(r"^- \[[ xX]\]", ln.strip())
        ]
        # An AC bullet looks like "- [ ] (inferred) ..." or "- [ ] ..."; strip
        # the checkbox prefix and test whether the remainder begins with
        # "(inferred)".
        def _is_inferred(line: str) -> bool:
            without_box = re.sub(r"^- \[[ xX]\]\s*", "", line)
            return without_box.startswith("(inferred)")

        non_inferred = [ln for ln in ac_lines if not _is_inferred(ln)]
        if non_inferred:
            evidence_section = ""
            if "## Evidence" in body:
                evidence_section = body.split("## Evidence", 1)[1]
                evidence_section = evidence_section.split("\n## ", 1)[0]
            if not re.search(r"Q\d+", evidence_section):
                violations.append(
                    Violation(
                        path,
                        "ticket has non-(inferred) Acceptance criteria but Evidence section does not trace to any Q&A id (Q\\d+)",
                    )
                )

    return violations


ROUND_TRIP_WORD_RATIO_FLOOR = 0.95


def _word_count(text: str) -> int:
    """Count whitespace-separated tokens, ignoring frontmatter, HTML comments,
    and header decoration lines (===, ---, leading metadata before the body)."""
    # Strip YAML frontmatter
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + 5 :]
    # Strip HTML comments (`<!-- ... -->`), including chunk and timestamp markers.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Strip decorative separator lines (===, ---).
    text = re.sub(r"^[=\-]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Strip likely-header lines (Date:, Participants:, Duration:, etc.) at the
    # very start, before the body.
    lines = text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        label_match = re.match(r"^[A-Z][A-Za-z .'-]+:", stripped)
        if label_match and stripped.split(":", 1)[0].strip().lower() in {
            "date",
            "duration",
            "participants",
            "participant",
            "meeting",
            "title",
            "subject",
            "recording",
            "transcript",
            "time",
        }:
            body_start = i + 1
            continue
        # First non-header, non-blank, non-separator line: stop walking header.
        break
    text = "\n".join(lines[body_start:])
    return len(text.split())


def check_intake_round_trip(
    folder: pathlib.Path,
    floor: float = ROUND_TRIP_WORD_RATIO_FLOOR,
) -> List[Violation]:
    """Compare word counts between `source.*` and `normalized.md`. If
    intake silently dropped content, the ratio will fall below the floor.

    This is the deterministic gate that catches the failure mode an LLM
    reviewer would otherwise be the only line of defense against —
    free, runs every time, catches what the LLM-driven intake used to risk."""
    normalized = folder / "normalized.md"
    if not normalized.exists():
        return []
    sources = sorted(p for p in folder.glob("source.*") if p.is_file())
    if not sources:
        return []
    if len(sources) > 1:
        return [
            Violation(
                folder,
                f"intake round-trip: multiple source.* files present: {[s.name for s in sources]}",
            )
        ]
    source = sources[0]
    src_words = _word_count(source.read_text())
    norm_words = _word_count(normalized.read_text())
    if src_words == 0:
        return []
    ratio = norm_words / src_words
    if ratio < floor:
        return [
            Violation(
                folder,
                f"intake round-trip: normalized.md has {norm_words} words "
                f"vs source {src_words} (ratio {ratio:.2f} < {floor:.2f}); "
                "content may have been silently dropped during intake",
            )
        ]
    return []


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_invariants.py <meeting_folder>", file=sys.stderr)
        return 2
    folder = pathlib.Path(argv[1])
    violations: list[Violation] = []
    if (folder / "normalized.md").exists():
        violations.extend(check_normalized(folder / "normalized.md"))
    if (folder / "outline.md").exists():
        violations.extend(check_outline(folder / "outline.md"))
    qa_ids: set[str] | None = None
    if (folder / "qa.md").exists():
        violations.extend(check_qa(folder / "qa.md"))
        qa_ids = collect_qa_ids(folder / "qa.md")
    if (folder / "clusters.md").exists():
        violations.extend(check_clusters(folder / "clusters.md", qa_ids=qa_ids))
    tickets_dir = folder / "tickets"
    if tickets_dir.is_dir():
        for ticket in sorted(tickets_dir.glob("*.md")):
            violations.extend(check_ticket(ticket))
            violations.extend(check_no_internal_scaffolding_in_ticket_prose(ticket))
    # Cross-file checks (need access to the whole meeting folder).
    violations.extend(check_intake_round_trip(folder))
    violations.extend(check_qa_chunks_present(folder))
    violations.extend(check_walk_back_coverage(folder))
    violations.extend(check_quote_provenance(folder))
    violations.extend(check_ticket_cluster_counts(folder))
    violations.extend(check_devrev_files(folder))
    for v in violations:
        print(f"{v.path}: {v.message}", file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
