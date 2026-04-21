from triage4.autonomy.route_planner import (
    all_shortest_paths,
    bfs_path,
    plan_robot_route,
)


def _edges_simple() -> list[tuple[str, str]]:
    # Ring: A — B — C — D — A with a diagonal B — D.
    return [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A"), ("B", "D")]


def test_bfs_path_returns_start_when_same():
    assert bfs_path([], "A", "A") == ["A"]


def test_bfs_path_finds_shortest_route():
    # A → C: via B-C or D-C. Both are two hops.
    path = bfs_path(_edges_simple(), "A", "C")
    assert path[0] == "A" and path[-1] == "C"
    assert len(path) == 3


def test_bfs_path_unreachable_returns_start_only():
    # Two disconnected components: (A,B) vs (X,Y).
    edges: list[tuple[str, str]] = [("A", "B"), ("X", "Y")]
    assert bfs_path(edges, "A", "Y") == ["A"]


def test_all_shortest_paths_covers_connected_component():
    paths = all_shortest_paths(_edges_simple(), "A")
    assert set(paths) == {"A", "B", "C", "D"}
    for target, path in paths.items():
        assert path[0] == "A"
        assert path[-1] == target


def test_plan_robot_route_wrapper():
    # UAV at node "waypoint_1", casualty at "sector_B4".
    edges: list[tuple[str, str]] = [
        ("uav_1", "waypoint_1"),
        ("waypoint_1", "waypoint_2"),
        ("waypoint_2", "sector_B4"),
    ]
    route = plan_robot_route(edges, "uav_1", "sector_B4")
    assert route == ["uav_1", "waypoint_1", "waypoint_2", "sector_B4"]


def test_bfs_directed_respects_direction():
    # Edge only goes A → B, not B → A.
    edges: list[tuple[str, str]] = [("A", "B")]
    assert bfs_path(edges, "A", "B", directed=True) == ["A", "B"]
    assert bfs_path(edges, "B", "A", directed=True) == ["B"]
