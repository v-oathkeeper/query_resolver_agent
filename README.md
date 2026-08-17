# 🤖 N+1 Query Resolver Agent

> An autonomous AI agent that scans an Express.js codebase, identifies the N+1
> MongoDB query antipattern, and rewrites the offending route with a single
> optimized `$in` batch query — with user-gated write approval before touching
> any file.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Part 1 — Running the Sandbox](#-part-1--running-the-sandbox)
- [Part 2 — Running the Agent](#-part-2--running-the-agent)
- [Part 3 — Benchmarking with k6](#-part-3--benchmarking-with-k6)
- [Benchmark Results](#-benchmark-results)
- [How the Agent Works](#-how-the-agent-works)
- [Safety Architecture](#-safety-architecture)
- [The N+1 Problem Explained](#-the-n1-problem-explained)

---

## 🎯 Project Overview

This project demonstrates **autonomous AI-driven backend optimization** using
entirely free, open-source tools. It consists of two independent parts:

| Component | Description |
|---|---|
| **The Sandbox** | A Node.js/Express/MongoDB backend with a deliberate N+1 query bottleneck at `GET /api/users-with-posts` |
| **The Agent** | A Python autonomous agent (Google Antigravity SDK) that reads the codebase, detects the bottleneck, and applies the fix |

The agent uses the **Google Antigravity SDK** to orchestrate an LLM that:
1. Reads the Express route file using built-in file I/O tools
2. Identifies the exact antipattern (a `Post.find()` call inside a `for` loop)
3. Asks the user for **explicit terminal approval** before writing any changes
4. Rewrites the file with a single MongoDB `$in` batch query
5. Verifies the fix was applied and reports a summary

The performance impact is measured with a **k6 load test**, producing before/after
latency numbers (p50, p95, p99) that demonstrate the optimization.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Project Layout                              │
│                                                                     │
│  ┌─────────────────────────────┐   ┌─────────────────────────────┐ │
│  │   SANDBOX (Node.js)         │   │   AGENT (Python)            │ │
│  │                             │   │                             │ │
│  │  Express + Mongoose         │   │  Google Antigravity SDK     │ │
│  │                             │   │                             │ │
│  │  GET /api/users-with-posts  │   │  main.py   ← entry point   │ │
│  │  ┌─────────────────────┐   │   │  runner.py ← exec loop     │ │
│  │  │  users = User.find()│   │   │  hooks.py  ← safety gate   │ │
│  │  │  for (user of users)│   │◀──│                             │ │
│  │  │    Post.find(userId)│   │   │  1. Reads users.js          │ │
│  │  │  ← N+1 ANTIPATTERN │   │   │  2. Detects the for-loop    │ │
│  │  └─────────────────────┘   │   │  3. Asks user to approve    │ │
│  │                             │   │  4. Writes the $in fix      │ │
│  │  MongoDB :27017             │   │  5. Verifies the change     │ │
│  └─────────────────────────────┘   └─────────────────────────────┘ │
│                 ▲                                                    │
│                 │                                                    │
│  ┌──────────────────────────────┐                                   │
│  │   k6 LOAD TEST               │                                   │
│  │   load_tests/test.js         │                                   │
│  │   Measures p95 before/after  │                                   │
│  └──────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Internal Architecture

```
main.py  ──────────────────────────────────────────────────────────────
  │  Builds LocalAgentConfig with:
  │    • SYSTEM_PROMPT  (surgical 5-step instructions)
  │    • CapabilitiesConfig()  (enables file read/write tools)
  │    • WRITE_SAFETY_POLICIES  (ask_user gates on edit_file)
  │
  └──▶  runner.py  ─────────────────────────────────────────────────────
          │  run_optimization_loop(agent, target_file)
          │  Drives the agent and streams three event types live:
          │    🟡 Thoughts    — agent's internal reasoning
          │    🔵 Tool Calls  — view_file, edit_file dispatched
          │    ⚪ Text        — agent's final prose output
          │
          └──▶  hooks.py  ───────────────────────────────────────────────
                  Intercepts edit_file calls via PreToolCallDecideHook
                  Prints terminal prompt, blocks until user types y/n
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Sandbox server | Node.js 18+ / Express 4 | Industry-standard REST backend |
| Database | MongoDB (local) + Mongoose | ODM with realistic schema relationships |
| Agent runtime | Python 3.12 | First-class async support |
| Agent SDK | Google Antigravity SDK 0.1.11 | Free-tier autonomous agent orchestration |
| Load testing | k6 | Industry-standard, scriptable, free |
| Version control | Git + GitHub | Clean phase-by-phase commit history |

All tools are **100% free and open-source**.

---

## 📁 Project Structure

```
query_resolver_agent/
│
├── sandbox/                         # Part 1: The buggy Express app
│   ├── package.json
│   └── src/
│       ├── server.js                # Express entry point + MongoDB connection
│       ├── seed.js                  # Populates DB with 50 users + ~250 posts
│       ├── models/
│       │   ├── User.js              # Mongoose User schema
│       │   └── Post.js              # Mongoose Post schema (userId FK)
│       └── routes/
│           └── users.js            # ⚠️ THE N+1 ANTIPATTERN (agent's target)
│
├── agent/                           # Part 2: The autonomous optimizer
│   ├── main.py                      # Entry point — config + banner + preflight
│   ├── runner.py                    # Core streaming execution loop
│   ├── hooks.py                     # Declarative safety policies (ask_user)
│   ├── __init__.py
│   └── requirements.txt             # google-antigravity + frozen deps
│
├── load_tests/                      # Part 3: Performance benchmarking
│   └── test.js                      # k6 script — ramp profile + custom metrics
│
├── venv/                            # Python virtual environment (not committed)
├── .gitignore
└── README.md                        # This file
```

---

## 📦 Prerequisites

| Tool | Version | Install |
|---|---|---|
| Node.js | ≥ 18.0.0 | https://nodejs.org/ |
| MongoDB | ≥ 6.0 | https://www.mongodb.com/try/download/community |
| Python | ≥ 3.12 | https://python.org |
| k6 | Latest | https://k6.io/docs/get-started/installation/ |
| Git | Any | https://git-scm.com |

---

## 🚀 Part 1 — Running the Sandbox

### Step 1: Install dependencies

```bash
cd sandbox
npm install
```

### Step 2: Start MongoDB

Make sure MongoDB is running locally on the default port `27017`.

```bash
# Option A: Start natively
mongod

# Option B: Docker
docker run -d -p 27017:27017 --name mongo mongo:7
```

### Step 3: Seed the database

This populates MongoDB with **50 users** and **~250 posts** — enough to make the
N+1 problem observable.

```bash
npm run seed
```

Expected output:
```
✅  Connected to MongoDB → mongodb://127.0.0.1:27017/n1_sandbox
🗑️   Cleared existing users and posts.
👤  Inserted 50 users.
📝  Inserted 234 posts across 50 users.

🎉  Seed complete! The N+1 endpoint will now fire 51 DB queries.
    → GET http://localhost:3000/api/users-with-posts to observe the antipattern.
```

### Step 4: Start the server

```bash
npm start
```

The server starts at `http://localhost:3000`.

### Step 5: Observe the N+1 problem

```bash
curl http://localhost:3000/api/users-with-posts | python -m json.tool
```

Notice the response metadata:
```json
{
  "queryStrategy": "N+1 (UNOPTIMIZED)",
  "totalQueries": 51,
  "durationMs": 312
}
```

**51 database queries** for 50 users — this is the N+1 antipattern in action.

---

## 🤖 Part 2 — Running the Agent

### Step 1: Activate the virtual environment

```bash
# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 2: Install agent dependencies (first time only)

```bash
pip install -r agent/requirements.txt
```

### Step 3: Run the agent

```bash
python agent/main.py
```

The agent will:

**Phase 1 — Read**: Call `view_file` to read `sandbox/src/routes/users.js`

**Phase 2 — Analyze**: Identify the `for...of` loop containing `Post.find({ userId: user._id })`

**Phase 3 — Plan**: Construct the `$in` batch query replacement mentally

**Phase 4 — Ask**: Print the safety gate prompt:

```
======================================================================
  🔐  AGENT REQUESTING WRITE PERMISSION
======================================================================
  Tool     : edit_file
  Target   : .../sandbox/src/routes/users.js
======================================================================
  The agent wants to modify the file above.
  Review the agent's plan above before approving.

  ➡  Allow this write? [y/N]:
```

Type `y` and press Enter to approve. The agent will apply the fix.

**Phase 5 — Verify**: The agent reads the file again and confirms `$in` is present,
then prints a summary of what changed.

### What the optimized code looks like

The agent replaces this antipattern:

```javascript
// ❌ BEFORE — N+1: fires 1 query per user
for (const user of users) {
  const posts = await Post.find({ userId: user._id }).lean();
  results.push({ ...user, posts });
}
```

With this optimized version:

```javascript
// ✅ AFTER — Single $in batch query: always 2 total queries
const userIds = users.map(u => u._id);
const allPosts = await Post.find({ userId: { $in: userIds } }).lean();

// Group in memory — O(n), zero extra DB calls
const postsByUserId = new Map();
for (const post of allPosts) {
  const key = post.userId.toString();
  if (!postsByUserId.has(key)) postsByUserId.set(key, []);
  postsByUserId.get(key).push(post);
}

const results = users.map(user => {
  const posts = postsByUserId.get(user._id.toString()) || [];
  return { userId: user._id, name: user.name, email: user.email, posts, postCount: posts.length };
});
```

After the fix, the endpoint response reflects the optimization:
```json
{
  "queryStrategy": "OPTIMIZED ($in batch query)",
  "totalQueries": 2,
  "durationMs": 18
}
```

---

## 📊 Part 3 — Benchmarking with k6

The k6 script runs a realistic load profile against the endpoint and records
detailed latency distributions. Run it **before** and **after** the agent to
produce benchmark evidence of the optimization.

### Install k6

```bash
# Windows (winget)
winget install k6

# macOS (Homebrew)
brew install k6

# Docker
docker run --rm -i grafana/k6 run - < load_tests/test.js
```

### Run the baseline benchmark (BEFORE the agent)

Make sure the sandbox is still running the **unoptimized** code (before you ran
the agent), then:

```bash
k6 run load_tests/test.js --out json=load_tests/results_before.json
```

### Run the optimized benchmark (AFTER the agent)

After the agent has applied the `$in` fix and the server is still running:

```bash
k6 run load_tests/test.js --out json=load_tests/results_after.json
```

### k6 Load Profile

The test ramps virtual users (VUs) through four stages over ~100 seconds:

```
VUs │ 25 ┤          ████████████████
    │ 10 ┤ ████████                  ████████
    │  0 ┤─────┬────────┬────────┬───────────
    │       15s    30s     45s     60s+
```

---

## 📈 Benchmark Results

> Results below are representative. Your exact numbers will depend on your
> machine specs and MongoDB performance. The **ratio** between before/after is
> what matters.

### Before (N+1 — 51 queries per request)

```
✓ checks.........................: 100.00%
✓ http_req_failed................: 0.00%

http_req_duration.............: avg=287ms  min=198ms  med=264ms  max=891ms
                                p(90)=412ms p(95)=503ms p(99)=712ms
server_side_duration_ms.......: avg=271ms  p(95)=489ms
reported_query_count..........: avg=51      (N+1 confirmed: 1 + 50 users)
```

### After (Optimized — 2 queries per request)

```
✓ checks.........................: 100.00%
✓ http_req_failed................: 0.00%

http_req_duration.............: avg=22ms   min=14ms   med=20ms   max=61ms
                                p(90)=31ms  p(95)=37ms  p(99)=52ms
server_side_duration_ms.......: avg=18ms   p(95)=29ms
reported_query_count..........: avg=2       (optimized: always exactly 2)
```

### Summary

| Metric | Before (N+1) | After (Optimized) | Improvement |
|---|---|---|---|
| p95 response time | ~503ms | ~37ms | **~13.6× faster** |
| Median response time | ~264ms | ~20ms | **~13.2× faster** |
| DB queries per request | 51 | 2 | **~96% reduction** |
| Throughput (req/s) | ~35 | ~450 | **~12.9× higher** |

> **Key insight**: The N+1 pattern makes latency scale linearly with the number
> of users in the database. With 1,000 users, the unoptimized endpoint would
> fire **1,001 queries** and take seconds per request. The optimized version
> always fires exactly **2 queries** regardless of user count — it scales O(1).

---

## 🧠 How the Agent Works

The agent is built on the **Google Antigravity SDK** using its `LocalAgentConfig`
to run entirely locally (no cloud API required for the agent runtime itself).

### Key SDK Components Used

| Component | Purpose |
|---|---|
| `Agent` | Async context manager — manages the full LLM lifecycle |
| `LocalAgentConfig` | Configuration: system prompt, tools, policies |
| `CapabilitiesConfig` | Enables write tools (`edit_file`, `create_file`) |
| `policies=` | Declarative safety rules — ASK_USER before writes |
| `response.chunks` | Raw event stream (thoughts, tool calls, text) |

### System Prompt Design

The system prompt in `agent/main.py` is structured as a **5-step deterministic
plan** that the agent follows sequentially:

```
STEP 1 — READ     → view_file the target route
STEP 2 — ANALYZE  → locate the for-loop antipattern
STEP 3 — PLAN     → construct the $in replacement mentally
STEP 4 — WRITE    → edit_file (gated by ask_user safety hook)
STEP 5 — VERIFY   → read file again, confirm $in is present
```

This deterministic structure minimizes hallucination and ensures the agent
always produces the exact code pattern required.

### Live Event Streaming

The `runner.py` execution loop consumes `response.chunks` and displays three
distinct event types in real time:

| Event | Color | Description |
|---|---|---|
| `Thought` | 🟡 Yellow/dim | Agent's internal reasoning ("I can see the for-loop on line 33...") |
| `ToolCall` | 🔵 Blue | A tool being dispatched (`view_file → users.js`) |
| `ToolResult` | Dim | The tool's return value |
| `Text` | ⚪ White | Agent's final prose output |

---

## 🔐 Safety Architecture

The agent has **zero ability** to modify files without your explicit approval.
This is enforced at the SDK policy layer — not just at the prompt level.

```
agent/hooks.py implements two ASK_USER policies:
  1. Policy("create_file", Decision.ASK_USER, handler=_confirm_write)
  2. Policy("edit_file",   Decision.ASK_USER, handler=_confirm_write)

When the agent calls edit_file:
  1. The SDK intercepts the call via PreToolCallDecideHook.
  2. _confirm_write() prints the tool name + target file path.
  3. Execution BLOCKS until the user types y or n at the terminal.
  4. Only y/yes proceeds — all other input (including Enter) denies.
```

This pattern is directly analogous to `sudo` in Unix — the agent can **plan** any
change it wants, but it cannot **execute** a write without a human in the loop.

---

## 🐛 The N+1 Problem Explained

The N+1 problem is named for the number of database queries it generates.
Given N parent records, the naive implementation fires 1 query to get the
parents, then N queries inside a loop to get each set of children:

```
User.find()               → 1 query
  Post.find(userId: A)    → 1 query  (user 1)
  Post.find(userId: B)    → 1 query  (user 2)
  Post.find(userId: C)    → 1 query  (user 3)
  ...
  Post.find(userId: N)    → 1 query  (user N)
                          ──────────────────
Total                     = 1 + N queries
```

MongoDB's `$in` operator solves this in a single round-trip:

```
User.find()                              → 1 query
Post.find({ userId: { $in: [...all] }}) → 1 query
                                         ──────────
Total                                    = 2 queries  (always)
```

The `$in` query is processed by MongoDB's query planner which uses the `userId`
index (defined in `Post.js`) to efficiently resolve all IDs in one B-tree scan.

---

## 📄 License

MIT — free to use, fork, and build on.
