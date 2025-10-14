# aiagent/analyzer.py
import os
import csv
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data")
RAW_PATH = os.path.join(DATA_PATH, "candidates_raw.csv")
SCORED_PATH = os.path.join(DATA_PATH, "candidates_scored.csv")


def ai_estimate_score(candidate: dict) -> dict:
    """
    ChatGPTを使って候補者の総合スコア（0〜10）と判定（send/skip）を算出。
    """
    name = candidate.get("name", "")
    role = candidate.get("role", "")
    company = candidate.get("company", "")
    location = candidate.get("location", "")
    education = candidate.get("education", "")
    exp_years = candidate.get("experience_years", "")
    profile_url = candidate.get("profile_url", "")

    # ChatGPTに与える指示文
    prompt = f"""
    以下の人物がLinkedInでリファラル採用の対象として適切かを10点満点で評価してください。

    [条件]
    - 年齢：40歳以下が望ましい（学歴・経歴年数から推定）
    - 職種：ITコンサル、SIer、システムエンジニア、データアナリストなどを優先
    - 地域：「Japan」「Tokyo」などを含む場合は高評価
    - 役職：CEO, CFO, COO, Partner, Director など上位職なら低評価
    - その他：コンサルティング/システム開発系の経験があれば高評価

    [出力フォーマット（JSONのみ）]
    {{
      "score": <0〜10の数値>,
      "decision": "send" または "skip",
      "reason": "<簡潔な理由>"
    }}

    [入力データ]
    名前: {name}
    職種: {role}
    会社: {company}
    地域: {location}
    学歴: {education}
    経験年数: {exp_years}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        result_text = response.choices[0].message.content.strip()

        # JSON抽出（例: {"score": 8.2, "decision": "send", "reason": "〜"})
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if match:
            import json
            result = json.loads(match.group())
        else:
            result = {"score": 0, "decision": "skip", "reason": "解析失敗"}

        candidate.update(result)
        return candidate

    except Exception as e:
        print(f"❌ {name} のスコアリング中にエラー: {e}")
        candidate.update({"score": 0, "decision": "skip", "reason": "例外発生"})
        return candidate


def analyze_candidates(input_csv: str = RAW_PATH, output_csv: str = SCORED_PATH) -> list:
    """
    CSVを読み込み、AIでスコアリングして結果を保存。
    戻り値として送信対象（decision=send）のみ返す。
    """
    if not os.path.exists(input_csv):
        print(f"⚠️ 入力ファイルが見つかりません: {input_csv}")
        return []

    os.makedirs(DATA_PATH, exist_ok=True)

    with open(input_csv, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        candidates = [row for row in reader]

    print(f"📊 候補者数: {len(candidates)} 件 → AIスコアリング開始...")

    results = []
    for i, c in enumerate(candidates, start=1):
        print(f"🔹 [{i}/{len(candidates)}] {c.get('name')} を評価中...")
        scored = ai_estimate_score(c)
        results.append(scored)

    # 保存
    with open(output_csv, "w", newline='', encoding="utf-8") as f:
        fieldnames = ["name", "role", "company", "location", "education", "experience_years", "score", "decision", "reason", "profile_url"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    send_list = [r for r in results if r.get("decision") == "send"]
    print(f"✅ スコアリング完了: {len(send_list)} 件を送信対象として抽出しました。")
    return send_list


# --- スクリプトとして直接実行された場合 ---
if __name__ == "__main__":
    # ダミーデータでテスト
    os.makedirs(DATA_PATH, exist_ok=True)
    test_csv = os.path.join(DATA_PATH, "candidates_raw.csv")
    if not os.path.exists(test_csv):
        with open(test_csv, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "role", "company", "location", "education", "experience_years", "profile_url"])
            writer.writerow(["佐藤花子", "ITコンサルタント", "KPMG", "Tokyo", "早稲田大学", "8", "https://www.linkedin.com/in/sample1"])
            writer.writerow(["鈴木一郎", "CEO", "ABC Corp", "Japan", "慶應義塾大学", "20", "https://www.linkedin.com/in/sample2"])

    send_targets = analyze_candidates()
    print("\n🎯 送信対象:")
    for t in send_targets:
        print(f"- {t['name']} ({t['score']}点): {t['decision']}")
