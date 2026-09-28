from . import capacity


def build_bom(scenario, products, install_ratio=0.15, ops_years=3, ops_ratio=0.08,
              platform_price_ref=0.0, platform_channels=0):
    by_sku = {p.sku: p for p in products}
    lines = []
    for pt in scenario.points:
        p = by_sku.get(pt.product_sku)
        if not p:
            raise KeyError("未在产品库中找到机型: %s" % pt.product_sku)
        amount = p.unit_price_ref * pt.quantity
        lines.append({
            "sku": p.sku, "name": p.name, "qty": pt.quantity,
            "unit": p.unit_price_ref, "amount": amount, "group": "前端",
        })

    cameras = scenario.total_cameras()
    streams = scenario.streams()
    storage = capacity.storage_tb(streams, scenario.record_days)
    nvr_sku = next((p for p in products if p.category == "recorder"), None)
    nvr_capacity = nvr_sku.capacity_ch if nvr_sku else 32
    nvr_qty = capacity.channel_capacity(nvr_capacity, cameras)
    if nvr_sku:
        lines.append({"sku": nvr_sku.sku, "name": nvr_sku.name, "qty": nvr_qty,
                      "unit": nvr_sku.unit_price_ref, "amount": nvr_sku.unit_price_ref * nvr_qty,
                      "group": "存储"})

    disk = next((p for p in products if p.category == "storage"), None)
    disk_qty = int(-(-storage // 8.0)) if disk else 0
    if disk:
        lines.append({"sku": disk.sku, "name": disk.name, "qty": disk_qty,
                      "unit": disk.unit_price_ref, "amount": disk.unit_price_ref * disk_qty,
                      "group": "存储"})

    sw = next((p for p in products if p.category == "switch"), None)
    sw_qty = int(-(-cameras // 16))
    if sw:
        lines.append({"sku": sw.sku, "name": sw.name, "qty": sw_qty,
                      "unit": sw.unit_price_ref, "amount": sw.unit_price_ref * sw_qty,
                      "group": "网络"})

    edge = next((p for p in products if p.category == "edge"), None)
    boxes = capacity.compute_tops(streams)["boxes"]
    if edge:
        lines.append({"sku": edge.sku, "name": edge.name, "qty": boxes,
                      "unit": edge.unit_price_ref, "amount": edge.unit_price_ref * boxes,
                      "group": "算力"})

    plat = next((p for p in products if p.category == "platform"), None)
    if plat:
        ch = platform_channels or max(cameras, 100)
        price = platform_price_ref or plat.unit_price_ref
        amount = price * (ch / 100.0 if plat.unit_price_ref else 1)
        lines.append({"sku": plat.sku, "name": plat.name, "qty": ch,
                      "unit": round(amount / ch, 2) if ch else 0,
                      "amount": round(amount, 2), "group": "平台"})

    hw = sum(x["amount"] for x in lines)
    install = hw * install_ratio
    annual_ops = hw * ops_ratio
    ops = annual_ops * ops_years
    total = hw + install + ops
    return {
        "lines": lines,
        "cameras": cameras,
        "storage_tb": storage,
        "hardware": round(hw, 2),
        "install": round(install, 2),
        "ops_3y": round(ops, 2),
        "total": round(total, 2),
        "ops_years": ops_years,
    }
