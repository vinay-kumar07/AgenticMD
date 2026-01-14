import json
from app.controllers import SimulationController
from app.models import load_tasks
from app.views import SimulationView


USER_REQUEST = (
    "You are a Molecular Simulation expert trying to write simulation code for a task. "
    "The task will be provided in the form of a json having keys problem_description, "
    "input_data_path, interatomic_potential, interatomic_potential_path, and output_description. "
    "Guidelines: (1) Read the initial configuration of atoms from input_data_path; "
    "(2) Choose the interatomic potential provided in the json and read the file from "
    "interatomic_potential_path."
)


def main() -> None:
    tasks = load_tasks("Tasks/npt_ensemble_tasks.json")
    view = SimulationView(logs_dir="logs/11nov", scripts_dir="generated_scripts")
    controller = SimulationController(user_request=USER_REQUEST, view=view)
    controller.run_all(tasks)


if __name__ == "__main__":
    main()
