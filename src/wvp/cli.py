import argparse
import json
import os

from .catalog import load_products, load_scenario
from .capacity import storage_tb, bandwidth_mbps, poe_budget, compute_tops
from .selection import selection_matrix
from .bom import build_bom
from .diagram import build_svg
from .rules import RuleEngine
from . import reporting

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _paths():
    return {
        "products": os.path.join(HERE, "data", "products.json"),
        "templates": os.path.join(HERE, "templates"),
    }


def cmd_generate(args):
    p = _paths()
    products = load_products(p["products"])
    scenario = load_scenario(args.scenario)
    by_sku = {x.sku: x for x in products}

    streams = scenario.streams()
    cap = {
        "cameras": scenario.total_cameras(),
        "storage_tb": storage_tb(streams, scenario.record_days),
        "bandwidth_mbps": bandwidth_mbps(streams),
        "poe": poe_budget([(by_sku[pt.product_sku], pt.quantity) for pt in scenario.points]),
        "compute": compute_tops(streams),
    }
    bom = build_bom(scenario, products)
    svg = build_svg(scenario, bom)

    out_dir = args.out or os.path.join(HERE, "outputs", scenario.sid)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "06-系统架构图.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    reporting.bom_to_csv(bom, os.path.join(out_dir, "03-设备清单BOM.csv"))

    need = {"env": "outdoor", "min_resolution": 4.0, "min_night": 50,
            "requires_ai": ["region_intrusion", "line_crossing", "helmet"]}
    ctx = {
        "scenario": scenario,
        "capacity": cap,
        "bom": bom,
        "products": by_sku,
        "matrix": selection_matrix(products, need),
        "rule_count": len(scenario.rules),
    }
    reporting.render_all(p["templates"], out_dir, ctx)
    summary = {"scenario": scenario.sid, "out_dir": out_dir, **cap}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def cmd_rules_demo(args):
    import yaml
    with open(args.rules, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    from .models import Rule
    rules = [Rule(**r) for r in raw["rules"]]
    eng = RuleEngine.from_rules(rules)
    frames = raw.get("demo_frames", {})
    prev = []
    for frame in frames.get("frames", []):
        ev = eng.evaluate(frame, prev)
        print(json.dumps({"events": ev}, ensure_ascii=False))
        prev = frame
    m = eng.metrics(frames.get("truth", []), frames.get("detected", []))
    print(json.dumps({"metrics": m}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser(prog="wvp", description="视频物联售前解决方案工作台")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="按场景生成整套方案交付物")
    g.add_argument("--scenario", required=True)
    g.add_argument("--out", default=None)
    g.set_defaults(func=cmd_generate)

    r = sub.add_parser("rules-demo", help="跑一遍规则引擎演示")
    r.add_argument("--rules", required=True)
    r.set_defaults(func=cmd_rules_demo)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
