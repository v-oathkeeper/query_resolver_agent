/**
 * load_tests/test.js
 * ──────────────────────────────────────────────────────────────────────────
 * k6 Load Test — N+1 Query Resolver Agent Benchmark
 * ──────────────────────────────────────────────────────────────────────────
 * This script measures the real-world performance impact of the autonomous
 * agent's optimization. Run it BEFORE and AFTER triggering the agent to
 * produce benchmark evidence of the latency reduction.
 *
 * Install k6:
 *   Windows (winget):  winget install k6
 *   macOS (brew):      brew install k6
 *   Linux:             https://k6.io/docs/get-started/installation/
 *
 * Usage:
 *   # 1. Baseline (run BEFORE the agent optimizes — captures N+1 performance)
 *   k6 run load_tests/test.js --out json=load_tests/results_before.json
 *
 *   # 2. Optimized (run AFTER the agent applies the $in fix)
 *   k6 run load_tests/test.js --out json=load_tests/results_after.json
 *
 *   # 3. Compare p95 latency across the two result files to show the speedup
 *
 * What this test measures:
 *   - http_req_duration p(50)  →  Median latency
 *   - http_req_duration p(95)  →  p95 latency (primary benchmark KPI)
 *   - http_req_duration p(99)  →  p99 latency (tail latency)
 *   - http_reqs              →  Total requests completed
 *   - http_req_failed        →  Error rate (must stay at 0%)
 *   - checks                 →  Custom assertions (response shape validation)
 * ──────────────────────────────────────────────────────────────────────────
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ─────────────────────────────────────────────────────────────────────────────
// Custom Metrics
// ─────────────────────────────────────────────────────────────────────────────

// Tracks the reported durationMs from the API response body itself.
// This is the server-side measured time — excludes network overhead.
const serverSideDuration = new Trend("server_side_duration_ms", true);

// Tracks the total number of DB queries the endpoint reported making.
const reportedQueryCount = new Trend("reported_query_count");

// Tracks whether the endpoint returned data in the expected shape.
const dataIntegrityErrors = new Counter("data_integrity_errors");


// ─────────────────────────────────────────────────────────────────────────────
// Test Configuration
// ─────────────────────────────────────────────────────────────────────────────

export const options = {
  // Load profile: ramp up → sustain → ramp down
  stages: [
    { duration: "15s", target: 10  },  // Ramp up to 10 concurrent users over 15s
    { duration: "30s", target: 10  },  // Hold at 10 concurrent users for 30s
    { duration: "15s", target: 25  },  // Ramp up to 25 concurrent users
    { duration: "30s", target: 25  },  // Hold at 25 concurrent users for 30s
    { duration: "10s", target:  0  },  // Ramp down to 0
  ],

  // Pass/fail thresholds — the benchmark "definition of done"
  thresholds: {
    // p95 response time must be under 5 seconds (generous for the N+1 baseline)
    "http_req_duration{scenario:default}": ["p(95)<5000"],

    // Zero errors allowed
    http_req_failed: ["rate<0.01"],

    // Custom: server-reported p95 duration under 4 seconds
    server_side_duration_ms: ["p(95)<4000"],

    // All checks must pass at 99%+ rate
    checks: ["rate>0.99"],
  },
};


// ─────────────────────────────────────────────────────────────────────────────
// Target Endpoint
// ─────────────────────────────────────────────────────────────────────────────

const BASE_URL = __ENV.BASE_URL || "http://localhost:3000";
const ENDPOINT = `${BASE_URL}/api/users-with-posts`;


// ─────────────────────────────────────────────────────────────────────────────
// Virtual User Script (runs once per VU per iteration)
// ─────────────────────────────────────────────────────────────────────────────

export default function () {
  const response = http.get(ENDPOINT, {
    headers: { Accept: "application/json" },
    tags: { endpoint: "users-with-posts" },
  });

  // ── HTTP-level assertions ─────────────────────────────────────────────────
  const httpChecks = check(response, {
    "status is 200": (r) => r.status === 200,
    "response is JSON": (r) => r.headers["Content-Type"]?.includes("application/json"),
    "response time < 5s": (r) => r.timings.duration < 5000,
  });

  // ── Parse and validate response body ─────────────────────────────────────
  if (response.status === 200) {
    let body;
    try {
      body = JSON.parse(response.body);
    } catch {
      dataIntegrityErrors.add(1);
      return;
    }

    // Business logic checks
    const bodyChecks = check(body, {
      "success is true":    (b) => b.success === true,
      "data is an array":   (b) => Array.isArray(b.data),
      "users exist":        (b) => b.userCount > 0,
      "each user has posts field": (b) =>
        b.data.every((u) => Object.hasOwn(u, "posts") && Array.isArray(u.posts)),
      "queryStrategy present":  (b) => typeof b.queryStrategy === "string",
      "totalQueries reported":  (b) => typeof b.totalQueries === "number",
    });

    if (!bodyChecks) {
      dataIntegrityErrors.add(1);
    }

    // Record custom metrics from the response body
    if (typeof body.durationMs === "number") {
      serverSideDuration.add(body.durationMs);
    }
    if (typeof body.totalQueries === "number") {
      reportedQueryCount.add(body.totalQueries);
    }
  } else {
    dataIntegrityErrors.add(1);
  }

  // Think time between requests — prevents completely synthetic "wall of traffic"
  sleep(0.5);
}


// ─────────────────────────────────────────────────────────────────────────────
// Lifecycle: Setup & Teardown
// ─────────────────────────────────────────────────────────────────────────────

export function setup() {
  console.log("=".repeat(60));
  console.log("  N+1 Query Resolver Agent — k6 Benchmark");
  console.log("=".repeat(60));
  console.log(`  Endpoint   : ${ENDPOINT}`);
  console.log(`  Load model : Ramp 0→10→25→0 VUs over ~100s`);
  console.log(`  KPI target : p95 http_req_duration < 5000ms`);
  console.log("=".repeat(60));

  // Sanity check: make sure the server is actually reachable before the test
  const healthCheck = http.get(`${BASE_URL}/health`);
  if (healthCheck.status !== 200) {
    throw new Error(
      `Server not reachable at ${BASE_URL}/health (status: ${healthCheck.status}).\n` +
        "Start the sandbox first: cd sandbox && npm start"
    );
  }
  console.log("  Server health check: OK ✅");
  console.log("=".repeat(60));
  console.log();
}

export function teardown() {
  console.log();
  console.log("=".repeat(60));
  console.log("  Benchmark complete. Compare these key metrics:");
  console.log("    • http_req_duration p(95)  — primary KPI");
  console.log("    • server_side_duration_ms p(95)");
  console.log("    • reported_query_count avg — should drop from N+1 → 2");
  console.log("=".repeat(60));
}
