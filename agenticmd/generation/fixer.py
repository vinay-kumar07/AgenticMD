import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agenticmd.core.interfaces import ScriptFixer
from agenticmd.generation.prompts import SCRIPT_FIX_PROMPT
from agenticmd.utils.llm import LLMComponent


class LLMScriptFixer(LLMComponent, ScriptFixer):
    """Fixes a failing script by asking the LLM to correct the error.

    ``fix_prompt`` defaults to the LAMMPS fix prompt; pass a different prompt
    to reuse this class for other engines (e.g. GROMACS).
    """

    def __init__(self, llm, logger=None, fix_prompt: str = SCRIPT_FIX_PROMPT):
        super().__init__(llm, logger)
        self.fix_prompt = fix_prompt

    def fix(self, script: str, error: str, task: dict) -> str:
        self.logger.info("Requesting script fix.")
        user_prompt = (
            f"Task: {json.dumps(task)}\n\n"
            f"Failing script:\n{script}\n\n"
            f"Error output:\n{error}"
        )
        result = self._call_llm("Fix", [
            SystemMessage(content=self.fix_prompt),
            HumanMessage(content=user_prompt),
        ])
        self.logger.info("Fixed script generated.")
        return result.content
