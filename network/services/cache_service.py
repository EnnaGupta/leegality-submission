import json
import logging

from django.core.cache import cache

from network.models import Edge

logger = logging.getLogger(__name__)

GRAPH_CACHE_KEY = "graph:adjacency"
GRAPH_CACHE_TTL = 60 * 60  # 1 hour


def get_adjacency_list() -> dict[str, list[tuple[str, float]]]:
    # Return cached graph if available, otherwise rebuild from DB
    cached = _get_from_cache()
    if cached is not None:
        return cached

    logger.info("Graph cache miss — rebuilding from database.")
    adjacency = _build_from_db()
    _set_to_cache(adjacency)
    return adjacency


def invalidate_cache() -> None:
    # Clear cache whenever nodes or edges change
    try:
        cache.delete(GRAPH_CACHE_KEY)
        logger.info("Graph cache invalidated.")
    except Exception:
        logger.warning("Failed to invalidate graph cache in Redis.", exc_info=True)


def _build_from_db() -> dict[str, list[tuple[str, float]]]:
    adjacency: dict[str, list[tuple[str, float]]] = {}
    edges = (
        Edge.objects
        .select_related("source", "destination")
        .all()
    )

    for edge in edges:
        src_name = edge.source.name
        dst_name = edge.destination.name
        adjacency.setdefault(src_name, []).append((dst_name, edge.latency))

    return adjacency


def _get_from_cache() -> dict[str, list[tuple[str, float]]] | None:
    try:
        raw = cache.get(GRAPH_CACHE_KEY)
        if raw is None:
            return None
        data = json.loads(raw)
        return {
            node: [(n, w) for n, w in neighbors]
            for node, neighbors in data.items()
        }
    except Exception:
        logger.warning("Failed to read graph cache from Redis.", exc_info=True)
        return None


def _set_to_cache(adjacency: dict[str, list[tuple[str, float]]]) -> None:
    try:
        serialisable = {
            node: [[n, w] for n, w in neighbors]
            for node, neighbors in adjacency.items()
        }
        cache.set(GRAPH_CACHE_KEY, json.dumps(serialisable), GRAPH_CACHE_TTL)
    except Exception:
        logger.warning("Failed to write graph cache to Redis.", exc_info=True)
