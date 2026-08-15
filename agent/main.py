"""
agent/main.py
─────────────────────────────────────────────────────────────────────────────
N+1 Query Resolver Agent — Entry Point
─────────────────────────────────────────────────────────────────────────────
This script bootstraps the autonomous agent using the Google Antigravity SDK.

The agent is configured to:
  1. Read the Express route file from the sandbox.
  2. Identify the N+1 query antipattern (a DB call inside a for-loop).
  3. Rewrite the file with a single optimized MongoDB `$in` batch query.
  4. Ask for user confirmation before writing any changes (safety hook).

Usage:
  python agent/main.py

Prerequisites:
  - Python virtual environment activated (venv/)
  - google-antigravity SDK installed (pip install google-antigravity)
─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import sys
from pathlib import Path

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

# ─────────────────────────────────────────────────────────────────────────────
# Path Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Root of the project (one level up from /agent)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The specific Express route file the agent will analyze and optimize
TARGET_ROUTE_FILE = PROJECT_ROOT / "sandbox" / "src" / "routes" / "users.js"


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""
You are an expert backend performance engineer and autonomous code optimization agent.

Your ONLY objective is to detect and fix the N+1 database query antipattern in the
following Express.js route file:

  {TARGET_ROUTE_FILE}

## What is the N+1 Problem?
The N+1 problem occurs when code fetches a list of N items (1 query), and then
executes an additional database query for EACH item inside a loop (N queries).
Total = 1 + N round-trips to the database, which scales catastrophically.

## Your Task — Step by Step:
1. READ the file at the path above using your file reading tool.
2. ANALYZE the code to locate the for-loop that fires a MongoDB query on each iteration.
3. PLAN the fix: Replace the loop with a single optimized query using MongoDB's `$in`
   operator to batch-fetch all related documents in one round-trip.
4. WRITE the optimized version back to the same file. You MUST request user
   permission before writing, as per your safety policy.

## The Optimized Pattern You Must Produce:
Instead of:
  for (const user of users) {{
    const posts = await Post.find({{ userId: user._id }}).lean();
  }}

You must produce:
  const userIds = users.map(u => u._id);
  const allPosts = await Post.find({{ userId: {{ $in: userIds }} }}).lean();
  // Then group posts by userId in memory using a Map

## Critical Rules:
- Do NOT modify any other file. Only touch the target route file.
- Preserve ALL existing comments and code structure outside the N+1 loop.
- Update the `queryStrategy` field in the response JSON to "OPTIMIZED ($in batch query)".
- Update the `totalQueries` field to always be `2` (1 for users + 1 for posts).
- Be autonomous — do not ask for clarification. Proceed directly with the plan.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent Bootstrap
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 70)
    print("  🤖  N+1 Query Resolver Agent")
    print("=" * 70)
    print(f"  Target: {TARGET_ROUTE_FILE}")
    print("=" * 70)
    print()

    # LocalAgentConfig wires the system prompt and enables write capabilities.
    # CapabilitiesConfig() is required to unlock file I/O and run_command tools.
    config = LocalAgentConfig(
        system_instructions=SYSTEM_PROMPT,
        capabilities=CapabilitiesConfig(),
    )

    async with Agent(config) as agent:
        print("✅  Agent initialized. Starting autonomous analysis...\n")

        # Trigger the agent with a concise task description.
        # The system prompt carries all the detailed instructions.
        response = await agent.chat(
            f"Begin your analysis. The target file is: {TARGET_ROUTE_FILE}\n"
            "Read it, identify the N+1 antipattern, and apply the $in optimization."
        )

        # Stream response tokens to stdout in real time
        print("─" * 70)
        print("  Agent Output:")
        print("─" * 70)
        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()
        print()
        print("─" * 70)
        print("✅  Agent run complete.")


if __name__ == "__main__":
    asyncio.run(main())
