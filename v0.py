import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List

from tools import Tools


@dataclass
class TaskSpec:
    problem_description: str
    input_data_path: str
    interatomic_potential: str
    interatomic_potential_path: str
    output_description: str

    @classmethod
    def from_dict(cls, payload: Dict) -> "TaskSpec":
        return cls(
            problem_description=payload["problem_description"],
            input_data_path=payload["input_data_path"],
            interatomic_potential=payload["interatomic_potential"],
            interatomic_potential_path=payload["interatomic_potential_path"],
            output_description=payload["output_description"],
        )


USER_REQUEST = (
    "You are a Molecular Simulation expert trying to write simulation code for a task. "
    "The task will be provided in the form of a json having keys problem_description, "
    "input_data_path, interatomic_potential, interatomic_potential_path, and output_description. "
    "Guidelines: (1) Read the initial configuration of atoms from input_data_path; "
    "(2) Choose the interatomic potential provided in the json and read the file from "
    "interatomic_potential_path."
)


def load_tasks(path: str) -> List[TaskSpec]:
    with open(path, "r") as f:
        tasks_raw = json.load(f)
    return [TaskSpec.from_dict(t) for t in tasks_raw]


def ensure_dirs(*paths: str) -> None:
    for path in paths:
        os.makedirs(path, exist_ok=True)


def run_task(tools: Tools, task: TaskSpec, logs_dir: str, scripts_dir: str) -> None:
    run_id = str(uuid.uuid4())
    log_file_name = os.path.join(logs_dir, f"app_npt_ensemble_{run_id}.log")
    ensure_dirs(logs_dir, scripts_dir)

    # Reconfigure logger for per-run log file.
    from tools import get_logger  # local import to avoid circular issues at module import
    tools.logger = get_logger(name=f"agenticmd.tools.{run_id}", log_path=log_file_name, level=logging.DEBUG)

    tools.logger.info("Starting run | run_id=%s", run_id)

    task_payload = asdict(task)

    commands = tools.command_estimator(USER_REQUEST, task_payload)
    commands_info = tools.command_info_retriever(commands)

    script = tools.script_generator(USER_REQUEST, task_payload, commands_info)
    script_path = os.path.join(scripts_dir, f"npt_ensemble_{run_id}.in")
    with open(script_path, "w") as script_file:
        script_file.write(script)

    tools.run_simulation(script_path, task_payload, run_id)
    evaluation = tools.evaluate_results(run_id, task_payload)
    tools.logger.info("Evaluation summary:\n%s", evaluation)


def main() -> None:
    tasks = load_tasks("Tasks/npt_ensemble_tasks.json")
    tools = Tools()
    for task in tasks:
        run_task(tools, task, logs_dir="logs/11nov", scripts_dir="generated_scripts")


if __name__ == "__main__":
    main()
