CLASS_SAFETY_HELMET = "helmet"
CLASS_PERSON = "person"
CLASS_VEHICLE = "vehicle"


def point_in_polygon(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _orient(a, b, c):
    v = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def _on_segment(a, b, c):
    return (min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and
            min(a[1], c[1]) <= b[1] <= max(a[1], c[1]))


def segments_intersect(p1, q1, p2, q2):
    o1 = _orient(p1, q1, p2)
    o2 = _orient(p1, q1, q2)
    o3 = _orient(p2, q2, p1)
    o4 = _orient(p2, q2, q1)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p2, q1):
        return True
    if o2 == 0 and _on_segment(p1, q2, q1):
        return True
    if o3 == 0 and _on_segment(p2, p1, q2):
        return True
    if o4 == 0 and _on_segment(p2, q1, q2):
        return True
    return False


def bbox_center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class PolygonZone:
    def __init__(self, rid, poly, classes=None, name=""):
        self.rid = rid
        self.poly = poly
        self.classes = classes or [CLASS_PERSON]
        self.name = name

    def hit(self, det):
        if det["cls"] not in self.classes:
            return False
        return point_in_polygon(bbox_center(det["bbox"]), self.poly)


class LineZone:
    def __init__(self, rid, line, classes=None, direction="both", name=""):
        self.rid = rid
        self.line = line
        self.classes = classes or [CLASS_PERSON]
        self.direction = direction
        self.name = name

    def crossed(self, prev, cur):
        if prev is None:
            return False
        if cur["cls"] not in self.classes:
            return False
        if prev.get("cls") != cur["cls"]:
            return False
        a = bbox_center(prev["bbox"])
        b = bbox_center(cur["bbox"])
        p, q = self.line
        return segments_intersect(a, b, p, q)


class RuleEngine:
    def __init__(self, polygon_zones=None, line_zones=None, class_filters=None):
        self.polygon_zones = polygon_zones or []
        self.line_zones = line_zones or []
        self.class_filters = class_filters or []

    @classmethod
    def from_rules(cls, rules):
        pz, lz, cf = [], [], []
        for r in rules:
            if r.kind == "polygon":
                pz.append(PolygonZone(r.rid, r.zone, r.classes or None, r.name))
            elif r.kind == "line":
                lz.append(LineZone(r.rid, r.line, r.classes or None, name=r.name))
            elif r.kind == "class_filter":
                cf.append({"rid": r.rid, "classes": r.classes, "name": r.name})
        return cls(pz, lz, cf)

    def evaluate(self, detections, prev_detections=None):
        events = []
        for d in detections:
            for z in self.polygon_zones:
                if z.hit(d):
                    events.append({"rule": z.rid, "type": "region_intrusion",
                                   "name": z.name, "cls": d["cls"], "track": d.get("track")})
        if prev_detections:
            prev_map = {(d.get("track"), d.get("cls")): d for d in prev_detections if d.get("track")}
            for d in detections:
                prev = prev_map.get((d.get("track"), d.get("cls")))
                for z in self.line_zones:
                    if z.crossed(prev, d):
                        events.append({"rule": z.rid, "type": "line_crossing",
                                       "name": z.name, "cls": d["cls"], "track": d.get("track")})
        return events

    def missing_compliance(self, detections, required_ppe=("helmet",)):
        persons = [d for d in detections if d["cls"] == CLASS_PERSON]
        wearers = set()
        for d in detections:
            for ppe in required_ppe:
                if d["cls"] == ppe and d.get("track"):
                    wearers.add(d["track"])
        out = []
        for p in persons:
            if p.get("track") not in wearers:
                out.append({"rule": "ppe", "type": "ppe_violation",
                            "cls": "person", "track": p.get("track"),
                            "name": "未佩戴" + "/".join(required_ppe)})
        return out

    def metrics(self, truth_events, detected_events):
        truth = {(e.get("rule"), e.get("track")) for e in truth_events}
        hit = {(e.get("rule"), e.get("track")) for e in detected_events}
        tp = len(truth & hit)
        fp = len(hit - truth)
        fn = len(truth - hit)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        return {"tp": tp, "fp": fp, "fn": fn,
                "precision": round(precision, 4), "recall": round(recall, 4),
                "false_alarm_rate": round(fp / (tp + fp), 4) if (tp + fp) else 0.0}
