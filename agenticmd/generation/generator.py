import json
import logging
import os
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agenticmd.core.interfaces import DocsFetcher, PotentialDownloader, ScriptGenerator
from agenticmd.generation.prompts import DRAFT_SCRIPT_PROMPT, REFINE_SCRIPT_PROMPT
from agenticmd.utils.llm import LLMComponent

# Pair styles that require an external potential file
_FILE_BASED_STYLES = {
    "eam", "eam/alloy", "eam/fs", "meam", "meam/c",
    "tersoff", "reaxff", "airebo", "airebo/morse",
    "sw", "bop", "comb", "comb3", "vashishta",
}


def _parse_commands(script: str) -> Dict[str, str]:
    """Return {command_token: first_full_line} for each unique command in the script.

    Passing the full line to the docs fetcher allows it to resolve style-specific
    sub-pages (e.g. 'pair_style lj/cut 2.5' → pair_lj_cut.html).
    """
    seen: Dict[str, str] = {}
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        cmd = stripped.split()[0].lower()
        if cmd not in seen:
            seen[cmd] = stripped
    return seen


class DraftRefineScriptGenerator(LLMComponent, ScriptGenerator):
    """
    Two-pass script generator (Template Method pattern):
      1. Draft    — LLM writes freely from its own knowledge.
      2. Extract  — parse every command used in the draft.
      3. Retrieve — fetch official docs for each command via DocsFetcher.
      4. Potential — detect and download any file-based potential via PotentialDownloader.
      5. Refine   — LLM corrects the draft using the retrieved docs.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        docs_fetcher: DocsFetcher,
        potential_downloader: PotentialDownloader,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(llm, logger)
        self.docs_fetcher = docs_fetcher
        self.potential_downloader = potential_downloader

    def generate(self, problem: str, task: dict, working_dir: str) -> str:
        os.makedirs(working_dir, exist_ok=True)

        self.logger.info("Generating draft script.")
        draft = self._draft(problem, task)

        commands = _parse_commands(draft)
        self.logger.info("Extracted %d commands: %s", len(commands), list(commands.keys()))

        docs = {cmd: self.docs_fetcher.fetch(cmd, full_line)
                for cmd, full_line in commands.items()}
        self.logger.info("Documentation retrieved for %d commands.", len(docs))

        self._handle_potential(draft, working_dir)

        self.logger.info("Refining script with documentation.")
        return self._refine(draft, docs, problem, task)

    # ------------------------------------------------------------------

    def _draft(self, problem: str, task: dict) -> str:
        result = self._call_llm("Draft", [
            SystemMessage(content=DRAFT_SCRIPT_PROMPT),
            HumanMessage(content=f"Problem: {problem}\nTask: {json.dumps(task)}"),
        ])
        return result.content

    def _refine(self, draft: str, docs: dict, problem: str, task: dict) -> str:
        user_prompt = (
            f"Problem: {problem}\nTask: {json.dumps(task)}\n\n"
            f"Draft script:\n{draft}\n\n"
            f"Command documentation:\n{json.dumps(docs, indent=2)}"
        )
        result = self._call_llm("Refine", [
            SystemMessage(content=REFINE_SCRIPT_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return result.content

    def _handle_potential(self, draft: str, working_dir: str) -> None:
        """Detect file-based pair style in draft and delegate download."""
        pair_style = None
        for line in draft.splitlines():
            parts = line.strip().split()
            if not parts or parts[0].startswith("#"):
                continue
            if parts[0] == "pair_style" and len(parts) > 1:
                pair_style = parts[1].lower()
            elif parts[0] == "pair_coeff" and pair_style in _FILE_BASED_STYLES:
                if len(parts) > 3:
                    filename = parts[3]
                    elements = [e for e in parts[4:] if e != "NULL"] or [filename.split(".")[0]]
                    self.logger.info("File-based potential: %s, elements=%s", filename, elements)
                    self.potential_downloader.download(elements, pair_style, filename, working_dir)
                break
