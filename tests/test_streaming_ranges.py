import unittest
from LucyBot.util.ranges import parse_byte_range


class ByteRangeTests(unittest.TestCase):
    def test_full_response(self):
        self.assertEqual(parse_byte_range(None, 100), (0, 99, False))

    def test_explicit_range(self):
        self.assertEqual(parse_byte_range("bytes=10-19", 100), (10, 19, True))

    def test_open_ended_range(self):
        self.assertEqual(parse_byte_range("bytes=90-", 100), (90, 99, True))

    def test_suffix_range(self):
        self.assertEqual(parse_byte_range("bytes=-10", 100), (90, 99, True))

    def test_suffix_larger_than_file(self):
        self.assertEqual(parse_byte_range("bytes=-200", 100), (0, 99, True))

    def test_end_clamped_to_file_size(self):
        self.assertEqual(parse_byte_range("bytes=90-200", 100), (90, 99, True))

    def test_out_of_bounds(self):
        self.assertIsNone(parse_byte_range("bytes=100-", 100))

    def test_reversed_range(self):
        self.assertIsNone(parse_byte_range("bytes=20-10", 100))

    def test_invalid_multiple_ranges(self):
        self.assertIsNone(parse_byte_range("bytes=0-1,4-5", 100))

    def test_empty_file(self):
        self.assertIsNone(parse_byte_range(None, 0))


if __name__ == "__main__":
    unittest.main()
      
