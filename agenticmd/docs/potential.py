"""
Downloads interatomic potential files from the LAMMPS GitHub potentials repository.

Scoring: +2 per matching element symbol in filename, +1 if potential type appears in filename.
The best match is downloaded; alternatives are logged for transparency.
"""

import logging
import os
from typing import List, Optional

import requests

from agenticmd.core.interfaces import PotentialDownloader

_GITHUB_API = "https://api.github.com/repos/lammps/lammps/contents/potentials"
_GITHUB_RAW = "https://raw.githubusercontent.com/lammps/lammps/develop/potentials"


class GitHubPotentialDownloader(PotentialDownloader):
    """Searches the LAMMPS GitHub potentials directory and downloads the best match."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._listing: Optional[List[str]] = None  # cached after first fetch

    def download(self, elements: List[str], potential_type: str,
                 filename: str, working_dir: str) -> None:
        try:
            all_files = self._fetch_listing()
        except Exception as e:
            self.logger.error("Could not fetch potential listing: %s", e)
            return

        candidates = self._score(all_files, elements, potential_type)
        if not candidates:
            self.logger.warning("No potential found for elements=%s type=%s", elements, potential_type)
            return

        best = candidates[0][1]
        self.logger.info("Best match: %s | alternatives: %s", best, [c[1] for c in candidates[1:4]])

        url = f"{_GITHUB_RAW}/{best}"
        try:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            dest = os.path.join(working_dir, filename)
            with open(dest, "wb") as f:
                f.write(r.content)
            self.logger.info("Downloaded %s → %s (%d bytes)", best, dest, len(r.content))
        except Exception as e:
            self.logger.error("Download failed for %s: %s", url, e)

    def _score(self, all_files: List[str], elements: List[str],
               potential_type: str) -> List[tuple]:
        elements_lower = {e.lower() for e in elements}
        ptype_lower = potential_type.lower()
        candidates = []
        for f in all_files:
            f_lower = f.lower()
            elem_score = sum(1 for e in elements_lower if e in f_lower)
            if elem_score == 0:
                continue
            type_score = int(ptype_lower in f_lower)
            candidates.append((elem_score * 2 + type_score, f))
        candidates.sort(reverse=True)
        return candidates

    def _fetch_listing(self) -> List[str]:
        if self._listing is not None:
            return self._listing
        self.logger.info("Fetching LAMMPS potentials listing from GitHub.")
        resp = requests.get(_GITHUB_API, timeout=15)
        resp.raise_for_status()
        self._listing = [item["name"] for item in resp.json() if item.get("type") == "file"]
        self.logger.debug("Found %d potential files.", len(self._listing))
        return self._listing
