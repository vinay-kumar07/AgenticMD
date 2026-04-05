"""
Direct scraper for LAMMPS documentation at https://docs.lammps.org/.

URL resolution:
  - Simple commands (run, lattice, ...)    → {command}.html
  - Styled commands (pair_style lj/cut)    → {prefix}_{style}.html
  - Special overrides (fix nvt/npt/nph)    → fix_nh.html
"""

import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from agenticmd.core.interfaces import DocsFetcher

_BASE = "https://docs.lammps.org"

_FIX_URL_OVERRIDES: Dict[str, str] = {
    "nvt": "fix_nh",
    "npt": "fix_nh",
    "nph": "fix_nh",
}

# Position of the style token in the split line for each styled command
_STYLE_ARG_POS: Dict[str, int] = {
    "pair_style":     1,
    "bond_style":     1,
    "angle_style":    1,
    "dihedral_style": 1,
    "improper_style": 1,
    "kspace_style":   1,
    "fix":            3,   # fix ID group-ID <style> ...
    "compute":        3,   # compute ID group-ID <style> ...
    "dump":           3,   # dump ID group-ID <style> file
}

_URL_PREFIX: Dict[str, str] = {
    "pair_style":     "pair",
    "bond_style":     "bond",
    "angle_style":    "angle",
    "dihedral_style": "dihedral",
    "improper_style": "improper",
    "kspace_style":   "kspace",
    "fix":            "fix",
    "compute":        "compute",
    "dump":           "dump",
}

_STRIP_SECTIONS = ("restrictions", "related-commands", "default", "examples")


class LAMMPSDocScraper(DocsFetcher):
    """Fetches and parses LAMMPS documentation pages on demand with in-memory caching."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._cache: Dict[str, str] = {}

    def fetch(self, command: str, full_line: str = "") -> str:
        for url in self._candidate_urls(command.lower(), full_line):
            if url in self._cache:
                self.logger.debug("Cache hit: %s", url)
                return self._cache[url]
            content = self._scrape(url)
            if content:
                self.logger.info("Fetched: %s", url)
                self._cache[url] = content
                return content
        msg = f"No documentation found for '{command}'."
        self.logger.warning(msg)
        return msg

    def _candidate_urls(self, cmd: str, full_line: str) -> List[str]:
        urls: List[str] = []
        parts = full_line.split() if full_line else [cmd]
        style_pos = _STYLE_ARG_POS.get(cmd)

        if style_pos is not None and len(parts) > style_pos:
            style = parts[style_pos].lower()
            prefix = _URL_PREFIX.get(cmd)
            if cmd == "fix" and style in _FIX_URL_OVERRIDES:
                urls.append(f"{_BASE}/{_FIX_URL_OVERRIDES[style]}.html")
            elif prefix:
                slug = style.replace("/", "_").replace("-", "_")
                urls.append(f"{_BASE}/{prefix}_{slug}.html")

        base_url = f"{_BASE}/{cmd}.html"
        if not urls or urls[-1] != base_url:
            urls.append(base_url)
        return urls

    def _scrape(self, url: str) -> str:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                self.logger.debug("HTTP %d: %s", resp.status_code, url)
                return ""
            return self._parse(BeautifulSoup(resp.text, "html.parser"))
        except Exception as e:
            self.logger.debug("Fetch error for %s: %s", url, e)
            return ""

    def _parse(self, soup: BeautifulSoup) -> str:
        parts: List[str] = []

        # Syntax: pre/code blocks give the exact argument format
        pre_blocks = soup.find_all("pre")[:4]
        if pre_blocks:
            parts.append("SYNTAX:\n" + "\n".join(b.get_text(strip=True) for b in pre_blocks))

        # Extract restrictions before modifying the tree
        restr_sec = soup.find("section", {"id": "restrictions"})
        restr_text = ""
        if restr_sec:
            restr_text = restr_sec.get_text(separator=" ", strip=True)
            restr_sec.extract()

        # Main documentation: strip boilerplate, then get remaining text
        main = soup.find("div", role="main") or soup.find("section") or soup.body
        if main:
            for sec_id in _STRIP_SECTIONS:
                sec = main.find("section", {"id": sec_id})
                if sec:
                    sec.extract()
            doc_text = main.get_text(separator=" ", strip=True)
            if len(doc_text) > 3000:
                doc_text = doc_text[:3000] + " [truncated]"
            parts.append(f"DOCUMENTATION:\n{doc_text}")

        if restr_text:
            parts.append(f"RESTRICTIONS:\n{restr_text}")

        return "\n\n".join(parts)
