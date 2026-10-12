"""Append-only audit trail for the Campus Customs team.

Every step of every agent loop lands in output/audit_trail.json. The file is a
JSON array that only ever grows: each run reads what is there, adds its own
lines, and writes the whole list back. Earlier runs are never wiped, so the
history of what the agents did survives across resets of the database.

What gets recorded, per step:
  * which agent acted, who asked it, and how deep the delegation went
  * the prompt it received and the text it produced
  * every MCP tool call, with arguments and the returned payload
  * token and request usage, so cost is auditable too
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AUDIT_PATH, OUTPUT_DIR
from .models import AuditStep

# Long payloads are trimmed so one run cannot produce an unreadable file. The
# limit is generous enough to keep whole tool results and agent answers.
MAX_FIELD_CHARS = 4000


def _trim(value: Any) -> Any:
    """Keep the record readable without throwing away the substance."""
    if isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        return value[:MAX_FIELD_CHARS] + f"... [trimmed, {len(value)} chars total]"
    if isinstance(value, dict):
        return {k: _trim(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_trim(v) for v in value]
    return value


class AuditTrail:
    """Collects steps for one run and appends them to the shared file."""

    def __init__(self, run_id: str, shop_date: str, path: Path | None = None) -> None:
        self.run_id = run_id
        self.shop_date = shop_date
        self.path = path or AUDIT_PATH
        self._seq = 0

    # -- writing -----------------------------------------------------------

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def record(
        self,
        *,
        agent: str,
        caller: str,
        depth: int,
        step_type: str,
        detail: dict[str, Any] | None = None,
        usage: dict[str, Any] | None = None,
    ) -> None:
        """Append exactly one step. Nothing already in the file is touched."""
        step = AuditStep(
            run_id=self.run_id,
            seq=self._next_seq(),
            recorded_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            shop_date=self.shop_date,
            agent=agent,
            caller=caller,
            depth=depth,
            step_type=step_type,
            detail=_trim(detail or {}),
            usage=usage or {},
        )
        self._append(step.model_dump())

    def _append(self, record: dict[str, Any]) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        existing: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                existing = loaded if isinstance(loaded, list) else [loaded]
            except json.JSONDecodeError:
                # A corrupt file must not cost us the new record, and must not
                # be silently deleted either. Keep it beside the trail.
                broken = self.path.with_suffix(".corrupt.json")
                broken.write_text(self.path.read_text(encoding="utf-8"), encoding="utf-8")
                existing = [{
                    "note": "previous audit_trail.json was not valid JSON",
                    "preserved_copy": broken.name,
                }]
        existing.append(record)

        # Written to a sibling temp file, then renamed into place. A plain write
        # truncates the file and refills it, leaving the trail unreadable for as
        # long as that takes — and at a few megabytes that window is real. A
        # Ctrl-C landing inside it would leave invalid JSON, and the recovery
        # path above would then start a fresh list and lose every step ever
        # recorded. os.replace is atomic on Windows and POSIX alike, so a reader
        # sees either the old file or the new one, never a half-written one.
        # Nothing about the format on disk changes.
        tmp = self.path.with_name(self.path.name + ".writing")
        tmp.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    # -- extracting agent-loop steps ---------------------------------------

    def record_agent_messages(
        self, *, agent: str, caller: str, depth: int, messages: list[Any],
        skip_live: bool = True,
    ) -> None:
        """Turn one agent run's message history into individual audit steps.

        Each model response, each tool call and each tool result becomes its own
        line, so the loop can be replayed later rather than summarised.

        Anything the live handler already recorded is skipped, so a step is not
        written twice. Only the prompt each agent received is always taken from
        here, because no event carries it.
        """
        for message in messages:
            for part in getattr(message, "parts", []):
                part_name = type(part).__name__

                if part_name in ("TextPart", "ThinkingPart", "ToolCallPart", "ToolReturnPart")                         and skip_live:
                    continue

                if part_name == "UserPromptPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="agent_started",
                        detail={"prompt_received": _as_text(getattr(part, "content", ""))},
                    )
                elif part_name == "TextPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="model_response",
                        detail={"text": _as_text(getattr(part, "content", ""))},
                    )
                elif part_name == "ThinkingPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="model_response",
                        detail={"thinking": _as_text(getattr(part, "content", ""))},
                    )
                elif part_name == "ToolCallPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="tool_call",
                        detail={
                            "tool_name": getattr(part, "tool_name", None),
                            "tool_args": _as_args(getattr(part, "args", None)),
                            "tool_call_id": getattr(part, "tool_call_id", None),
                        },
                    )
                elif part_name == "ToolReturnPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="tool_result",
                        detail={
                            "tool_name": getattr(part, "tool_name", None),
                            "tool_call_id": getattr(part, "tool_call_id", None),
                            "result": _as_args(getattr(part, "content", None)),
                        },
                    )
                elif part_name == "RetryPromptPart":
                    self.record(
                        agent=agent, caller=caller, depth=depth, step_type="refusal",
                        detail={
                            "tool_name": getattr(part, "tool_name", None),
                            "retry_reason": _as_text(getattr(part, "content", "")),
                        },
                    )


    def live_handler(self, *, agent: str, caller: str, depth: int):
        """Return an event_stream_handler that records steps as they happen.

        Without this, an agent's whole message history is only written once its
        run returns — so a two-minute run shows nothing on the board until it is
        over, and the dashboard looks hung rather than busy. This writes each
        tool call and each answer the moment the framework emits it.

        Steps recorded here are tagged `live` so the post-run pass can skip
        them and the same work is not logged twice.
        """

        async def handler(ctx: Any, stream: Any) -> None:
            async for event in stream:
                name = type(event).__name__
                try:
                    if name in ("FunctionToolCallEvent", "ToolCallEvent"):
                        part = getattr(event, "part", None)
                        self.record(
                            agent=agent, caller=caller, depth=depth,
                            step_type="tool_call",
                            detail={
                                "live": True,
                                "tool_name": getattr(part, "tool_name", None),
                                "tool_args": _as_args(getattr(part, "args", None)),
                                "tool_call_id": getattr(part, "tool_call_id", None),
                            },
                        )
                    elif name in ("FunctionToolResultEvent", "ToolResultEvent"):
                        result = getattr(event, "result", None)
                        self.record(
                            agent=agent, caller=caller, depth=depth,
                            step_type="tool_result",
                            detail={
                                "live": True,
                                "tool_name": getattr(result, "tool_name", None),
                                "tool_call_id": getattr(result, "tool_call_id", None),
                                "result": _as_args(getattr(result, "content", None)),
                            },
                        )
                    elif name == "PartStartEvent":
                        part = getattr(event, "part", None)
                        if type(part).__name__ == "TextPart":
                            text = _as_text(getattr(part, "content", ""))
                            if text.strip():
                                self.record(
                                    agent=agent, caller=caller, depth=depth,
                                    step_type="model_response",
                                    detail={"live": True, "text": text},
                                )
                except Exception:  # noqa: BLE001 - logging must never break a run
                    continue

        return handler


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_as_text(v) for v in value)
    return str(value)


def _as_args(value: Any) -> Any:
    """Tool args arrive as a JSON string or a dict depending on the model."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def usage_dict(usage: Any) -> dict[str, Any]:
    """Flatten a pydantic-ai usage object into something JSON can hold."""
    if usage is None:
        return {}
    out: dict[str, Any] = {}
    for key in ("requests", "tool_calls", "input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if value is not None:
            out[key] = value
    return out
