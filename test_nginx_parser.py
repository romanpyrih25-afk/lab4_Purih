import io
import types
import unittest
from unittest.mock import mock_open, patch

from nginx_parser import (
    count_traffic,
    human,
    lines_from_chunks,
    parse_line,
    read_chunks,
)

LINE_1 = (b'1.2.3.4 - - [07/May/2017:00:08:35 +0300] "GET /login/index.php HTTP/1.0" '
          b'200 21351 "http://example.com/" "Mozilla/5.0"')
LINE_2 = (b'5.6.7.8 - - [07/May/2017:00:08:52 +0300] "POST /login/index.php HTTP/1.0" '
          b'303 454 "-" "Mozilla/5.0"')
LINE_DASH = (b'9.9.9.9 - - [07/May/2017:01:00:00 +0300] "GET / HTTP/1.0" '
             b'304 - "-" "curl/7.0"')

REQ_1 = len(b"GET /login/index.php HTTP/1.0")
REQ_2 = len(b"POST /login/index.php HTTP/1.0")
REQ_DASH = len(b"GET / HTTP/1.0")

SAMPLE_LOG = LINE_1 + b"\n" + LINE_2 + b"\n"


class TestReadChunks(unittest.TestCase):
    def test_is_generator(self):
        self.assertIsInstance(read_chunks(io.BytesIO(b"abc")), types.GeneratorType)

    def test_splits_into_chunks(self):
        self.assertEqual(list(read_chunks(io.BytesIO(b"abcdefg"), 3)), [b"abc", b"def", b"g"])

    def test_empty_file(self):
        self.assertEqual(list(read_chunks(io.BytesIO(b""), 3)), [])


class TestLinesFromChunks(unittest.TestCase):
    def test_line_split_between_chunks(self):
        chunks = [b"aa\nb", b"b\ncc", b"c\n"]
        self.assertEqual(list(lines_from_chunks(chunks)), [b"aa", b"bb", b"ccc"])

    def test_last_line_without_newline(self):
        self.assertEqual(list(lines_from_chunks([b"x\ny"])), [b"x", b"y"])


class TestParseLine(unittest.TestCase):
    def test_get_line(self):
        self.assertEqual(parse_line(LINE_1), (21351, REQ_1))

    def test_post_line(self):
        self.assertEqual(parse_line(LINE_2), (454, REQ_2))

    def test_dash_bytes_is_zero(self):
        self.assertEqual(parse_line(LINE_DASH), (0, REQ_DASH))

    def test_garbage_line(self):
        self.assertIsNone(parse_line(b"this is not a log line"))
        self.assertIsNone(parse_line(b""))


class TestCountTraffic(unittest.TestCase):
    def test_sums_with_mock_open(self):
        m = mock_open(read_data=SAMPLE_LOG)
        with patch("builtins.open", m):
            sent, received = count_traffic("fake.log")
        m.assert_called_once_with("fake.log", "rb")
        self.assertEqual(sent, 21351 + 454)
        self.assertEqual(received, REQ_1 + REQ_2)

    def test_small_chunks_give_same_result(self):
        m = mock_open(read_data=SAMPLE_LOG)
        with patch("builtins.open", m):
            self.assertEqual(count_traffic("fake.log", chunk_size=7),
                             (21351 + 454, REQ_1 + REQ_2))

    def test_skips_bad_lines_and_dash(self):
        data = LINE_1 + b"\nbroken line\n\n" + LINE_DASH
        with patch("builtins.open", mock_open(read_data=data)):
            self.assertEqual(count_traffic("fake.log"), (21351, REQ_1 + REQ_DASH))

    def test_empty_file(self):
        with patch("builtins.open", mock_open(read_data=b"")):
            self.assertEqual(count_traffic("fake.log"), (0, 0))


class TestHuman(unittest.TestCase):
    def test_units(self):
        self.assertEqual(human(500), "500.00 Б")
        self.assertEqual(human(2048), "2.00 КБ")
        self.assertEqual(human(3 * 1024 ** 2), "3.00 МБ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
