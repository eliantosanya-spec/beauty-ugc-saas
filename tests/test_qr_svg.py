import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qr_svg import make_qr, qr_svg


class QrSvgTests(unittest.TestCase):
    def test_generates_svg_for_upload_url(self):
        svg = qr_svg("http://127.0.0.1:8000/u/demo-public-id")

        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)
        self.assertIn("Upload QR code", svg)

    def test_matrix_is_expected_size(self):
        matrix = make_qr("http://127.0.0.1:8000/u/demo-public-id")

        self.assertEqual(len(matrix), 29)
        self.assertTrue(all(len(row) == 29 for row in matrix))
        self.assertTrue(matrix[0][0])


if __name__ == "__main__":
    unittest.main()
