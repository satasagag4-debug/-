# Preset Sync Feed

- raw ベースURL: `https://raw.githubusercontent.com/satasagag4-debug/-/main/`

投稿プリセット（投稿文・メディア・指定リプライ）と運用ルールの同期用フィード。

## ファイル

| path | 内容 |
| --- | --- |
| `manifest.json` | 現在の版情報（`updated_at`, `total_posts`, `max_id`, `rules_version`） |
| `posts.json` | 投稿一覧 |
| `posts.md` | 投稿一覧（Markdown） |
| `rules.json` | 運用ルール（JSON） |
| `rules.md` | 運用ルール（Markdown） |
| `scripts/precheck_slot.py` | 定期枠開始前の自動チェック用軽量スクリプト（任意・推奨） |
| `media/` | メディア本体 |

## 取得手順（差分チェック・省エネ推奨）

1. `https://raw.githubusercontent.com/satasagag4-debug/-/main/manifest.json` だけを取得する（トークン付きでアクセス）。
2. ローカルに保存してある `max_id`・`rules_version`・`updated_at` を、取得した manifest の値と比較する。
3. すべて前回と同じであれば、更新なしとしてここで終了する（`posts.json` や `media/` は読みに行かない）。
4. `max_id` が増えていれば `https://raw.githubusercontent.com/satasagag4-debug/-/main/posts.json` を取得し、`id` がローカルの `max_id` より大きい要素を取り込む。
5. 取り込む要素の `media` に書かれたパスを `https://raw.githubusercontent.com/satasagag4-debug/-/main/` + そのパス（例 `https://raw.githubusercontent.com/satasagag4-debug/-/main/media/p1_1.mp4`）で取得してローカルに保存する。
6. `rules_version` が変わっていれば `https://raw.githubusercontent.com/satasagag4-debug/-/main/rules.json`（または `https://raw.githubusercontent.com/satasagag4-debug/-/main/rules.md`）を取得して置き換える。
7. manifest の `max_id`・`rules_version`・`updated_at` をローカルに記録する。

## データ仕様

- 文字コードは UTF-8。
- `posts.json`: `{"total": <int>, "posts": [<post>, ...]}`
- `post`: `id` (int), `text` (string, 投稿本文), `media_type` (string), `media` (string の配列, メディアのパス), `tree_reply` (string, 指定リプライ。設定がある投稿のみ)
- メディアのパスは `media/p{id}_{index}.{ext}`（`index` は 1 始まり）。
- `rules.json`: `version`, `items`（`no`, `title`, `rule`）
