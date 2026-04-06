import logging
import os
import subprocess
from typing import Optional, Tuple

from agenticmd.core.interfaces import SimulationRunner


class GROMACSSubprocessRunner(SimulationRunner):
    """Runs a GROMACS bash script directly via subprocess in the working directory."""

    def __init__(self, timeout: int = 600, logger: Optional[logging.Logger] = None):
        self.timeout = timeout
        self.logger = logger or logging.getLogger(__name__)

    def run(self, script_path: str, working_dir: str) -> Tuple[bool, str]:
        self.logger.info(
            "Running GROMACS script | script=%s | working_dir=%s",
            script_path, working_dir,
        )
        try:
            result = subprocess.run(
                ["bash", os.path.abspath(script_path)],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            self.logger.info("Script exited with code %d", result.returncode)
            if result.returncode != 0:
                error = result.stderr or result.stdout
                self.logger.error("GROMACS error: %s", error[:500])
                return False, error
            return True, ""
        except subprocess.TimeoutExpired:
            msg = f"Script timed out after {self.timeout}s"
            self.logger.error(msg)
            return False, msg
        except Exception as e:
            self.logger.exception("Subprocess error: %s", e)
            return False, str(e)
