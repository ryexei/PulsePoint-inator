import heapq

def dijkstra(graph, start, end):

    distances = {node: float("inf") for node in graph}
    previous = {node: None for node in graph}

    distances[start] = 0
    queue = [(0, start)]

    while queue:
        current_distance, current = heapq.heappop(queue)

        if current == end:
            break

        for neighbor, weight in graph[current]:
            new_distance = current_distance + weight

            if new_distance < distances[str(neighbor)]:
                distances[str(neighbor)] = new_distance
                previous[str(neighbor)] = current
                heapq.heappush(queue, (new_distance, str(neighbor)))

    # reconstruct path
    path = []
    node = end
    while node:
        path.append(node)
        node = previous[node]

    return path[::-1], distances[end]