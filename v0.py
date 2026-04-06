import argparse
import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agenticmd.agent import MDAgent
from agenticmd.docs import GROMACSDocScraper, GitHubPotentialDownloader, LAMMPSDocScraper
from agenticmd.generation import DraftRefineScriptGenerator, GROMACSScriptGenerator, LLMScriptFixer
from agenticmd.generation.gromacs_prompts import GROMACS_SCRIPT_FIX_PROMPT
from agenticmd.postprocessing import LLMPostProcessor
from agenticmd.simulation import GROMACSSubprocessRunner, LAMMPSServerRunner
from agenticmd.utils import get_logger


@dataclass
class TaskSpec:
    id: str
    problem_description: str
    metrics: List[str]

    @classmethod
    def from_dict(cls, payload: Dict) -> "TaskSpec":
        return cls(
            id=payload["id"],
            problem_description=payload["problem_description"],
            metrics=payload.get("metrics", []),
        )


def load_tasks(path: str) -> List[TaskSpec]:
    with open(path) as f:
        return [TaskSpec.from_dict(t) for t in json.load(f)]


def build_agent(engine: str, llm: ChatOpenAI, logger) -> MDAgent:
    """Factory: wire components for the chosen simulation engine."""
    if engine == "lammps":
        generator = DraftRefineScriptGenerator(
            llm=llm,
            docs_fetcher=LAMMPSDocScraper(logger),
            potential_downloader=GitHubPotentialDownloader(logger),
            logger=logger,
        )
        runner = LAMMPSServerRunner(logger=logger)
        fixer = LLMScriptFixer(llm, logger)
    elif engine == "gromacs":
        generator = GROMACSScriptGenerator(
            llm=llm,
            docs_fetcher=GROMACSDocScraper(logger),
            logger=logger,
        )
        runner = GROMACSSubprocessRunner(logger=logger)
        fixer = LLMScriptFixer(llm, logger, fix_prompt=GROMACS_SCRIPT_FIX_PROMPT)
    else:
        raise ValueError(f"Unknown engine: {engine!r}. Choose 'lammps' or 'gromacs'.")

    return MDAgent(
        generator=generator,
        fixer=fixer,
        runner=runner,
        processor=LLMPostProcessor(llm, logger),
        max_retries=3,
        logger=logger,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AgenticMD — agentic molecular dynamics simulation framework"
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to tasks JSON file",
    )
    parser.add_argument(
        "--engine",
        choices=["lammps", "gromacs"],
        default="lammps",
        help="Simulation engine to use (default: lammps)",
    )
    parser.add_argument(
        "--workspace",
        default="workspace",
        help="Base directory for task working directories (default: workspace)",
    )
    parser.add_argument(
        "--logs",
        default="logs/latest",
        help="Directory for log files (default: logs/latest)",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    llm = ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=os.getenv("OPENAI_API_KEY"))
    os.makedirs(args.logs, exist_ok=True)

    for task in load_tasks(args.tasks):
        logger = get_logger(
            f"agenticmd.{task.id}",
            log_path=os.path.join(args.logs, f"{task.id}.log"),
        )
        metrics = build_agent(args.engine, llm, logger).run(asdict(task), base_dir=args.workspace)
        logger.info("Completed | metrics=%s", metrics)


if __name__ == "__main__":
    main()
