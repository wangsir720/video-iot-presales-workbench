import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp import optics  # noqa: E402
from wvp.models import CameraPoint, Product  # noqa: E402


def _cam(sku="C1", sensor="1/2.8", pw=2560, ph=1440, f=4.0, form="bullet"):
    return Product(sku=sku, name="测试机型", category="camera", form=form, resolution_mp=4.0,
                   fps=25, codec="H.265", bitrate_mbps=4.5, night_vision_m=60, poe_w=12.0,
                   ip_rating="IP67", sensor=sensor, pixel_w=pw, pixel_h=ph, focal_mm=f)


def test_fov_horizontal_reasonable():
    v = optics.fov_deg(5.37, 4.0)
    assert 60 < v < 75


def test_fov_narrows_as_focal_grows():
    assert optics.fov_deg(5.37, 2.8) > optics.fov_deg(5.37, 12.0)


def test_coverage_known_value():
    assert abs(optics.coverage_m(5.37, 4.0, 60) - 80.55) < 0.01


def test_pixels_per_meter_known_value():
    v = optics.pixels_per_meter(2560, 5.37, 4.0, 60)
    assert abs(v - 31.8) < 0.1


def test_pixels_per_meter_drops_with_distance():
    a = optics.pixels_per_meter(2560, 5.37, 4.0, 30)
    b = optics.pixels_per_meter(2560, 5.37, 4.0, 60)
    assert a > b


def test_pixels_per_meter_guards_zero_distance():
    assert optics.pixels_per_meter(2560, 5.37, 4.0, 0) == 0.0


def test_max_distance_for_detect():
    assert abs(optics.max_distance_m(2560, 5.37, 4.0, 25.0) - 76.3) < 0.2


def test_required_focal_and_pick_ladder():
    need = optics.required_focal_mm(5.37, 2560, 60, 125.0)
    assert abs(need - 15.73) < 0.05
    assert optics.pick_focal(need) == 16.0


def test_pick_focal_bounds():
    assert optics.pick_focal(1.0) == 2.8
    assert optics.pick_focal(999.0) == 50.0


def test_tilt_deg_known_value():
    assert abs(optics.tilt_deg(4.0, 60) - 3.8) < 0.1


def test_dori_table_ordering():
    t = optics.dori_table(2560, 5.37, 4.0)
    assert t["identify"] < t["recognize"] < t["observe"] < t["detect"] < t["monitor"]


def test_evaluate_point_meets_detect():
    p = CameraPoint(pid="P1", purpose="周界", product_sku="C1", quantity=1, stream_mbps=4.5,
                    distance_m=60, level="detect", install_height_m=4.0)
    r = optics.evaluate_point(p, _cam())
    assert r["supported"] is True
    assert r["ok"] is True
    assert r["ppm_need"] == 25.0
    assert r["tilt_deg"] == 3.8
    assert r["max_distance_m"] > 60


def test_evaluate_point_fails_identify_and_suggests():
    p = CameraPoint(pid="P2", purpose="人脸", product_sku="C1", quantity=1, stream_mbps=4.5,
                    distance_m=60, level="identify")
    r = optics.evaluate_point(p, _cam())
    assert r["ok"] is False
    assert r["suggest_focal_mm"] >= 16.0
    assert "建议换" in r["advice"]


def test_thermal_not_supported():
    th = Product(sku="TH", name="热成像", category="camera", form="thermal", resolution_mp=2.0,
                 fps=25, codec="H.265", bitrate_mbps=3.0, night_vision_m=300, poe_w=10.0,
                 ip_rating="IP67")
    p = CameraPoint(pid="P3", purpose="深水区", product_sku="TH", quantity=1, stream_mbps=3.0,
                    distance_m=200)
    r = optics.evaluate_point(p, th)
    assert r["supported"] is False
    assert "热成像" in r["reason"]


def test_evaluate_scenario_summary_counts():
    prods = {"C1": _cam(), "TH": Product(sku="TH", name="热像", category="camera", form="thermal",
                                        resolution_mp=2.0, fps=25, codec="H.265", bitrate_mbps=3.0,
                                        night_vision_m=300, poe_w=10.0, ip_rating="IP67")}
    pts = [CameraPoint(pid="P1", purpose="a", product_sku="C1", quantity=2, stream_mbps=4.5,
                       distance_m=60, level="detect"),
           CameraPoint(pid="P2", purpose="b", product_sku="C1", quantity=2, stream_mbps=4.5,
                       distance_m=200, level="detect"),
           CameraPoint(pid="P3", purpose="c", product_sku="TH", quantity=1, stream_mbps=3.0,
                       distance_m=200)]
    sc = type("S", (), {"points": pts})()
    rep = optics.evaluate_scenario(sc, prods)
    assert rep["summary"]["points"] == 3
    assert rep["summary"]["checked"] == 2
    assert rep["summary"]["skipped"] == 1
    assert rep["summary"]["ok"] == 1
    assert rep["summary"]["ng"] == 1
