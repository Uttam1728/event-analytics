# Event Analytics

A modular FastAPI application for collecting and processing `page_view` events with Redis-based minute bucket counting and persistent event storage.

---

## 🚀 Setup and Run Instructions

### 1. Using Docker Compose (Recommended)

This project includes a `docker-compose.yml` for easy setup. **Redis** is included as a service and is required for analytics.

#### Prerequisites
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/)

#### Steps
```bash
git clone https://github.com/Uttam1728/event-analytics
cd event-analytics
docker-compose up --build
```
- The API will be available at: [http://localhost:8000](http://localhost:8000)
- Redis will be available at: `localhost:6379`
- **API Testing:** Import the provided `event-analytics.postman_collection.json` into [Postman](https://www.postman.com/) to try all endpoints with example requests and responses.

### 2. Local Development (Without Docker)

#### Prerequisites
- Python 3.10+
- Redis server running locally (default: `localhost:6379`)

#### Steps
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379
uvicorn main:app --reload
```

---

## 📝 Project Overview

- **FastAPI** backend for ingesting, analyzing, and persisting event data
- **Redis** for real-time analytics (minute bucket counting)
- **Persistent storage** for event backup and recovery

---

## 📚 API Endpoints

### Health
- `GET /health/` — Service health check

### Events
- `POST /events` — Ingest a new `page_view` event (JSON body)

### Analytics
- `GET /analytics/page_views_per_minute` — Page view counts per minute (last 5 minutes)
- `GET /analytics/minute-buckets/{minute_key}` — Count for a specific minute bucket

### Persistent Events
- `GET /persistent/status` — Status and statistics of persistent event processor

- See the included `event-analytics.postman_collection.json` for ready-to-use API requests and example payloads.

---

## 🧪 Development & Testing

- All dependencies are listed in `requirements.txt`.
- Main entry point: `main.py`
- Routers: `app/routers/`
- **API Testing:** Use the included Postman collection (`event-analytics.postman_collection.json`) for quick endpoint validation.
- **Load Testing:** Use `load_test.py` to simulate high event throughput and test system performance. See the script for usage instructions and options.

---

## 📁 Directory Structure

```
.
├── app/
│   ├── routers/           # API route definitions
│   ├── services/          # Business logic and Redis integration
│   ├── models/            # Pydantic models
├── persistent_events/     # Persistent event storage
├── main.py                # FastAPI entry point
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker build file
├── docker-compose.yml     # Multi-service orchestration
```

---

## ℹ️ Notes
- Redis data is persisted via Docker volume (`redis_data`).
- API docs available at `/docs` and `/redoc` when running.
- For custom configuration, edit environment variables in `docker-compose.yml` or your shell.

---

## 🧐 Design Q&A

**Q: How does your approach ensure concurrency & accuracy for per-minute counts?**
- Uses **Redis** for per-minute counting.
- Relies on atomic operations (`INCR`/`INCRBY`), which are:
  - Single-threaded and atomic in Redis.
  - Immune to race conditions and data corruption, even with high concurrency.
- No manual locking or complex synchronization needed.

**Q: How would you scale to millions of events per second?**
- **Sharding**: Distribute events across multiple Redis instances or clusters.
- **Batching**: Aggregate counts in memory, then periodically flush to Redis to reduce write load.
- **Stream Processing**: Integrate with tools like Kafka or Redis Streams for asynchronous, distributed ingestion.
- **Optimized Data Structures**:
  - Use Redis **HyperLogLog** for approximate unique counts (saves memory).
  - Use **sorted sets** for more granular analytics.
- **Horizontal scaling**: Deploy multiple API and worker instances behind a load balancer.

**Q: How is data durability ensured?**
- **Redis AOF (Append-Only File)**:
  - All write operations are logged and can be replayed after a restart.
  - Enabled via `redis-server --appendonly yes` in Docker Compose.
- **Backups**:
  - Periodically back up Redis data.
  - Persist aggregated results to disk or a database (via the persistent event processor).
- **Failover**:
  - For production, consider Redis replication and automated failover.

**Q: How would you add unique users per minute?**
- For each minute bucket, maintain a Redis **Set**:
  - `SADD page_view_users_YYYY-MM-DD_HH:MM user_id`
- To get the unique user count:
  - Use `SCARD` on the set.
- For very high cardinality:
  - Use **HyperLogLog** (`PFADD`/`PFCOUNT`) for approximate unique counts.
- **Challenges:**
  - Memory usage increases with the number of unique users.
  - Need expiry policies to clean up old sets and save memory.
  - Approximate structures (HyperLogLog) trade accuracy for efficiency.

**Q: Why did you choose these technologies and data structures?**
- **Python & FastAPI**:
  - Rapid development and async support.
  - Strong ecosystem for APIs and background processing.
- **Redis**:
  - In-memory speed and atomic operations.
  - Persistence options (AOF, RDB) for durability.
  - High throughput for real-time analytics.
- **Data Structures**:
  - **Strings** for counters (fast, simple).
  - **Sets** for unique users (accurate, easy to query).
  - **JSONL files** for persistent event storage (portable, easy to back up).
- **File-based Persistence**:
  - Simple and portable for small/medium scale.
  - Can be replaced with a database for larger scale or advanced querying.

**Q: What future enhancements are possible?**
- **Additional Time Windows**:
  - Add per-hour or per-day buckets by aggregating minute counts.
  - Maintain separate counters (e.g., `page_view_YYYY-MM-DD_HH`).
- **Other Event Types**:
  - Extend event models and routers to support new types (e.g., clicks, signups).
- **Advanced Analytics**:
  - Endpoints for top pages, user retention, funnel analysis, etc.
- **Storage Upgrades**:
  - Migrate persistent storage to scalable databases (e.g., PostgreSQL, BigQuery).
- **Monitoring & Alerting**:
  - Integrate with monitoring tools for real-time health and performance tracking.

**Q: How do you manage per-minute aggregation and handle timestamps? Why did you choose this approach?**
- **Minute Bucketing:**
  - Each event's timestamp is truncated to the minute (e.g., `2024-06-07T12:34:56Z` → `2024-06-07T12:34:00Z`).
  - The system generates a unique key for each minute bucket (e.g., `page_view_YYYY-MM-DD_HH:MM`).
  - All events within the same minute increment the same Redis counter.
- **Why this approach?**
  - **Simplicity:** Easy to implement and reason about.
  - **Efficiency:** Reduces the number of keys and operations in Redis, making aggregation fast and scalable.
  - **Query Performance:** Allows quick retrieval of per-minute analytics without post-processing.
  - **Extensibility:** The same pattern can be used for other time windows (hourly, daily) by changing the truncation logic.
- **Timestamp Handling:**
  - All timestamps are normalized to UTC to avoid timezone issues.
  - Truncation is done using standard datetime functions, ensuring consistency across the system.
- **Alternatives Considered:**
  - Storing raw timestamps for each event (would require expensive queries for aggregation).
  - Using more granular buckets (per-second) — not needed for most analytics use cases and would increase storage/processing overhead.

---

## License

MIT (or specify your license here)