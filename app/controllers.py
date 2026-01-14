import logging
import uuid
from dataclasses import asdict
from typing import Iterable

from tools import Tools, get_logger
from app.models import TaskSpec
from app.views import SimulationView


class SimulationController:
    """Coordinates the LAMMPS pipeline (controller)."""

    def __init__(self, user_request: str, view: SimulationView):
        self.user_request = user_request
        self.view = view

    def run_all(self, tasks: Iterable[TaskSpec]) -> None:
        for task in tasks:
            self.run_task(task)

    def run_task(self, task: TaskSpec) -> None:
        run_id = str(uuid.uuid4())
        log_path = self.view.log_path(run_id)
        script_path = self.view.script_path(run_id)

        logger = get_logger(name=f"agenticmd.tools.{run_id}", log_path=log_path, level=logging.DEBUG)
        tools = Tools(logger=logger)

        payload = asdict(task)

        commands = tools.command_estimator(self.user_request, payload)
        commands_info = tools.command_info_retriever(commands)

        script = tools.script_generator(self.user_request, payload, commands_info)
        self.view.write_script(script_path, script)

        tools.run_simulation(script_path, payload, run_id)
        evaluation = tools.evaluate_results(run_id, payload)
        logger.info("Evaluation summary:\n%s", evaluation)
