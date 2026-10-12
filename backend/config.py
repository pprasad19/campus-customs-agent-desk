"""Model wiring and run limits for the Campus Customs team.

Every agent in this homework talks to gpt-6-luna through Portkey, using
PORTKEY_API_KEY from a .env. The model name is a hard-coded
constant on purpose: there is no environment override, so no other model can
slip into a run by way of a stray variable.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

# Homework 5/backend/config.py -> Homework 5/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Look for the .env inside this folder first, so the homework works as a
# self-contained project when it is handed in on its own. Fall back to the
# class-folder .env one level up, which is where the key lives during the term.
# The first file found wins; neither is required to exist at import time, and a
# missing key is reported by build_model() rather than here.
for _env_path in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"):
    if _env_path.exists():
        load_dotenv(_env_path)
        break

MCP_CONFIG_PATH = PROJECT_ROOT / ".mcp.json"
OUTPUT_DIR = PROJECT_ROOT / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# The only model permitted anywhere in this homework.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# Reasoning has to be switched off for this deployment.
#
# gpt-6-luna is served here through Azure OpenAI, and that deployment rejects
# any /v1/chat/completions request that carries BOTH function tools and a
# reasoning_effort, with:
#
#   "Function tools with reasoning_effort are not supported for
#    gpt-6-luna-global in /v1/chat/completions. To use function tools, use
#    /v1/responses or set reasoning_effort to 'none'."
#
# Every agent on this team uses tools — that is the whole design — so the
# effort is pinned to 'none' and pydantic-ai stops sending reasoning with the
# request. The alternative the error suggests, switching to the /v1/responses
# endpoint, is a larger change for no benefit here.
MODEL_SETTINGS = OpenAIChatModelSettings(openai_reasoning_effort="none")


# --------------------------------------------------------------------------
# Token and loop limits
# --------------------------------------------------------------------------
#
# A team of five agents that can all call each other will happily talk forever.
# These caps are the difference between a run that costs cents and one that
# costs a lot, so they are set deliberately rather than left to chance.

# Connecting to the MCP server.
#
# The server is a separate Python process that has to import pydantic, fastmcp
# and sqlite before it can answer the protocol handshake — about five seconds
# cold, and longer while the machine is also running uvicorn, the Vite dev
# server and a model call. These windows are deliberately generous: the cost of
# waiting is a slow first tool call, while the cost of being too strict is the
# whole run failing with "Failed to initialize server session".
MCP_INIT_TIMEOUT_SECONDS = 120
MCP_READ_TIMEOUT_SECONDS = 120

MAX_DELEGATION_DEPTH = 3        # boss -> specialist -> specialist, then stop
MAX_DELEGATIONS_PER_RUN = 12    # shared across the whole team, not per agent

# One ceiling for the whole run, not one per agent.
#
# Delegated agents run with `usage=ctx.usage`, so every agent's tokens land in
# the same counter — that is what makes the token ceiling team-wide rather than
# per-agent. The consequence is that a smaller "per specialist" UsageLimits does
# not do what it looks like it does: it would be checked against the team's
# accumulated usage, so a limit of 8 requests stops the run as soon as the team
# as a whole has made 8, regardless of which agent is asking. Every run
# therefore shares these limits, and runaway delegation is held back by
# MAX_DELEGATION_DEPTH and MAX_DELEGATIONS_PER_RUN instead, which count the
# thing actually at risk of looping.
TEAM_USAGE_LIMITS = UsageLimits(
    request_limit=100,           # total model calls across the entire team run
    tool_calls_limit=160,        # total MCP tool calls across the entire run
    total_tokens_limit=750_000,  # hard ceiling; the run stops rather than overspends
)


def build_model() -> OpenAIChatModel:
    """Return a gpt-6-luna model routed through Portkey.

    Raises if the key is missing rather than silently falling back to a
    different provider or model.
    """
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError(
            "PORTKEY_API_KEY is missing. Copy .env.example to .env in the "
            "Homework 5 folder and add the key."
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": api_key,
            "x-portkey-provider": "openai",
        },
    )
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt(role: str) -> str:
    """Read one agent's instructions from backend/prompts/<role>.md."""
    path = PROMPTS_DIR / f"{role}.md"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file for role {role!r} at {path}")
    return path.read_text(encoding="utf-8")
