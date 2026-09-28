import json
from .models import Product, Scenario, CameraPoint, Rule


def load_products(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    items = []
    for r in raw["products"]:
        items.append(Product(**r))
    return items


def filter_products(items, category=None, form=None, min_resolution=None, min_night=None,
                    requires_ai=None, env=None):
    out = []
    for p in items:
        if category and p.category != category:
            continue
        if form and p.form != form:
            continue
        if min_resolution and p.resolution_mp < min_resolution:
            continue
        if min_night and p.night_vision_m < min_night:
            continue
        if env == "outdoor" and p.ip_rating == "IP41":
            continue
        if requires_ai:
            missing = [r for r in requires_ai if r not in p.ai_rules]
            if missing:
                continue
        out.append(p)
    return out


def load_scenario(path):
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    points = [CameraPoint(**p) for p in raw.get("points", [])]
    rules = [Rule(**r) for r in raw.get("rules", [])]
    return Scenario(
        sid=raw["sid"],
        name=raw["name"],
        site=raw["site"],
        client_type=raw["client_type"],
        objective=raw["objective"],
        record_days=raw.get("record_days", 30),
        points=points,
        rules=rules,
        requirements=raw.get("requirements", []),
        extras=raw.get("extras", []),
    )
