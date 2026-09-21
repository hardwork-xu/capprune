"""Run after installing the package. / 安装包后运行此演示。"""

from capprune.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["demo"]))
