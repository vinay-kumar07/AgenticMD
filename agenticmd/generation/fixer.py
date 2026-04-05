import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agenticmd.core.interfaces import ScriptFixer
from agenticmd.generation.prompts import SCRIPT_FIX_PROMPT
from agenticmd.utils.llm import LLMComponent


class LLMScriptFixer(LLMComponent, ScriptFixer):
    """Fixes a failing LAMMPS script by asking the LLM to correct the error."""

    def fix(self, script: str, error: str, task: dict) -> str:
        self.logger.info("Requesting script fix.")
        user_prompt = (
            f"Task: {json.dumps(task)}\n\n"
            f"Failing script:\n{script}\n\n"
            f"Error output:\n{error}"
        )
        self._log_prompt("ScriptFixer", SCRIPT_FIX_PROMPT, user_prompt)
        result = self.llm.invoke([
            SystemMessage(content=SCRIPT_FIX_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        self.logger.info("Fixed script generated.")
        return result.content
