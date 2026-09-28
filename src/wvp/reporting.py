import os
from jinja2 import Environment, FileSystemLoader


def _env(template_dir):
    return Environment(loader=FileSystemLoader(template_dir), trim_blocks=True,
                       lstrip_blocks=True, keep_trailing_newline=True)


def render(template_dir, template_name, context):
    tpl = _env(template_dir).get_template(template_name)
    return tpl.render(**context)


def save(text, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def render_all(template_dir, out_dir, ctx):
    outs = []
    for tpl, name in [("01-需求调研表.md.j2", "01-需求调研表.md"),
                      ("02-技术方案书.md.j2", "02-技术方案书.md"),
                      ("04-TCO对比.md.j2", "04-TCO对比.md"),
                      ("05-POC测试报告.md.j2", "05-POC测试报告.md"),
                      ("06-技术标偏离表.md.j2", "06-技术标偏离表.md")]:
        text = render(template_dir, tpl, ctx)
        outs.append(save(text, os.path.join(out_dir, name)))
    return outs


def bom_to_csv(bom, path):
    import csv
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["分组", "SKU", "名称", "数量", "公开参考单价(元)", "金额(元)"])
        for l in bom["lines"]:
            w.writerow([l["group"], l["sku"], l["name"], l["qty"], l["unit"], l["amount"]])
        w.writerow([])
        w.writerow(["", "", "硬件小计", "", "", bom["hardware"]])
        w.writerow(["", "", "施工安装", "", "", bom["install"]])
        w.writerow(["", "", "3 年运维", "", "", bom["ops_3y"]])
        w.writerow(["", "", "合计（参考）", "", "", bom["total"]])
    return path
