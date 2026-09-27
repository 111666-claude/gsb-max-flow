"""命令行入口：算最大流，--min-cut 时追加最小割。"""

import argparse
import sys

from .flow import FlowError, max_flow, min_cut, parse_edges


def build_parser():
    parser = argparse.ArgumentParser(prog="max-flow", description="有向图最大流与最小割")
    parser.add_argument("--edges", help="逗号分隔的 u-v:容量")
    parser.add_argument("--source", default="s", help="源点")
    parser.add_argument("--sink", default="t", help="汇点")
    parser.add_argument("--min-cut", action="store_true", help="额外输出最小割")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.edges:
        print("错误：需要 --edges", file=sys.stderr)
        return 2
    try:
        edges = parse_edges(args.edges)
        value = max_flow(edges, args.source, args.sink)
        print("flow=%d" % value)
        if args.min_cut:
            side, capacity = min_cut(edges, args.source, args.sink)
            print("cut=%s" % ",".join(side))
            print("cut_capacity=%d" % capacity)
    except (FlowError, ValueError) as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
