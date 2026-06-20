import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

import cgi
import mimetypes
import secrets
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from caption import generate_caption
from qr_svg import qr_svg
from storage import Storage
import templates


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = DATA_DIR / "app.sqlite3"
PYTHON = "python"

storage = Storage(DB_PATH)
sessions = {}


class App(BaseHTTPRequestHandler):
    server_version = "BeautyUGCSaaS/0.1"

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            return self.redirect("/login")
        if path == "/login":
            return self.html(templates.login())
        if path == "/logout":
            sid = self.session_id()
            if sid:
                sessions.pop(sid, None)
            return self.redirect("/login")
        if path == "/dashboard":
            user = self.require_user()
            if not user:
                return
            store = storage.get_store(user["store_id"])
            return self.html(templates.dashboard(store, storage.list_submissions(store["id"])))
        if path == "/settings":
            user = self.require_user()
            if not user:
                return
            saved = parse_qs(urlparse(self.path).query).get("saved") == ["1"]
            return self.html(templates.settings(storage.get_store(user["store_id"]), saved=saved))
        if path == "/qr":
            user = self.require_user()
            if not user:
                return
            return self.html(templates.qr_page(storage.get_store(user["store_id"]), self.base_url()))
        if path == "/qr.svg":
            user = self.require_user()
            if not user:
                return
            store = storage.get_store(user["store_id"])
            upload_url = f"{self.base_url()}/u/{store['public_upload_id']}"
            return self.svg(qr_svg(upload_url))
        if path.startswith("/u/"):
            public_id = path.split("/", 2)[2]
            store = storage.get_store_by_public_id(public_id)
            if not store:
                return self.not_found()
            return self.html(templates.upload_form(store))
        if path.startswith("/submission/"):
            user = self.require_user()
            if not user:
                return
            parts = path.strip("/").split("/")
            if len(parts) == 2 and parts[1].isdigit():
                submission = storage.get_submission(int(parts[1]), user["store_id"])
                if not submission:
                    return self.not_found()
                return self.html(templates.submission_detail(storage.get_store(user["store_id"]), submission))
        if path.startswith("/uploads/"):
            return self.file(UPLOAD_DIR / Path(path).name)
        if path.startswith("/static/"):
            return self.file(STATIC_DIR / Path(path).name)
        return self.not_found()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/login":
            data = self.form_urlencoded()
            user = storage.authenticate(data.get("email", ""), data.get("password", ""))
            if not user:
                return self.html(templates.login("メールアドレスまたはパスワードが違います。"), status=401)
            sid = secrets.token_urlsafe(24)
            sessions[sid] = user["id"], user["store_id"]
            return self.redirect("/dashboard", set_cookie=sid)
        if path == "/settings":
            user = self.require_user()
            if not user:
                return
            data = self.form_urlencoded()
            storage.update_store(user["store_id"], data)
            return self.redirect("/settings?saved=1")
        if path.startswith("/submit/"):
            public_id = path.split("/", 2)[2]
            store = storage.get_store_by_public_id(public_id)
            if not store:
                return self.not_found()
            return self.handle_customer_submit(store)
        if path.startswith("/submission/"):
            user = self.require_user()
            if not user:
                return
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[1].isdigit() and parts[2] == "generate":
                return self.generate_submission(int(parts[1]), user["store_id"])
            if len(parts) == 3 and parts[1].isdigit() and parts[2] == "save":
                data = self.form_urlencoded()
                storage.update_generated_caption(int(parts[1]), user["store_id"], data.get("caption", ""), "")
                return self.redirect(f"/submission/{parts[1]}")
            if len(parts) == 3 and parts[1].isdigit() and parts[2] == "status":
                data = self.form_urlencoded()
                storage.update_submission_status(int(parts[1]), user["store_id"], data.get("status", "posted"))
                return self.redirect(f"/submission/{parts[1]}")
        return self.not_found()

    def handle_customer_submit(self, store):
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        if not form.getfirst("consent"):
            return self.html(templates.upload_form(store, "掲載許可への同意が必要です。"), status=400)
        photo = form["photo"] if "photo" in form else None
        if photo is None or not getattr(photo, "filename", ""):
            return self.html(templates.upload_form(store, "写真を選択してください。"), status=400)

        suffix = Path(photo.filename).suffix.lower()
        if suffix not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            suffix = ".jpg"
        filename = f"{secrets.token_urlsafe(16)}{suffix}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        target = UPLOAD_DIR / filename
        with target.open("wb") as fh:
            fh.write(photo.file.read())

        selected = form.getlist("selected_comments")
        storage.create_submission(
            store_id=store["id"],
            image_url=f"/uploads/{filename}",
            menu_name=form.getfirst("menu_name", ""),
            instagram_id=form.getfirst("instagram_id", ""),
            selected_comments=selected,
            free_comment=form.getfirst("free_comment", ""),
        )
        return self.html(templates.thanks(store))

    def generate_submission(self, submission_id, store_id):
        store = storage.get_store(store_id)
        submission = storage.get_submission(submission_id, store_id)
        if not submission:
            return self.not_found()
        payload = {
            **submission,
            "selected_comments": ",".join(submission["selected_comments"]),
        }
        result = generate_caption(store, payload)
        storage.update_generated_caption(submission_id, store_id, result["caption"], " ".join(result["hashtags"]))
        return self.redirect(f"/submission/{submission_id}")

    def require_user(self):
        sid = self.session_id()
        session = sessions.get(sid)
        if not session:
            self.redirect("/login")
            return None
        return {"id": session[0], "store_id": session[1]}

    def session_id(self):
        raw = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie(raw)
        if "sid" not in jar:
            return None
        return jar["sid"].value

    def form_urlencoded(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        parsed = parse_qs(raw)
        return {key: values[-1] if values else "" for key, values in parsed.items()}

    def html(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def svg(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def file(self, path):
        if not path.exists() or not path.is_file():
            return self.not_found()
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location, set_cookie=None):
        self.send_response(302)
        self.send_header("Location", location)
        if set_cookie:
            self.send_header("Set-Cookie", f"sid={set_cookie}; HttpOnly; Path=/; SameSite=Lax")
        self.end_headers()

    def not_found(self):
        return self.html(templates.page("見つかりません", "<section class='panel'>ページが見つかりません。</section>"), status=404)

    def base_url(self):
        return f"http://{self.headers.get('Host', '127.0.0.1:8000')}"

    def log_message(self, format, *args):
        return


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    storage.init_db()
    storage.ensure_demo()
    server = ThreadingHTTPServer(("127.0.0.1", 8000), App)
    print("Beauty UGC SaaS running at http://127.0.0.1:8000")
    print("Demo login: demo@example.com / password123")
    server.serve_forever()


if __name__ == "__main__":
    main()
