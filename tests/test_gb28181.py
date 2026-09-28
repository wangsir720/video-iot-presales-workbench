import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp import gb28181 as gb  # noqa: E402
from wvp.models import CameraPoint, Product  # noqa: E402

GOOD_ID = "33010600001311000001"


def _row(did=GOOD_ID, ip="10.20.10.11", port="5060", ch="4", name="dev", codec="H.265",
         transport="UDP"):
    return {"name": name, "vendor": "v", "device_id": did, "ip": ip, "port": port,
            "transport": transport, "channels": ch, "codec": codec, "location": "L"}


def test_parse_device_id_segments():
    seg = gb.parse_device_id(GOOD_ID)
    assert seg["center"] == "33010600"
    assert seg["industry"] == "00"
    assert seg["type"] == "131"
    assert seg["network"] == "1"
    assert seg["seq"] == "000001"


def test_parse_rejects_wrong_length():
    assert gb.parse_device_id("330106000013110000") is None
    assert gb.parse_device_id("330106000013110000012") is None


def test_check_id_rejects_non_digits():
    issues, seg = gb.check_device_id("33010600A01311000001")
    assert seg is None
    assert issues[0][0] == gb.BLOCK


def test_check_id_rejects_bad_province():
    issues, seg = gb.check_device_id("99010600001311000001")
    assert seg is not None
    assert any("省级行政区划" in m for _, _, m in issues)


def test_check_id_rejects_zero_sequence():
    issues, _ = gb.check_device_id("33010600001311000000")
    assert any("序号段" in m for _, _, m in issues)


def test_check_id_type_code_membership():
    ok, _ = gb.check_device_id(GOOD_ID, allowed_type_codes=["131"])
    assert not any(lv == gb.BLOCK for lv, _, _ in ok)
    bad, _ = gb.check_device_id(GOOD_ID, allowed_type_codes=["132"])
    assert any("类型编码" in m for _, _, m in bad)


def test_check_ip_classification():
    assert gb.check_ip("192.168.1.10")[1] == "private"
    assert gb.check_ip("8.8.8.8")[1] == "public"
    assert gb.check_ip("10.0.0.999")[1] == "invalid"


def test_duplicate_id_and_address_detected():
    rep = gb.check_devices([_row(name="A"), _row(name="B")])
    msgs = [m for _, _, m in rep["issues"]]
    assert any("国标 ID 与" in m for m in msgs)
    assert any("重复" in m and "10.20.10.11:5060" in m for m in msgs)
    assert rep["summary"]["blocking"] >= 2


def test_private_subnet_warned_once():
    rows = [_row(name="A", ip="10.20.10.11"), _row(name="B", ip="10.20.10.12", did=GOOD_ID[:-1] + "2")]
    rep = gb.check_devices(rows)
    warns = [m for lv, _, m in rep["issues"] if lv == gb.WARN and "私网网段" in m]
    assert len(warns) == 1


def test_rtp_port_conflict_blocked():
    rep = gb.check_devices([_row(port="30500")])
    assert any("RTP 端口冲突" in m for _, _, m in rep["issues"])


def test_missing_fields_blocked():
    rep = gb.check_devices([_row(ip="", port="")])
    assert rep["summary"]["blocking"] >= 2


def test_platform_capacity_gap():
    rep = gb.check_devices([_row(ch="30")], platform_capacity_ch=16)
    assert rep["summary"]["channels"] == 30
    assert rep["summary"]["gap"] == -14
    assert any("超过平台授权路数" in m for _, _, m in rep["issues"])


def test_build_onboarding_list_is_valid():
    prod = Product(sku="C1", name="c", category="camera", form="bullet", resolution_mp=4.0,
                   fps=25, codec="H.265", bitrate_mbps=4.5, night_vision_m=60, poe_w=12.0,
                   ip_rating="IP67")
    pts = [CameraPoint(pid="P1", purpose="a", product_sku="C1", quantity=6, stream_mbps=4.5,
                       distance_m=60, zone="东周界"),
           CameraPoint(pid="P2", purpose="b", product_sku="C1", quantity=2, stream_mbps=4.5,
                       distance_m=45, zone="装卸区")]
    sc = type("S", (), {"sid": "demo", "points": pts})()
    rows = gb.build_onboarding_list(sc, {"C1": prod})
    assert len(rows) == 2
    assert rows[0]["channels"] == "6"
    rep = gb.check_devices(rows, allowed_type_codes=["131"])
    assert rep["summary"]["blocking"] == 0
    assert all(len(r["device_id"]) == 20 for r in rows)


def test_render_markdown_has_sections():
    rep = gb.check_devices([_row()])
    md = gb.render_markdown(rep, title="T")
    assert "# T" in md
    assert "预检结论" in md
    assert "设备接入清单" in md
    assert "口径说明" in md


def test_load_devices_csv_roundtrip(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("设备名称,厂商,国标ID,IP,端口,协议,通道数,编码,安装位置\n"
                 "A,v,%s,10.0.0.1,5060,UDP,4,H.265,L\n" % GOOD_ID, encoding="utf-8")
    rows = gb.load_devices_csv(str(p))
    assert len(rows) == 1
    assert rows[0]["device_id"] == GOOD_ID
    assert rows[0]["channels"] == "4"
