import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp.rules import (  # noqa: E402
    point_in_polygon, segments_intersect, PolygonZone, LineZone, RuleEngine, bbox_center,
)

SQUARE = [[0.1, 0.55], [0.9, 0.55], [0.9, 0.95], [0.1, 0.95]]


def test_point_in_polygon_inside_outside():
    assert point_in_polygon((0.5, 0.70), SQUARE) is True
    assert point_in_polygon((0.05, 0.20), SQUARE) is False


def test_point_in_polygon_degenerate():
    assert point_in_polygon((0.5, 0.5), [[0.0, 0.0], [1.0, 1.0]]) is False


def test_segments_intersect_cross():
    assert segments_intersect((0.3, 0.7), (0.3, 0.45), (0.05, 0.5), (0.95, 0.5)) is True


def test_segments_intersect_parallel_no_cross():
    assert segments_intersect((0.3, 0.2), (0.3, 0.3), (0.05, 0.5), (0.95, 0.5)) is False


def test_bbox_center():
    cx, cy = bbox_center([0.2, 0.4, 0.4, 0.6])
    assert abs(cx - 0.3) < 1e-9 and abs(cy - 0.5) < 1e-9


def test_polygon_zone_class_filter():
    z = PolygonZone("R1", SQUARE, classes=["person"])
    inside = {"cls": "person", "track": 1, "bbox": [0.40, 0.60, 0.60, 0.80]}
    other = {"cls": "vehicle", "track": 2, "bbox": [0.40, 0.60, 0.60, 0.80]}
    assert z.hit(inside) is True
    assert z.hit(other) is False


def test_line_zone_crossing():
    z = LineZone("R2", [[0.05, 0.50], [0.95, 0.50]], classes=["person"])
    prev = {"cls": "person", "track": 1, "bbox": [0.30, 0.60, 0.36, 0.80]}
    cur = {"cls": "person", "track": 1, "bbox": [0.30, 0.38, 0.36, 0.52]}
    assert z.crossed(prev, cur) is True
    assert z.crossed(None, cur) is False


def test_rule_engine_evaluate_region_and_line():
    from wvp.models import Rule
    rules = [
        Rule(rid="R1", kind="polygon", name="禁区", zone=SQUARE, classes=["person"]),
        Rule(rid="R2", kind="line", name="警戒线", line=[[0.05, 0.50], [0.95, 0.50]], classes=["person"]),
    ]
    eng = RuleEngine.from_rules(rules)
    f1 = [{"cls": "person", "track": 1, "bbox": [0.30, 0.60, 0.36, 0.80]}]
    f2 = [{"cls": "person", "track": 1, "bbox": [0.30, 0.38, 0.36, 0.52]}]
    ev1 = eng.evaluate(f1, None)
    ev2 = eng.evaluate(f2, f1)
    assert any(e["rule"] == "R1" for e in ev1)
    assert any(e["rule"] == "R2" for e in ev2)


def test_rule_engine_ppe_violation():
    eng = RuleEngine()
    dets = [
        {"cls": "person", "track": 1, "bbox": [0.3, 0.6, 0.36, 0.8]},
        {"cls": "helmet", "track": 1, "bbox": [0.31, 0.58, 0.35, 0.64]},
        {"cls": "person", "track": 2, "bbox": [0.5, 0.6, 0.56, 0.8]},
    ]
    out = eng.missing_compliance(dets)
    assert len(out) == 1
    assert out[0]["track"] == 2


def test_metrics_values():
    eng = RuleEngine()
    truth = [{"rule": "R1", "track": 1}, {"rule": "R2", "track": 1}, {"rule": "R1", "track": 2}]
    detected = truth + [{"rule": "R1", "track": 9}]
    m = eng.metrics(truth, detected)
    assert m["tp"] == 3 and m["fp"] == 1 and m["fn"] == 0
    assert abs(m["precision"] - 0.75) < 1e-6
    assert m["recall"] == 1.0
    assert abs(m["false_alarm_rate"] - 0.25) < 1e-6

def test_rule_engine_line_crossing_with_ppe_on_same_track():
    from wvp.models import Rule
    rules = [Rule(rid="R2", kind="line", name="警戒线", line=[[0.05, 0.50], [0.95, 0.50]], classes=["person"])]
    eng = RuleEngine.from_rules(rules)
    f1 = [{"cls": "person", "track": 1, "bbox": [0.30, 0.60, 0.36, 0.80]},
          {"cls": "helmet", "track": 1, "bbox": [0.31, 0.58, 0.35, 0.64]}]
    f2 = [{"cls": "person", "track": 1, "bbox": [0.30, 0.38, 0.36, 0.52]}]
    ev = eng.evaluate(f2, f1)
    assert any(e["rule"] == "R2" and e["track"] == 1 for e in ev)
