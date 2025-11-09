'''#!/usr/bin/env python3
import requests, json

BROKER = "http://10.243.172.126:8001"
ADMIN = "http://10.243.175.183:8000"

def get_allowed_topics():
    try:
        r = requests.get(f"{ADMIN}/allowed_topics", timeout=5)
        return set(r.json().get("allowed_topics", []))
    except Exception as e:
        print("[Producer]  could not fetch allowed_topics:", e)
        return set()

def send_message(topic, message, key=None):
    payload = {"topic": topic, "message": message, "key": key}
    r = requests.post(f"{BROKER}/publish", json=payload)
    try:
        print(r.json())
    except Exception:
        print("[Producer]  Non-JSON broker response:", r.status_code, r.text)

if __name__ == "__main__":
    print(f"[Producer] Broker={BROKER}")
    while True:
        allowed = get_allowed_topics()
        print(f"[Producer] Allowed topics: {allowed}")
        raw = input("Enter JSON: ")
        if not raw: 
            continue
        try:
            msg = json.loads(raw)
            t, m = msg["topic"], msg["message"]
            if t not in allowed:
                print(f"[Producer]  {t} not allowed yet (approved/active)."); 
                continue
            send_message(t, m, msg.get("key"))
        except Exception as e:
            print("X", e)'''
            
#!/usr/bin/env python3
import requests, json

BROKER = "http://10.243.172.126:8001"
ADMIN = "http://10.243.175.183:8000"

def get_allowed_topics():
    try:
        r = requests.get(f"{ADMIN}/allowed_topics", timeout=5)
        return set(r.json().get("allowed_topics", []))
    except Exception as e:
        print("[Producer] ⚠️ could not fetch allowed_topics:", e)
        return set()

def send_message(topic, message, key=None):
    payload = {"topic": topic, "message": message, "key": key}
    try:
        r = requests.post(f"{BROKER}/publish", json=payload, timeout=5)
        print("[Producer] ✅", r.json())
    except Exception as e:
        print("[Producer] ⚠️ Broker error:", e)

def request_new_topic(topic):
    payload = {"topic": topic, "from": "producer"}
    try:
        r = requests.post(f"{ADMIN}/request", json=payload, timeout=5)
        if r.status_code == 200:
            print(f"[Producer] 🆕 Requested new topic '{topic}' successfully.")
        else:
            print(f"[Producer] ⚠️ Failed to request topic '{topic}': {r.status_code} {r.text}")
    except Exception as e:
        print(f"[Producer] ❌ Could not contact admin: {e}")

if __name__ == "__main__":
    print(f"[Producer] Broker={BROKER} | Admin={ADMIN}")

    while True:
        choice = input("\nChoose action: [s]end message / [r]equest topic / [q]uit: ").strip().lower()
        if choice == "q":
            print("Exiting producer...")
            break
        elif choice == "r":
            topic = input("Enter new topic name (e.g. topic-metal): ").strip()
            request_new_topic(topic)
        elif choice == "s":
            allowed = get_allowed_topics()
            print(f"[Producer] Allowed topics: {allowed}")
            raw = input("Enter JSON: ")
            if not raw:
                continue
            try:
                msg = json.loads(raw)
                t, m = msg["topic"], msg["message"]
                if t not in allowed:
                    print(f"[Producer] 🚫 {t} not allowed yet. Try requesting it first.")
                    continue
                send_message(t, m, msg.get("key"))
            except Exception as e:
                print("❌ Invalid JSON:", e)
        else:
            print("Invalid choice. Try again.")




	

