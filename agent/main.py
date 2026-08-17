"""
agent/main.py
─────────────────────────────────────────────────────────────────────────────
N+1 Query Resolver Agent — Entry Point  (Phase 4: Core Agent Logic)
─────────────────────────────────────────────────────────────────────────────
Autonomous agent that scans an Express.js codebase, detects the N+1 MongoDB
query antipattern, and rewrites the route file with a single optimized $in
batch query — all with user approval gating before any file is touched.

Usage
─────
  # Activate the virtual environment first
  .\\venv\\Scripts\\activate          # Windows
  source venv/bin/activate          # macOS / Linux

  # Run the agent
  python agent/main.py

Prerequisites
─────────────
  - google-antigravity SDK   →  pip install -r agent/requirements.txt
  - MongoDB running locally   →  mongod  (or Docker: docker run -p 27017:27017 mongo)
  - Sandbox seeded            →  cd sandbox && npm install && npm run seed

Architecture
────────────
  main.py         ← You are here. Bootstrap + config.
  hooks.py        ← Declarative ask_user safety policies.
  runner.py       ← Core streaming agentic execution loop.

  ┌──────────────────────────────────────────────────────────────────────┐
  │                         Agent Lifecycle                              │
  │                                                                      │
  │  main.py               runner.py                  hooks.py          │
  │  ┌──────────┐          ┌──────────────────────┐   ┌──────────────┐  │
  │  │ Config   │─────────▶│ run_optimization_loop│──▶│ ask_user gate│  │
  │  │ (system  │          │                      │   │              │  │
  │  │  prompt  │          │ • Stream Thoughts     │   │ user must    │  │
  │  │  policies│          │ • Stream ToolCalls    │   │ approve y/n  │  │
  │  │  hooks)  │          │ • Stream Text         │   │ before write │  │
  │  └──────────┘          │ • Verify optimization │   └──────────────┘  │
  │                        └──────────────────────┘                      │
  └──────────────────────────────────────────────────────────────────────┘
─────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import sys
from pathlib import Path

from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig

# Phase 3: Declarative safety policies (ask_user before any file write)
from hooks import WRITE_SAFETY_POLICIES

# Phase 4: The core agentic execution loop
from runner import run_optimization_loop, Colors, _c


# ─────────────────────────────────────────────────────────────────────────────
# Path Configuration
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT      = Path(__file__).resolve().parent.parent
TARGET_ROUTE_FILE = PROJECT_ROOT / "sandbox" / "src" / "routes" / "users.js"


# ─────────────────────────────────────────────────────────────────────────────
# System Prompt — The Agent's Brain
# ─────────────────────────────────────────────────────────────────────────────
# This is the most critical part of Phase 4. The system prompt is the agent's
# complete mental model of its task. It must be:
#   • Specific enough that the agent writes exactly the right code.
#   • Flexible enough that it can adapt to what it actually reads in the file.
#   • Safe: it names the one file to touch and no others.

SYSTEM_PROMPT = f"""
You are an expert backend performance engineer and an autonomous code optimization agent.
You have deep knowledge of MongoDB, Mongoose, Node.js, and database query optimization.

═══════════════════════════════════════════════════════════════════════════════
MISSION
═══════════════════════════════════════════════════════════════════════════════
Detect and eliminate the N+1 database query antipattern in this specific file:

  TARGET FILE: {TARGET_ROUTE_FILE}

This is your ONLY objective. Touch no other file.

═══════════════════════════════════════════════════════════════════════════════
BACKGROUND: THE N+1 PROBLEM
═══════════════════════════════════════════════════════════════════════════════
The N+1 problem is one of the most destructive database antipatterns:

  Step 1: ONE query fetches all N parent records (e.g., all users).
  Step 2: A for-loop runs N separate queries, one per parent record.
  Total:  1 + N database round-trips. With 50 users = 51 queries. With
          1,000 users = 1,001 queries. Latency grows linearly with N.

The fix is a single batch query using MongoDB's $in operator:
  Post.find({{ userId: {{ $in: userIds }} }})
This fetches ALL child records in exactly ONE round-trip, regardless of N.

═══════════════════════════════════════════════════════════════════════════════
YOUR EXACT EXECUTION PLAN — FOLLOW THIS PRECISELY
═══════════════════════════════════════════════════════════════════════════════

STEP 1 — READ
  Call view_file on: {TARGET_ROUTE_FILE}
  Read every line carefully. Identify the exact for-loop causing the N+1 issue.

STEP 2 — ANALYZE
  Locate these specific elements in the code:
    a) The variable name of the users array (likely `users`)
    b) The model name used for the child query (likely `Post`)
    c) The foreign key field name (likely `userId`)
    d) What the loop pushes into the results array

STEP 3 — PLAN
  Mentally construct the optimized version. The pattern you must produce:

  // ─── OPTIMIZED: Single $in batch query replaces the N+1 loop ───────────
  // Step A: Collect all parent IDs upfront
  const userIds = users.map(u => u._id);

  // Step B: ONE query fetches ALL child records in a single DB round-trip
  const allPosts = await Post.find({{ userId: {{ $in: userIds }} }}).lean();

  // Step C: Group child records in memory with a Map — O(n), zero extra queries
  const postsByUserId = new Map();
  for (const post of allPosts) {{
    const key = post.userId.toString();
    if (!postsByUserId.has(key)) postsByUserId.set(key, []);
    postsByUserId.get(key).push(post);
  }}

  // Step D: Build the results array from the in-memory Map
  const results = users.map(user => {{
    const posts = postsByUserId.get(user._id.toString()) || [];
    return {{
      userId: user._id,
      name:   user.name,
      email:  user.email,
      posts,
      postCount: posts.length,
    }};
  }});

STEP 4 — WRITE
  Use the edit_file tool to apply the optimization. You will be asked for
  explicit user approval before the write executes — wait for it.

  When writing the optimized file:
    ✓ KEEP all the existing header comments about the N+1 problem (they serve
      as documentation of the "before" state).
    ✓ ADD a new comment block above the optimized code labelled:
      "OPTIMIZED: Replaced N+1 loop with single MongoDB $in batch query"
    ✓ CHANGE `queryStrategy` in the JSON response to: "OPTIMIZED ($in batch query)"
    ✓ CHANGE `totalQueries` to always be exactly `2`
    ✓ REMOVE the old for-loop that calls Post.find inside it
    ✗ DO NOT touch any other file, model, or route

STEP 5 — VERIFY & REPORT
  After writing, read the file again with view_file to confirm the change
  was applied. Then write a concise summary:
    • What the antipattern was and where it was found
    • What the optimized code does differently
    • The theoretical improvement: N+1 → 2 queries (from ~51 to 2 with 50 users)

═══════════════════════════════════════════════════════════════════════════════
CONSTRAINTS
═══════════════════════════════════════════════════════════════════════════════
  • Only modify: {TARGET_ROUTE_FILE}
  • Be fully autonomous — do not ask for clarification, just execute.
  • If you encounter an error, report it clearly and stop.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Banner Printer
# ─────────────────────────────────────────────────────────────────────────────

def print_banner() -> None:
    print()
    print(_c(Colors.CYAN, "═" * 70))
    print(_c(Colors.BOLD + Colors.WHITE, "  🤖  N+1 QUERY RESOLVER AGENT"))
    print(_c(Colors.DIM,  "  Autonomous Backend Performance Optimizer"))
    print(_c(Colors.CYAN, "═" * 70))
    print(_c(Colors.DIM,  f"  Target  :  {TARGET_ROUTE_FILE}"))
    print(_c(Colors.DIM,   "  Safety  :  write approval required (ask_user hook)"))
    print(_c(Colors.DIM,   "  Streams :  thoughts  ·  tool calls  ·  text output"))
    print(_c(Colors.CYAN, "═" * 70))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Preflight Checks
# ─────────────────────────────────────────────────────────────────────────────

def preflight_checks() -> bool:
    """Verify prerequisites before spinning up the agent."""
    ok = True

    if not TARGET_ROUTE_FILE.exists():
        print(_c(Colors.RED,
            f"  ❌  Target file not found: {TARGET_ROUTE_FILE}\n"
            "      Have you run `cd sandbox && npm install`?"
        ))
        ok = False
    else:
        print(_c(Colors.GREEN, f"  ✅  Target file exists: {TARGET_ROUTE_FILE.name}"))

    return ok


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print_banner()

    # ── Preflight ────────────────────────────────────────────────────────────
    if not preflight_checks():
        sys.exit(1)
    print()

    # ── Agent Config ─────────────────────────────────────────────────────────
    config = LocalAgentConfig(
        system_instructions=SYSTEM_PROMPT,

        # CapabilitiesConfig enables write tools (edit_file, create_file).
        # Without this, the agent is read-only by default.
        capabilities=CapabilitiesConfig(),

        # Safety policies from Phase 3: any write tool invocation must
        # first pass the ask_user gate defined in hooks.py.
        policies=WRITE_SAFETY_POLICIES,
    )

    # ── Run ──────────────────────────────────────────────────────────────────
    async with Agent(config) as agent:
        print(_c(Colors.GREEN, "  ✅  Agent initialized."))
        print(_c(Colors.DIM,   "  📡  Connecting to model..."))
        print()

        result = await run_optimization_loop(
            agent,
            TARGET_ROUTE_FILE,
            show_thoughts=True,
            show_tool_calls=True,
        )

    # ── Results ──────────────────────────────────────────────────────────────
    print(_c(Colors.CYAN, str(result)))

    if result.optimization_verified:
        print(_c(Colors.GREEN,
            "\n  🎉  Optimization confirmed! Run the k6 benchmark to measure the speedup."
            "\n      cd sandbox && npm start"
            "\n      k6 run load_tests/test.js\n"
        ))
    else:
        print(_c(Colors.YELLOW,
            "\n  ⚠️   Optimization could not be auto-verified."
            "\n      Please manually inspect the target file.\n"
        ))

    sys.exit(0 if result.success else 1)


if __name__ == "__main__":
    asyncio.run(main())
