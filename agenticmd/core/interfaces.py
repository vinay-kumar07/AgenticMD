from abc import ABC, abstractmethod
from typing import Dict, List, Tuple


class DocsFetcher(ABC):
    @abstractmethod
    def fetch(self, command: str, full_line: str = "") -> str:
        """Return documentation for a LAMMPS command.
        full_line: complete script line used to resolve style sub-pages."""


class PotentialDownloader(ABC):
    @abstractmethod
    def download(self, elements: List[str], potential_type: str,
                 filename: str, working_dir: str) -> None:
        """Search for and download an interatomic potential file to working_dir."""


class ScriptGenerator(ABC):
    @abstractmethod
    def generate(self, problem: str, task: dict, working_dir: str) -> str:
        """Generate a complete LAMMPS input script."""


class ScriptFixer(ABC):
    @abstractmethod
    def fix(self, script: str, error: str, task: dict) -> str:
        """Return a corrected script given the LAMMPS error output."""


class SimulationRunner(ABC):
    @abstractmethod
    def run(self, script_path: str, working_dir: str) -> Tuple[bool, str]:
        """Run the simulation. Returns (success, error_text)."""


class PostProcessor(ABC):
    @abstractmethod
    def process(self, working_dir: str, task: dict) -> Dict[str, float]:
        """Compute required metrics from simulation output."""
