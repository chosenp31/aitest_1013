# aiagent/linkedin_scorer_v2.py
# OpenAI APIを使った詳細プロフィールのスコアリング（HR除外、年齢厳格化）

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
INPUT_FILE = os.path.join(DATA_DIR, "profile_details.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "candidates_scored_v2.csv")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages_v2.csv")

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# スコアリング基準
MIN_SCORE = int(os.getenv("MIN_SCORE", 60))
MAX_SEND_COUNT = int(os.getenv("MAX_SEND_COUNT", 50))  # テスト時は2

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
あなたはIT業界のリクルーターです。以下の候補者の詳細プロフィールを分析して、スコアリングしてください。

【候補者情報】
名前: {name}
ヘッドライン: {headline}
場所: {location}
職歴:
{experiences}

学歴:
{education}

スキル: {skills}

【評価基準】

1. 年齢評価（0-25点）
   - 学歴の卒業年から年齢を推定（大学卒業を22歳と仮定）
   - 計算式: 現在年齢 = 2025年 - 卒業年 + 22歳
   - 25-30歳: 25点
   - 31-35歳: 20点
   - 36-40歳: 15点
   - 41歳以上: **即座に除外（スコア0、decision: "skip"）**

2. IT業界経験評価（0-40点）
   - キーワード: SIer, ITコンサルタント, エンジニア, DXエンジニア, システム開発, クラウド, AI, データサイエンス
   - 現在のIT業界経験が3年以上: 40点
   - 現在のIT業界経験が1-3年: 30点
   - 過去にIT業界経験あり: 20点
   - IT業界経験なし: 0点

3. ポジション評価（-30 〜 +20点）
   - エンジニア・開発者: +20点
   - ITコンサルタント: +15点
   - プロジェクトマネージャー: +10点
   - 以下は**即座に除外（スコア0、decision: "skip"）**:
     - 経営層: 社長, CEO, CIO, CTO, CFO, 代表取締役, 執行役員, 取締役
     - HR・人材関係: 人材紹介, 人材派遣, リクルーター, 採用担当, ヘッドハンター, キャリアアドバイザー, 人事コンサルタント

4. その他の除外条件（即座にスコア0、decision: "skip"）
   - 学生（在学中）
   - IT業界と無関係（飲食、販売、製造、小売など）
   - 現在以下の企業に勤務している者:
     * フューチャー株式会社
     * フューチャーアーキテクト株式会社

【出力形式】
以下のJSON形式で出力してください。他の説明は一切不要です。

{{
  "estimated_age": 推定年齢（数値、不明な場合はnull）,
  "age_reasoning": "年齢推定の根拠",
  "age_score": 年齢スコア（0-25）,
  "it_experience_score": IT経験スコア（0-40）,
  "position_score": ポジションスコア（-30 〜 +20）,
  "total_score": 合計スコア（age_score + it_experience_score + position_score）,
  "decision": "send" または "skip",
  "reason": "スコアリングの理由（簡潔に1-2文）"
}}

【重要な注意事項】
- 41歳以上は必ず除外（decision: "skip"、total_score: 0）
- 経営層（社長、CEO、取締役等）は必ず除外（decision: "skip"、total_score: 0）
- HR・人材関係（リクルーター、採用担当等）は必ず除外（decision: "skip"、total_score: 0）
- 合計スコアが60点以上の場合は "send"、それ未満は "skip"
"""

# ==============================
# 候補者スコアリング
# ==============================
def score_candidate(candidate):
    """OpenAI APIで候補者をスコアリング"""

    name = candidate.get("name", "不明")
    headline = candidate.get("headline", "情報なし")
    location = candidate.get("location", "情報なし")
    experiences = candidate.get("experiences", "情報なし")
    education = candidate.get("education", "情報なし")
    skills = candidate.get("skills", "情報なし")

    # プロンプト生成
    prompt = SCORING_PROMPT.format(
        name=name,
        headline=headline,
        location=location,
        experiences=experiences,
        education=education,
        skills=skills
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
            max_tokens=400
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
            "age_score": result.get("age_score", 0),
            "it_experience_score": result.get("it_experience_score", 0),
            "position_score": result.get("position_score", 0),
            "total_score": result.get("total_score", 0),
            "decision": result.get("decision", "skip"),
            "reason": result.get("reason", "")
        }

    except json.JSONDecodeError as e:
        print(f"⚠️ JSON解析エラー ({name}): {e}")
        print(f"   レスポンス: {content}")
        return {
            "estimated_age": None,
            "age_reasoning": "解析エラー",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": "AIレスポンスの解析に失敗"
        }
    except Exception as e:
        print(f"⚠️ APIエラー ({name}): {e}")
        return {
            "estimated_age": None,
            "age_reasoning": "エラー",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": f"APIエラー: {str(e)}"
        }

# ==============================
# メイン処理
# ==============================
def score_all_candidates():
    """全候補者をスコアリング"""

    if not os.path.exists(INPUT_FILE):
        print(f"❌ エラー: プロフィール詳細ファイルが見つかりません: {INPUT_FILE}")
        print(f"💡 先に linkedin_get_profiles.py を実行してください")
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
    print(f"🧠 AIスコアリング開始（詳細プロフィール版）")
    print(f"{'='*70}")
    print(f"候補者数: {total} 件")
    print(f"使用モデル: {OPENAI_MODEL}")
    print(f"最低スコア: {MIN_SCORE} 点")
    print(f"除外条件: 41歳以上、経営層、HR職種")
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
            "profile_url": candidate.get("profile_url", ""),
            "headline": candidate.get("headline", ""),
            "location": candidate.get("location", ""),
            "estimated_age": score_result["estimated_age"],
            "age_reasoning": score_result["age_reasoning"],
            "age_score": score_result["age_score"],
            "it_experience_score": score_result["it_experience_score"],
            "position_score": score_result["position_score"],
            "total_score": score_result["total_score"],
            "decision": score_result["decision"],
            "reason": score_result["reason"]
        }

        results.append(result)

        # 結果表示
        total_score = score_result["total_score"]
        decision = score_result["decision"]
        age = score_result["estimated_age"]

        if decision == "send":
            send_count += 1
            print(f"   ✅ スコア: {total_score}点 (年齢{score_result['age_score']} + IT{score_result['it_experience_score']} + 役職{score_result['position_score']}) | 推定年齢: {age}歳 | 判定: 送信対象")
        else:
            skip_count += 1
            print(f"   ⚪ スコア: {total_score}点 | 推定年齢: {age}歳 | 判定: スキップ")

        print(f"   理由: {score_result['reason']}\n")

    # CSV保存（全候補者）
    print(f"\n{'='*70}")
    print(f"💾 スコアリング結果を保存中...")
    print(f"{'='*70}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "profile_url", "headline", "location",
                      "estimated_age", "age_reasoning", "age_score",
                      "it_experience_score", "position_score", "total_score",
                      "decision", "reason"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ 保存完了: {OUTPUT_FILE}")

    # 送信対象を抽出（スコア順でソート）
    send_targets = [r for r in results if r["decision"] == "send"]
    send_targets.sort(key=lambda x: x["total_score"], reverse=True)  # スコア降順

    # 上限件数まで絞り込み
    send_targets_limited = send_targets[:MAX_SEND_COUNT]

    # 送信対象リストを保存
    if send_targets_limited:
        with open(MESSAGES_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "profile_url", "total_score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for target in send_targets_limited:
                writer.writerow({
                    "name": target["name"],
                    "profile_url": target["profile_url"],
                    "total_score": target["total_score"]
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
        print(f"💡 次のステップ: python3 aiagent/linkedin_send_messages.py でメッセージを送信")
    else:
        print(f"⚠️ 送信対象が0件です。")

    return len(send_targets_limited)

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    score_all_candidates()
