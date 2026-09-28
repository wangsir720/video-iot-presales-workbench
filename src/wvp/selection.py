from .catalog import filter_products


SCORE_FIELDS = ("resolution_mp", "night_vision_m", "bitrate_mbps", "unit_price_ref")


def score_product(p, need):
    score = 0.0
    if need.get("min_resolution"):
        score += 30 if p.resolution_mp >= need["min_resolution"] else -100
    if need.get("min_night"):
        score += 25 if p.night_vision_m >= need["min_night"] else -100
    if need.get("env") == "outdoor":
        score += 15 if p.ip_rating in ("IP66", "IP67") else -50
    req = need.get("requires_ai") or []
    if req:
        hit = sum(1 for r in req if r in p.ai_rules)
        score += 30 * (hit / len(req))
    if need.get("form") and p.form == need["form"]:
        score += 15
    if need.get("prefer_low_bitrate") and p.bitrate_mbps <= 4.0:
        score += 5
    return round(score, 1)


def select(products, need, category="camera", top_n=3):
    pool = filter_products(
        products,
        category=category,
        form=need.get("form"),
        min_resolution=need.get("min_resolution"),
        min_night=need.get("min_night"),
        requires_ai=need.get("requires_ai"),
        env=need.get("env"),
    )
    pool = [p for p in pool if score_product(p, need) > 0] or pool
    pool.sort(key=lambda p: (-score_product(p, need), p.unit_price_ref))
    return pool[:top_n]


def selection_matrix(products, need):
    rows = []
    for p in select(products, need, top_n=6):
        rows.append({"sku": p.sku, "name": p.name, "score": score_product(p, need),
                     "price_ref": p.unit_price_ref, "ip": p.ip_rating})
    return rows
