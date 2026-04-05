import json
import logging
import os
from typing import Dict, Optional

from agenticmd.core.interfaces import PostProcessor, ScriptFixer, ScriptGenerator, SimulationRunner

USER_REQUEST = (
    "You are a Molecular Simulation expert writing LAMMPS code. "
    "Build the entire simulation system using LAMMPS commands (lattice, region, "
    "create_box, create_atoms, etc.) — do not use read_data. "
    "Download any required potential files using the download_file tool."
)


class MDAgent:
    """
    Facade that orchestrates the full MD simulation pipeline:
      1. Generate a script (draft → retrieve docs → refine).
      2. Run the simulation; on failure, fix and retry (self-correction loop).
      3. Post-process output to compute required metrics.
      4. Write final_answer.json to the task's working directory.

    Each task runs in its own isolated directory: {base_dir}/{task_id}/
    """

    def __init__(
        self,
        generator: ScriptGenerator,
        fixer: ScriptFixer,
        runner: SimulationRunner,
        processor: PostProcessor,
        max_retries: int = 3,
        logger: Optional[logging.Logger] = None,
    ):
        self.generator = generator
        self.fixer = fixer
        self.runner = runner
        self.processor = processor
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)

    def run(self, task: dict, base_dir: str) -> Dict[str, float]:
        """Execute the full pipeline. Returns computed metrics and writes final_answer.json."""
        task_id = task["id"]
        working_dir = os.path.join(base_dir, task_id)
        os.makedirs(working_dir, exist_ok=True)
        self.logger.info("Pipeline started | task_id=%s | working_dir=%s", task_id, working_dir)

        script = self.generator.generate(USER_REQUEST, task, working_dir)

        for attempt in range(1, self.max_retries + 1):
            script_path = os.path.join(working_dir, f"script_attempt{attempt}.in")
            with open(script_path, "w") as f:
                f.write(script)
            self.logger.info("Attempt %d/%d | script=%s", attempt, self.max_retries, script_path)

            success, error = self.runner.run(script_path, working_dir)
            if success:
                self.logger.info("Simulation succeeded on attempt %d.", attempt)
                break

            self.logger.warning("Attempt %d failed: %s", attempt, error[:300])
            if attempt < self.max_retries:
                script = self.fixer.fix(script, error, task)
            else:
                self.logger.error("All %d attempts failed. Proceeding to post-processing.", self.max_retries)

        metrics = self.processor.process(working_dir, task)
        answer_path = os.path.join(working_dir, "final_answer.json")
        with open(answer_path, "w") as f:
            json.dump(metrics, f, indent=2)
        self.logger.info("Final answer written | metrics=%s", metrics)
        return metrics
