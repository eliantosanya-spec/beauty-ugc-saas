import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from caption import generate_caption


class CaptionTests(unittest.TestCase):
    def test_generates_max_five_hashtags(self):
        store = {
            "name": "AIBC Beauty Demo",
            "business_type": "hair",
            "area": "渋谷",
            "booking_url": "https://example.com/book",
            "post_tone": "丁寧",
            "coupon_enabled": 1,
            "coupon_description": "次回500円OFF",
            "lottery_enabled": 1,
            "lottery_description": "今月の抽選に参加",
        }
        submission = {
            "menu_name": "透明感カラー",
            "instagram_id": "customer_id",
            "selected_comments": "理想の雰囲気になりました,スタッフさんが丁寧でした",
            "free_comment": "相談しながら決められて安心でした",
        }

        result = generate_caption(store, submission)

        self.assertLessEqual(len(result["hashtags"]), 5)
        self.assertNotIn("@customer_id", result["caption"])
        self.assertIn("透明感カラー", result["caption"])
        self.assertIn("理想の雰囲気", result["caption"])
        self.assertIn("次回500円OFF", result["caption"])
        self.assertIn("今月の抽選", result["caption"])

    def test_esthetic_caption_filters_effect_claims(self):
        store = {
            "name": "AIBC Esthe",
            "business_type": "esthetic",
            "area": "新宿",
            "booking_url": "",
            "post_tone": "高級感",
            "coupon_enabled": 0,
            "coupon_description": "",
            "lottery_enabled": 0,
            "lottery_description": "",
        }
        submission = {
            "menu_name": "フェイシャル",
            "instagram_id": "",
            "selected_comments": "リラックスできました",
            "free_comment": "シミが消えて痩せた気がします",
        }

        result = generate_caption(store, submission)

        self.assertNotIn("シミが消え", result["caption"])
        self.assertNotIn("痩せ", result["caption"])
        self.assertIn("リラックス", result["caption"])


if __name__ == "__main__":
    unittest.main()
