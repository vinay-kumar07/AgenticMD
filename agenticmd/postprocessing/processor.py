import json
import logging
import os
import subprocess
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from agenticmd.core.interfaces import PostProcessor
from agenticmd.postprocessing.prompts import POST_PROCESSING_PROMPT
from agenticmd.utils.llm import LLMComponent


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

class _ReadFile(BaseModel):
    """Read a file from the simulation working directory."""
    filename: str = Field(description="Filename to read (e.g. 'log.lammps', 'dump.lammpstrj')")


class _RunPython(BaseModel):
    """Execute Python code to analyse simulation data. Print any values you want to capture."""
    code: str = Field(description="Python code to run; numpy and pandas are available")


class _SubmitAnswer(BaseModel):
    """Submit the final computed metric values to finish post-processing."""
    metrics: Dict[str, float] = Field(description="Metric names mapped to computed float values")


# ---------------------------------------------------------------------------
# Post-processor
# ---------------------------------------------------------------------------

class LLMPostProcessor(LLMComponent, PostProcessor):
    """
    Agentic post-processor: the LLM reads output files, runs Python analysis
    code, and submits final metric values via the submit_answer tool.
    """

    def __init__(self, llm: ChatOpenAI, logger: Optional[logging.Logger] = None):
        super().__init__(llm.bind_tools([_ReadFile, _RunPython, _SubmitAnswer]), logger)

    def process(self, working_dir: str, task: dict) -> Dict[str, float]:
        self.logger.info("Starting post-processing | working_dir=%s", working_dir)
        user_prompt = (
            f"Task: {json.dumps(task)}\n"
            f"Required metrics: {task['metrics']}\n"
            f"Files in working directory: {os.listdir(working_dir)}"
        )
        messages = [
            SystemMessage(content=POST_PROCESSING_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        turn = 0
        while turn < 10: 
            turn += 1
            response = self._call_llm(f"PostProcess-turn{turn}", messages)
            messages.append(response)
    
            if not response.tool_calls:
                self.logger.warning("LLM finished without submit_answer; attempting JSON parse.")
                try:
                    return json.loads(response.content)
                except json.JSONDecodeError:
                    self.logger.error("Could not parse metrics from LLM response.")
                    return {}

            for tc in response.tool_calls:
                name, args = tc["name"], tc["args"]
                if name in ("_SubmitAnswer", "SubmitAnswer", "_submitanswer", "submit_answer"):
                    metrics = args.get("metrics", args)
                    if not metrics:
                        self.logger.warning("_SubmitAnswer called with empty metrics — asking LLM to retry.")
                        messages.append(ToolMessage(
                            content="Error: metrics was empty. Re-read the output files and call _SubmitAnswer again with the actual computed values.",
                            tool_call_id=tc["id"],
                        ))
                        break  # go to next turn
                    self.logger.info("Metrics submitted: %s", metrics)
                    messages.append(ToolMessage(content="Answer recorded.", tool_call_id=tc["id"]))
                    return metrics
                result = self._dispatch_tool(name, args, working_dir)
                self._log_tool_result(name, args, str(result))
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            
            return {}

    def _dispatch_tool(self, name: str, args: dict, working_dir: str) -> str:
        if name == "_ReadFile":
            return self._read_file(args["filename"], working_dir)
        if name == "_RunPython":
            return self._run_python(args["code"], working_dir)
        return f"Unknown tool: {name}"

    def _read_file(self, filename: str, working_dir: str) -> str:
        path = os.path.join(working_dir, filename)
        try:
            with open(path) as f:
                content = f.read()
            return content[:12000] + "\n... [truncated]" if len(content) > 12000 else content
        except FileNotFoundError:
            return f"Error: {filename} not found."

    def _run_python(self, code: str, working_dir: str) -> str:
        self.logger.info("Running Python analysis code.")
        try:
            result = subprocess.run(
                ["python", "-c", code],
                cwd=working_dir, capture_output=True, text=True, timeout=60,
            )
            output = result.stdout
            if result.stderr:
                output += f"\nSTDERR: {result.stderr}"
            return output or "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: execution timed out."
        except Exception as e:
            return f"Error: {e}"
