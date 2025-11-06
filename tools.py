import os
from typing import List
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from prompt import *
from langchain_core.messages import HumanMessage, SystemMessage
from query_rag import LAMMPSQueryRAG

class Tools:
    def __init__(self):
        load_dotenv()
        self.llm = ChatOpenAI(model="gpt-5", temperature=0.0, openai_api_key=os.getenv("OPENAI_API_KEY"))

    def command_estimator(self, problem_description: str, log_file=None) -> List[str]:
        if log_file:
            log_file.write(f"Estimating commands for problem description: {problem_description}\n")
            log_file.write("Using COMMAND_ESTIMATION_PROMPT:\n")
            log_file.write(f"{COMMAND_ESTIMATION_PROMPT.format(problem_description=problem_description)}\n")
        commands = self.llm.invoke([
            SystemMessage(content=COMMAND_ESTIMATION_PROMPT.format(problem_description=problem_description)),
            HumanMessage(content=problem_description)
        ])
        # Assuming the LLM returns a comma-separated list of commands
        command_list = [cmd.strip() for cmd in commands.content.split(",")]
        if log_file:
            log_file.write(f"Estimated commands: {command_list}\n\n")
        return command_list

    def potential_fetcher(self, element: str, log_file=None) -> List[str]:
        # Dummy implementation for potential fetching
        return ["potential1", "potential2", "potential3"]

    def command_info_retriever(self, commands: List[str], log_file=None) -> dict:
        lammps_query = LAMMPSQueryRAG()
        command_infos = {}
        for command in commands:
            info = lammps_query.query_rag_lammps(command)
            command_infos[command] = info
            if log_file:
                log_file.write(f"Retrieved info for command {command}: {info}\n\n")
        return command_infos

    def script_generator(self, problem_description:str, commands_info: dict, log_file=None) -> str:
        if log_file:
            log_file.write("Generating script\n")
            log_file.write("Using SCRIPT_GENERATION_PROMPT:\n")
            log_file.write(f"{SCRIPT_GENERATION_PROMPT.format(problem_description=problem_description, commands_info=commands_info)}\n")
        script = self.llm.invoke([
            SystemMessage(content=SCRIPT_GENERATION_PROMPT.format(problem_description=problem_description, commands_info=commands_info)),
            HumanMessage(content=f"problem_description: {problem_description} \n guidelines: {commands_info}")
        ])
        if log_file:
            log_file.write(f"Generated script content: \n{script.content}\n")
        return script.content