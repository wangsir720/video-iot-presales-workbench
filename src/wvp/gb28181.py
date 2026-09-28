"""GB/T 28181 设备接入预检：国标 ID 结构校验、接入参数检查、通道数与平台授权核对。

口径说明
--------
- 国标 ID 为 20 位十进制数字，分五段：中心编码(8) + 行业编码(2) + 类型编码(3) +
  网络标识(1) + 序号(6)。
- 中心编码前 2 位 / 前 6 位按 GB/T 2260 行政区划代码校验。
- **类型编码取值随平台设备目录与行业约定不同**，本工具不臆断标准取值，只校验
  “是否落在配置文件给出的允许集合内”，默认示例见 `config/gb28181-device-types.yaml`。
- 端口口径（注册端口与媒体端口段）按通用工程实践给出，可在调用时调整。
- 本预检用于设备纳管前的自查，不能替代平台侧实际的注册与目录同步验证。
"""
import csv
import ipaddress
import os
import re

ID_RE = re.compile(r"^\d{20}$")

PROVINCE_CODES = {
    "11": "北京市", "12": "天津市", "13": "河北省", "14": "山西省", "15": "内蒙古自治区",
    "21": "辽宁省", "22": "吉林省", "23": "黑龙江省",
    "31": "上海市", "32": "江苏省", "33": "浙江省", "34": "安徽省", "35": "福建省",
    "36": "江西省", "37": "山东省",
    "41": "河南省", "42": "湖北省", "43": "湖南省", "44": "广东省", "45": "广西壮族自治区",
    "46": "海南省",
    "50": "重庆市", "51": "四川省", "52": "贵州省", "53": "云南省", "54": "西藏自治区",
    "61": "陕西省", "62": "甘肃省", "63": "青海省", "64": "宁夏回族自治区", "65": "新疆维吾尔自治区",
    "71": "台湾省", "81": "香港特别行政区", "82": "澳门特别行政区",
}

SEGMENTS = [("center", 0, 8, "中心编码"), ("industry", 8, 10, "行业编码"),
            ("type", 10, 13, "类型编码"), ("network", 13, 14, "网络标识"),
            ("seq", 14, 20, "序号")]

FIELDS = {
    "name": "设备名称", "vendor": "厂商", "device_id": "国标ID", "ip": "IP",
    "port": "端口", "transport": "协议", "channels": "通道数", "codec": "编码",
    "location": "安装位置",
}

BLOCK = "阻断"
WARN = "提示"


def parse_device_id(did):
    """拆解 20 位国标 ID 并返回各段。"""
    did = (did or "").strip()
    if not ID_RE.match(did):
        return None
    out = {}
    for key, a, b, label in SEGMENTS:
        out[key] = did[a:b]
        out[key + "_label"] = label
    return out


def check_device_id(did, allowed_type_codes=None):
    """校验国标 ID 结构，返回 (issues, segments)。"""
    issues = []
    did = (did or "").strip()
    seg = parse_device_id(did)
    if seg is None:
        n = len(did)
        issues.append((BLOCK, "国标ID", "国标 ID 必须为 20 位数字，当前 %d 位（%r）" % (n, did)))
        return issues, None

    if seg["center"][:2] not in PROVINCE_CODES:
        issues.append((BLOCK, "国标ID",
                       "中心编码前 2 位 %s 不是有效的省级行政区划代码" % seg["center"][:2]))
    if seg["center"][2:6] == "0000":
        issues.append((WARN, "国标ID", "中心编码中区县段为 0000，请确认是否为本级中心编码"))
    if seg["seq"] == "000000":
        issues.append((BLOCK, "国标ID", "序号段为 000000，无法唯一标识设备"))
    if allowed_type_codes and seg["type"] not in set(allowed_type_codes):
        issues.append((BLOCK, "国标ID",
                       "类型编码 %s 不在平台设备目录允许集合 %s 内"
                       % (seg["type"], ",".join(sorted(allowed_type_codes)))))
    return issues, seg


def check_ip(ip):
    """返回 (issues, kind)，kind ∈ {public, private, invalid}。"""
    ip = (ip or "").strip()
    try:
        obj = ipaddress.ip_address(ip)
    except ValueError:
        return [(BLOCK, "IP", "IP 地址格式非法：%r" % ip)], "invalid"
    if obj.is_private:
        return [(WARN, "IP",
                 "私网地址 %s：跨区/跨网接入需确认 NAT 或 GB/T 28181 端口映射后的公网可注册性"
                 % ip)], "private"
    return [], "public"


def check_devices(rows, platform_capacity_ch=0, sip_port=5060, rtp_range=(30000, 30500),
                  allowed_type_codes=None):
    """对设备接入清单做整体预检。"""
    issues = []
    if rtp_range[0] <= sip_port <= rtp_range[1]:
        issues.append((BLOCK, "端口段",
                       "配置的媒体流接收段 %d-%d 覆盖了平台 SIP 端口 %d，请在调用时调整端口段"
                       % (rtp_range[0], rtp_range[1], sip_port)))
    seen_id, seen_addr, seen_net = {}, {}, set()
    total_ch = 0
    devices = []

    for idx, r in enumerate(rows, start=1):
        name = (r.get("name") or "").strip() or "第 %d 行" % idx
        rec = {"name": name, "vendor": r.get("vendor", ""), "device_id": r.get("device_id", ""),
               "ip": r.get("ip", ""), "port": str(r.get("port", "")).strip(),
               "transport": r.get("transport", ""), "channels": _int(r.get("channels")),
               "codec": r.get("codec", ""), "location": r.get("location", "")}
        before = len(issues)

        for key in ("device_id", "ip", "port"):
            if not rec[key]:
                issues.append((BLOCK, FIELDS[key], "%s：缺失必填字段" % name))

        id_issues, seg = check_device_id(rec["device_id"], allowed_type_codes)
        issues.extend([(lv, f, "%s：%s" % (name, msg)) for lv, f, msg in id_issues])
        rec["segments"] = seg

        ip_issues, kind = check_ip(rec["ip"])
        for lv, f, msg in ip_issues:
            if "私网地址" in msg:
                try:
                    net = str(ipaddress.ip_network(rec["ip"] + "/24", strict=False))
                except ValueError:
                    net = rec["ip"]
                if net in seen_net:
                    continue
                seen_net.add(net)
                f = "IP"
                msg = ("私网网段 %s：跨区/跨网接入需确认 NAT 或国标端口映射后的公网可注册性"
                       % net)
            issues.append((lv, f, "%s：%s" % (name, msg)))
        rec["ip_kind"] = kind

        if rec["port"]:
            if not rec["port"].isdigit() or not (0 < int(rec["port"]) < 65536):
                issues.append((BLOCK, "端口", "%s：端口 %r 非法" % (name, rec["port"])))
            elif rtp_range[0] <= int(rec["port"]) <= rtp_range[1]:
                issues.append((BLOCK, "端口",
                               "%s：端口 %s 落在媒体流接收段 %d-%d 内，与 RTP 端口冲突"
                               % (name, rec["port"], rtp_range[0], rtp_range[1])))

        if rec["device_id"]:
            if rec["device_id"] in seen_id:
                issues.append((BLOCK, "国标ID", "%s：国标 ID 与「%s」重复" % (name, seen_id[rec["device_id"]])))
            else:
                seen_id[rec["device_id"]] = name
        addr = "%s:%s" % (rec["ip"], rec["port"])
        if rec["ip"]:
            if addr in seen_addr:
                issues.append((BLOCK, "IP:端口", "%s：%s 与「%s」重复" % (name, addr, seen_addr[addr])))
            else:
                seen_addr[addr] = name

        if rec["transport"] and rec["transport"].upper() not in ("UDP", "TCP", "GB28181", "SIP"):
            issues.append((WARN, "协议", "%s：接入协议 %r 非常见取值（UDP/TCP）" % (name, rec["transport"])))
        if rec["codec"] and rec["codec"].upper() not in ("H.264", "H.265", "H265", "H264"):
            issues.append((WARN, "编码", "%s：编码格式 %r 非常见取值（H.264/H.265）" % (name, rec["codec"])))

        total_ch += rec["channels"] if rec["channels"] > 0 else 0
        rec["_new"] = issues[before:]
        devices.append(rec)

    gap = (platform_capacity_ch - total_ch) if platform_capacity_ch else 0
    if platform_capacity_ch and total_ch > platform_capacity_ch:
        issues.append((BLOCK, "平台授权",
                       "通道总数 %d 超过平台授权路数 %d，缺口 %d 路"
                       % (total_ch, platform_capacity_ch, total_ch - platform_capacity_ch)))

    blocking = [i for i in issues if i[0] == BLOCK]
    warnings = [i for i in issues if i[0] == WARN]

    return {
        "devices": devices,
        "issues": issues,
        "summary": {
            "devices": len(rows),
            "channels": total_ch,
            "platform_capacity_ch": platform_capacity_ch,
            "gap": gap,
            "blocking": len(blocking),
            "warnings": len(warnings),
        },
    }


def load_devices_csv(path):
    """读取设备接入清单 CSV（表头为中文列名）。"""
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for raw in csv.DictReader(f):
            row = {}
            for key, label in FIELDS.items():
                row[key] = (raw.get(label) or "").strip()
            if any(row.values()):
                rows.append(row)
    return rows


def build_onboarding_list(scenario, products_by_sku, center_code="33010600",
                          industry_code="00", type_code="131", start_seq=1):
    """按场景点位生成一份结构合规的设备接入清单。

    每个点位生成一台前端设备；通道数取点位数；安装位置取点位区域。
    """
    rows = []
    seq = start_seq
    for pt in scenario.points:
        prod = products_by_sku[pt.product_sku]
        row = {
            "name": "%s-%s" % (scenario.sid, pt.pid),
            "vendor": "参数化档位（%s）" % prod.form,
            "device_id": "%s%s%s1%06d" % (center_code, industry_code, type_code, seq),
            "ip": "10.20.%d.%d" % (10 + (seq // 200), 10 + seq),
            "port": "5060",
            "transport": "UDP",
            "channels": str(pt.quantity),
            "codec": "H.265",
            "location": pt.zone or pt.purpose,
        }
        rows.append(row)
        seq += 1
    return rows


def load_type_config(path):
    """读取类型编码 / 中心编码配置（YAML）。缺失时返回空配置。"""
    if not path or not os.path.isfile(path):
        return {}
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def render_markdown(report, title="设备接入清单与预检"):
    """把预检结果渲染成 Markdown 报告。"""
    s = report["summary"]
    lines = ["# %s" % title, "", "## 一、预检结论", "",
             "| 指标 | 结果 |", "|---|---|",
             "| 设备条目 | %d |" % s["devices"],
             "| 通道数合计 | %d |" % s["channels"],
             "| 平台授权路数 | %s |" % (s["platform_capacity_ch"] or "未提供"),
             "| 授权余量 | %s |" % (("%d 路" % s["gap"]) if s["platform_capacity_ch"] else "—"),
             "| 阻断项 | %d |" % s["blocking"],
             "| 提示项 | %d |" % s["warnings"], ""]
    if report["issues"]:
        lines += ["## 二、问题清单", "", "| 级别 | 字段 | 说明 |", "|---|---|---|"]
        for lv, field, msg in report["issues"]:
            lines.append("| %s | %s | %s |" % (lv, field, msg))
        lines.append("")
    else:
        lines += ["## 二、问题清单", "", "未发现问题。", ""]

    lines += ["## 三、设备接入清单", "",
              "| 设备名称 | 国标 ID | IP:端口 | 协议 | 通道数 | 编码 | 安装位置 |",
              "|---|---|---|---|---:|---|---|"]
    for d in report["devices"]:
        lines.append("| %s | %s | %s:%s | %s | %d | %s | %s |"
                     % (d["name"], d["device_id"] or "—", d["ip"] or "—", d["port"] or "—",
                        d["transport"] or "—", d["channels"], d["codec"] or "—",
                        d["location"] or "—"))
    lines += ["", "## 四、口径说明", "",
              "- 国标 ID 为 20 位十进制数字：中心编码(8) + 行业编码(2) + 类型编码(3) + 网络标识(1) + 序号(6)；",
              "  中心编码前 2 位按 GB/T 2260 省级行政区划代码校验。",
              "- 类型编码取值随平台设备目录与行业约定不同，本表按配置文件给出的允许集合校验。",
              "- 端口口径按通用工程实践（注册端口与媒体流接收段不重叠）检查，可在调用时调整。",
              "- 本预检为纳管前自查，不替代平台侧实际注册与目录同步验证。"]
    return "\n".join(lines) + "\n"


def _int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return 0
