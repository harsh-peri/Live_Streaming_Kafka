#!/usr/bin/env python3
# =============================================
# Admin Control Plane Server for Kafka Topics
# =============================================

from flask import Flask, request, jsonify
import sqlite3
import os

DB = "control_plane.db"
app = Flask(__name__)

# ---------- DB Setup ----------
def init_db():
    new_db = not os.path.exists(DB)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    if new_db:
        cur.execute("""
            CREATE TABLE topics (
                topic_name TEXT PRIMARY KEY,
                partitions INTEGER DEFAULT 1,
                replication_factor INTEGER DEFAULT 1,
                status TEXT CHECK(status IN ('pending','approved','rejected','active')) DEFAULT 'pending'
            );
        """)
        print("[Init] 🧱 Created topics table.")

    # Ensure user_subscriptions table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_subscriptions (
            user TEXT NOT NULL,
            topic TEXT NOT NULL,
            PRIMARY KEY (user, topic)
        );
    """)
    conn.commit()
    conn.close()
    print("[Init] ✅ DB ready with user_subscriptions table.")

# ---------- API Endpoints ----------

# List all topics (any status)
@app.route("/topics", methods=["GET"])
def all_topics():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT * FROM topics")
    rows = cur.fetchall()
    conn.close()
    return jsonify({"topics": rows})

# List only approved topics
@app.route("/approved_topics", methods=["GET"])
def approved_topics():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT topic_name FROM topics WHERE status='approved'")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return jsonify({"approved_topics": rows})

# Approve a topic manually (admin action)
@app.route("/approve_topic", methods=["POST"])
def approve_topic():
    data = request.get_json(force=True)
    topic = data.get("topic")
    if not topic:
        return jsonify({"error": "Missing 'topic'"}), 400

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE topics SET status='approved' WHERE topic_name=?", (topic,))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO topics (topic_name, status) VALUES (?, 'approved')", (topic,))
    conn.commit()
    conn.close()
    print(f"[Admin] ✅ Approved topic: {topic}")
    return jsonify({"status": "approved", "topic": topic}), 200

# Reject a topic
@app.route("/reject_topic", methods=["POST"])
def reject_topic():
    data = request.get_json(force=True)
    topic = data.get("topic")
    if not topic:
        return jsonify({"error": "Missing 'topic'"}), 400

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("UPDATE topics SET status='rejected' WHERE topic_name=?", (topic,))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO topics (topic_name, status) VALUES (?, 'rejected')", (topic,))
    conn.commit()
    conn.close()
    print(f"[Admin] ❌ Rejected topic: {topic}")
    return jsonify({"status": "rejected", "topic": topic}), 200

# Producer/Broker can request a new topic -> goes to 'pending'
@app.route("/request", methods=["POST"])
def request_topic():
    data = request.get_json(force=True)
    topic = data.get("topic")
    source = data.get("from", "unknown")
    if not topic:
        return jsonify({"error": "Missing 'topic'"}), 400

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT status FROM topics WHERE topic_name=?", (topic,))
    row = cur.fetchone()
    if row:
        conn.close()
        msg = f"Topic '{topic}' already exists with status '{row[0]}'"
        print(f"[Admin] ℹ️ {msg}")
        return jsonify({"status": row[0], "message": msg}), 200

    cur.execute("INSERT INTO topics (topic_name, status) VALUES (?, 'pending')", (topic,))
    conn.commit()
    conn.close()

    print(f"[Admin] 📨 New topic request from {source}: '{topic}' (pending approval)")
    return jsonify({"status": "pending", "topic": topic}), 200

# For compatibility with your old UI that queried /allowed_topics
@app.route("/allowed_topics", methods=["GET"])
def allowed_topics():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT topic_name FROM topics WHERE status IN ('approved','active')")
    topics = [r[0] for r in cur.fetchall()]
    conn.close()

    # Log user IP + topics into user_subscriptions
    user_ip = request.remote_addr or "unknown"
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    for topic in topics:
        try:
            cur.execute("INSERT OR IGNORE INTO user_subscriptions (user, topic) VALUES (?, ?)", (user_ip, topic))
        except Exception as e:
            print(f"[Warn] Could not log subscription: {e}")
    conn.commit()
    conn.close()

    print(f"[Log] 📡 {user_ip} fetched allowed topics ({len(topics)} logged).")
    return jsonify({"allowed_topics": topics})

# List all user subscriptions
@app.route("/subscriptions", methods=["GET"])
def get_subscriptions():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT user, topic FROM user_subscriptions")
    rows = cur.fetchall()
    conn.close()
    return jsonify({"subscriptions": rows})

# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    print("[Admin] 🚀 Server running on http://0.0.0.0:8000")
    app.run(host="0.0.0.0", port=8000, debug=False)

