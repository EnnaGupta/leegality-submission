# Network Route Optimization API

A REST API that models a network of servers as a **directed weighted graph** and finds the **shortest (lowest-latency) route** between any two servers using **Dijkstra's algorithm**.

---

## Tech Stack

- **Django 5 + Django REST Framework** — REST API and ORM
- **PostgreSQL** — persistent source of truth
- **Redis** — cached graph adjacency list (lazy-load / cache-aside pattern)
- **Docker / Docker Compose** — one-command setup

---

## Architecture

```
Client / Postman
       │
       ▼
  Django REST API
       │
  ┌────┴────┐
  ▼         ▼
PostgreSQL  Redis (adjacency cache)
```

- **Writes** (nodes, edges) → saved to PostgreSQL, Redis cache **invalidated**.
- **Route queries** → read adjacency list from Redis (cache hit) or PostgreSQL (cache miss, then populate Redis).
- PostgreSQL is always the source of truth. Redis is disposable.

---

## Quick Start

```bash
git clone <repo-url>
cd Leegality-assignment
docker compose up --build
```

Interactive Web Dashboard at **http://localhost:8000/**  
REST API Endpoints at **http://localhost:8000/** (`/nodes`, `/edges`, `/routes/shortest`, etc.)  

---

## API Endpoints

Summary of all available API endpoints:

| Method | Endpoint | Description | Request Body / Params | Status Code |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | `/` | Interactive Web Dashboard | None | 200 OK |
| **GET** | `/nodes` | List all servers/nodes | None | 200 OK |
| **POST** | `/nodes` | Add a new server/node | `{"name": "ServerA"}` | 201 Created / 400 Bad Request |
| **DELETE** | `/nodes/<id>` | Delete a server/node (cascades edges) | None | 204 No Content / 404 Not Found |
| **GET** | `/edges` | List all directed edges | None | 200 OK |
| **POST** | `/edges` | Add a directed edge with latency | `{"source": "ServerA", "destination": "ServerB", "latency": 12.5}` | 201 Created / 400 Bad Request |
| **PUT** | `/edges/<id>` | Update edge latency | `{"latency": 15.0}` | 200 OK / 400 Bad Request / 404 Not Found |
| **DELETE** | `/edges/<id>` | Delete an edge | None | 204 No Content / 404 Not Found |
| **POST** | `/routes/shortest` | Find shortest route using Dijkstra's algorithm | `{"source": "ServerA", "destination": "ServerD"}` | 200 OK / 400 / 404 Not Found |
| **GET** | `/routes/history` | Query past calculated routes | Query params: `source`, `destination`, `limit`, `date_from`, `date_to` | 200 OK |

---

### 1. Nodes API

#### Add Node
```bash
curl -X POST http://localhost:8000/nodes \
  -H "Content-Type: application/json" \
  -d '{"name": "ServerA"}'
```
**Response (201 Created):**
```json
{"id": 1, "name": "ServerA"}
```
*Errors:* `400 Bad Request` if name is missing or node already exists (case- and whitespace-insensitive).

#### List Nodes
```bash
curl http://localhost:8000/nodes
```
**Response (200 OK):**
```json
[
  {"id": 1, "name": "ServerA"},
  {"id": 2, "name": "ServerB"}
]
```

#### Delete Node
```bash
curl -X DELETE http://localhost:8000/nodes/1
```
**Response (204 No Content)**  
*Note:* Deleting a node cascades and removes all connected edges, automatically invalidating the cache.

---

### 2. Edges API

#### Add Edge
```bash
curl -X POST http://localhost:8000/edges \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerB", "latency": 12.5}'
```
**Response (201 Created):**
```json
{"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5}
```
*Errors:* `400 Bad Request` if source/destination nodes do not exist, source == destination, latency <= 0, or edge already exists.

#### List Edges
```bash
curl http://localhost:8000/edges
```
**Response (200 OK):**
```json
[
  {"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5}
]
```

#### Update Edge Latency
```bash
curl -X PUT http://localhost:8000/edges/1 \
  -H "Content-Type: application/json" \
  -d '{"latency": 18.0}'
```
**Response (200 OK):**
```json
{"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 18.0}
```

#### Delete Edge
```bash
curl -X DELETE http://localhost:8000/edges/1
```
**Response (204 No Content)**

---

### 3. Shortest Route & Route History

#### Find Shortest Route
```bash
curl -X POST http://localhost:8000/routes/shortest \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerD"}'
```
**Response (200 OK, Path Exists):**
```json
{
  "total_latency": 23.4,
  "path": ["ServerA", "ServerB", "ServerD"]
}
```
**Response (404 Not Found, No Path):**
```json
{
  "error": "No path exists between ServerA and ServerD"
}
```

#### Query Route History
```bash
curl "http://localhost:8000/routes/history?source=ServerA&limit=10"
```
**Response (200 OK):**
```json
[
  {
    "id": 1,
    "source": "ServerA",
    "destination": "ServerD",
    "total_latency": 23.4,
    "path": ["ServerA", "ServerB", "ServerD"],
    "created_at": "2026-10-01T10:30:00Z"
  }
]
```
*Optional Query Parameters:*
- `source`: Filter by source node name
- `destination`: Filter by destination node name
- `limit`: Maximum number of history entries returned
- `date_from` / `date_to`: Filter by ISO 8601 timestamp

---

## Caching Strategy

**Lazy-load / Cache-aside pattern:**

1. On `POST /routes/shortest` → check Redis for the adjacency list.
2. **Cache hit** → run Dijkstra directly (no DB query).
3. **Cache miss** → load all edges from PostgreSQL → store in Redis → run Dijkstra.
4. On edge/node **create or delete** → invalidate the Redis cache key.
5. If Redis is down → transparently fallback to PostgreSQL.

---

## Dijkstra's Algorithm

- Uses Python's `heapq` as a min-priority queue.
- Maintains `distances` and `predecessors` dictionaries.
- Skips stale heap entries for efficiency.
- Returns `(total_latency, path_list)` or `None` if unreachable.
- Edges are **directed**: A→B does not imply B→A.

---

## Development Notes

- **Debug mode** is enabled (`DJANGO_DEBUG=True` in `docker-compose.yml`) since this is a local development setup. In production, this would be set to `False` and `ALLOWED_HOSTS` would be restricted.
- **`runserver`** is used in the Dockerfile for convenience — it serves static files and auto-reloads on code changes. For production, this would be replaced with `gunicorn` (already included in `requirements.txt`).
- **`collectstatic`** runs with `2>/dev/null || true` during the Docker build to avoid failing on missing static directories. This is acceptable for a dev setup.

