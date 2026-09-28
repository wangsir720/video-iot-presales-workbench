LAYERS = [
    ("前端感知层", ["IPC 周界 / 球机 / 热成像", "AI 摄像机（区域入侵·越界·安全帽）"]),
    ("网络传输层", ["PoE 接入交换机", "汇聚交换机 + 千兆/万兆上联"]),
    ("存储与算力层", ["NVR / CVR 视频存储", "边缘 AI 盒子（规则二次研判）"]),
    ("平台应用层", ["视频综合管理平台", "门禁 / 报警 / 消防联动", "看板与报表"]),
]


def build_svg(scenario, bom, width=940, box_h=46, gap=22, top=70):
    height = top + len(LAYERS) * (box_h + gap) + 40
    parts = []
    parts.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
                 'viewBox="0 0 %d %d" font-family="Microsoft YaHei, sans-serif">' % (width, height, width, height))
    parts.append('<rect width="100%" height="100%" fill="#FFFFFF"/>')
    parts.append('<text x="24" y="34" font-size="18" font-weight="bold" fill="#1F3864">'
                 + _esc(scenario.name) + ' · 系统架构</text>')
    parts.append('<text x="24" y="54" font-size="12" fill="#5A5A5A">'
                 + _esc("点位 %d 路 ｜ 存储 %.2f TB ｜ 参考总价 %.2f 万元" %
                        (bom["cameras"], bom["storage_tb"], bom["total"] / 10000)) + '</text>')
    y = top
    for idx, (layer, items) in enumerate(LAYERS):
        parts.append('<rect x="24" y="%d" rx="6" width="%d" height="%d" fill="#F4F6F9" '
                     'stroke="#D6DCE5"/>' % (y, width - 48, box_h))
        parts.append('<text x="40" y="%d" font-size="13" font-weight="bold" fill="#1F3864">%s</text>'
                     % (y + box_h / 2 + 5, _esc(layer)))
        x = 200
        for it in items:
            w = max(150, 14 * len(it) // 2 + 40)
            parts.append('<rect x="%d" y="%d" rx="4" width="%d" height="30" fill="#FFFFFF" '
                         'stroke="#2E5FA3"/>' % (x, y + 8, w))
            parts.append('<text x="%d" y="%d" font-size="11" fill="#000000">%s</text>'
                         % (x + 10, y + 28, _esc(it)))
            x += w + 12
        if idx < len(LAYERS) - 1:
            parts.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#2E5FA3" '
                         'stroke-width="1.5" marker-end="url(#a)"/>'
                         % (width / 2, y + box_h, width / 2, y + box_h + gap - 6))
        y += box_h + gap
    parts.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="4" refY="4" '
                 'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2E5FA3"/></marker></defs>')
    parts.append('</svg>')
    return "\n".join(parts)


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
