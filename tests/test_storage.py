import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import Storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.sqlite3"
        self.storage = Storage(self.db_path)
        self.storage.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_demo_store_login_and_submission_lifecycle(self):
        store_id = self.storage.create_store(
            name="AIBC Beauty Demo",
            business_type="hair",
            area="渋谷",
            instagram_account="aibc_beauty",
            booking_url="https://example.com/book",
            post_tone="丁寧",
            coupon_enabled=1,
            coupon_code="PHOTO500",
            coupon_description="次回500円OFF",
            lottery_enabled=1,
            lottery_description="今月の抽選に参加",
        )
        self.storage.create_user(store_id, "demo@example.com", "password123")

        user = self.storage.authenticate("demo@example.com", "password123")
        self.assertIsNotNone(user)
        self.assertEqual(user["store_id"], store_id)
        self.assertIsNone(self.storage.authenticate("demo@example.com", "wrong"))

        store = self.storage.get_store(store_id)
        submission_id = self.storage.create_submission(
            store_id=store_id,
            image_url="/uploads/sample.jpg",
            menu_name="透明感カラー",
            instagram_id="customer_id",
            selected_comments=["理想の雰囲気になりました"],
            free_comment="相談しやすかったです",
        )
        submission = self.storage.get_submission(submission_id, store_id)

        self.assertEqual(submission["store_id"], store_id)
        self.assertEqual(store["public_upload_id"], self.storage.get_store_by_public_id(store["public_upload_id"])["public_upload_id"])

        self.storage.update_generated_caption(submission_id, store_id, "caption text", "#渋谷美容院")
        self.storage.update_submission_status(submission_id, store_id, "posted")
        updated = self.storage.get_submission(submission_id, store_id)

        self.assertEqual(updated["generated_caption"], "caption text")
        self.assertEqual(updated["generated_hashtags"], "#渋谷美容院")
        self.assertEqual(updated["status"], "posted")


if __name__ == "__main__":
    unittest.main()
