import os
import json
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import requests

from query_rag import LAMMPSQueryRAG
from prompt import COMMAND_ESTIMATION_PROMPT, SCRIPT_GENERATION_PROMPT


def get_logger(name: str = "agenticmd.tools",
               log_path: Optional[str] = None,
               level: int = logging.INFO) -> logging.Logger:
    """Create or retrieve a configured logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(level)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    if log_path:
        fh = logging.FileHandler(log_path)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


class Tools:
    def __init__(self, logger: Optional[logging.Logger] = None, log_path: Optional[str] = None):
        load_dotenv()
        self.logger = logger or get_logger(log_path=log_path, level=logging.INFO)
        self.logger.info("Initializing Tools and ChatOpenAI client...")
        self.llm = ChatOpenAI(model="gpt-5", temperature=0.0, openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.lammps_query = LAMMPSQueryRAG()
        self.logger.info("Clients initialized successfully.")

    # ---------- Utility ----------
    def _log_prompt(self, title: str, system_prompt: str, user_prompt: str, max_chars: int = 3000):
        """Helper to log prompts neatly (truncated to avoid spam)."""
        def truncate(text):
            return text if len(text) <= max_chars else text[:max_chars] + " ... [truncated]"
        self.logger.debug(f"🧠 {title} | System Prompt:\n{truncate(system_prompt)}")
        self.logger.debug(f"👤 {title} | User Prompt:\n{truncate(user_prompt)}")

    # ---------- Command Estimation ----------
    def command_estimator(self, problem_description: str, task: dict) -> List[str]:
        self.logger.info("Estimating LAMMPS commands for given problem.")
        generation_prompt = COMMAND_ESTIMATION_PROMPT.format(problem_description=problem_description)
        user_prompt = problem_description + " Task: " + json.dumps(task)
        self._log_prompt("Command Estimation", generation_prompt, user_prompt)

        commands = self.llm.invoke([
            SystemMessage(content=generation_prompt),
            HumanMessage(content=user_prompt)
        ])
        command_list = [cmd.strip() for cmd in commands.content.split(",")]
        self.logger.info("Initial command estimation complete.")
        self.logger.debug("Initial command list: %s", command_list)

        # Reflection / validation step
        reflection_prompt = f"""
        You are now in reflection mode.
        Review the following LAMMPS commands proposed for this simulation:
        {command_list}

        Question 1: Are all the mandatory commands for the given problem included?
        The mandatory commands are: units, dimension, boundary, atom_style, read_data,
        pair_style, pair_coeff, minimize, fix, unfix, run.
        Question 2: Are any redundant or irrelevant commands present?
        Question 3: Suggest corrections or improvements if needed.

        Respond in JSON format:
        {{
            "assessment": "...summary...",
            "revised_commands": ["cmd1", "cmd2", ...]
        }}
        """
        self._log_prompt("Command Reflection", "You are a critical LAMMPS command reviewer.", reflection_prompt)

        reflection = self.llm.invoke([
            SystemMessage(content="You are a critical LAMMPS command reviewer."),
            HumanMessage(content=reflection_prompt)
        ])

        try:
            reflection_data = json.loads(reflection.content)
            final_commands = reflection_data.get("revised_commands", command_list)
            self.logger.info("Command reflection complete. Commands revised successfully.")
            self.logger.debug("Reflection assessment: %s", reflection_data.get("assessment", ""))
        except json.JSONDecodeError:
            self.logger.warning("Reflection output not valid JSON; using original command list.")
            final_commands = command_list

        return final_commands

    # ---------- Potential Fetcher ----------
    def potential_fetcher(self, element: str) -> List[str]:
        self.logger.info("Fetching potential files for element '%s' (dummy).", element)
        return ["potential1", "potential2", "potential3"]

    # ---------- Command Info Retrieval ----------
    def command_info_retriever(self, commands: List[str]) -> Dict[str, str]:
        self.logger.info("Fetching command documentation/info via RAG.")
        command_infos = {}
        for cmd in commands:
            self.logger.debug("Querying RAG for command '%s'", cmd)
            command_infos[cmd] = self.lammps_query.query_rag_lammps(cmd)
        self.logger.info("Command info retrieval complete.")
        return command_infos

    # ---------- Script Generator ----------
    def script_generator(self, problem_description: str, task: dict, commands_info: dict) -> str:
        self.logger.info("Generating final LAMMPS script.")
        generation_prompt = SCRIPT_GENERATION_PROMPT.format(
            problem_description=problem_description,
            commands_info=commands_info
        )
        user_prompt = (
            f"problem_description: {problem_description + task['problem_description']} \n "
            f"guidelines: {commands_info} \n "
            f"Hardcode the input data file path as {task['input_data_path']} and potential file as {task['interatomic_potential_path']}. "
            f"All logs should be written in log.lammps file, don't create separate log files for each command."
        )
        self._log_prompt("Script Generation", generation_prompt, user_prompt)

        script = self.llm.invoke([
            SystemMessage(content=generation_prompt),
            HumanMessage(content=user_prompt)
        ])

        self.logger.info("Script generation complete.")
        self.logger.debug("Generated script (truncated):\n%s", script.content[:1000])
        return script.content

    # ---------- Simulation Runner ----------
    def run_simulation(self, script_path: str, task: dict, run_id: str) -> None:
        self.logger.info(f"Running LAMMPS simulation | run_id={run_id}")
        url = "http://127.0.0.1:8000/run_lammps"
        params = {"run_id": run_id}

        try:
            with open(script_path, "rb") as f:
                files = {"file": f}
                self.logger.debug("Sending POST to %s with params=%s", url, params)
                response = requests.post(url, params=params, files=files, timeout=300)

            self.logger.info("Simulation request completed | status=%d", response.status_code)
            if response.status_code == 200:
                self.logger.info("LAMMPS simulation ran successfully.")
            else:
                self.logger.error("LAMMPS run failed | response: %s", response.text[:500])
        except Exception as e:
            self.logger.exception("Simulation execution failed: %s", e)

    # ---------- Evaluation ----------
    def evaluate_results(self, run_id: str, task: dict) -> str:
        self.logger.info(f"Evaluating LAMMPS results | run_id={run_id}")
        path = os.path.join("server", "runs", run_id, "log.lammps")

        try:
            with open(path, 'r') as f:
                log_content = f.read()
        except FileNotFoundError:
            self.logger.error("log.lammps not found for run_id=%s", run_id)
            return "Error: log.lammps not found."

        evaluation_prompt = (
            f"You are a Molecular Simulation expert. Given the LAMMPS log file content below, analyze the results "
            f"in context of the task description: {task['problem_description']}. "
            f"The results of the logs file should match the output description provided in the task: {task['output_description']}. "
            f"Identify if the simulation ran successfully, any errors or warnings, and key results such as temperature, pressure, energy values."
        )
        user_prompt = f"Here is the LAMMPS log file content:\n{log_content}\n\nPlease provide a detailed evaluation."
        self._log_prompt("Simulation Evaluation", evaluation_prompt, user_prompt[:3000])

        evaluation = self.llm.invoke([
            SystemMessage(content=evaluation_prompt),
            HumanMessage(content=user_prompt)
        ])

        self.logger.info("Evaluation complete.")
        self.logger.debug("Evaluation response (truncated):\n%s", getattr(evaluation, "content", str(evaluation))[:2000])
        return getattr(evaluation, "content", str(evaluation))
