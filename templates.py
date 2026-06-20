import html


BUSINESS_OPTIONS = [
    ("hair", "美容院"),
    ("nail", "ネイルサロン"),
    ("eyelash", "アイラッシュ"),
    ("esthetic", "エステ"),
]

COMMENT_OPTIONS = {
    "common": [
        "仕上がりに満足しています",
        "またお願いしたいです",
        "スタッフさんが丁寧でした",
        "雰囲気が良かったです",
        "初めてでも安心できました",
        "友達にも紹介したいです",
    ],
    "hair": ["髪色がきれいで気に入りました", "セットしやすくなりました", "理想の雰囲気になりました"],
    "nail": ["デザインがかわいくて気に入りました", "色味がイメージ通りでした", "手元を見るのが楽しくなりました"],
    "eyelash": ["自然な仕上がりで満足です", "目元が華やかになりました", "朝のメイクが楽になりました"],
    "esthetic": ["リラックスできました", "施術後のすっきり感がありました", "また定期的に通いたいです"],
}

STATUS_LABELS = {
    "unreviewed": "未確認",
    "adopted": "採用",
    "rejected": "却下",
    "generated": "投稿文生成済み",
    "posted": "投稿済み",
}


def esc(value):
    return html.escape(str(value or ""), quote=True)


def page(title, body, authed=False):
    nav = ""
    bottom_nav = ""
    if authed:
        nav = """
        <nav class="top-nav">
          <a href="/dashboard">投稿候補</a>
          <a href="/settings">店舗設定</a>
          <a href="/qr">アップロードURL</a>
          <a href="/logout">ログアウト</a>
        </nav>
        """
        bottom_nav = """
        <nav class="bottom-nav" aria-label="スマホ用ナビ">
          <a href="/dashboard"><span>投稿</span></a>
          <a href="/qr"><span>URL</span></a>
          <a href="/settings"><span>設定</span></a>
        </nav>
        """
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  <header class="app-header">
    <div>
      <p class="eyebrow">Beauty UGC SaaS</p>
      <h1>{esc(title)}</h1>
    </div>
    {nav}
  </header>
  <main class="app-main">{body}</main>
  {bottom_nav}
  <script src="/static/app.js"></script>
</body>
</html>"""


def login(error=""):
    err = f'<p class="error">{esc(error)}</p>' if error else ""
    return page(
        "店舗ログイン",
        f"""
        <section class="panel narrow">
          {err}
          <form method="post" action="/login" class="form-stack">
            <label>メールアドレス<input name="email" type="email" value="demo@example.com" required></label>
            <label>パスワード<input name="password" type="password" value="password123" required></label>
            <button class="primary" type="submit">ログイン</button>
          </form>
          <p class="hint">デモ: demo@example.com / password123</p>
        </section>
        """,
    )


def dashboard(store, submissions):
    rows = []
    for item in submissions:
        comments = ", ".join(item["selected_comments"])
        rows.append(
            f"""
            <article class="submission-card">
              <img src="{esc(item['image_url'])}" alt="">
              <div class="submission-card-body">
                <div class="card-row">
                  <span class="badge">{esc(STATUS_LABELS.get(item['status'], item['status']))}</span>
                  <span class="muted">{esc(item['created_at'])}</span>
                </div>
                <h2>{esc(item['menu_name'] or 'メニュー未入力')}</h2>
                <p>{esc(comments or item['free_comment'] or 'コメント未入力')}</p>
                <a class="button-link card-action" href="/submission/{item['id']}">確認する</a>
              </div>
            </article>
            """
        )
    empty = '<section class="panel"><p>まだ投稿候補はありません。アップロードURLをお客さんに案内してください。</p></section>'
    body = f"""
    <section class="summary-grid">
      <div class="metric"><span>店舗</span><strong>{esc(store['name'])}</strong></div>
      <div class="metric"><span>投稿候補</span><strong>{len(submissions)}</strong></div>
      <div class="metric"><span>業種</span><strong>{esc(store['business_type'])}</strong></div>
    </section>
    <section class="list-stack">{''.join(rows) if rows else empty}</section>
    """
    return page("投稿候補", body, authed=True)


def settings(store, saved=False):
    saved_msg = '<p class="success">保存しました。</p>' if saved else ""
    business_options = "".join(
        f'<option value="{key}" {"selected" if store["business_type"] == key else ""}>{label}</option>'
        for key, label in BUSINESS_OPTIONS
    )
    tone_options = "".join(
        f'<option {"selected" if store["post_tone"] == tone else ""}>{tone}</option>'
        for tone in ["丁寧", "親しみやすい", "高級感", "かわいい", "シンプル"]
    )
    body = f"""
    <section class="panel">
      {saved_msg}
      <form method="post" action="/settings" class="form-grid">
        <label>店舗名<input name="name" value="{esc(store['name'])}" required></label>
        <label>業種<select name="business_type">{business_options}</select></label>
        <label>地域<input name="area" value="{esc(store['area'])}" placeholder="渋谷"></label>
        <label>Instagramアカウント<input name="instagram_account" value="{esc(store['instagram_account'])}" placeholder="shop_account"></label>
        <label>予約URL<input name="booking_url" value="{esc(store['booking_url'])}" placeholder="https://..."></label>
        <label>投稿トーン<select name="post_tone">{tone_options}</select></label>
        <label class="check"><input type="checkbox" name="coupon_enabled" {"checked" if store['coupon_enabled'] else ""}> 次回割引クーポンを表示</label>
        <label>クーポンコード<input name="coupon_code" value="{esc(store['coupon_code'])}" placeholder="PHOTO500"></label>
        <label>クーポン説明<input name="coupon_description" value="{esc(store['coupon_description'])}" placeholder="次回来店時に500円OFF"></label>
        <label class="check"><input type="checkbox" name="lottery_enabled" {"checked" if store['lottery_enabled'] else ""}> 抽選キャンペーンを表示</label>
        <label class="wide">抽選説明<input name="lottery_description" value="{esc(store['lottery_description'])}" placeholder="今月の抽選キャンペーンに参加"></label>
        <button class="primary" type="submit">保存</button>
      </form>
    </section>
    """
    return page("店舗設定", body, authed=True)


def qr_page(store, base_url):
    upload_url = f"{base_url}/u/{store['public_upload_id']}"
    return page(
        "アップロードURL",
        f"""
        <section class="panel print-card">
          <p class="eyebrow">お客様にこのURLを案内してください</p>
          <h2>{esc(store['name'])}</h2>
          <div class="qr-layout">
            <div class="qr-box">
              <img src="/qr.svg" alt="お客さん用アップロードQRコード">
            </div>
            <div>
              <p class="qr-title">スマホで読み取ると写真送信フォームが開きます。</p>
              <p class="hint">受付、施術席、レジ横に印刷して置いてください。</p>
            </div>
          </div>
          <p class="upload-url">{esc(upload_url)}</p>
          <button class="secondary" data-copy="{esc(upload_url)}">URLをコピー</button>
          <button class="secondary" type="button" onclick="window.print()">印刷する</button>
        </section>
        """,
        authed=True,
    )


def upload_form(store, error=""):
    comments = COMMENT_OPTIONS["common"] + COMMENT_OPTIONS.get(store["business_type"], [])
    checks = "".join(
        f'<label class="choice"><input type="checkbox" name="selected_comments" value="{esc(comment)}"> {esc(comment)}</label>'
        for comment in comments
    )
    err = f'<p class="error">{esc(error)}</p>' if error else ""
    return page(
        f"{store['name']} 写真送信",
        f"""
        <section class="customer-intro">
          <p class="eyebrow">写真提供フォーム</p>
          <h2>{esc(store['name'])}</h2>
          <p>仕上がり写真を送ると、店舗SNSで紹介される場合があります。特典がある場合は送信後に表示されます。</p>
        </section>
        <section class="panel">
          {err}
          <form method="post" action="/submit/{esc(store['public_upload_id'])}" enctype="multipart/form-data" class="form-stack">
            <label>写真<input name="photo" type="file" accept="image/*" required></label>
            <label>メニュー名<input name="menu_name" placeholder="例: 透明感カラー、ワンカラーネイル"></label>
            <label>Instagram ID 任意<input name="instagram_id" placeholder="例: customer_id"></label>
            <fieldset>
              <legend>感想を選択 任意</legend>
              <div class="choice-grid">{checks}</div>
            </fieldset>
            <label>自由コメント 任意<textarea name="free_comment" rows="4" placeholder="相談しやすかった、仕上がりが気に入った等"></textarea></label>
            <label class="check"><input type="checkbox" name="consent" value="1" required> 店舗SNSや販促物で写真を使用することに同意します</label>
            <button class="primary" type="submit">送信する</button>
          </form>
        </section>
        """,
    )


def thanks(store):
    perks = []
    if store["coupon_enabled"]:
        perks.append(f"<li><strong>{esc(store['coupon_code'])}</strong> {esc(store['coupon_description'])}</li>")
    if store["lottery_enabled"]:
        perks.append(f"<li>{esc(store['lottery_description'])}</li>")
    perk_html = f"<ul>{''.join(perks)}</ul>" if perks else "<p>ご協力ありがとうございました。</p>"
    return page(
        "送信完了",
        f"""
        <section class="panel narrow">
          <h2>写真を送信しました</h2>
          <p>店舗スタッフが確認します。</p>
          {perk_html}
        </section>
        """,
    )


def submission_detail(store, submission):
    selected = ", ".join(submission["selected_comments"])
    caption = submission["generated_caption"] or "まだ投稿文は生成されていません。"
    mention = f"@{submission['instagram_id']}" if submission["instagram_id"] else "未入力"
    post_text = esc(caption)
    return page(
        "投稿確認",
        f"""
        <section class="detail-grid">
          <div class="panel">
            <img class="detail-image" src="{esc(submission['image_url'])}" alt="">
            <dl>
              <dt>メニュー</dt><dd>{esc(submission['menu_name'] or '未入力')}</dd>
              <dt>Instagram ID</dt><dd>{esc(mention)}</dd>
              <dt>選択式コメント</dt><dd>{esc(selected or '未入力')}</dd>
              <dt>自由コメント</dt><dd>{esc(submission['free_comment'] or '未入力')}</dd>
              <dt>ステータス</dt><dd>{esc(STATUS_LABELS.get(submission['status'], submission['status']))}</dd>
            </dl>
          </div>
          <div class="panel action-panel">
            <div class="mobile-action-bar">
              <form method="post" action="/submission/{submission['id']}/generate">
                <button class="primary" type="submit">AI生成</button>
              </form>
              <button class="secondary" type="button" data-copy-target="caption-copy">コピー</button>
              <form method="post" action="/submission/{submission['id']}/status">
                <input type="hidden" name="status" value="posted">
                <button type="submit" class="secondary">投稿済み</button>
              </form>
            </div>
            <form method="post" action="/submission/{submission['id']}/generate" class="desktop-only">
              <button class="primary" type="submit">AI投稿文を生成</button>
            </form>
            <form method="post" action="/submission/{submission['id']}/save" class="form-stack">
              <textarea name="caption" rows="12">{post_text}</textarea>
              <button class="secondary desktop-only" type="button" data-copy-target="caption-copy">Instagram用にコピー</button>
              <textarea id="caption-copy" class="visually-hidden">{post_text}</textarea>
              <button class="primary" type="submit">編集内容を保存</button>
            </form>
            <form method="post" action="/submission/{submission['id']}/status" class="button-row desktop-only">
              <input type="hidden" name="status" value="posted">
              <button type="submit" class="secondary">投稿済みにする</button>
            </form>
          </div>
        </section>
        """,
        authed=True,
    )
