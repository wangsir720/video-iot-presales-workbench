"""点位与镜头估算：视场角 / 覆盖宽度 / 像素密度 / DORI 最远距离 / 建议焦距 / 俯角。

口径说明
--------
- 靶面尺寸取公开通用档位（16:9 常见值），用于方案阶段估算，不作为厂商正式规格。
- 像素密度分级采用 IEC/EN 62676-4 常用的 DORI 口径（monitor / detect / observe /
  recognize / identify），单位为目标处像素数每米（px/m）。
- 全部结果为估算值，最终以现场勘查与厂商正式彩页为准。
"""
import math

SENSORS = {
    "1/3": (4.80, 2.70),
    "1/2.9": (5.00, 2.81),
    "1/2.8": (5.37, 3.02),
    "1/1.8": (7.20, 4.05),
}

DORI_PPM = {
    "monitor": 12.5,
    "detect": 25.0,
    "observe": 62.5,
    "recognize": 125.0,
    "identify": 250.0,
}

DORI_LABEL = {
    "monitor": "监视",
    "detect": "探测",
    "observe": "观察",
    "recognize": "识别",
    "identify": "辨识",
}

FOCAL_LADDER = (2.8, 4.0, 6.0, 8.0, 12.0, 16.0, 25.0, 50.0)


def sensor_size(name):
    if name not in SENSORS:
        raise KeyError("未知靶面档位: %s" % name)
    return SENSORS[name]


def fov_deg(sensor_mm, focal_mm):
    """由靶面边长与焦距求视场角（度）。"""
    return round(math.degrees(2.0 * math.atan(sensor_mm / (2.0 * focal_mm))), 2)


def coverage_m(sensor_mm, focal_mm, distance_m):
    """给定距离处的覆盖宽度（m）。"""
    return round(sensor_mm * distance_m / focal_mm, 2)


def pixels_per_meter(pixel_w, sensor_w_mm, focal_mm, distance_m):
    """目标处的像素密度（px/m）。"""
    if distance_m <= 0:
        return 0.0
    return round(pixel_w * focal_mm / (sensor_w_mm * distance_m), 1)


def max_distance_m(pixel_w, sensor_w_mm, focal_mm, ppm):
    """满足指定像素密度要求时允许的最远监视距离（m）。"""
    return round(pixel_w * focal_mm / (sensor_w_mm * ppm), 1)


def required_focal_mm(sensor_w_mm, pixel_w, distance_m, ppm):
    """在给定距离上达到指定像素密度所需的焦距（mm）。"""
    return round(sensor_w_mm * distance_m * ppm / pixel_w, 2)


def pick_focal(need_mm, ladder=FOCAL_LADDER):
    """在标准焦距阶梯里选出不小于需求值的最近档位。"""
    for f in ladder:
        if f >= need_mm:
            return f
    return ladder[-1]


def tilt_deg(install_height_m, ground_distance_m):
    """安装高度与地面覆盖距离对应的俯角（度）。"""
    if ground_distance_m <= 0:
        return 90.0
    return round(math.degrees(math.atan(install_height_m / ground_distance_m)), 1)


def dori_table(pixel_w, sensor_w_mm, focal_mm):
    """该焦距下各 DORI 等级对应的最远有效距离（m）。"""
    return {k: max_distance_m(pixel_w, sensor_w_mm, focal_mm, v) for k, v in DORI_PPM.items()}


def is_imaging(product):
    """该机型是否可用于本表的几何估算（热成像与后端设备不适用）。"""
    return bool(getattr(product, "sensor", "")) and getattr(product, "pixel_w", 0) > 0 \
        and getattr(product, "focal_mm", 0) > 0 and product.form != "thermal"


def evaluate_point(point, product, level=None):
    """评估单个点位：覆盖、密度、建议焦距、是否满足目标等级、偏差建议。"""
    level = level or getattr(point, "level", "") or "detect"
    out = {"pid": point.pid, "sku": product.sku, "name": product.name,
           "purpose": point.purpose, "level": level,
           "level_label": DORI_LABEL.get(level, level),
           "distance_m": point.distance_m, "quantity": point.quantity,
           "supported": False, "advice": ""}
    if not is_imaging(product):
        out["reason"] = "非可见光成像机型（如热成像），几何估算不适用，按 IFOV 与探测目标另行校核"
        return out

    sw, sh = sensor_size(product.sensor)
    pw, ph = product.pixel_w, product.pixel_h
    f = product.focal_mm
    ppm_need = DORI_PPM.get(level, DORI_PPM["detect"])

    ppm = pixels_per_meter(pw, sw, f, point.distance_m)
    out.update({
        "supported": True,
        "sensor": product.sensor,
        "pixel": "%dx%d" % (pw, ph),
        "focal_mm": f,
        "fov_h_deg": fov_deg(sw, f),
        "fov_v_deg": fov_deg(sh, f),
        "coverage_w_m": coverage_m(sw, f, point.distance_m),
        "coverage_h_m": coverage_m(sh, f, point.distance_m),
        "ppm": ppm,
        "ppm_need": ppm_need,
        "max_distance_m": max_distance_m(pw, sw, f, ppm_need),
        "ok": ppm >= ppm_need,
        "dori": dori_table(pw, sw, f),
    })
    if getattr(point, "install_height_m", 0) > 0:
        out["tilt_deg"] = tilt_deg(point.install_height_m, point.distance_m)

    need_f = required_focal_mm(sw, pw, point.distance_m, ppm_need)
    out["required_focal_mm"] = need_f
    if ppm >= ppm_need:
        out["advice"] = "现有 %s mm 镜头满足「%s」要求（余量 %.0f%%）" % (
            f, out["level_label"], (ppm / ppm_need - 1.0) * 100.0)
    else:
        sug = pick_focal(need_f)
        out["suggest_focal_mm"] = sug
        out["advice"] = "密度不足：%s 处仅 %.1f px/m（需 %.1f），建议换 %.1f mm 档或缩短至 %.0f m 以内" % (
            point.distance_m, ppm, ppm_need, sug, out["max_distance_m"])
    return out


def evaluate_scenario(scenario, products_by_sku, level=None):
    """整个场景的点位评估 + 汇总。"""
    rows = []
    for pt in scenario.points:
        prod = products_by_sku[pt.product_sku]
        rows.append(evaluate_point(pt, prod, level))
    checked = [r for r in rows if r["supported"]]
    ok = [r for r in checked if r["ok"]]
    return {
        "rows": rows,
        "summary": {
            "points": len(rows),
            "checked": len(checked),
            "ok": len(ok),
            "ng": len(checked) - len(ok),
            "skipped": len(rows) - len(checked),
        },
    }
