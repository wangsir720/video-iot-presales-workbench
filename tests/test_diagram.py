import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp.catalog import load_products, load_scenario  # noqa: E402
from wvp.bom import build_bom  # noqa: E402
from wvp.diagram import build_svg, LAYERS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle():
    products = load_products(os.path.join(ROOT, "data", "products.json"))
    scenario = load_scenario(os.path.join(ROOT, "config", "scenarios", "campus.yaml"))
    return scenario, build_bom(scenario, products)


def test_svg_is_wellformed_and_has_layers():
    scenario, bom = _bundle()
    svg = build_svg(scenario, bom)
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    for layer, _items in LAYERS:
        assert layer in svg


def test_svg_escapes_scenario_name():
    scenario, bom = _bundle()
    scenario.name = "A & B <test>"
    svg = build_svg(scenario, bom)
    assert "&amp;" in svg and "<test>" not in svg
