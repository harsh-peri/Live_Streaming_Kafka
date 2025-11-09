#!/usr/bin/env python3
import requests, time, threading

ADMIN = "http://10.243.175.183:8000"
BROKER = "http://10.243.172.126:8001"
USER = "user1"         # optional for tracking subscriptions
POLL_INTERVAL = 5      # seconds between topic list refresh
FETCH_INTERVAL = 2     # seconds between consume checks

# Keeps last offsets so we don't reread old messages
offsets = {}
current_topics = set()
stop_event = threading.Event()

def fetch_allowed_topics():
    """Get allowed (approved + active) topics from Admin."""
    try:
        r = requests.get(f"{ADMIN}/allowed_topics", timeout=5)
        if r.status_code == 200:
            data = r.json().get("allowed_topics", [])
            return set(data)
        print(f"[Consumer] ⚠️ Admin returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[Consumer] ❌ Failed to reach Admin: {e}")
    return set()

def consume_topic(topic):
    """Poll broker for new messages from a single topic."""
    global offsets
    last_offset = offsets.get(topic, 0)
    try:
        r = requests.get(f"{BROKER}/consume", params={"topic": topic, "offset": last_offset}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            msgs = data.get("messages", [])
            if msgs:
                for msg in msgs:
                    print(f"[{topic}] {msg}")
                offsets[topic] = data.get("offset", last_offset)
    except Exception as e:
        print(f"[Consumer] ⚠️ Broker error for {topic}: {e}")

def topic_watcher():
    """Continuously update the list of allowed topics from Admin."""
    global current_topics
    while not stop_event.is_set():
        allowed = fetch_allowed_topics()
        if allowed != current_topics:
            added = allowed - current_topics
            removed = current_topics - allowed
            if added:
                print(f"[Consumer] 🟢 New topics detected: {added}")
                for t in added:
                    offsets[t] = 0  # start from offset 0
            if removed:
                print(f"[Consumer] 🔴 Topics removed: {removed}")
                for t in removed:
                    offsets.pop(t, None)
            current_topics = allowed
        time.sleep(POLL_INTERVAL)

def consume_loop():
    """Continuously consume from all current topics."""
    while not stop_event.is_set():
        for t in list(current_topics):
            consume_topic(t)
        time.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    print(f"[Consumer] 🚀 Started dynamic consumer")
    print(f"[Consumer] Admin={ADMIN} | Broker={BROKER}")

    # Start background watcher
    threading.Thread(target=topic_watcher, daemon=True).start()

    # Start consume loop
    try:
        consume_loop()
    except KeyboardInterrupt:
        stop_event.set()
        print("\n🛑 Stopping consumer cleanly...")
