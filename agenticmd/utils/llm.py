import logging
from typing import Optional

from langchain_openai import ChatOpenAI


class LLMComponent:
    """Base mixin providing a shared LLM client and prompt logging for all LLM-backed components."""

    def __init__(self, llm: ChatOpenAI, logger: Optional[logging.Logger] = None):
        self.llm = llm
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def _log_prompt(self, title: str, system_prompt: str, user_prompt: str,
                    max_chars: int = 3000) -> None:
        def _truncate(text: str) -> str:
            return text if len(text) <= max_chars else text[:max_chars] + " ... [truncated]"
        self.logger.debug("%s | System:\n%s", title, _truncate(system_prompt))
        self.logger.debug("%s | User:\n%s", title, _truncate(user_prompt))
