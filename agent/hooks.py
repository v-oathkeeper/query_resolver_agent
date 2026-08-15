"""
agent/hooks.py
─────────────────────────────────────────────────────────────────────────────
Declarative Safety Policies for the N+1 Query Resolver Agent
─────────────────────────────────────────────────────────────────────────────
This module implements the safety layer that sits BETWEEN the agent's reasoning
and any file-write action. Before the agent can modify any Express source file,
it MUST receive explicit terminal approval from the user.

Architecture:
  ┌──────────────────┐     ┌───────────────────────┐     ┌────────────────┐
  │  Agent (LLM)     │────▶│  PreToolCallDecideHook │────▶│  File on Disk  │
  │  wants to write  │     │  (this file)           │     │  (only if OK)  │
  └──────────────────┘     └───────────────────────┘     └────────────────┘
                                       │
                                       │ ask_user() → terminal prompt
                                       ▼
                               ┌───────────────┐
                               │     USER      │
                               │  [y/n] ?      │
                               └───────────────┘

The SDK's `ask_user()` helper creates an ASK_USER policy that, by default,
delegates approval to the host platform's UI. Since we are running in a
terminal (non-interactive CLI), we provide a custom `handler` that prints
a clear prompt and reads stdin input, giving the user full visibility and
control before any code is changed.
─────────────────────────────────────────────────────────────────────────────
"""

from google.antigravity.hooks.policy import Policy, Decision, ask_user
from google.antigravity.types import HookResult, BuiltinTools


# ─────────────────────────────────────────────────────────────────────────────
# Custom Ask-User Handler
# ─────────────────────────────────────────────────────────────────────────────

async def _confirm_write(tool_call) -> HookResult:
    """
    Terminal confirmation handler invoked before any file-write tool call.

    Displays the tool name and target file path, then prompts the user for
    explicit approval. Returns HookResult(allow=True) only if the user types
    'y' or 'yes'. All other input (including Enter alone) defaults to DENY.

    Args:
        tool_call: The ToolCall object from the SDK, containing .name and .args.

    Returns:
        HookResult — allow=True to proceed, allow=False to block.
    """
    tool_name = tool_call.name
    # Try to surface the file path from common arg names
    args = tool_call.args or {}
    file_path = (
        args.get("path")
        or args.get("file_path")
        or args.get("target_file")
        or args.get("filename")
        or "[unknown path]"
    )

    print("\n" + "=" * 70)
    print("  🔐  AGENT REQUESTING WRITE PERMISSION")
    print("=" * 70)
    print(f"  Tool     : {tool_name}")
    print(f"  Target   : {file_path}")
    print("=" * 70)
    print("  The agent wants to modify the file above.")
    print("  Review the agent's plan above before approving.")
    print()

    try:
        response = input("  ➡  Allow this write? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  ⛔  Input interrupted — denying write.")
        return HookResult(allow=False, message="Write denied: user interrupted input.")

    if response in ("y", "yes"):
        print("  ✅  Write APPROVED by user.")
        print("=" * 70 + "\n")
        return HookResult(allow=True, message="Write approved by user.")
    else:
        print("  ⛔  Write DENIED by user.")
        print("=" * 70 + "\n")
        return HookResult(allow=False, message="Write denied by user.")


# ─────────────────────────────────────────────────────────────────────────────
# Safety Policy Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Policy 1: Ask user before creating any new file
POLICY_ASK_ON_CREATE = ask_user(
    tool=BuiltinTools.CREATE_FILE,
    handler=_confirm_write,
    name="require-approval-before-create-file",
)

# Policy 2: Ask user before editing/overwriting any existing file
POLICY_ASK_ON_EDIT = ask_user(
    tool=BuiltinTools.EDIT_FILE,
    handler=_confirm_write,
    name="require-approval-before-edit-file",
)

# Collect all policies into a single exportable list
WRITE_SAFETY_POLICIES = [
    POLICY_ASK_ON_CREATE,
    POLICY_ASK_ON_EDIT,
]
