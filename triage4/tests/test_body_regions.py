from triage4.perception.body_regions import BodyRegionPolygonizer


def test_build_from_bbox_returns_all_regions():
    polygonizer = BodyRegionPolygonizer()
    regions = polygonizer.build_from_bbox([0, 0, 10, 30])
    assert set(regions.keys()) == {"head", "torso", "left_arm", "right_arm", "left_leg", "right_leg"}
    assert all(len(poly) == 4 for poly in regions.values())


def test_build_from_center_handles_defaults():
    polygonizer = BodyRegionPolygonizer()
    regions = polygonizer.build_from_center(50.0, 50.0, width=10.0, height=30.0)
    torso = regions["torso"]
    xs = [p[0] for p in torso]
    ys = [p[1] for p in torso]

    assert min(xs) < 50.0 < max(xs)
    # torso is vertically between head and legs; it sits above the body centre
    assert min(ys) < 50.0
    assert max(ys) <= 65.0
    assert all(len(poly) == 4 for poly in regions.values())
