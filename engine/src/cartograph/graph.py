"""Graph algorithms over the call graph."""

from collections import deque


def impact(callers_of: dict[int, set[int]], start: int, max_depth: int = 3) -> dict[int, int]:
    """Everything that could break if `start` changes: breadth-first search over the reversed
    call graph (who calls me, who calls them, ...). Returns {function id: distance}, start
    excluded. O(V + E) over the reachable part; `max_depth` stops it spreading to everything."""
    dist = {start: 0}
    todo = deque([start])
    while todo:
        fid = todo.popleft()
        if dist[fid] == max_depth:
            continue
        for caller in callers_of.get(fid, ()):
            if caller not in dist:
                dist[caller] = dist[fid] + 1
                todo.append(caller)
    del dist[start]
    return dist
