# aiagent/linkedin_scorer.py
# OpenAI APIを使った候補者スコアリング（年齢推定を含む）

import os
import csv
import json
from dotenv import load_dotenv
from openai import OpenAI

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "candidates_raw.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "candidates_scored.csv")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.csv")

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# スコアリング基準
MAX_AGE = int(os.getenv("MAX_AGE", 40))
MIN_SCORE = int(os.getenv("MIN_SCORE", 60))
MAX_SEND_COUNT = int(os.getenv("MAX_SEND_COUNT", 10))  # 1回あたりの最大送信数

# ==============================
# OpenAIクライアント
# ==============================
if not OPENAI_API_KEY:
    print("❌ エラー: OPENAI_API_KEYが設定されていません")
    print("💡 .envファイルにOPENAI_API_KEYを設定してください")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# スコアリングプロンプト
# ==============================
SCORING_PROMPT = """
あなたはIT業界のリクルーターです。以下の候補者情報を分析して、スコアリングしてください。

【候補者情報】
名前: {name}
職歴/役職: {headline}
会社/組織: {company}
場所: {location}

【評価基準】
1. 年齢推定（40歳以下が望ましい）
   - 職歴の年数、会社名、役職から推定
   - 大学卒業を22歳と仮定して計算

2. IT業界経験
   - SIer、エンジニア、ITコンサルタント、DXエンジニアなどの経験
   - 関連業界: システム開発、クラウド、AI、データサイエンスなど

3. 除外対象
   - 学生、未経験者
   - IT業界と無関係（飲食、販売、製造など）
   - 推定年齢が40歳を大きく超える
   - 経営層の役職（社長、CEO、CIO、執行役員、取締役など）

【出力形式】
以下のJSON形式で出力してください。他の説明は一切不要です。

{{
  "estimated_age": 推定年齢（数値、不明な場合はnull）,
  "age_reasoning": "年齢推定の根拠",
  "score": スコア（0-100の整数）,
  "decision": "send" または "skip",
  "reason": "スコアリングの理由（簡潔に1-2文）"
}}

【スコアの目安】
- 90-100点: 完璧にマッチ（IT業界経験豊富、適切な年齢、関連スキル）
- 70-89点: 良好（IT業界経験あり、年齢範囲内）
- 60-69点: 可（IT業界経験あり、一部条件不一致）
- 40-59点: 微妙（IT業界だが条件が一部不一致）
- 0-39点: 不適合（学生、未経験、無関係な業界、年齢超過、経営層）

60点以上の場合は"send"、それ未満は"skip"としてください。
"""

# ==============================
# 候補者スコアリング
# ==============================
def score_candidate(candidate):
    """OpenAI APIで候補者をスコアリング"""

    name = candidate.get("name", "不明")
    headline = candidate.get("headline", "情報なし")
    company = candidate.get("company", "情報なし")
    location = candidate.get("location", "情報なし")

    # プロンプト生成
    prompt = SCORING_PROMPT.format(
        name=name,
        headline=headline,
        company=company,
        location=location
    )

    try:
        # OpenAI API呼び出し
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはIT業界のリクルーターです。JSON形式で出力してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        # レスポンス解析
        content = response.choices[0].message.content.strip()

        # JSON抽出（```json ... ```で囲まれている場合も対応）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        return {
            "estimated_age": result.get("estimated_age"),
            "age_reasoning": result.get("age_reasoning", ""),
            "score": result.get("score", 0),
            "decision": result.get("decision", "skip"),
            "reason": result.get("reason", "")
        }

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON解析エラー ({name}): {e}")
        print(f"   レスポンス: {content}")
        return {
            "estimated_age": None,
            "age_reasoning": "解析エラー",
            "score": 0,
            "decision": "skip",
            "reason": "AIレスポンスの解析に失敗"
        }
    except Exception as e:
        print(f"⚠️ APIエラー ({name}): {e}")
        return {
            "estimated_age": None,
            "age_reasoning": "エラー",
            "score": 0,
            "decision": "skip",
            "reason": f"APIエラー: {str(e)}"
        }

# ==============================
# メイン処理
# ==============================
def score_all_candidates():
    """全候補者をスコアリング"""

    if not os.path.exists(INPUT_FILE):
        print(f"❌ エラー: 候補者ファイルが見つかりません: {INPUT_FILE}")
        print(f"💡 先に linkedin_search.py を実行してください")
        return

    # CSV読み込み
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    if not candidates:
        print("⚠️ 候補者データが空です")
        return

    total = len(candidates)
    print(f"\n{'='*70}")
    print(f"🧠 AIスコアリング開始")
    print(f"{'='*70}")
    print(f"候補者数: {total} 件")
    print(f"使用モデル: {OPENAI_MODEL}")
    print(f"最低スコア: {MIN_SCORE} 点")
    print(f"年齢上限: {MAX_AGE} 歳")
    print(f"{'='*70}\n")

    results = []
    send_count = 0
    skip_count = 0

    for idx, candidate in enumerate(candidates, start=1):
        name = candidate.get("name", "不明")
        print(f"[{idx}/{total}] 📊 {name} をスコアリング中...")

        # スコアリング実行
        score_result = score_candidate(candidate)

        # 結果を統合
        result = {
            "name": candidate.get("name", ""),
            "url": candidate.get("url", ""),
            "headline": candidate.get("headline", ""),
            "company": candidate.get("company", ""),
            "location": candidate.get("location", ""),
            "estimated_age": score_result["estimated_age"],
            "age_reasoning": score_result["age_reasoning"],
            "score": score_result["score"],
            "decision": score_result["decision"],
            "reason": score_result["reason"]
        }

        results.append(result)

        # 結果表示
        score = score_result["score"]
        decision = score_result["decision"]
        age = score_result["estimated_age"]

        if decision == "send":
            send_count += 1
            print(f"   ✅ スコア: {score}点 | 推定年齢: {age}歳 | 判定: 送信対象")
        else:
            skip_count += 1
            print(f"   ⚪ スコア: {score}点 | 推定年齢: {age}歳 | 判定: スキップ")

        print(f"   理由: {score_result['reason']}\n")

    # CSV保存（全候補者）
    print(f"\n{'='*70}")
    print(f"💾 スコアリング結果を保存中...")
    print(f"{'='*70}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "url", "headline", "company", "location",
                      "estimated_age", "age_reasoning", "score", "decision", "reason"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ 保存完了: {OUTPUT_FILE}")

    # 送信対象を抽出（スコア順でソート）
    send_targets = [r for r in results if r["decision"] == "send"]
    send_targets.sort(key=lambda x: x["score"], reverse=True)  # スコア降順

    # 上限件数まで絞り込み
    send_targets_limited = send_targets[:MAX_SEND_COUNT]

    # 送信対象リストを保存（メッセージ機能は削除）
    if send_targets_limited:
        with open(MESSAGES_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "url", "score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for target in send_targets_limited:
                writer.writerow({
                    "name": target["name"],
                    "url": target["url"],
                    "score": target["score"]
                })

        print(f"✅ 送信対象リストを保存: {MESSAGES_FILE}")

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 スコアリング完了サマリー")
    print(f"{'='*70}")
    print(f"総候補者数: {total} 件")
    print(f"✅ 送信対象: {len(send_targets)} 件（{MIN_SCORE}点以上）")
    if len(send_targets) > MAX_SEND_COUNT:
        print(f"   📌 今回送信: {len(send_targets_limited)} 件（上限: {MAX_SEND_COUNT}件）")
        print(f"   ⏭️  次回送信: {len(send_targets) - MAX_SEND_COUNT} 件")
    else:
        print(f"   📌 今回送信: {len(send_targets_limited)} 件")
    print(f"⚪ スキップ: {skip_count} 件")
    print(f"{'='*70}\n")

    if send_targets_limited:
        print(f"💡 次のステップ: python3 aiagent/linkedin_pipeline_improved.py で送信を実行")
    else:
        print(f"⚠️ 送信対象が0件です。検索条件を変更してみてください。")

    return len(send_targets_limited)

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    score_all_candidates()
