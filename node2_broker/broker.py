

#!/usr/bin/env python3
from flask import Flask, request, jsonify
from threading import Lock, Thread
import json, time, requests

app = Flask(__name__)

ADMIN_ALLOWED = "http://10.243.175.183:8000/allowed_topics"
BROKER_HOST = "10.243.172.126"
BROKER_PORT = 8001
SYNC_INTERVAL = 5

topics = {}
topic_locks = {}
approved_topics = set()

def pull_allowed_once():
    try:
        res = requests.get(ADMIN_ALLOWED, timeout=5)
        if res.status_code == 200:
            data = res.json().get("allowed_topics", [])
            return set(data)
        else:
            print(f"[SYNC] ⚠️ Admin {res.status_code}: {res.text}", flush=True)
            return set()
    except Exception as e:
        print(f"[SYNC] ❌ {e}", flush=True)
        return set()

def sync_with_admin():
    while True:
        new_topics = pull_allowed_once()
        for t in new_topics - approved_topics:
            approved_topics.add(t)
            if t not in topics:
                topics[t] = []
                topic_locks[t] = Lock()
            print(f"[SYNC] ✅ Allowed from admin: {t}", flush=True)
        # Optionally: drop topics that are no longer allowed
        for t in list(approved_topics):
            if t not in new_topics:
                approved_topics.remove(t)
                print(f"[SYNC] 🧹 Removed from allowed: {t}", flush=True)
        time.sleep(SYNC_INTERVAL)

@app.route("/publish", methods=["POST"])
def publish():
    data = request.get_json() or {}
    topic = data.get("topic")
    msg = data.get("message")
    key = data.get("key")

    if not topic or msg is None:
        return jsonify({"error": "Topic and message required"}), 400

    if topic not in approved_topics:
        print(f"[BROKER] ❌ '{topic}' not yet allowed (approved/active)", flush=True)
        return jsonify({"status": "Topic not approved"}), 403

    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "key": key,
        "message": msg
    }

    with topic_locks[topic]:
        topics[topic].append(record)
    print(f"[BROKER] 📥 Received on {topic}: {json.dumps(record)}", flush=True)
    return jsonify({"status": "Message received"}), 200

@app.route("/consume", methods=["GET"])
def consume():
    topic = request.args.get("topic")
    offset = int(request.args.get("offset", 0))
    if topic not in topics:
        return jsonify({"messages": [], "offset": offset})
    with topic_locks[topic]:
        msgs = topics[topic][offset:]
        new_offset = offset + len(msgs)
    return jsonify({"messages": msgs, "offset": new_offset})

@app.route("/topics", methods=["GET"])
def list_topics():
    return jsonify({"allowed": list(approved_topics), "all": list(topics.keys())})

if __name__ == "__main__":
    print(f"[BROKER] 🚀 Running at {BROKER_HOST}:{BROKER_PORT}", flush=True)
    # Do one sync before serving to avoid first-request race
    approved_topics |= pull_allowed_once()
    for t in approved_topics:
        if t not in topics:
            topics[t] = []
            topic_locks[t] = Lock()
    Thread(target=sync_with_admin, daemon=True).start()
    app.run(host=BROKER_HOST, port=BROKER_PORT)
