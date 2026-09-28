import argparse
import json
import os

from .catalog import load_products, load_scenario
from .capacity import storage_tb, bandwidth_mbps, poe_budget, compute_tops
from .selection import selection_matrix
from .bom import build_bom
from .diagram import build_svg
from .rules import RuleEngine
from . import optics
from . import gb28181
from . import reporting

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _paths():
    return {
        "products": os.path.join(HERE, "data", "products.json"),
        "templates": os.path.join(HERE, "templates"),
        "types": os.path.join(HERE, "config", "gb28181-device-types.yaml"),
    }


def _platform_channels(bom):
    for l in bom["lines"]:
        if l["group"] == "平台":
            return int(l["qty"])
    return 0


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

    # 点位与镜头估算
    opt = optics.evaluate_scenario(scenario, by_sku)

    # 生成设备接入清单并做 GB/T 28181 预检
    cfg = gb28181.load_type_config(p["types"]) or {}
    rows = gb28181.build_onboarding_list(
        scenario, by_sku,
        center_code=cfg.get("center_code", "33010600"),
        industry_code=cfg.get("industry_code", "00"),
        type_code=(cfg.get("allowed_type_codes") or ["131"])[0])
    gb = gb28181.check_devices(rows, platform_capacity_ch=_platform_channels(bom),
                               allowed_type_codes=cfg.get("allowed_type_codes"))
    reporting.save(gb28181.render_markdown(
        gb, title="设备接入清单与预检 · %s" % scenario.name),
        os.path.join(out_dir, "08-设备接入清单与预检.md"))

    need = {"env": "outdoor", "min_resolution": 4.0, "min_night": 50,
            "requires_ai": ["region_intrusion", "line_crossing", "helmet"]}
    ctx = {
        "scenario": scenario,
        "capacity": cap,
        "bom": bom,
        "products": by_sku,
        "matrix": selection_matrix(products, need),
        "rule_count": len(scenario.rules),
        "optics": opt,
    }
    reporting.render_all(p["templates"], out_dir, ctx)
    summary = {"scenario": scenario.sid, "out_dir": out_dir, **cap,
               "optics": opt["summary"],
               "gb28181": gb["summary"]}
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


def cmd_optics(args):
    products = load_products(_paths()["products"])
    scenario = load_scenario(args.scenario)
    by_sku = {x.sku: x for x in products}
    rep = optics.evaluate_scenario(scenario, by_sku)
    print("场景：%s（%s）" % (scenario.name, scenario.sid))
    print("点位 %d 个：可估算 %d，满足 %d，需调整 %d，不适用 %d"
          % (rep["summary"]["points"], rep["summary"]["checked"], rep["summary"]["ok"],
             rep["summary"]["ng"], rep["summary"]["skipped"]))
    for r in rep["rows"]:
        if r["supported"]:
            print("  %-4s %-22s %-10s 密度 %6.1f/%-5.1f px/m  %s"
                  % (r["pid"], r["purpose"], "满足" if r["ok"] else "需调整",
                     r["ppm"], r["ppm_need"], r["advice"]))
        else:
            print("  %-4s %-22s 不适用：%s" % (r["pid"], r["purpose"], r["reason"]))
    return rep


def cmd_gb28181_check(args):
    cfg = gb28181.load_type_config(args.types) if args.types else {}
    rows = gb28181.load_devices_csv(args.devices)
    rep = gb28181.check_devices(rows, platform_capacity_ch=args.platform_ch,
                                allowed_type_codes=cfg.get("allowed_type_codes"),
                                sip_port=args.sip_port)
    md = gb28181.render_markdown(rep, title="设备接入预检 · %s" % os.path.basename(args.devices))
    if args.out:
        reporting.save(md, args.out)
        print("已写出：%s" % args.out)
    print(md)
    return rep


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

    o = sub.add_parser("optics", help="按场景做点位与镜头估算")
    o.add_argument("--scenario", required=True)
    o.set_defaults(func=cmd_optics)

    c = sub.add_parser("gb28181-check", help="对设备接入清单做 GB/T 28181 预检")
    c.add_argument("--devices", required=True)
    c.add_argument("--platform-ch", type=int, default=0)
    c.add_argument("--sip-port", type=int, default=5060)
    c.add_argument("--types", default=None, help="类型编码配置文件（YAML）")
    c.add_argument("--out", default=None)
    c.set_defaults(func=cmd_gb28181_check)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
