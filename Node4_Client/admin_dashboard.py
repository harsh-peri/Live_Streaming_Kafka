#!/usr/bin/env python3
import streamlit as st
import requests
import sqlite3
import os
import socket
import time

# -------------------- CONFIG --------------------
API_BASE = "http://10.243.175.183:8000"
BACKEND = "http://10.243.175.183:8000"   # Flask admin server
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "control_plane.db")

# Components to monitor
NODES = {
    "Admin (You)": ("10.243.175.183", 8000),
    "Broker": ("10.243.172.126", 9092),
    "Producer": ("10.243.113.67", 9092),
    "Consumer": ("10.243.216.114", 9092),
}

REFRESH_INTERVAL = 10  # seconds

st.set_page_config(page_title="Kafka Control Plane Dashboard", layout="wide")
st.title("🧭 Kafka Ecosystem Admin Dashboard")

# -------------------- DB FUNCTIONS --------------------
def get_topics():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("SELECT topic_name, partitions, replication_factor, status FROM topics")
    rows = cur.fetchall()
    conn.close()
    return rows

def refresh_topics():
    st.session_state["topics"] = get_topics()

# -------------------- NETWORK HEALTH CHECK --------------------
def check_port(host, port, timeout=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False

def get_health_status():
    health = {}
    for name, (host, port) in NODES.items():
        ok = check_port(host, port)
        health[name] = {"ip": host, "port": port, "status": "🟢 UP" if ok else "🔴 DOWN"}
    return health

# -------------------- BACKEND OPERATIONS --------------------
def call_api(endpoint, payload):
    try:
        r = requests.post(f"{BACKEND}/{endpoint}", json=payload, timeout=3)
        if r.status_code == 200:
            st.toast(f"{endpoint} OK ✅", icon="✅")
            return True
        else:
            st.error(f"{endpoint} failed: {r.status_code}")
            return False
    except Exception as e:
        st.error(f"Error contacting backend: {e}")
        return False

# -------------------- UI --------------------
tabs = st.tabs(["📊 System Health", "🧩 Topics", "🧠 Subscriptions"])

# -------------------- TAB 1: HEALTH --------------------
with tabs[0]:
    st.subheader("🌐 Ecosystem Health Status")
    st.caption("Ping results are live — green = reachable, red = down")
    health = get_health_status()

    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    for i, (name, data) in enumerate(health.items()):
        with cols[i]:
            st.metric(
                label=f"{name}\n({data['ip']}:{data['port']})",
                value=data["status"]
            )
    st.caption(f"Last checked at {time.strftime('%H:%M:%S')}. Auto-refresh every {REFRESH_INTERVAL}s.")
    st.rerun() if st.button("🔄 Refresh Now") else None

# -------------------- TAB 2: TOPICS --------------------
with tabs[1]:
    st.subheader("🧩 Topic Management")

    if "topics" not in st.session_state:
        refresh_topics()

    topics = st.session_state["topics"]

    if not topics:
        st.info("No topics found in database yet.")
    else:
        st.dataframe(topics, use_container_width=True)

        for topic_name, p, r, status in topics:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{topic_name}** — {status}")
            with col2:
                if st.button(f"✅ Approve {topic_name}", key=f"approve_{topic_name}"):
                    call_api("approve_topic", {"topic": topic_name})
                    refresh_topics()
                    st.rerun()
            with col3:
                if status != "rejected" and st.button(f"❌ Reject {topic_name}", key=f"reject_{topic_name}"):
                    call_api("reject_topic", {"topic": topic_name})
                    refresh_topics()
                    st.rerun()

    st.divider()
    st.header("🕓 Pending Topic Requests")

try:
    topics_resp = requests.get(f"{API_BASE}/topics").json()
    pending_topics = [t for t in topics_resp["topics"] if t[3] == "pending"]

    if not pending_topics:
        st.info("No pending topic requests at the moment.")
    else:
        for t_name, parts, repl, status in pending_topics:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            col1.write(f"**{t_name}**")
            col2.write(f"Partitions: {parts}")
            col3.write(f"Replicas: {repl}")
            with col4:
                if st.button(f"✅ Approve {t_name}", key=f"a_{t_name}"):
                    requests.post(f"{API_BASE}/approve_topic", json={"topic": t_name})
                    st.success(f"Approved {t_name}")
                    st.rerun()
                if st.button(f"❌ Reject {t_name}", key=f"r_{t_name}"):
                    requests.post(f"{API_BASE}/reject_topic", json={"topic": t_name})
                    st.warning(f"Rejected {t_name}")
                    st.rerun()
except Exception as e:
    st.error(f"Failed to fetch topics: {e}")

# -------------------- TAB 3: SUBSCRIPTIONS --------------------
with tabs[2]:
    st.subheader("🧠 User Subscriptions")
    try:
        r = requests.get(f"{BACKEND}/subscriptions")
        subs = r.json().get("subscriptions", [])
        if subs:
            st.dataframe(subs, use_container_width=True)
        else:
            st.info("No subscriptions found.")
    except Exception as e:
        st.error(f"Failed to load subscriptions: {e}")

# -------------------- AUTO REFRESH --------------------
st.empty()
time.sleep(REFRESH_INTERVAL)
st.rerun()

