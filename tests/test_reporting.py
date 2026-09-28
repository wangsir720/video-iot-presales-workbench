import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp.catalog import load_products, load_scenario  # noqa: E402
from wvp.bom import build_bom  # noqa: E402
from wvp.capacity import storage_tb, bandwidth_mbps, poe_budget, compute_tops  # noqa: E402
from wvp.selection import selection_matrix  # noqa: E402
from wvp import reporting  # noqa: E402
from wvp import optics  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ctx(sid):
    products = load_products(os.path.join(ROOT, "data", "products.json"))
    scenario = load_scenario(os.path.join(ROOT, "config", "scenarios", sid + ".yaml"))
    by_sku = {p.sku: p for p in products}
    streams = scenario.streams()
    cap = {
        "cameras": scenario.total_cameras(),
        "storage_tb": storage_tb(streams, scenario.record_days),
        "bandwidth_mbps": bandwidth_mbps(streams),
        "poe": poe_budget([(by_sku[p.product_sku], p.quantity) for p in scenario.points]),
        "compute": compute_tops(streams),
    }
    bom = build_bom(scenario, products)
    need = {"env": "outdoor", "min_resolution": 4.0, "min_night": 50,
            "requires_ai": ["region_intrusion", "line_crossing", "helmet"]}
    return {"scenario": scenario, "capacity": cap, "bom": bom, "products": by_sku,
            "matrix": selection_matrix(products, need), "rule_count": len(scenario.rules),
            "optics": optics.evaluate_scenario(scenario, by_sku)}


def test_all_templates_render():
    outs = reporting.render_all(os.path.join(ROOT, "templates"), os.path.join(ROOT, "outputs", "_test"),
                                _ctx("factory-perimeter"))
    assert len(outs) == 6
    for p in outs:
        assert os.path.getsize(p) > 200


def test_optics_doc_contains_point_table():
    text = reporting.render(os.path.join(ROOT, "templates"), "07-点位与镜头估算.md.j2",
                            _ctx("factory-perimeter"))
    assert "点位估算结果" in text and "像素密度" in text
    assert "不适用" in text
    assert "P01" in text


def test_solution_doc_contains_key_numbers():
    text = reporting.render(os.path.join(ROOT, "templates"), "02-技术方案书.md.j2",
                            _ctx("factory-perimeter"))
    assert "摄像机总数" in text and "存储需求" in text
    assert "边缘算力" in text and "工程量清单" in text


def test_report_generates_for_every_scenario():
    for sid in ("factory-perimeter", "campus", "water-conservancy"):
        ctx = _ctx(sid)
        text = reporting.render(os.path.join(ROOT, "templates"), "01-需求调研表.md.j2", ctx)
        assert ctx["scenario"].name in text
