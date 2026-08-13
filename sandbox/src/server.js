const express = require("express");
const mongoose = require("mongoose");
const userRoutes = require("./routes/users");

// ---------------------------------------------------------------------------
// App Configuration
// ---------------------------------------------------------------------------
const app = express();
const PORT = process.env.PORT || 3000;
const MONGODB_URI =
  process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/n1_sandbox";

// ---------------------------------------------------------------------------
// Middleware
// ---------------------------------------------------------------------------
app.use(express.json());

// ---------------------------------------------------------------------------
// Health Check
// ---------------------------------------------------------------------------
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    dbState: mongoose.connection.readyState === 1 ? "connected" : "disconnected",
    uptime: process.uptime(),
  });
});

// ---------------------------------------------------------------------------
// Routes
// ---------------------------------------------------------------------------
app.use("/api", userRoutes);

// ---------------------------------------------------------------------------
// 404 Catch-all
// ---------------------------------------------------------------------------
app.use((req, res) => {
  res.status(404).json({ success: false, error: "Route not found" });
});

// ---------------------------------------------------------------------------
// MongoDB Connection + Server Start
// ---------------------------------------------------------------------------
async function start() {
  try {
    await mongoose.connect(MONGODB_URI);
    console.log(`✅  MongoDB connected → ${MONGODB_URI}`);
    app.listen(PORT, () => {
      console.log(`🚀  Sandbox server running → http://localhost:${PORT}`);
      console.log(`📡  N+1 endpoint: http://localhost:${PORT}/api/users-with-posts`);
    });
  } catch (err) {
    console.error("❌  Failed to connect to MongoDB:", err.message);
    process.exit(1);
  }
}

start();
