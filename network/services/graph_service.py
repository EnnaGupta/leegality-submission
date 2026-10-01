import heapq
from typing import Optional


def find_shortest_path(
    graph: dict[str, list[tuple[str, float]]],
    source: str,
    destination: str,
) -> Optional[tuple[float, list[str]]]:
    # Same node has 0 latency
    if source == destination:
        return (0.0, [source])

    distances: dict[str, float] = {source: 0.0}
    predecessors: dict[str, str] = {}
    heap: list[tuple[float, str]] = [(0.0, source)]

    while heap:
        current_dist, current_node = heapq.heappop(heap)

        if current_node == destination:
            return (current_dist, _reconstruct_path(predecessors, source, destination))

        # Skip outdated entries
        if current_dist > distances.get(current_node, float("inf")):
            continue

        for neighbor, latency in graph.get(current_node, []):
            new_dist = current_dist + latency
            if new_dist < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_dist
                predecessors[neighbor] = current_node
                heapq.heappush(heap, (new_dist, neighbor))

    return None


def _reconstruct_path(
    predecessors: dict[str, str],
    source: str,
    destination: str,
) -> list[str]:
    # Backtrack from destination to source
    path = [destination]
    current = destination
    while current != source:
        current = predecessors[current]
        path.append(current)
    path.reverse()
    return path
