import json
from dataclasses import dataclass
from typing import Dict, List


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


def load_tasks(path: str) -> List[TaskSpec]:
    with open(path, "r") as f:
        tasks_raw = json.load(f)
    return [TaskSpec.from_dict(t) for t in tasks_raw]
