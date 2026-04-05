"""
Quality test for LAMMPSDocScraper.

Metrics:
  - Fetch success rate : % of commands that returned non-empty content
  - Syntax found       : % where a SYNTAX section was extracted
  - Command match      : % where the command name appears in the returned content
  - Avg content length : proxy for how much information was captured

Commands are sampled from the existing lammps_data.json so the same command
population is used for a fair comparison with the old RAG test.
"""

import json
import random
import re
from dataclasses import dataclass, field
from typing import Tuple

from agenticmd.docs import LAMMPSDocScraper

SAMPLE_SIZE = 30   # keep low — each call is an HTTP request
RANDOM_SEED = 42


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_raw_command(raw: str) -> Tuple[str, str]:
    """Return (command_token, synthetic_full_line) from a raw JSON command name.

    Raw names look like: 'fix npt command\\uf0c1' or 'pair_style lj/cut command\\uf0c1'
    """
    cleaned = raw.replace("\uf0c1", "").strip()
    if cleaned.lower().endswith(" command"):
        cleaned = cleaned[:-8].strip()
    cleaned = cleaned.lower()

    parts = cleaned.split()
    token = parts[0]

    # Construct a syntactically realistic full line so style resolution works
    if token == "fix" and len(parts) > 1:
        full_line = f"fix 1 all {' '.join(parts[1:])}"
    elif token == "compute" and len(parts) > 1:
        full_line = f"compute 1 all {' '.join(parts[1:])}"
    elif token == "dump" and len(parts) > 1:
        full_line = f"dump 1 all {' '.join(parts[1:])} 100 dump.out"
    else:
        full_line = cleaned

    return token, full_line


@dataclass
class Result:
    command: str
    full_line: str
    url_tried: str = ""
    fetched: bool = False
    has_syntax: bool = False
    command_in_content: bool = False
    content_length: int = 0
    snippet: str = ""


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with open("data/LAMMPSData/lammps_data.json") as f:
        lammps_data = json.load(f)

    random.seed(RANDOM_SEED)
    sample = random.sample(lammps_data, SAMPLE_SIZE)

    scraper = LAMMPSDocScraper()
    results = []

    for entry in sample:
        token, full_line = parse_raw_command(entry["command"])
        print(f"  Fetching: {token!r:25s}  (line: {full_line[:60]})")

        content = scraper.fetch(token, full_line)

        r = Result(command=token, full_line=full_line)
        r.fetched            = bool(content) and "No documentation found" not in content
        r.has_syntax         = "SYNTAX:" in content
        r.command_in_content = token.replace("_", " ") in content.lower() or token in content.lower()
        r.content_length     = len(content)
        r.snippet            = content[:120].replace("\n", " ")
        results.append(r)

    # ---------------------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------------------
    n = len(results)
    fetch_rate   = sum(r.fetched for r in results) / n
    syntax_rate  = sum(r.has_syntax for r in results) / n
    match_rate   = sum(r.command_in_content for r in results) / n
    avg_len      = sum(r.content_length for r in results) / n

    print("\n" + "=" * 60)
    print(f"  Sample size          : {n}")
    print(f"  Fetch success rate   : {fetch_rate:.0%}")
    print(f"  Syntax section found : {syntax_rate:.0%}")
    print(f"  Command name in doc  : {match_rate:.0%}")
    print(f"  Avg content length   : {avg_len:.0f} chars")
    print("=" * 60)

    # Show failures for debugging
    failures = [r for r in results if not r.fetched]
    if failures:
        print(f"\nFailed to fetch ({len(failures)}):")
        for r in failures:
            print(f"  - {r.command!r:25s}  full_line: {r.full_line}")

    # Show a few successful snippets
    successes = [r for r in results if r.fetched][:3]
    if successes:
        print("\nSample fetched content (first 120 chars):")
        for r in successes:
            print(f"  [{r.command}] {r.snippet}")
