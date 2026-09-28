"""一键为全部场景生成方案交付物。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from wvp.cli import cmd_generate  # noqa: E402


class Args:
    def __init__(self, scenario, out=None):
        self.scenario = scenario
        self.out = out


def main():
    sc_dir = os.path.join(ROOT, "config", "scenarios")
    for fn in sorted(os.listdir(sc_dir)):
        if not fn.endswith(".yaml"):
            continue
        cfg = os.path.join(sc_dir, fn)
        cmd_generate(Args(cfg))


if __name__ == "__main__":
    main()
