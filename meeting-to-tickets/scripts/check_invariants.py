"""Structural and rigor checks for the meeting-to-tickets pipeline.

Phase 1 of this file covers normalized.md. Subsequent tasks add qa.md,
clusters.md, and ticket markdown files.
"""
from __future__ import annotations

import dataclasses
import pathlib
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


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_invariants.py <meeting_folder>", file=sys.stderr)
        return 2
    folder = pathlib.Path(argv[1])
    violations: list[Violation] = []
    normalized = folder / "normalized.md"
    if normalized.exists():
        violations.extend(check_normalized(normalized))
    for v in violations:
        print(f"{v.path}: {v.message}", file=sys.stderr)
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
