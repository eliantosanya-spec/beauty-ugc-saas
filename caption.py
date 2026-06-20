BUSINESS_LABELS = {
    "hair": "美容院",
    "nail": "ネイルサロン",
    "eyelash": "アイラッシュサロン",
    "esthetic": "エステサロン",
}

BUSINESS_HASHTAGS = {
    "hair": ["美容院", "ヘアスタイル", "ヘアカラー"],
    "nail": ["ネイルサロン", "ネイルデザイン", "大人ネイル"],
    "eyelash": ["アイラッシュ", "まつげ", "目元美容"],
    "esthetic": ["エステ", "リラクゼーション", "美容ケア"],
}

PROHIBITED_TERMS = [
    "治る",
    "治った",
    "完治",
    "痩せる",
    "痩せた",
    "シミが消える",
    "シミが消え",
    "小顔になる",
    "必ず",
]


def split_comments(value):
    if not value:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item and item.strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def sanitize_text(text):
    clean = text or ""
    for term in PROHIBITED_TERMS:
        clean = clean.replace(term, "")
    return " ".join(clean.split())


def tone_prefix(tone):
    return {
        "高級感": "落ち着いた雰囲気で",
        "かわいい": "やわらかく華やかな雰囲気で",
        "親しみやすい": "親しみやすい雰囲気で",
        "シンプル": "シンプルに",
        "丁寧": "丁寧に",
    }.get(tone or "", "丁寧に")


def build_hashtags(store, submission):
    area = (store.get("area") or "").replace(" ", "")
    business_type = store.get("business_type") or "hair"
    menu = (submission.get("menu_name") or "").replace(" ", "")

    tags = []
    if area:
        label = BUSINESS_LABELS.get(business_type, "美容サロン").replace("サロン", "")
        tags.append(f"#{area}{label}")
    if menu:
        tags.append(f"#{menu}")
    for tag in BUSINESS_HASHTAGS.get(business_type, ["美容サロン"]):
        tags.append(f"#{tag}")

    unique = []
    for tag in tags:
        if tag not in unique:
            unique.append(tag)
    return unique[:5]


def generate_caption(store, submission):
    business_type = store.get("business_type") or "hair"
    menu_name = sanitize_text(submission.get("menu_name") or "本日の施術")
    selected_comments = [sanitize_text(item) for item in split_comments(submission.get("selected_comments"))]
    free_comment = sanitize_text(submission.get("free_comment") or "")
    tone = tone_prefix(store.get("post_tone"))

    intro_by_type = {
        "hair": f"{tone}{menu_name}を仕上げました。",
        "nail": f"{tone}{menu_name}を楽しめるデザインに仕上げました。",
        "eyelash": f"{tone}{menu_name}で目元の印象を整えました。",
        "esthetic": f"{tone}{menu_name}の時間を過ごしていただきました。",
    }
    lines = [intro_by_type.get(business_type, f"{tone}{menu_name}を仕上げました。")]

    if selected_comments:
        lines.append(f"お客様からは「{selected_comments[0]}」とのお声をいただきました。")
    if free_comment:
        lines.append(f"ご感想: {free_comment}")

    booking_url = store.get("booking_url") or ""
    if booking_url:
        lines.append("ご予約はプロフィールリンク、または店舗ページから。")
    else:
        lines.append("ご予約や詳細は店舗プロフィールからご確認ください。")

    if store.get("coupon_enabled") and store.get("coupon_description"):
        lines.append(f"投稿協力特典: {sanitize_text(store.get('coupon_description'))}")
    if store.get("lottery_enabled") and store.get("lottery_description"):
        lines.append(f"キャンペーン: {sanitize_text(store.get('lottery_description'))}")

    hashtags = build_hashtags(store, submission)
    caption = "\n".join(lines + ["", " ".join(hashtags)])
    return {"caption": caption, "hashtags": hashtags}
