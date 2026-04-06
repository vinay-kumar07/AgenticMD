import logging
import time
from typing import Any, List, Optional

from langchain_openai import ChatOpenAI

_SEP_THICK = "=" * 72
_SEP_THIN  = "-" * 72


class LLMComponent:
    """Base mixin providing a shared LLM client and trajectory logging."""

    def __init__(self, llm: ChatOpenAI, logger: Optional[logging.Logger] = None):
        self.llm = llm
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def _call_llm(self, stage: str, messages: List[Any]) -> Any:
        """
        Invoke the LLM with full trajectory logging:
          - Logs every message in the prompt (role + content).
          - Logs the response content and any tool calls.
          - Logs wall-clock time for the call.
        """
        # --- Prompt ---
        self.logger.info("\n%s\n[%s] PROMPT\n%s", _SEP_THICK, stage, _SEP_THIN)
        for msg in messages:
            role = type(msg).__name__.replace("Message", "").upper()
            content = msg.content if hasattr(msg, "content") else str(msg)
            self.logger.info("[%s] %s:\n%s", stage, role, content)
            self.logger.info(_SEP_THIN)

        t0 = time.time()
        response = self.llm.invoke(messages)
        elapsed = time.time() - t0

        # --- Response ---
        self.logger.info("\n%s\n[%s] RESPONSE  (%.1fs)\n%s", _SEP_THICK, stage, elapsed, _SEP_THIN)
        if response.content:
            self.logger.info("%s", response.content)
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                self.logger.info("  → TOOL CALL: %s | args=%s", tc["name"], tc["args"])
        self.logger.info(_SEP_THICK)

        return response

    def _log_tool_result(self, tool_name: str, _args: dict, result: str) -> None:
        """Log a tool call result (used by post-processor)."""
        self.logger.info("  ← TOOL RESULT [%s]: %s", tool_name, result[:500] +
                         (" ... [truncated]" if len(result) > 500 else ""))

    # Keep for backward compatibility
    def _log_prompt(self, title: str, system_prompt: str, user_prompt: str,
                    max_chars: int = 3000) -> None:
        def _t(text: str) -> str:
            return text if len(text) <= max_chars else text[:max_chars] + " ... [truncated]"
        self.logger.debug("%s | System:\n%s", title, _t(system_prompt))
        self.logger.debug("%s | User:\n%s", title, _t(user_prompt))
