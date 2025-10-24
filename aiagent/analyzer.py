# aiagent/analyzer.py
# ✅ 全候補者をスコアリング対象にする（モックモード・閾値70）

import os
import csv
import random
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
INPUT_FILE = os.path.join(DATA_DIR, "candidates_raw.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "candidates_scored.csv")

def analyze_candidates():
    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ファイルが存在しません: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    if df.empty:
        print("⚠️ 候補者データが空です。")
        return

    rows = df.to_dict("records")

    # ✅ ここから本処理（制限解除済み）
    print(f"🧠 {len(rows)} 件の候補者をスコアリングします（モックモード）。")

    results = []
    for r in rows:
        name = r["name"]
        url = r["url"]

        # モックスコア生成
        score = random.randint(40, 95)
        reason = "モック: 経験・職種・SIer関連度を考慮した仮スコア"
        decision = "send" if score >= 70 else "skip"

        results.append({
            "name": name,
            "url": url,
            "score": score,
            "decision": decision,
            "reason": reason
        })

    # CSV出力
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url", "score", "decision", "reason"])
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ スコアリング完了: {len(results)} 件 → {OUTPUT_FILE}")
    print("🧠 （モックモード動作中・API未使用）")

if __name__ == "__main__":
    analyze_candidates()
