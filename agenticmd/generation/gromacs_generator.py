import json
import logging
import os
import re
from typing import Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agenticmd.core.interfaces import DocsFetcher, ScriptGenerator
from agenticmd.generation.gromacs_prompts import GROMACS_DRAFT_PROMPT, GROMACS_REFINE_PROMPT
from agenticmd.utils.llm import LLMComponent


def _parse_mdp_keywords(script: str) -> Dict[str, str]:
    """Extract MDP keyword → full line from inside heredoc blocks targeting *.mdp files."""
    keywords: Dict[str, str] = {}
    in_mdp = False
    for line in script.splitlines():
        stripped = line.strip()
        if re.search(r"cat\s*[>]+\s*\S+\.mdp", stripped):
            in_mdp = True
            continue
        if in_mdp and re.match(r"^EOF\s*$", stripped):
            in_mdp = False
            continue
        if in_mdp and "=" in stripped and not stripped.startswith(";"):
            kw = stripped.split("=")[0].strip().lower().replace("-", "_")
            if kw and kw not in keywords:
                keywords[kw] = stripped
    return keywords


def _parse_gmx_commands(script: str) -> Dict[str, str]:
    """Extract gmx tool name → first full command line (e.g. 'grompp' → 'gmx grompp ...')."""
    commands: Dict[str, str] = {}
    for line in script.splitlines():
        stripped = line.strip()
        parts = stripped.split()
        if len(parts) >= 2 and parts[0] == "gmx":
            tool = parts[1]
            if tool not in commands:
                commands[tool] = stripped
    return commands


class GROMACSScriptGenerator(LLMComponent, ScriptGenerator):
    """
    Two-pass bash script generator for GROMACS (Template Method pattern):
      1. Draft    — LLM writes a bash script from its own knowledge.
      2. Extract  — parse MDP keywords + gmx tool names from the draft.
      3. Retrieve — fetch official docs for each item via DocsFetcher.
      4. Refine   — LLM corrects the draft using the retrieved docs.
    """

    def __init__(
        self,
        llm: ChatOpenAI,
        docs_fetcher: DocsFetcher,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(llm, logger)
        self.docs_fetcher = docs_fetcher

    def generate(self, problem: str, task: dict, working_dir: str) -> str:
        os.makedirs(working_dir, exist_ok=True)

        self.logger.info("Generating GROMACS draft script.")
        draft = self._draft(problem, task)

        mdp_keywords = _parse_mdp_keywords(draft)
        gmx_commands = _parse_gmx_commands(draft)
        self.logger.info(
            "Extracted %d MDP keywords, %d gmx commands.",
            len(mdp_keywords), len(gmx_commands),
        )

        docs: Dict[str, str] = {}
        for kw, full_line in mdp_keywords.items():
            docs[kw] = self.docs_fetcher.fetch(kw, full_line)
        for tool, full_line in gmx_commands.items():
            docs[f"gmx {tool}"] = self.docs_fetcher.fetch(tool, full_line)
        self.logger.info("Documentation retrieved for %d items.", len(docs))

        self.logger.info("Refining GROMACS script with documentation.")
        return self._refine(draft, docs, problem, task)

    # ------------------------------------------------------------------

    def _draft(self, problem: str, task: dict) -> str:
        result = self._call_llm("GROMACSdraft", [
            SystemMessage(content=GROMACS_DRAFT_PROMPT),
            HumanMessage(content=f"Problem: {problem}\nTask: {json.dumps(task)}"),
        ])
        return result.content

    def _refine(self, draft: str, docs: dict, problem: str, task: dict) -> str:
        user_prompt = (
            f"Problem: {problem}\nTask: {json.dumps(task)}\n\n"
            f"Draft script:\n{draft}\n\n"
            f"Command and keyword documentation:\n{json.dumps(docs, indent=2)}"
        )
        result = self._call_llm("GROMACSrefine", [
            SystemMessage(content=GROMACS_REFINE_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        return result.content
