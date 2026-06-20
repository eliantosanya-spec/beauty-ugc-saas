# Beauty UGC SaaS MVP

美容院、ネイル、アイラッシュ、エステなどの美容店舗向けUGC集客SaaS MVPです。

## 実行方法

```powershell
& 'C:\Users\User\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' beauty-ugc-saas\app.py
```

ブラウザで開きます。

```text
http://127.0.0.1:8000
```

## デモログイン

```text
メール: demo@example.com
パスワード: password123
```

## MVPでできること

- 店舗ログイン
- 店舗設定
- 店舗専用アップロードURL表示
- お客さんの写真アップロード
- 掲載許可チェック
- Instagram ID任意入力
- メニュー名任意入力
- 選択式コメント
- 自由入力コメント
- 投稿候補一覧
- 投稿文生成
- Instagram用コピー
- 投稿済みステータス管理
- クーポン/抽選キャンペーン表示
- スマホ向け下部ナビ
- スマホ向け投稿確認画面
- スマホ向けお客さん送信フォーム
- 店舗専用QR画像の自動生成

## MVPで入れていないもの

- Instagram API自動投稿
- LINE連携
- Stripe課金
- 動画対応
- 画像解析
- 複数スタッフ権限

## 画面を更新した後

コード更新後は、起動中の黒いサーバー画面を閉じてから、もう一度 `start-beauty-ugc-saas.cmd` を開いてください。
