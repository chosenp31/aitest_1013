# aiagent/message_generator.py
# ✅ 改行コードLF固定版（macOS/Linux互換）

import os
import csv

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
RAW_PATH = os.path.join(DATA_DIR, "candidates_scored.csv")
OUT_PATH = os.path.join(DATA_DIR, "messages.csv")

def generate_messages():
    print("🧠 候補者スコアリング結果を基にメッセージを生成中...")

    if not os.path.exists(RAW_PATH):
        print(f"❌ スコアリングファイルが見つかりません: {RAW_PATH}")
        return

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    if not candidates:
        print("⚠️ 候補者が存在しません。")
        return

    messages = []
    for row in candidates:
        name = row.get("name", "不明")
        url = row.get("url") or row.get("profile_url")
        score = float(row.get("score", 0))

        # --- 仮メッセージ生成 ---
        if score >= 80:
            message = f"はじめまして、{name}様。ぜひお話しできればと思います。"
        elif score >= 60:
            message = f"突然のご連絡失礼いたします。{name}様の経歴に関心を持ちました。"
        else:
            message = f"{name}様、貴重なご経験を拝見しました。ご興味あればお話させてください。"

        messages.append({"name": name, "url": url, "message": message})

    # --- CSV書き出し（改行コードをLFに固定） ---
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url", "message"])
        writer.writeheader()
        writer.writerows(messages)

    print(f"✅ メッセージ生成完了: {len(messages)} 件 → {OUT_PATH}")

if __name__ == "__main__":
    generate_messages()
