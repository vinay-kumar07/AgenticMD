import os
from typing import Iterable


class SimulationView:
    """Handles filesystem concerns for logs and scripts."""

    def __init__(self, logs_dir: str, scripts_dir: str):
        self.logs_dir = logs_dir
        self.scripts_dir = scripts_dir
        self._ensure_dirs(logs_dir, scripts_dir)

    def log_path(self, run_id: str) -> str:
        return os.path.join(self.logs_dir, f"app_npt_ensemble_{run_id}.log")

    def script_path(self, run_id: str) -> str:
        return os.path.join(self.scripts_dir, f"npt_ensemble_{run_id}.in")

    def write_script(self, path: str, content: str) -> None:
        with open(path, "w") as f:
            f.write(content)

    def _ensure_dirs(self, *paths: Iterable[str]) -> None:
        for path in paths:
            os.makedirs(path, exist_ok=True)
