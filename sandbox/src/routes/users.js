const express = require("express");
const router = express.Router();
const User = require("../models/User");
const Post = require("../models/Post");

// =============================================================================
// ⚠️  INTENTIONALLY UNOPTIMIZED ROUTE — THE N+1 QUERY PROBLEM
// =============================================================================
// This route demonstrates the classic N+1 database query antipattern.
//
// What happens here:
//   1. One query fetches ALL users from the database.          → 1 DB query
//   2. A for-loop then fires a SEPARATE DB query for EACH user → N DB queries
//
// Total DB queries = 1 + N  (where N = number of users in the database)
//
// With 100 users, this endpoint makes 101 round-trips to MongoDB.
// With 1000 users, it makes 1001 round-trips.
//
// This is the target for the autonomous resolver agent to detect and fix.
// The agent should replace this loop with a single MongoDB `$in` batch query.
// =============================================================================
router.get("/users-with-posts", async (req, res) => {
  try {
    const startTime = Date.now();

    // Query 1: Fetch all users
    const users = await User.find({}).lean();

    const results = [];

    // N Queries: For each user, fire a separate DB query — THE N+1 PROBLEM
    for (const user of users) {
      const posts = await Post.find({ userId: user._id }).lean(); // ← ANTIPATTERN
      results.push({
        userId: user._id,
        name: user.name,
        email: user.email,
        posts: posts,
        postCount: posts.length,
      });
    }

    const duration = Date.now() - startTime;

    res.json({
      success: true,
      queryStrategy: "N+1 (UNOPTIMIZED)",
      totalQueries: 1 + users.length,
      durationMs: duration,
      userCount: users.length,
      data: results,
    });
  } catch (err) {
    console.error("Error in /users-with-posts:", err.message);
    res.status(500).json({ success: false, error: "Internal server error" });
  }
});

module.exports = router;
