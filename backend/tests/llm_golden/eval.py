"""`make llm-eval`: run a real provider over the golden set. Opt-in; never in CI.

Env: LLM_EVAL_KIND (anthropic | openai_compatible), LLM_EVAL_BASE_URL, LLM_EVAL_API_KEY,
LLM_EVAL_MODEL (pinned id, e.g. claude-sonnet-5-5), optional LLM_EVAL_MAX_TOKENS and
LLM_EVAL_STRATEGY (skeptic | advocate). Prompt and schema come from app/llm/golden (shipped
in the image). Prints one JSON line per case, then the agreement with the expert classes
(#465); exits 1 if any case fails.
"""

import asyncio
import json
import os
import sys

from app.llm.providers import provider_registry
from app.models.llm import PromptTemplateVersion
from app.services.llm_runs import GOLDEN_DIR, load_golden, run_golden_case

HERE = GOLDEN_DIR


def golden_version(strategy: str = "skeptic") -> PromptTemplateVersion:
    system = "system.txt" if strategy == "skeptic" else "advocate.txt"
    return PromptTemplateVersion(
        system_text=(HERE / system).read_text(),
        user_text=(HERE / "user.txt").read_text(),
        output_schema=json.loads((HERE / "output_schema.json").read_text()),
    )


async def main() -> int:
    env = os.environ
    adapter = await provider_registry.acreate(
        env["LLM_EVAL_KIND"],
        base_url=env["LLM_EVAL_BASE_URL"],
        api_key=env["LLM_EVAL_API_KEY"],
        model=env["LLM_EVAL_MODEL"],
    )
    max_tokens = int(env.get("LLM_EVAL_MAX_TOKENS", "8192"))
    strategy = env.get("LLM_EVAL_STRATEGY", "skeptic")
    version = golden_version(strategy)
    cases = load_golden(HERE)
    failed = 0
    for case in cases:
        result = await run_golden_case(adapter, version, case, max_tokens, strategy)
        failed += not result["ok"]
        sys.stdout.write(json.dumps(result) + "\n")
    agreement = {
        "strategy": strategy,
        "passed": len(cases) - failed,
        "total": len(cases),
    }
    sys.stdout.write(json.dumps(agreement) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
