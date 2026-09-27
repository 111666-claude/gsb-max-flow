import io
import unittest
from contextlib import redirect_stdout

from maxflow.cli import main
from maxflow.flow import FlowError, max_flow, parse_edges


class ParseTest(unittest.TestCase):
    def test_two_edges(self):
        self.assertEqual(parse_edges("s-a:2,b-t:3"), [("s", "a", 2), ("b", "t", 3)])

    def test_blank_items_are_skipped(self):
        self.assertEqual(parse_edges("s-a:1,"), [("s", "a", 1)])

    def test_missing_colon(self):
        with self.assertRaises(FlowError):
            parse_edges("s-a")

    def test_missing_dash(self):
        with self.assertRaises(FlowError):
            parse_edges("sa:1")


class FlowTest(unittest.TestCase):
    def test_single_path(self):
        self.assertEqual(max_flow(parse_edges("s-a:3,a-t:3"), "s", "t"), 3)

    def test_parallel_edges_add_up(self):
        self.assertEqual(max_flow(parse_edges("s-a:1,s-a:2,a-t:5"), "s", "t"), 3)

    def test_self_loop_is_ignored(self):
        self.assertEqual(max_flow(parse_edges("s-a:2,a-a:9,a-t:2"), "s", "t"), 2)

    def test_no_path(self):
        self.assertEqual(max_flow(parse_edges("a-b:4"), "s", "t"), 0)

    def test_empty_graph(self):
        self.assertEqual(max_flow([], "s", "t"), 0)

    def test_flow_is_not_negative(self):
        self.assertGreaterEqual(max_flow(parse_edges("s-a:1,a-t:1"), "s", "t"), 0)


class CliTest(unittest.TestCase):
    def test_prints_flow(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--edges", "s-a:2,a-t:2", "--source", "s", "--sink", "t"])
        self.assertEqual(code, 0)
        self.assertEqual(buffer.getvalue().strip(), "flow=2")

    def test_missing_edges(self):
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
