import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp.bom import build_bom  # noqa: E402
from wvp.pricing import tco_compare  # noqa: E402
from wvp.catalog import load_products, load_scenario  # noqa: E402
from wvp import reporting  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle():
    products = load_products(os.path.join(ROOT, "data", "products.json"))
    scenario = load_scenario(os.path.join(ROOT, "config", "scenarios", "factory-perimeter.yaml"))
    return scenario, products, build_bom(scenario, products)


def test_bom_camera_count_and_storage():
    scenario, products, bom = _bundle()
    assert bom["cameras"] == 16
    assert abs(bom["storage_tb"] - 27.95) < 0.05


def test_bom_groups_cover_all_layers():
    _, _, bom = _bundle()
    groups = {l["group"] for l in bom["lines"]}
    assert {"前端", "存储", "网络", "算力", "平台"} <= groups


def test_bom_totals_add_up():
    _, _, bom = _bundle()
    assert abs(bom["total"] - (bom["hardware"] + bom["install"] + bom["ops_3y"])) < 0.02


def test_tco_compare_discount_improves_total():
    _, _, bom = _bundle()
    r = tco_compare(bom, alt_hw_discount=0.1)
    assert r["delta"] > 0


def test_bom_csv_written(tmp_path):
    _, _, bom = _bundle()
    p = reporting.bom_to_csv(bom, os.path.join(str(tmp_path), "bom.csv"))
    assert os.path.exists(p)
    txt = open(p, encoding="utf-8-sig").read()
    assert "合计（参考）" in txt
