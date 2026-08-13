/**
 * seed.js
 * -------
 * Populates the MongoDB database with realistic test data:
 *   - 50 Users
 *   - 3–7 Posts per User (≈ 250 Posts total)
 *
 * Run with: npm run seed
 */

const mongoose = require("mongoose");
const User = require("./models/User");
const Post = require("./models/Post");

const MONGODB_URI =
  process.env.MONGODB_URI || "mongodb://127.0.0.1:27017/n1_sandbox";

const FIRST_NAMES = [
  "Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Henry",
  "Isla", "James", "Karen", "Liam", "Mia", "Noah", "Olivia", "Paul",
  "Quinn", "Rachel", "Sam", "Tara", "Uma", "Victor", "Wendy", "Xander",
  "Yara", "Zane", "Aria", "Blake", "Chloe", "Dylan", "Ella", "Finn",
  "Gemma", "Hugo", "Iris", "Jake", "Kate", "Leo", "Maya", "Nate",
  "Opal", "Piper", "Rex", "Sara", "Tyler", "Ursula", "Vince", "Wren",
  "Ximena", "Yale",
];

const POST_TITLES = [
  "Getting Started with MongoDB Aggregations",
  "Why N+1 Queries Kill Performance",
  "Understanding Mongoose Populate vs $in",
  "Building RESTful APIs with Express",
  "Database Indexing Strategies for Node.js",
  "Async/Await Patterns in Modern JavaScript",
  "Optimizing MongoDB with Compound Indexes",
  "The Art of Writing Clean Backend Code",
  "Load Testing Your API with k6",
  "How AI Agents Can Refactor Your Codebase",
  "Understanding Event Loop in Node.js",
  "Profiling Database Queries in Production",
  "Horizontal vs Vertical Scaling Explained",
  "Redis Caching Strategies for Express Apps",
  "The Complete Guide to Mongoose Schemas",
];

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomElement(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function seed() {
  try {
    await mongoose.connect(MONGODB_URI);
    console.log(`✅  Connected to MongoDB → ${MONGODB_URI}`);

    // Clear existing data
    await User.deleteMany({});
    await Post.deleteMany({});
    console.log("🗑️   Cleared existing users and posts.");

    // Create Users
    const userDocs = FIRST_NAMES.map((name, i) => ({
      name,
      email: `${name.toLowerCase()}${i + 1}@example.com`,
    }));

    const users = await User.insertMany(userDocs);
    console.log(`👤  Inserted ${users.length} users.`);

    // Create Posts (3–7 per user)
    const postDocs = [];
    for (const user of users) {
      const postCount = randomInt(3, 7);
      for (let i = 0; i < postCount; i++) {
        postDocs.push({
          title: `${randomElement(POST_TITLES)} (Part ${i + 1})`,
          body: `This is a sample blog post by ${user.name}. It covers various backend engineering topics with depth and practical examples. Written specifically to demonstrate realistic data volumes.`,
          userId: user._id,
        });
      }
    }

    const posts = await Post.insertMany(postDocs);
    console.log(`📝  Inserted ${posts.length} posts across ${users.length} users.`);
    console.log(
      `\n🎉  Seed complete! The N+1 endpoint will now fire ${1 + users.length} DB queries.`
    );
    console.log(
      `    → GET http://localhost:3000/api/users-with-posts to observe the antipattern.\n`
    );
  } catch (err) {
    console.error("❌  Seed failed:", err.message);
  } finally {
    await mongoose.disconnect();
    console.log("🔌  Disconnected from MongoDB.");
  }
}

seed();
