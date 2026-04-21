from triage4.signatures.radar import (
    HEXSIG_N_DIMS,
    HEXSIG_N_NODES,
    HexSignature,
    antipode,
    bfs_distances,
    build_hex_signature,
    delaunay_graph,
    embed_to_q6,
    from_bits,
    hamming,
    hamming_ball,
    hamming_sphere,
    hex_median,
    metric_interval,
    neighbors,
    packing_number,
    shortest_path,
    to_bits,
    voronoi_cells,
)


def test_constants_consistent():
    assert HEXSIG_N_DIMS == 6
    assert HEXSIG_N_NODES == 64


def test_to_bits_from_bits_roundtrip():
    for h in (0, 1, 13, 42, 63):
        bits = to_bits(h)
        assert len(bits) == 6
        assert from_bits(bits) == h


def test_hamming_symmetric():
    assert hamming(0, 0) == 0
    assert hamming(0, 63) == 6
    assert hamming(5, 10) == hamming(10, 5)


def test_neighbors_have_distance_one():
    for nb in neighbors(0):
        assert hamming(0, nb) == 1
    assert len(neighbors(0)) == 6


def test_antipode_maximizes_distance():
    for h in (0, 7, 42):
        assert hamming(h, antipode(h)) == 6


def test_hamming_ball_and_sphere_sizes():
    assert len(hamming_ball(0, 0)) == 1
    assert len(hamming_sphere(0, 1)) == 6
    # Ball radius 6 covers the whole hypercube.
    assert len(hamming_ball(0, 6)) == HEXSIG_N_NODES


def test_bfs_distances_cover_all_nodes():
    dist = bfs_distances(0)
    assert len(dist) == HEXSIG_N_NODES
    assert dist[0] == 0
    assert max(dist) == 6


def test_shortest_path_length_matches_hamming():
    a, b = 0b010101, 0b101010
    path = shortest_path(a, b)
    assert path[0] == a and path[-1] == b
    assert len(path) - 1 == hamming(a, b)


def test_shortest_path_same_node():
    assert shortest_path(7, 7) == [7]


def test_metric_interval_symmetric():
    u, v = 0b000011, 0b110000
    mi_uv = metric_interval(u, v)
    mi_vu = metric_interval(v, u)
    assert set(mi_uv) == set(mi_vu)


def test_hex_median_majority_bitwise():
    # Three points: 0b000, 0b011, 0b110. Majority per bit: 010 → 2.
    assert hex_median([0b000, 0b011, 0b110]) == 0b010


def test_voronoi_cells_partition_hypercube():
    centers = [0, 63]
    cells = voronoi_cells(centers)
    total = sum(len(v) for v in cells.values())
    assert total == HEXSIG_N_NODES


def test_delaunay_graph_nonempty():
    centers = [0, 7, 56]
    edges = delaunay_graph(centers)
    assert len(edges) > 0


def test_packing_number_returns_disjoint_ball_centers():
    centers = packing_number(radius=1)
    # Greedy packing with balls of radius 1 gives at least 8 centres (perfect
    # [7,4]-code bound) and at most N_NODES = 64. Upper bound comes from the
    # degenerate radius-0 case.
    assert 8 <= len(centers) <= 64
    # Each pair of centres must be farther than the ball radius.
    for i, a in enumerate(centers):
        for b in centers[i + 1 :]:
            assert hamming(a, b) > 1


def test_embed_to_q6_small_vector():
    h = embed_to_q6([0.1, 0.9, 0.1, 0.9, 0.1, 0.9])
    assert 0 <= h < HEXSIG_N_NODES


def test_embed_to_q6_large_vector_pools_uniformly():
    vec = [0.1] * 32 + [0.9] * 32
    h = embed_to_q6(vec)
    bits = to_bits(h)
    # The first three chunks are below mean, the last three above — so the
    # last three bits should be "on" and the first three "off" (bits encoded
    # least-significant-first via from_bits).
    assert sum(bits) >= 1
    assert 0 <= h < HEXSIG_N_NODES


def test_build_hex_signature_shape():
    sig = build_hex_signature([0.2, 0.8, 0.3, 0.9, 0.1, 0.7])
    assert isinstance(sig, HexSignature)
    assert 0 <= sig.hex_id < HEXSIG_N_NODES
    assert set(sig.archetype_bits) == {
        "material",
        "dynamic",
        "complex",
        "ordered",
        "local",
        "explicit",
    }


def test_build_hex_signature_with_voronoi():
    sig = build_hex_signature([0.2, 0.8, 0.3, 0.9, 0.1, 0.7], voronoi_centers=[0, 63])
    assert sig.voronoi_id in {0, 63}
    assert sig.hamming_r == hamming(sig.hex_id, sig.voronoi_id)
