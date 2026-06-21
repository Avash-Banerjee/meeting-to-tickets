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

    dropped_entries = []
    for line in dropped_body.splitlines():
        s = line.strip()
        if not s.startswith("- Q "):
            continue
        dropped_entries.append(s)
        if " — " not in s:
            violations.append(Violation(path, f"qa.md dropped entry missing reason: {s}"))

    declared_total = frontmatter.get("total_qa")
    if isinstance(declared_total, int) and declared_total != len(blocks):
        violations.append(
            Violation(
                path,
                f"qa.md frontmatter total_qa={declared_total} does not match {len(blocks)} Q&A blocks found",
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


_QUOTED_SPAN_RE = re.compile(r'"([^"]+)"')


def _extract_quoted_spans(line: str) -> list[str]:
    """Return all double-quoted substrings within a line (curly normalized)."""
    normalized = line.translate({
        ord("“"): '"',
        ord("”"): '"',
    })
    return _QUOTED_SPAN_RE.findall(normalized)


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
                line = m.group(1)
                spans = _extract_quoted_spans(line)
                # If no double-quoted span found, fall back to the whole line
                # after the speaker prefix.
                if not spans:
                    fallback = re.sub(r"^[^:]+:\s*", "", line).strip()
                    if fallback:
                        spans = [fallback]
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
                if not spans:
                    fallback = re.sub(r"^-\s*[^:]+:\s*", "", s).strip()
                    if fallback:
                        spans = [fallback]
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_invariants.py <meeting_folder>", file=sys.stderr)
        return 2
    folder = pathlib.Path(argv[1])
    violations: list[Violation] = []
    if (folder / "normalized.md").exists():
        violations.extend(check_normalized(folder / "normalized.md"))
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
    # Cross-file checks (need access to the whole meeting folder).
    violations.extend(check_quote_provenance(folder))
    violations.extend(check_ticket_cluster_counts(folder))
    for v in violations:
        print(f"{v.path}: {v.message}", file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
