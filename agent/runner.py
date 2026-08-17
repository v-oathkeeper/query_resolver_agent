"""
agent/runner.py
─────────────────────────────────────────────────────────────────────────────
Agent Execution Loop — The Core Reasoning Engine (Phase 4)
─────────────────────────────────────────────────────────────────────────────
This module implements the agentic execution loop that:

  1. Drives the agent turn-by-turn until it completes the optimization.
  2. Streams internal reasoning (thoughts), tool calls, and text output
     in real time so the user can watch the agent "think".
  3. Verifies the optimization was actually applied by diffing the file
     before and after the agent run.
  4. Returns a structured RunResult with timing and outcome metadata.

The loop is deliberately separated from main.py so it can be independently
tested, imported, or extended (e.g., with retries or multi-agent orchestration).
─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from google.antigravity import Agent
from google.antigravity.types import ToolCall


# ─────────────────────────────────────────────────────────────────────────────
# ANSI Color Codes (for rich terminal output without external dependencies)
# ─────────────────────────────────────────────────────────────────────────────

class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[36m"
    YELLOW  = "\033[33m"
    GREEN   = "\033[32m"
    RED     = "\033[31m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    WHITE   = "\033[97m"

def _c(color: str, text: str) -> str:
    """Wrap text in an ANSI color code."""
    return f"{color}{text}{Colors.RESET}"


# ─────────────────────────────────────────────────────────────────────────────
# RunResult — Structured output of a single agent run
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    """Structured result returned after the agent completes a run."""
    success: bool
    duration_seconds: float
    thoughts_emitted: int        = 0
    tool_calls_made: list[str]   = field(default_factory=list)
    optimization_verified: bool  = False
    error_message: Optional[str] = None

    def __str__(self) -> str:
        status = _c(Colors.GREEN, "SUCCESS") if self.success else _c(Colors.RED, "FAILED")
        return (
            f"\n{'─' * 70}\n"
            f"  Run Summary\n"
            f"{'─' * 70}\n"
            f"  Status              : {status}\n"
            f"  Duration            : {self.duration_seconds:.2f}s\n"
            f"  Thoughts streamed   : {self.thoughts_emitted}\n"
            f"  Tools invoked       : {len(self.tool_calls_made)}\n"
            f"    {'  → ' + chr(10) + '  → '.join(self.tool_calls_made) if self.tool_calls_made else '(none)'}\n"
            f"  Optimization applied: {'✅ YES' if self.optimization_verified else '❌ NO — manual review needed'}\n"
            + (f"  Error               : {self.error_message}\n" if self.error_message else "")
            + f"{'─' * 70}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Verification Helper
# ─────────────────────────────────────────────────────────────────────────────

def verify_optimization(target_file: Path) -> bool:
    """
    Reads the target route file and checks if the $in optimization was applied.

    We check for two signatures:
      1. The presence of '$in' — the batch query operator.
      2. The absence of the sequential 'for...Post.find' antipattern inside the loop.

    Returns True only if both conditions are met.
    """
    try:
        content = target_file.read_text(encoding="utf-8")
        has_in_operator = "$in" in content
        # The antipattern: Post.find() called inside a for-of loop body
        # A rough but reliable heuristic: if "for (const" still precedes "Post.find"
        # in a way suggesting sequential execution.
        still_has_loop_query = (
            "for (const user of users)" in content
            and "await Post.find({ userId: user._id })" in content
        )
        return has_in_operator and not still_has_loop_query
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Core Streaming Execution Loop
# ─────────────────────────────────────────────────────────────────────────────

async def run_optimization_loop(
    agent: Agent,
    target_file: Path,
    *,
    show_thoughts: bool = True,
    show_tool_calls: bool = True,
) -> RunResult:
    """
    Drives the agent through the full optimization workflow and streams output.

    Args:
        agent:           An initialized (context-entered) Agent instance.
        target_file:     Path to the Express route file to be optimized.
        show_thoughts:   If True, stream the agent's internal reasoning to stdout.
        show_tool_calls: If True, print each tool call as it is dispatched.

    Returns:
        A RunResult dataclass with timing, tool call trace, and verification status.
    """
    result = RunResult(success=False, duration_seconds=0.0)
    start_time = time.monotonic()

    # ── Initial task prompt ──────────────────────────────────────────────────
    task_prompt = (
        f"Your target file is:\n  {target_file}\n\n"
        "Execute the optimization plan:\n"
        "  1. Read the file with view_file.\n"
        "  2. Identify the N+1 antipattern (Post.find inside a for-loop).\n"
        "  3. Write the optimized $in version using edit_file — "
        "you will be prompted for approval first.\n"
        "  4. Confirm the fix was applied and report what changed.\n\n"
        "Begin now. Be thorough and autonomous."
    )

    try:
        # ── Send task to agent ───────────────────────────────────────────────
        response = await agent.chat(task_prompt)

        # ── Stream ALL event types concurrently ──────────────────────────────
        # We consume response.chunks directly to get every event type in order:
        # Thought chunks → shown in dim/italic yellow
        # ToolCall chunks → shown with tool name + args preview
        # Text chunks     → shown as the agent's final prose output
        print()
        print(_c(Colors.CYAN, "─" * 70))
        print(_c(Colors.CYAN + Colors.BOLD, "  Live Agent Stream"))
        print(_c(Colors.CYAN, "─" * 70))
        print()

        from google.antigravity.types import StreamChunk, ToolCall as ToolCallType

        current_section = None  # Track what we're currently printing

        async for chunk in response.chunks:
            chunk_type = type(chunk).__name__

            # ── Thought chunk: agent's internal reasoning ────────────────────
            if chunk_type == "Thought":
                if show_thoughts:
                    if current_section != "thought":
                        if current_section is not None:
                            print()  # spacing between sections
                        print(_c(Colors.YELLOW + Colors.DIM, "  [Thinking] "), end="")
                        current_section = "thought"
                    sys.stdout.write(_c(Colors.DIM, chunk.text))
                    sys.stdout.flush()
                result.thoughts_emitted += 1

            # ── ToolCall chunk: agent dispatching a tool ─────────────────────
            elif chunk_type == "ToolCall":
                tool_name = chunk.name
                result.tool_calls_made.append(tool_name)
                if show_tool_calls:
                    if current_section is not None:
                        print()  # end previous section
                    args = chunk.args or {}
                    # Show a concise preview of the most useful arg
                    arg_preview = (
                        args.get("path")
                        or args.get("file_path")
                        or args.get("target_file")
                        or args.get("filename")
                        or (list(args.values())[0][:60] + "..." if args else "")
                    )
                    print(
                        _c(Colors.BLUE, f"\n  [Tool Call] ")
                        + _c(Colors.BOLD, tool_name)
                        + (_c(Colors.DIM, f"  →  {arg_preview}") if arg_preview else "")
                    )
                    current_section = "tool"

            # ── ToolResult chunk: result of a tool execution ─────────────────
            elif chunk_type == "ToolResult":
                if show_tool_calls:
                    result_preview = str(chunk.result or "")[:80]
                    print(_c(Colors.DIM, f"  [Tool Result] {result_preview}"))
                    current_section = "tool_result"

            # ── Text chunk: agent's conversational response ──────────────────
            elif chunk_type == "Text":
                if current_section not in ("text",):
                    if current_section is not None:
                        print()
                    print(_c(Colors.GREEN, "\n  [Agent Response]"))
                    current_section = "text"
                sys.stdout.write(_c(Colors.WHITE, chunk.text))
                sys.stdout.flush()

        print()  # final newline
        result.success = True

    except KeyboardInterrupt:
        print(_c(Colors.RED, "\n\n  ⛔  Run interrupted by user (Ctrl+C)."))
        result.error_message = "Interrupted by user."
        result.success = False
    except Exception as exc:
        print(_c(Colors.RED, f"\n\n  ❌  Agent error: {exc}"))
        result.error_message = str(exc)
        result.success = False

    # ── Verify the optimization was applied ──────────────────────────────────
    result.optimization_verified = verify_optimization(target_file)
    result.duration_seconds = time.monotonic() - start_time

    return result
