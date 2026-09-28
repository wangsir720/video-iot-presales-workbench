BITS_PER_MBPS = 1_000_000
SECONDS_PER_DAY = 86_400


def daily_gb(stream_mbps, hours=24):
    bits = stream_mbps * BITS_PER_MBPS * hours * 3600
    return bits / 8 / 1_000_000_000


def storage_tb(streams, days, hours_per_day=24, overhead=1.15, raid_factor=1.0, replicas=1):
    total_gb = sum(daily_gb(s, hours_per_day) for s in streams) * days
    total_gb = total_gb * overhead * raid_factor * replicas
    return round(total_gb / 1000.0, 2)


def bandwidth_mbps(streams, overhead=1.15):
    return round(sum(streams) * overhead, 2)


def uplink_recommendation(total_mbps):
    if total_mbps <= 200:
        return "千兆接入 + 千兆上联"
    if total_mbps <= 900:
        return "千兆接入 + 万兆上联"
    return "万兆接入 + 万兆上联（链路聚合）"


def poe_budget(products_with_qty):
    total_w = sum(p.poe_w * q for p, q in products_with_qty)
    return {
        "device_w": round(total_w, 1),
        "switch_w": round(total_w / 0.8, 1),
        "note": "交换机 PoE 预算按设备功耗 / 0.8 留 20% 余量",
    }


def compute_tops(streams, tops_per_stream=4.0, tops_per_box=32.0, reserve=1.15):
    need = len(streams) * tops_per_stream * reserve
    boxes = int(-(-need // tops_per_box))
    return {"need_tops": round(need, 1), "tops_per_box": tops_per_box, "boxes": boxes}


def channel_capacity(recorder_capacity_ch, cameras):
    return int(-(-cameras // recorder_capacity_ch))
