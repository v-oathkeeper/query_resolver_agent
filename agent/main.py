"""
agent/main.py
─────────────────────────────────────────────────────────────────────────────
N+1 Query Resolver Agent — Entry Point (Phase 3: Tooling & Permissions)
─────────────────────────────────────────────────────────────────────────────
This script bootstraps the autonomous agent using the Google Antigravity SDK.

The agent is configured to:
  1. Read the Express route file from the sandbox (read tools enabled).
  2. Identify the N+1 query antipattern (a DB call inside a for-loop).
  3. Request user permission BEFORE writing any changes (safety hook).
  4. Rewrite the file with a single optimized MongoDB `$in` batch query.

Safety Architecture:
  ┌──────────────┐   ┌───────────────────────────┐   ┌──────────────────┐
  │  Agent (LLM) │──▶│  hooks.py (ask_user gate) │──▶│  users.js on disk│
  │              │   │  ← user must approve y/n   │   │  (only if OK)    │
  └──────────────┘   └───────────────────────────┘   └──────────────────┘

Usage:
  python agent/main.py

Prerequisites:
  - Python virtual environment activated (venv/)
  - google-antigravity SDK installed  →  pip install -r agent/requirements.txt
  - MongoDB running locally           →  mongod
  - Node.js sandbox seeded            →  cd sandbox && npm install && npm run seed
─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import sys
from pathlib import Path

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
from google.antigravity.types import BuiltinTools

# Import our declarative safety policies (Phase 3)
from hooks import WRITE_SAFETY_POLICIES


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
1. READ the file at the path above using your `view_file` tool.
2. ANALYZE the code to locate the for-loop that fires a MongoDB query on each iteration.
3. PLAN the fix: Replace the loop with a single optimized query using MongoDB's `$in`
   operator to batch-fetch all related documents in one round-trip.
4. WRITE the optimized version back using the `edit_file` tool. You will be prompted
   for user confirmation before any write is executed — this is a safety gate.

## The Optimized Pattern You Must Produce:
Instead of:
  for (const user of users) {{
    const posts = await Post.find({{ userId: user._id }}).lean();
  }}

You must produce:
  // 1. Collect all user IDs into an array
  const userIds = users.map(u => u._id);

  // 2. Single batch query using $in — fetches ALL posts in one DB round-trip
  const allPosts = await Post.find({{ userId: {{ $in: userIds }} }}).lean();

  // 3. Group posts by userId in memory using a Map (O(n) — no extra DB calls)
  const postsByUserId = new Map();
  for (const post of allPosts) {{
    const key = post.userId.toString();
    if (!postsByUserId.has(key)) postsByUserId.set(key, []);
    postsByUserId.get(key).push(post);
  }}

  // 4. Build results array using the in-memory Map
  const results = users.map(user => {{
    const posts = postsByUserId.get(user._id.toString()) || [];
    return {{
      userId: user._id,
      name: user.name,
      email: user.email,
      posts,
      postCount: posts.length,
    }};
  }});

## Critical Rules:
- Do NOT modify any other file. Only touch the target route file.
- Preserve ALL existing comments explaining the N+1 problem (they document the "before").
- Add new comments explaining how the optimized `$in` approach works.
- Update the `queryStrategy` field in the response JSON to "OPTIMIZED ($in batch query)".
- Update the `totalQueries` field to always be `2` (1 for users + 1 for posts).
- Be autonomous — proceed directly with the plan, step by step.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Agent Bootstrap
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 70)
    print("  🤖  N+1 Query Resolver Agent  |  Phase 3: Tooling & Permissions")
    print("=" * 70)
    print(f"  Target : {TARGET_ROUTE_FILE}")
    print("  Safety : write_file requires user approval (ask_user hook active)")
    print("=" * 70)
    print()

    # CapabilitiesConfig() enables write tools (create_file, edit_file, run_command).
    # Without it the agent is read-only.
    config = LocalAgentConfig(
        system_instructions=SYSTEM_PROMPT,
        capabilities=CapabilitiesConfig(),

        # ── Safety Policies (Phase 3) ─────────────────────────────────────────
        # Declarative policies enforce that any call to `create_file` or
        # `edit_file` must first pass the ask_user gate defined in hooks.py.
        # The agent is allowed to call read tools freely (view_file, list_dir).
        policies=WRITE_SAFETY_POLICIES,
    )

    async with Agent(config) as agent:
        print("✅  Agent initialized with safety policies active.")
        print("📁  Read tools: ENABLED (no approval needed)")
        print("✏️   Write tools: GATED (user must approve each write)\n")

        # Trigger the agent with the task description.
        response = await agent.chat(
            f"Begin your analysis. The target file is:\n  {TARGET_ROUTE_FILE}\n\n"
            "Read it, identify the N+1 antipattern, plan the $in optimization, "
            "then request approval and apply the fix."
        )

        # ── Stream output ────────────────────────────────────────────────────
        print("─" * 70)
        print("  Agent Reasoning & Output:")
        print("─" * 70)

        async for token in response:
            sys.stdout.write(token)
            sys.stdout.flush()

        print()
        print("─" * 70)
        print("✅  Agent run complete.")


if __name__ == "__main__":
    asyncio.run(main())
