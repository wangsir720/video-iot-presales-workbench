import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from wvp import capacity  # noqa: E402


def test_daily_gb_known_value():
    assert abs(capacity.daily_gb(4.5) - 48.6) < 0.01


def test_daily_gb_scales_with_hours():
    assert abs(capacity.daily_gb(4.5, hours=12) - 24.3) < 0.01


def test_storage_tb_known_value():
    v = capacity.storage_tb([4.5] * 14 + [6.0] * 2, 30)
    assert abs(v - 27.945) < 0.02


def test_storage_tb_monotonic_in_days():
    a = capacity.storage_tb([4.0] * 8, 30)
    b = capacity.storage_tb([4.0] * 8, 60)
    assert abs(b - 2 * a) < 0.05


def test_bandwidth_overhead():
    assert abs(capacity.bandwidth_mbps([4.0] * 10) - 46.0) < 0.01


def test_uplink_recommendation_thresholds():
    assert capacity.uplink_recommendation(150).startswith("千兆接入 + 千兆")
    assert capacity.uplink_recommendation(500).startswith("千兆接入 + 万兆")
    assert capacity.uplink_recommendation(1200).startswith("万兆接入")


def test_compute_tops_rounds_up():
    r = capacity.compute_tops([4.0] * 16)
    assert r["need_tops"] == 73.6
    assert r["boxes"] == 3


def test_channel_capacity_rounds_up():
    assert capacity.channel_capacity(32, 16) == 1
    assert capacity.channel_capacity(32, 33) == 2
