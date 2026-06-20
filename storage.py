import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class Storage:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS stores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    business_type TEXT NOT NULL,
                    area TEXT NOT NULL DEFAULT '',
                    instagram_account TEXT NOT NULL DEFAULT '',
                    booking_url TEXT NOT NULL DEFAULT '',
                    post_tone TEXT NOT NULL DEFAULT '丁寧',
                    coupon_enabled INTEGER NOT NULL DEFAULT 0,
                    coupon_code TEXT NOT NULL DEFAULT '',
                    coupon_description TEXT NOT NULL DEFAULT '',
                    lottery_enabled INTEGER NOT NULL DEFAULT 0,
                    lottery_description TEXT NOT NULL DEFAULT '',
                    public_upload_id TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(store_id) REFERENCES stores(id)
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    store_id INTEGER NOT NULL,
                    image_url TEXT NOT NULL,
                    menu_name TEXT NOT NULL DEFAULT '',
                    instagram_id TEXT NOT NULL DEFAULT '',
                    selected_comments TEXT NOT NULL DEFAULT '[]',
                    free_comment TEXT NOT NULL DEFAULT '',
                    consent_checked INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'unreviewed',
                    generated_caption TEXT NOT NULL DEFAULT '',
                    generated_hashtags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(store_id) REFERENCES stores(id)
                );
                """
            )

    def create_store(self, **data):
        public_upload_id = data.get("public_upload_id") or secrets.token_urlsafe(12)
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO stores (
                    name, business_type, area, instagram_account, booking_url, post_tone,
                    coupon_enabled, coupon_code, coupon_description,
                    lottery_enabled, lottery_description, public_upload_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data.get("business_type", "hair"),
                    data.get("area", ""),
                    data.get("instagram_account", ""),
                    data.get("booking_url", ""),
                    data.get("post_tone", "丁寧"),
                    int(data.get("coupon_enabled", 0)),
                    data.get("coupon_code", ""),
                    data.get("coupon_description", ""),
                    int(data.get("lottery_enabled", 0)),
                    data.get("lottery_description", ""),
                    public_upload_id,
                ),
            )
            return cur.lastrowid

    def update_store(self, store_id, data):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE stores
                SET name=?, business_type=?, area=?, instagram_account=?, booking_url=?,
                    post_tone=?, coupon_enabled=?, coupon_code=?, coupon_description=?,
                    lottery_enabled=?, lottery_description=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    data["name"],
                    data["business_type"],
                    data.get("area", ""),
                    data.get("instagram_account", ""),
                    data.get("booking_url", ""),
                    data.get("post_tone", "丁寧"),
                    int(bool(data.get("coupon_enabled"))),
                    data.get("coupon_code", ""),
                    data.get("coupon_description", ""),
                    int(bool(data.get("lottery_enabled"))),
                    data.get("lottery_description", ""),
                    store_id,
                ),
            )

    def create_user(self, store_id, email, password):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO users (store_id, email, password_hash) VALUES (?, ?, ?)",
                (store_id, email.lower().strip(), hash_password(password)),
            )

    def authenticate(self, email, password):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email.lower().strip(),)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return dict(row)

    def get_store(self, store_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM stores WHERE id=?", (store_id,)).fetchone()
        return dict(row) if row else None

    def get_store_by_public_id(self, public_upload_id):
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM stores WHERE public_upload_id=?", (public_upload_id,)).fetchone()
        return dict(row) if row else None

    def create_submission(self, store_id, image_url, menu_name="", instagram_id="", selected_comments=None, free_comment=""):
        selected_comments = selected_comments or []
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO submissions (
                    store_id, image_url, menu_name, instagram_id, selected_comments, free_comment
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    store_id,
                    image_url,
                    menu_name.strip(),
                    instagram_id.strip().lstrip("@"),
                    json.dumps(selected_comments, ensure_ascii=False),
                    free_comment.strip(),
                ),
            )
            return cur.lastrowid

    def list_submissions(self, store_id):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM submissions WHERE store_id=? ORDER BY created_at DESC, id DESC",
                (store_id,),
            ).fetchall()
        return [decode_submission(row) for row in rows]

    def get_submission(self, submission_id, store_id):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM submissions WHERE id=? AND store_id=?",
                (submission_id, store_id),
            ).fetchone()
        return decode_submission(row) if row else None

    def update_generated_caption(self, submission_id, store_id, caption, hashtags):
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE submissions
                SET generated_caption=?, generated_hashtags=?, status='generated', updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND store_id=?
                """,
                (caption, hashtags, submission_id, store_id),
            )

    def update_submission_status(self, submission_id, store_id, status):
        with self.connect() as conn:
            conn.execute(
                "UPDATE submissions SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND store_id=?",
                (status, submission_id, store_id),
            )

    def ensure_demo(self):
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        if row["count"]:
            return
        store_id = self.create_store(
            name="AIBC Beauty Demo",
            business_type="hair",
            area="渋谷",
            instagram_account="aibc_beauty",
            booking_url="https://example.com/book",
            post_tone="丁寧",
            coupon_enabled=1,
            coupon_code="PHOTO500",
            coupon_description="次回来店時に500円OFF",
            lottery_enabled=1,
            lottery_description="今月の抽選キャンペーンに参加",
        )
        self.create_user(store_id, "demo@example.com", "password123")

    # ── JSON Backup / Restore ────────────────────────────────────

    def export_json(self):
        """Export all data as a JSON-serializable dict."""
        with self.connect() as conn:
            stores = [dict(r) for r in conn.execute("SELECT * FROM stores").fetchall()]
            users = [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]
            submissions = []
            for r in conn.execute("SELECT * FROM submissions").fetchall():
                s = dict(r)
                s["selected_comments"] = json.loads(s.get("selected_comments") or "[]")
                submissions.append(s)
        return {
            "version": 1,
            "stores": stores,
            "users": users,
            "submissions": submissions,
        }

    def import_json(self, data: dict, replace: bool = False):
        """Import data from export_json dict. Returns counts dict."""
        if "stores" not in data or "users" not in data or "submissions" not in data:
            raise ValueError("不正なバックアップファイルです。")
        with self.connect() as conn:
            if replace:
                conn.executescript("DELETE FROM submissions; DELETE FROM users; DELETE FROM stores;")

            store_count = 0
            for row in data["stores"]:
                conn.execute(
                    """INSERT OR IGNORE INTO stores (id, name, business_type, area, instagram_account,
                       booking_url, post_tone, coupon_enabled, coupon_code, coupon_description,
                       lottery_enabled, lottery_description, public_upload_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["name"], row["business_type"], row.get("area", ""),
                     row.get("instagram_account", ""), row.get("booking_url", ""),
                     row.get("post_tone", "丁寧"), row.get("coupon_enabled", 0),
                     row.get("coupon_code", ""), row.get("coupon_description", ""),
                     row.get("lottery_enabled", 0), row.get("lottery_description", ""),
                     row["public_upload_id"], row.get("created_at"), row.get("updated_at")),
                )
                store_count += 1

            user_count = 0
            for row in data["users"]:
                conn.execute(
                    """INSERT OR IGNORE INTO users (id, store_id, email, password_hash, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["store_id"], row["email"], row["password_hash"],
                     row.get("created_at"), row.get("updated_at")),
                )
                user_count += 1

            sub_count = 0
            for row in data["submissions"]:
                comments = json.dumps(row.get("selected_comments") or [], ensure_ascii=False)
                conn.execute(
                    """INSERT OR IGNORE INTO submissions (id, store_id, image_url, menu_name,
                       instagram_id, selected_comments, free_comment, consent_checked, status,
                       generated_caption, generated_hashtags, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (row["id"], row["store_id"], row["image_url"], row.get("menu_name", ""),
                     row.get("instagram_id", ""), comments, row.get("free_comment", ""),
                     row.get("consent_checked", 1), row.get("status", "unreviewed"),
                     row.get("generated_caption", ""), row.get("generated_hashtags", ""),
                     row.get("created_at"), row.get("updated_at")),
                )
                sub_count += 1

            # re-seq the sqlite_sequence so autoincrement doesn't collide
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('stores','users','submissions')"
            )

        return {"stores": store_count, "users": user_count, "submissions": sub_count}


def decode_submission(row):
    if not row:
        return None
    data = dict(row)
    data["selected_comments"] = json.loads(data.get("selected_comments") or "[]")
    return data


def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password, encoded):
    try:
        method, salt_hex, digest_hex = encoded.split("$", 2)
    except ValueError:
        return False
    if method != "pbkdf2_sha256":
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return hmac.compare_digest(actual, expected)
