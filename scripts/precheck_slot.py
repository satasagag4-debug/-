#!/usr/bin/env python3
"""X定期投稿枠の事前チェック（汎用・軽量版）

使い方:
  python3 scripts/precheck_slot.py [queue_or_posts.json]
引数を省略した場合は、presets/queue.json -> queue.json -> posts.json の順で探索します。
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)


def parse_dt(s):
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt.astimezone(JST)
    except Exception:
        return None


def resolve_json_path():
    if len(sys.argv) > 1:
        return sys.argv[1]
    for candidate in ("presets/queue.json", "queue.json", "posts.json"):
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError("queue.json または posts.json が見つかりません。引数でパスを指定してください。")


def main():
    path = resolve_json_path()
    with open(path, encoding="utf-8") as f:
        q = json.load(f)

    settings = q.get("settings", {})
    posts = q.get("posts", [])

    print(f"=== X定期枠 事前チェック ({NOW.strftime('%Y-%m-%d %H:%M:%S %Z')}) [{path}] ===")

    # 1. 連投ガード (60分)
    last_post_dt = parse_dt(settings.get("last_post_at"))
    if last_post_dt:
        diff_min = (NOW - last_post_dt).total_seconds() / 60.0
        guard_ok = diff_min >= 60.0
        print(f"[連投ガード] {'OK' if guard_ok else 'BLOCKED'} (前回: {last_post_dt.strftime('%m-%d %H:%M:%S')} / {diff_min:.1f}分前)")
    else:
        print("[連投ガード] OK (last_post_at なし)")

    # 2. 最優先指定
    np_id = settings.get("next_post_preset_id")
    if np_id is not None:
        print(f"[最優先指定] ID {np_id} (settings.next_post_preset_id)")
    else:
        print("[最優先指定] なし")

    # 3. 毎日18時前後の固定ポスト更新
    last_pin_dt = parse_dt(settings.get("last_pinned_at"))
    in_18_window = (17, 30) <= (NOW.hour, NOW.minute) <= (18, 45)
    pinned_today = last_pin_dt is not None and last_pin_dt.date() == NOW.date()
    if in_18_window and not pinned_today:
        print(f"[18時固定更新] 要実施 (過去24h以内の最勢いポストへ更新 / 前回固定: {last_pin_dt.strftime('%m-%d %H:%M') if last_pin_dt else 'なし'})")
    else:
        print(f"[18時固定更新] 不要 (現在窓外または本日更新済み / 前回: {last_pin_dt.strftime('%m-%d %H:%M') if last_pin_dt else 'なし'})")

    # 4. 勝ち馬 (最低12時間以上空け・24h以内再投下)
    winners_active = []
    winners_stale = []
    for p in posts:
        if p.get("status") in ("held_sensitive", "pending_hold", "held_duplicate"):
            continue
        if p.get("high_performing") or p.get("must_repost_within_24h"):
            lp = parse_dt(p.get("last_posted_at"))
            if not lp:
                continue
            hrs = (NOW - lp).total_seconds() / 3600.0
            if hrs <= 36.0:
                winners_active.append((p["id"], p.get("title") or p.get("text", "")[:18], hrs))
            else:
                winners_stale.append((p["id"], p.get("title") or p.get("text", "")[:18], hrs))
    print("[勝ち馬(直近)]")
    if winners_active:
        for pid, title, hrs in sorted(winners_active, key=lambda x: -x[2]):
            cd_ok = "12h空けOK" if hrs >= 12.0 else f"12h未満({hrs:.1f}h)"
            rem24 = 24.0 - hrs
            print(f"  - ID {pid} ({title[:18]}): 前回から {hrs:.1f}h [{cd_ok}] / 24h期限残り {rem24:.1f}h")
    else:
        print("  - 該当なし")
    if winners_stale:
        ids_str = ", ".join(f"ID {x[0]}({x[2]:.0f}h前)" for x in winners_stale)
        print(f"[勝ち馬(36h超え古いマーク)] {ids_str}")

    # 5. 40時間経過後削除 (エンタメリスト由来 & 芸能系・2026-11-16以降適用)
    cutoff_start = datetime(2026, 11, 16, 0, 0, 0, tzinfo=JST)
    del_targets = []
    for p in posts:
        is_target_type = (
            p.get("source_list") == "2122594457271070969"
            or p.get("delete_after_hours") == 40
            or p.get("is_celebrity") is True
            or p.get("category") == "celebrity_trend"
        )
        if not is_target_type:
            continue
        if any(k.startswith("post_deleted") or k.startswith("deleted_40h") for k in p.keys()):
            continue
        lp = parse_dt(p.get("last_posted_at"))
        if lp and lp >= cutoff_start:
            hrs = (NOW - lp).total_seconds() / 3600.0
            if hrs >= 40.0:
                del_targets.append((p["id"], p.get("title") or p.get("text", "")[:18], hrs, p.get("post_url", "")))
    print("[40h後削除対象]")
    if del_targets:
        for pid, title, hrs, url in del_targets:
            print(f"  - ID {pid} ({title[:18]}): {hrs:.1f}h経過 -> {url}")
    else:
        print("  - なし")

    # 6. エンタメリスト (21日クールダウン / 30日整理)
    entame_cd = []
    entame_drop = []
    for p in posts:
        if p.get("source_list") != "2122594457271070969":
            continue
        lp = parse_dt(p.get("last_posted_at"))
        added = parse_dt(p.get("added_at"))
        if lp and not p.get("high_performing"):
            days = (NOW - lp).total_seconds() / 86400.0
            if days < 21.0:
                entame_cd.append(f"ID {p['id']}(残{21-days:.0f}日)")
        if added and not p.get("high_performing") and (NOW - added).total_seconds() / 86400.0 >= 30.0:
            entame_drop.append(f"ID {p['id']}")
    print(f"[エンタメリスト21日CD中] {', '.join(entame_cd) if entame_cd else 'なし'}")
    print(f"[エンタメリスト30日整理候補] {', '.join(entame_drop) if entame_drop else 'なし'}")

    # 7. 未投稿ストック数
    queued = [p["id"] for p in posts if p.get("status") == "queued"]
    print(f"[未投稿ストック] {len(queued)}件 (先頭例: {queued[:10]})")


if __name__ == "__main__":
    main()
