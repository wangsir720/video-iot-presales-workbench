import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp.catalog import load_products, filter_products  # noqa: E402
from wvp.selection import select, score_product, selection_matrix  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEED = {"env": "outdoor", "min_resolution": 4.0, "min_night": 50,
        "requires_ai": ["region_intrusion", "line_crossing", "helmet"]}


def _products():
    return load_products(os.path.join(ROOT, "data", "products.json"))


def test_catalog_loads():
    items = _products()
    assert len(items) >= 10
    assert any(p.category == "camera" for p in items)


def test_filter_by_night_excludes_short_range():
    items = filter_products(_products(), category="camera", min_night=50)
    assert all(p.night_vision_m >= 50 for p in items)
    assert not any(p.sku == "IPC-D2-4M" for p in items)


def test_filter_by_env_excludes_indoor_only():
    items = filter_products(_products(), category="camera", env="outdoor")
    assert not any(p.ip_rating == "IP41" for p in items)


def test_select_returns_top_scored_camera():
    top = select(_products(), NEED, top_n=1)[0]
    assert top.sku == "IPC-B4-4M"
    assert score_product(top, NEED) == 100.0


def test_selection_matrix_shape():
    rows = selection_matrix(_products(), NEED)
    assert rows and rows[0]["score"] >= rows[-1]["score"]
    assert set(rows[0]) == {"sku", "name", "score", "price_ref", "ip"}
