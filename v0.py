import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agenticmd.agent import MDAgent
from agenticmd.docs import GitHubPotentialDownloader, LAMMPSDocScraper
from agenticmd.generation import DraftRefineScriptGenerator, LLMScriptFixer
from agenticmd.postprocessing import LLMPostProcessor
from agenticmd.simulation import LAMMPSServerRunner
from agenticmd.utils import get_logger


@dataclass
class TaskSpec:
    id: str
    problem_description: str
    metrics: List[str]
    ground_truth: Dict[str, Any]
    categories: List[str] = field(default_factory=list)
    level: str = ""
    keywords: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: Dict) -> "TaskSpec":
        return cls(
            id=payload["id"],
            problem_description=payload["problem_description"],
            metrics=payload.get("metrics", []),
            ground_truth=payload.get("ground_truth", {}),
            categories=payload.get("categories", []),
            level=str(payload.get("level", "")),
            keywords=payload.get("keywords", []),
        )


def load_tasks(path: str) -> List[TaskSpec]:
    with open(path) as f:
        return [TaskSpec.from_dict(t) for t in json.load(f)]


def build_agent(llm: ChatOpenAI, logger) -> MDAgent:
    return MDAgent(
        generator=DraftRefineScriptGenerator(
            llm=llm,
            docs_fetcher=LAMMPSDocScraper(logger),
            potential_downloader=GitHubPotentialDownloader(logger),
            logger=logger,
        ),
        fixer=LLMScriptFixer(llm, logger),
        runner=LAMMPSServerRunner(logger=logger),
        processor=LLMPostProcessor(llm, logger),
        max_retries=3,
        logger=logger,
    )


def main() -> None:
    load_dotenv()
    llm = ChatOpenAI(model="gpt-5", temperature=0.0, openai_api_key=os.getenv("OPENAI_API_KEY"))

    tasks = load_tasks("Tasks/npt_ensemble.json")
    workspace = "workspace"
    logs_dir = "logs/latest"
    os.makedirs(logs_dir, exist_ok=True)

    for task in tasks:
        logger = get_logger(
            f"agenticmd.{task.id}",
            log_path=os.path.join(logs_dir, f"{task.id}.log"),
        )
        metrics = build_agent(llm, logger).run(asdict(task), base_dir=workspace)
        logger.info("Completed | metrics=%s", metrics)


if __name__ == "__main__":
    main()
