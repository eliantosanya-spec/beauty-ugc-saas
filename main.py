import json
import os
import secrets
from pathlib import Path

import jinja2
from fastapi import FastAPI, Form, Request, UploadFile
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse, Response
from itsdangerous import URLSafeTimedSerializer

from storage import Storage
from config import COMMENT_OPTIONS, STATUS_LABELS, TONE_OPTIONS, BUSINESS_OPTIONS
from caption import generate_caption
from qr_svg import qr_svg

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "app.sqlite3"

# Production-ready secret: env var > file > random (persist across restarts)
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    key_file = BASE_DIR / ".secret_key"
    if key_file.exists():
        SECRET_KEY = key_file.read_text().strip()
    else:
        SECRET_KEY = secrets.token_hex(32)
        key_file.write_text(SECRET_KEY)

storage = Storage(DB_PATH)
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="session")

# ── Plain Jinja2 (bypass Starlette's Jinja2Templates caching issues) ──

jenv = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=jinja2.select_autoescape(),
    cache_size=50,
)

app = FastAPI(title="Beauty UGC SaaS")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def render(name: str, request: Request, **kw) -> HTMLResponse:
    """Render a Jinja2 template as HTMLResponse, passing request + authed info."""
    store = require_store(request)
    authed = store is not None
    kw.setdefault("request", request)
    kw.setdefault("authed", authed)
    if store:
        kw.setdefault("store", store)
    html = jenv.get_template(name).render(**kw)
    return HTMLResponse(html)


# ── Helpers ──────────────────────────────────────────────

def make_session(store_id: int, user_id: int) -> str:
    return serializer.dumps({"store_id": store_id, "user_id": user_id})


def get_session(sid: str | None) -> dict | None:
    if not sid:
        return None
    try:
        return serializer.loads(sid, max_age=86400 * 7)
    except Exception:
        return None


def require_store(request: Request) -> dict | None:
    sess = get_session(request.cookies.get("sid"))
    if not sess:
        return None
    return storage.get_store(sess["store_id"])


def base_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "127.0.0.1:8000"))
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{scheme}://{host}"


# ── Routes ───────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    return render("login.html", request=request, error=error)


@app.post("/login")
def login_post(request: Request, email: str = Form(), password: str = Form()):
    user = storage.authenticate(email, password)
    if not user:
        return render("login.html", request=request, error="メールアドレスまたはパスワードが違います。")
    sid = make_session(user["store_id"], user["id"])
    resp = RedirectResponse(url="/dashboard", status_code=302)
    resp.set_cookie("sid", sid, httponly=True, max_age=604800, samesite="lax")
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=302)
    resp.delete_cookie("sid")
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    submissions = storage.list_submissions(store["id"])
    return render("dashboard.html", request=request, submissions=submissions, status_labels=STATUS_LABELS)


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: bool = False):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    return render("settings.html", request=request, saved=saved,
                  business_options=BUSINESS_OPTIONS, tone_options=TONE_OPTIONS)


@app.post("/settings")
def settings_post(
    request: Request,
    name: str = Form(), business_type: str = Form(),
    area: str = Form(""), instagram_account: str = Form(""), booking_url: str = Form(""),
    post_tone: str = Form("丁寧"),
    coupon_enabled: bool = Form(False), coupon_code: str = Form(""), coupon_description: str = Form(""),
    lottery_enabled: bool = Form(False), lottery_description: str = Form(""),
):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    storage.update_store(store["id"], {
        "name": name, "business_type": business_type, "area": area,
        "instagram_account": instagram_account, "booking_url": booking_url,
        "post_tone": post_tone,
        "coupon_enabled": coupon_enabled, "coupon_code": coupon_code,
        "coupon_description": coupon_description,
        "lottery_enabled": lottery_enabled, "lottery_description": lottery_description,
    })
    return RedirectResponse(url="/settings?saved=1", status_code=302)


@app.get("/qr", response_class=HTMLResponse)
def qr_page(request: Request):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    upload_url = f"{base_url(request)}/u/{store['public_upload_id']}"
    return render("qr_page.html", request=request, upload_url=upload_url)


@app.get("/qr.svg", response_class=Response)
def qr_svg_endpoint(request: Request):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    upload_url = f"{base_url(request)}/u/{store['public_upload_id']}"
    return Response(content=qr_svg(upload_url), media_type="image/svg+xml",
                    headers={"Cache-Control": "no-store"})


@app.get("/u/{public_id}", response_class=HTMLResponse)
def upload_form_page(request: Request, public_id: str, error: str = ""):
    store = storage.get_store_by_public_id(public_id)
    if not store:
        return HTMLResponse("店舗が見つかりません", status_code=404)
    comments = COMMENT_OPTIONS["common"] + COMMENT_OPTIONS.get(store["business_type"], [])
    return render("upload_form.html", request=request, store=store, comments=comments, error=error, authed=False)


@app.post("/u/{public_id}", response_class=HTMLResponse)
async def upload_submit(
    request: Request, public_id: str,
    photo: UploadFile | None = None,
    menu_name: str = Form(""), instagram_id: str = Form(""),
    selected_comments: list[str] = Form([]), free_comment: str = Form(""),
    consent: bool = Form(False),
):
    store = storage.get_store_by_public_id(public_id)
    if not store:
        return HTMLResponse("店舗が見つかりません", status_code=404)

    if not consent:
        comments = COMMENT_OPTIONS["common"] + COMMENT_OPTIONS.get(store["business_type"], [])
        return render("upload_form.html", request=request, store=store, comments=comments,
                      error="掲載許可への同意が必要です。", authed=False)
    if not photo or not photo.filename:
        comments = COMMENT_OPTIONS["common"] + COMMENT_OPTIONS.get(store["business_type"], [])
        return render("upload_form.html", request=request, store=store, comments=comments,
                      error="写真を選択してください。", authed=False)

    suffix = Path(photo.filename).suffix.lower()
    if suffix not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        suffix = ".jpg"
    filename = f"{secrets.token_urlsafe(16)}{suffix}"
    target = UPLOAD_DIR / filename
    content = await photo.read()
    target.write_bytes(content)

    storage.create_submission(
        store_id=store["id"],
        image_url=f"/uploads/{filename}",
        menu_name=menu_name,
        instagram_id=instagram_id,
        selected_comments=selected_comments,
        free_comment=free_comment,
    )
    return render("thanks.html", request=request, store=store, authed=False)


@app.get("/submission/{submission_id}", response_class=HTMLResponse)
def submission_detail(request: Request, submission_id: int):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    submission = storage.get_submission(submission_id, store["id"])
    if not submission:
        return HTMLResponse("投稿が見つかりません", status_code=404)
    return render("submission_detail.html", request=request, submission=submission,
                  status_labels=STATUS_LABELS)


@app.post("/submission/{submission_id}/generate")
def submission_generate(request: Request, submission_id: int):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    submission = storage.get_submission(submission_id, store["id"])
    if not submission:
        return HTMLResponse("投稿が見つかりません", status_code=404)
    payload = {**submission, "selected_comments": ",".join(submission["selected_comments"])}
    result = generate_caption(store, payload)
    storage.update_generated_caption(submission_id, store["id"], result["caption"], " ".join(result["hashtags"]))
    return RedirectResponse(url=f"/submission/{submission_id}", status_code=302)


@app.post("/submission/{submission_id}/save")
def submission_save(request: Request, submission_id: int, caption: str = Form("")):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    storage.update_generated_caption(submission_id, store["id"], caption, "")
    return RedirectResponse(url=f"/submission/{submission_id}", status_code=302)


@app.post("/submission/{submission_id}/status")
def submission_status(request: Request, submission_id: int, status: str = Form("posted")):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    storage.update_submission_status(submission_id, store["id"], status)
    return RedirectResponse(url=f"/submission/{submission_id}", status_code=302)


# ── Backup / Restore ─────────────────────────────────────

@app.get("/backup", response_class=HTMLResponse)
def backup_page(request: Request):
    store = require_store(request)
    if not store:
        return RedirectResponse(url="/login", status_code=302)
    return render("backup.html", request=request)


@app.get("/api/backup")
def api_backup(request: Request):
    store = require_store(request)
    if not store:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    data = storage.export_json()
    return JSONResponse(content=data, headers={"Content-Disposition": "attachment; filename=beauty-ugc-backup.json"})


@app.post("/api/restore")
async def api_restore(request: Request, backup: UploadFile, mode: str = Form("merge")):
    store = require_store(request)
    if not store:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    if not backup.filename or not backup.filename.endswith(".json"):
        return JSONResponse({"error": "JSON ファイルを選択してください"}, status_code=400)
    content = await backup.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return JSONResponse({"error": "JSON の解析に失敗しました"}, status_code=400)
    try:
        result = storage.import_json(data, replace=(mode == "replace"))
        return JSONResponse({"ok": True, "imported": result})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ── Static files ─────────────────────────────────────────

@app.get("/uploads/{filename}")
def uploaded_file(filename: str):
    path = UPLOAD_DIR / filename
    if not path.exists() or not path.is_file():
        return HTMLResponse("", status_code=404)
    return FileResponse(path)


# ── Start ────────────────────────────────────────────────

SITE_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

def main():
    storage.init_db()
    storage.ensure_demo()
    port = int(os.environ.get("PORT", 8000))
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        forwarded_allow_ips="*",
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
