"""
Direct scraper for GROMACS documentation at https://manual.gromacs.org/current/.

Two documentation sources:
  - MDP keywords  → scraped from mdp-options.html (loaded once, cached in-memory)
  - gmx CLI tools → individual pages at onlinehelp/gmx-{tool}.html
"""

import logging
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from agenticmd.core.interfaces import DocsFetcher

_BASE = "https://manual.gromacs.org/current"
_MDP_PAGE_URL = f"{_BASE}/user-guide/mdp-options.html"
_TOOL_PAGE_URL = f"{_BASE}/onlinehelp/gmx-{{tool}}.html"


class GROMACSDocScraper(DocsFetcher):
    """
    Fetches GROMACS documentation on demand with in-memory caching.

    - MDP keyword  → looks up anchor ``id="mdp-{keyword}"`` on the MDP options page.
    - gmx tool     → fetches the per-tool onlinehelp page.

    The MDP options page is fetched at most once per instance.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._cache: Dict[str, str] = {}
        self._mdp_soup: Optional[BeautifulSoup] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(self, command: str, full_line: str = "") -> str:
        if command in self._cache:
            self.logger.debug("Cache hit: %s", command)
            return self._cache[command]

        # Determine source from context: gmx lines start with "gmx"
        if full_line.strip().startswith("gmx"):
            content = self._fetch_tool(command)
        else:
            content = self._fetch_mdp_keyword(command) or self._fetch_tool(command)

        if not content:
            content = f"No documentation found for '{command}'."
            self.logger.warning(content)
        else:
            self.logger.info("Fetched docs for '%s'", command)

        self._cache[command] = content
        return content

    # ------------------------------------------------------------------
    # MDP keyword lookup
    # ------------------------------------------------------------------

    def _fetch_mdp_keyword(self, keyword: str) -> str:
        soup = self._get_mdp_page()
        if not soup:
            return ""

        # Sphinx generates: <dt id="mdp-{keyword}">
        normalized = keyword.replace("_", "-")
        dt = soup.find("dt", {"id": f"mdp-{normalized}"}) or \
             soup.find("dt", {"id": f"mdp-{keyword}"})
        if not dt:
            return ""

        parts = [f"MDP OPTION: {dt.get_text(strip=True)}"]
        dd = dt.find_next_sibling("dd")
        if dd:
            desc = dd.get_text(separator=" ", strip=True)
            parts.append(desc[:2000])
        return "\n".join(parts)

    def _get_mdp_page(self) -> Optional[BeautifulSoup]:
        if self._mdp_soup is None:
            try:
                resp = requests.get(_MDP_PAGE_URL, timeout=15)
                if resp.status_code == 200:
                    self._mdp_soup = BeautifulSoup(resp.text, "html.parser")
                    self.logger.info("MDP options page loaded.")
                else:
                    self.logger.error("MDP page returned HTTP %d", resp.status_code)
            except Exception as e:
                self.logger.error("Failed to load MDP options page: %s", e)
        return self._mdp_soup

    # ------------------------------------------------------------------
    # gmx tool page
    # ------------------------------------------------------------------

    def _fetch_tool(self, tool: str) -> str:
        url = _TOOL_PAGE_URL.format(tool=tool)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                self.logger.debug("HTTP %d for tool page: %s", resp.status_code, url)
                return ""
            return self._parse_tool_page(BeautifulSoup(resp.text, "html.parser"))
        except Exception as e:
            self.logger.debug("Tool page fetch error (%s): %s", tool, e)
            return ""

    def _parse_tool_page(self, soup: BeautifulSoup) -> str:
        parts = []
        pre_blocks = soup.find_all("pre")[:3]
        if pre_blocks:
            parts.append("SYNOPSIS:\n" + "\n".join(b.get_text(strip=True) for b in pre_blocks))
        main = soup.find("div", role="main") or soup.find("section") or soup.body
        if main:
            text = main.get_text(separator=" ", strip=True)
            if len(text) > 3000:
                text = text[:3000] + " [truncated]"
            parts.append(f"DOCUMENTATION:\n{text}")
        return "\n\n".join(parts)
