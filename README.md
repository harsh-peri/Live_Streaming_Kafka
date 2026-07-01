# Live Streaming — Distributed Pub/Sub System

A Kafka-inspired real-time message streaming system built from scratch in Python, deployed across 4 machines over a ZeroTier virtual LAN. Topics can be created, updated, or deactivated dynamically at runtime. Unlike standard Kafka setups, this system separates persistence from routing — messages are written to a database *before* the broker touches them, so no message is lost even if the broker goes down mid-flight.

Built without Kafka, RabbitMQ, or any external message queue library. Every primitive — topic management, pub/sub routing, persistence, and health monitoring — is implemented from scratch.

---

## Architecture

The key design decision here is that the **DB Admin node sits between the producer and the broker**, not after it. This means every message is persisted the moment it enters the system, independent of whether the broker or consumers are healthy.

```
                        ┌──────────────────────────────┐
                        │        DB Admin Node         │
┌──────────────┐        │  ┌────────────┐  ┌────────┐  │        ┌──────────────┐
│   Producer   │───────▶|  │  DB Write  │  │ Health │  │        │   Consumer   │
│   (Node 1)   │        │  │  (persist) │  │Monitor │  │        │   (Node 3)   │
└──────────────┘        │  └─────┬──────┘  └────────┘  │        └──────┬───────┘
                        │        │    (Node 4/Client)  │               │
                        └────────┼────────────────────-┘               │
                                 │                                     │
                                 ▼                                     │
                        ┌──────────────┐                               │
                        │    Broker    │───────────────────────────────▶
                        │   (Node 2)   │
                        └──────────────┘
```

| Node | Role | What it does |
|---|---|---|
| `producer_node` | Producer | Publishes messages to named topics |
| `node2_broker` | Broker | Reads from DB Admin, routes to subscribed consumers |
| `Node3_Consumer` | Consumer | Subscribes to topics, receives routed messages |
| `Node4_Client` | DB Admin + Monitor | Persists every message to DB on arrival; monitors health of all nodes |

---

## Why DB Admin Sits Before the Broker

In a standard Kafka setup, the broker is responsible for both routing *and* persistence (via the commit log). Here, persistence is decoupled — the DB Admin writes every incoming message to the database the moment the producer sends it. The broker then reads from the DB Admin and routes to consumers.

This means:
- A broker crash doesn't lose any messages — they're already in the DB
- The broker can recover and replay from the DB without producer involvement
- The health monitor and persistence layer share a single node, which simplifies the cluster topology

The tradeoff is that the DB Admin becomes a single point of failure. In production you'd replicate it — but for a 4-node prototype this was the right call.

---

## Features

**Dynamic Topic Lifecycle**
Topics are created, updated, and deactivated at runtime without restarting any node. Consumers detect new topics and re-subscribe automatically.

**Message Persistence Before Routing**
Every message is written to the database by the DB Admin node before the broker receives it. Broker or consumer failures don't result in message loss.

**Cluster Health Monitoring**
The DB Admin node continuously monitors all nodes. Failures are detected with millisecond-level lag and displayed live on the dashboard — which node is up, which topics are active, broker connection status, and current consumer subscriptions.

**Observed Performance**
Tested across 4 laptops on a ZeroTier virtual LAN:

| Metric | Value |
|---|---|
| Message throughput | ~1,000 messages/sec |
| End-to-end latency | ~1–2 seconds (producer → consumer) |
| Node failure detection | Near real-time (ms-level lag) |
| Message durability | Persisted to DB before broker routing |

---

## Tech Stack

- **Language:** Python (100%)
- **Networking:** ZeroTier virtual LAN
- **Persistence:** Database managed by DB Admin node
- **Concurrency:** Python threading / socket programming

---

## Setup & Running

Each folder is a standalone node. Run each on a separate machine joined to the same ZeroTier network. Update the IP addresses in each node's config to match your ZeroTier-assigned IPs before starting.

### Start Order

```bash
# 1. DB Admin first — everything else depends on it
cd Node4_Client
python client.py

# 2. Broker — connects to DB Admin
cd node2_broker
python broker.py

# 3. Consumer
cd Node3_Consumer
python consumer.py

# 4. Producer last
cd producer_node
python producer.py
```

Once all four are running, the DB Admin dashboard shows live cluster state. Messages produced by Node 1 will be persisted to the DB, routed through the broker, and delivered to the consumer in real time.

---

## Limitations & What's Next

- **DB Admin is a single point of failure.** Replicating it with a consensus mechanism (Raft or Paxos) would be the real-world fix.
- **No message replay API.** Messages are persisted but there's no consumer-facing API to request historical messages from a given offset (like Kafka's offset management).
- **Static node discovery.** IPs are configured manually. Dynamic discovery would require a separate registry service.
- **In-memory broker state.** The broker's routing table is rebuilt on restart — a persistent routing state would make recovery faster.

---

## What I Learned

The most interesting insight was realising why Kafka puts the broker *in charge* of persistence rather than separating it out: it simplifies offset management and replay. In this system, because the DB Admin owns persistence, the broker has no native concept of "replay from offset X" — it just routes what it receives. That's fine for fire-and-forget messaging but breaks down for any use case where consumers need to catch up after a crash.

The other hard lesson: distributed health monitoring is deceptively tricky. Network partitions look identical to node crashes from the monitor's perspective, and you need timeouts tuned carefully or you get false-positive failure alerts flooding the dashboard.

---

## Project Context

Built for the Big Data (BD) course at PES University — the constraint was to implement Kafka-like primitives without using Kafka itself..
