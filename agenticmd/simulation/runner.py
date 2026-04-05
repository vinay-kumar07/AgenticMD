import logging
import os
from typing import Optional, Tuple

import requests

from agenticmd.core.interfaces import SimulationRunner


class LAMMPSServerRunner(SimulationRunner):
    """Submits a LAMMPS script to the local Flask server and runs it in-place."""

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000/run_lammps",
        timeout: int = 300,
        logger: Optional[logging.Logger] = None,
    ):
        self.server_url = server_url
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

    def run(self, script_path: str, working_dir: str) -> Tuple[bool, str]:
        self.logger.info("Submitting simulation | working_dir=%s", working_dir)
        payload = {
            "work_dir": os.path.abspath(working_dir),
            "script":   os.path.basename(script_path),
        }
        try:
            response = requests.post(self.server_url, json=payload, timeout=self.timeout)
            self.logger.info("Server response | status=%d", response.status_code)

            if response.status_code != 200:
                error = response.text[:2000]
                self.logger.error("Server error: %s", error)
                return False, error

            data = response.json()
            returncode = data.get("returncode", -1)
            if returncode != 0:
                error = data.get("stderr") or data.get("stdout", "")
                self.logger.error("LAMMPS exited %d: %s", returncode, error[:500])
                return False, error

            self.logger.info("Simulation completed successfully.")
            return True, ""

        except Exception as e:
            self.logger.exception("Simulation failed: %s", e)
            return False, str(e)
