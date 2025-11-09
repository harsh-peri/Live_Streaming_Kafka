'''#!/usr/bin/env python3
import streamlit as st
import requests
import json
import os

# ==============================
# CONFIG
# ==============================
ADMIN = "http://10.243.175.183:8000"
BROKER = "http://10.243.172.126:8001"
NEWS_DIR = "./news"

# ==============================
# HELPERS
# ==============================
@st.cache_data(ttl=30)
def get_allowed_topics():
    try:
        r = requests.get(f"{ADMIN}/allowed_topics", timeout=5)
        data = r.json()
        return set(data.get("allowed_topics", []))
    except Exception as e:
        st.warning(f"Could not fetch topics from admin: {e}")
        return set()

def load_news_files():
    all_news = {}
    for file in os.listdir(NEWS_DIR):
        if file.endswith(".json"):
            path = os.path.join(NEWS_DIR, file)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        topic_name = file.replace(".json", "")
                        all_news[topic_name] = data
            except Exception as e:
                st.error(f"Error loading {file}: {e}")
    return all_news

def send_message(topic, message, key=None):
    payload = {"topic": topic, "message": message, "key": key}
    try:
        r = requests.post(f"{BROKER}/publish", json=payload, timeout=5)
        try:
            response = r.json()
        except:
            response = {"status": "error", "details": r.text}
        return response
    except Exception as e:
        return {"status": "failed", "details": str(e)}


def request_topic(topic):
    payload = {"topic": topic}
    try:
        r = requests.post(f"{ADMIN}/request_topic", json=payload, timeout=5)
        if r.status_code == 201:
            st.info(f"🆕 Requested admin approval for new topic: {topic}")
        else:
            st.warning(f"⚠️ Topic already exists or could not request: {r.text}")
    except Exception as e:
        st.error(f"Could not contact admin: {e}")


# ==============================
# STREAMLIT UI
# ==============================
st.set_page_config(page_title="Dynamic Kafka Producer", layout="wide")

st.title("📰 Dynamic Kafka Producer Dashboard")
st.caption("Send topic-based messages via Admin + Broker APIs")

allowed_topics = get_allowed_topics()
all_news = load_news_files()

# Sidebar
st.sidebar.header("Controls")
st.sidebar.write(f" Allowed topics: {', '.join(allowed_topics) if allowed_topics else 'None'}")

mode = st.sidebar.radio("Choose Mode", ["Select News", "Manual JSON Input"])

# --- Select Mode ---
if mode == "Select News":
    topic = st.selectbox("Select a topic:", sorted(all_news.keys()))
    if topic:
        st.subheader(f" News under {topic}")
        for i, item in enumerate(all_news[topic]):
            with st.expander(f"News #{i+1}: {item['message'][:60]}..."):
                st.json(item)
                if st.button(f"Send #{i+1}", key=f"{topic}_{i}"):
                    if topic not in allowed_topics:
                        st.error(f" {topic} not approved yet.")
                    else:
                        result = send_message(topic, item["message"])
                        st.success(f"Sent to broker: {result}")

# --- Manual Mode ---
else:
    st.subheader(" Manual JSON Entry")
    st.code('{"topic": "topic-news", "message": "Some text", "key": "optional"}')
    raw = st.text_area("Enter JSON:", height=200)
    if st.button("Send Message"):
        try:
            msg = json.loads(raw)
            topic = msg["topic"]
            message = msg["message"]
            if topic not in allowed_topics:
                st.error(f" {topic} not allowed yet.")
            else:
                result = send_message(topic, message, msg.get("key"))
                st.success(f" Sent successfully: {result}")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

st.divider()
st.caption("© Dynamic Kafka Project — Streamlit Frontend v2.0 ")'''

#!/usr/bin/env python3
import streamlit as st
import requests
import json
import os

# ==============================
# CONFIG
# ==============================
ADMIN = "http://10.243.175.183:8000"
BROKER = "http://10.243.172.126:8001"
NEWS_DIR = "./news"

# ==============================
# HELPERS
# ==============================
@st.cache_data(ttl=30)
def get_allowed_topics():
    try:
        r = requests.get(f"{ADMIN}/allowed_topics", timeout=5)
        data = r.json()
        return set(data.get("allowed_topics", []))
    except Exception as e:
        st.warning(f"Could not fetch topics from admin: {e}")
        return set()

def load_news_files():
    all_news = {}
    for file in os.listdir(NEWS_DIR):
        if file.endswith(".json"):
            path = os.path.join(NEWS_DIR, file)
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        topic_name = file.replace(".json", "")
                        all_news[topic_name] = data
            except Exception as e:
                st.error(f"Error loading {file}: {e}")
    return all_news

def send_message(topic, message, key=None):
    payload = {"topic": topic, "message": message, "key": key}
    try:
        r = requests.post(f"{BROKER}/publish", json=payload, timeout=5)
        return r.json()
    except Exception as e:
        return {"status": "failed", "details": str(e)}

def request_topic(topic):
    payload = {"topic": topic, "from": "producer"}
    try:
        r = requests.post(f"{ADMIN}/request", json=payload, timeout=5)
        if r.status_code == 200:
            st.success(f"🆕 Requested new topic: {topic}")
        else:
            st.warning(f"⚠️ Could not request topic ({r.status_code}): {r.text}")
    except Exception as e:
        st.error(f"❌ Could not contact admin: {e}")

# ==============================
# STREAMLIT UI
# ==============================
st.set_page_config(page_title="Dynamic Kafka Producer", layout="wide")

st.title("📰 Dynamic Kafka Producer Dashboard")
st.caption("Send topic-based messages or request new topics via Admin + Broker APIs")

allowed_topics = get_allowed_topics()
all_news = load_news_files()

# Sidebar
st.sidebar.header("⚙️ Controls")
st.sidebar.write(f"✅ Allowed topics: {', '.join(allowed_topics) if allowed_topics else 'None'}")

# --- Request new topic section ---
st.sidebar.subheader("🆕 Request New Topic")
preset_topics = [
    "topic-metal", "topic-ai", "topic-crypto", "topic-gold",
    "topic-silver", "topic-business", "topic-disaster", "topic-cybersecurity"
]
topic_choice = st.sidebar.selectbox("Pick a topic to request:", preset_topics)
if st.sidebar.button("Request Selected Topic"):
    request_topic(topic_choice)

custom_topic = st.sidebar.text_input("Or enter custom topic name:")
if st.sidebar.button("Request Custom Topic"):
    if custom_topic:
        request_topic(custom_topic)
    else:
        st.warning("Please enter a topic name.")

mode = st.sidebar.radio("Choose Mode", ["Select News", "Manual JSON Input"])

# --- Select News Mode ---
if mode == "Select News":
    topic = st.selectbox("Select a topic:", sorted(all_news.keys()))
    if topic:
        st.subheader(f"🗞️ News under {topic}")
        for i, item in enumerate(all_news[topic]):
            with st.expander(f"News #{i+1}: {item['message'][:60]}..."):
                st.json(item)
                if st.button(f"Send #{i+1}", key=f"{topic}_{i}"):
                    if topic not in allowed_topics:
                        st.error(f"🚫 {topic} not approved yet.")
                    else:
                        result = send_message(topic, item["message"])
                        st.success(f"✅ Sent to broker: {result}")

# --- Manual Input Mode ---
else:
    st.subheader("✍️ Manual JSON Entry")
    st.code('{"topic": "topic-news", "message": "Some text", "key": "optional"}')
    raw = st.text_area("Enter JSON:", height=200)
    if st.button("Send Message"):
        try:
            msg = json.loads(raw)
            topic = msg["topic"]
            message = msg["message"]
            if topic not in allowed_topics:
                st.error(f"🚫 {topic} not allowed yet.")
            else:
                result = send_message(topic, message, msg.get("key"))
                st.success(f"✅ Sent successfully: {result}")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

st.divider()
st.caption("© Dynamic Kafka Project — Streamlit Frontend v3.0 🚀")


