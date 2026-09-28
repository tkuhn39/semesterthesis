"""Print verification evidence for ``sources.yaml`` entries; never writes the registry.

    python scripts/verify_sources.py              # offline checks: files exist, ISBN checksums, status
    python scripts/verify_sources.py --crossref   # additionally resolve DOIs via api.crossref.org

For every DOI the Crossref title, container, year, authors and ORCIDs are printed so the user can
compare them with the PDF and then set ``verified.method: crossref`` / ``confirmed_by_user: true``
by hand (ADR-103: nothing is written automatically).
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

from gearcore.trace import load_sources

REPO_ROOT = Path(__file__).resolve().parents[3]


def isbn13_ok(isbn: str) -> bool:
    digits = [int(c) for c in isbn.replace("-", "") if c.isdigit()]
    if len(digits) != 13:
        return False
    total = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return (10 - total % 10) % 10 == digits[12]


def crossref(doi: str) -> dict[str, Any]:
    url = f"https://api.crossref.org/works/{doi}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "gearcore-verify/1.0 (thesis tooling)"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 — fixed https host
        payload = json.load(response)
    message = payload["message"]
    authors = [
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        + (f" [{a['ORCID']}]" if a.get("ORCID") else "")
        for a in message.get("author", [])
    ]
    issued = message.get("issued", {}).get("date-parts", [[None]])[0][0]
    return {
        "title": " ".join(message.get("title", [])),
        "container": " ".join(message.get("container-title", [])),
        "year": issued,
        "authors": authors,
        "volume": message.get("volume"),
        "page": message.get("page"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--crossref", action="store_true", help="resolve DOIs online")
    args = parser.parse_args()
    problems = 0
    for key, entry in load_sources().items():
        flags: list[str] = []
        file = entry.get("file")
        if file and not (REPO_ROOT / file).is_file():
            flags.append("FILE MISSING (local literature folder is git-ignored)")
        isbn = entry.get("isbn13")
        if isbn and not isbn13_ok(str(isbn)):
            flags.append("ISBN CHECKSUM INVALID")
        if entry.get("status") == "missing":
            flags.append("no verifiable identifier — must not be cited from code")
        if not entry.get("confirmed_by_user"):
            flags.append("not yet confirmed by user")
        doi = entry.get("doi")
        line = f"{key:<28} {entry.get('type', '?'):<10} {entry['verified'].get('method')!s:<16}"
        print(line + ("; ".join(flags) if flags else "ok"))
        if flags and "not yet confirmed" not in flags[0]:
            problems += 1
        if doi and args.crossref:
            try:
                meta = crossref(str(doi))
            except Exception as exc:  # noqa: BLE001 — network diagnostics are reported, not hidden
                print(f"    crossref {doi}: FAILED ({exc})")
                problems += 1
                continue
            print(f"    crossref {doi}: {meta['title']!r}")
            print(
                f"      {meta['container']} {meta['volume'] or ''} ({meta['year']}) p. {meta['page'] or '?'}"
            )
            for author in meta["authors"]:
                print(f"      - {author}")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
