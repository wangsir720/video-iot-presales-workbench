def tco_compare(bom, alt_platform_share=0.0, alt_hw_discount=0.0):
    hw = bom["hardware"]
    alt_hw = hw * (1 - alt_hw_discount)
    alt_total = alt_hw + bom["install"] + bom["ops_3y"]
    return {
        "baseline": bom["total"],
        "alternative": round(alt_total, 2),
        "delta": round(bom["total"] - alt_total, 2),
        "delta_pct": round((bom["total"] - alt_total) / bom["total"] * 100, 2) if bom["total"] else 0,
        "note": "方案对比仅按公开参考价测算，正式报价以厂商报价单为准",
    }
