from dataclasses import dataclass, field
from typing import List


@dataclass
class Product:
    sku: str
    name: str
    category: str
    form: str
    resolution_mp: float
    fps: int
    codec: str
    bitrate_mbps: float
    night_vision_m: int
    poe_w: float
    ip_rating: str
    ai_rules: List[str] = field(default_factory=list)
    unit_price_ref: float = 0.0
    capacity_ch: int = 0
    note: str = ""
    sensor: str = ""
    pixel_w: int = 0
    pixel_h: int = 0
    focal_mm: float = 0.0


@dataclass
class CameraPoint:
    pid: str
    purpose: str
    product_sku: str
    quantity: int
    stream_mbps: float
    distance_m: float
    env: str = "outdoor"
    zone: str = ""
    level: str = "detect"
    install_height_m: float = 0.0


@dataclass
class Rule:
    rid: str
    kind: str
    name: str = ""
    zone: List[List[float]] = field(default_factory=list)
    line: List[List[float]] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)


@dataclass
class Scenario:
    sid: str
    name: str
    site: str
    client_type: str
    objective: str
    record_days: int
    points: List[CameraPoint]
    rules: List[Rule]
    requirements: List[str] = field(default_factory=list)
    extras: List[str] = field(default_factory=list)

    def total_cameras(self):
        return sum(p.quantity for p in self.points)

    def streams(self):
        out = []
        for p in self.points:
            out.extend([p.stream_mbps] * p.quantity)
        return out
