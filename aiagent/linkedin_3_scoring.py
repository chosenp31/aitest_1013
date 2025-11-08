# aiagent/linkedin_3_scoring.py
# スコアリングのみ（OpenAI APIで候補者を評価）
# profiles_master.csv で統合管理

import os
import csv
import json
import random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# アカウント名の定義
AVAILABLE_ACCOUNTS = ["依田", "桜井", "田中"]

def select_account():
    """アカウントを選択"""
    print(f"\n{'='*70}")
    print(f"📋 使用するLinkedInアカウントを選択")
    print(f"{'='*70}")
    for idx, account in enumerate(AVAILABLE_ACCOUNTS, start=1):
        print(f"{idx}. {account}")
    print(f"{'='*70}\n")

    while True:
        choice = input(f"アカウント番号を入力 (1-{len(AVAILABLE_ACCOUNTS)}): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_ACCOUNTS):
                selected = AVAILABLE_ACCOUNTS[choice_num - 1]
                print(f"\n✅ 選択: {selected}\n")
                return selected
            else:
                print(f"⚠️ 1-{len(AVAILABLE_ACCOUNTS)}の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

def get_account_paths(account_name):
    """アカウント毎のディレクトリとファイルパスを取得"""
    account_dir = os.path.join(BASE_DIR, "data", account_name)
    os.makedirs(account_dir, exist_ok=True)

    return {
        'account_dir': account_dir,
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'profiles_file': os.path.join(account_dir, "profiles_detailed.csv")
    }

# スコアリングプロンプト
SCORING_PROMPT = """
あなたはIT業界のリクルーターです。以下の候補者の詳細プロフィールを分析して、スコアリングしてください。

【候補者情報】
名前: {name}
ヘッドライン: {headline}
場所: {location}
LinkedIn Premium会員: {is_premium}
職歴:
{experiences}

学歴:
{education}

スキル: {skills}

【重要：最初に除外条件をチェック】
以下の条件に1つでも該当する場合は、スコアリングを行わず即座に除外してください：

1. **LinkedIn Premium会員の除外（最優先）**
   - is_premium が "True" または "yes" の場合 → 即座に除外
   - decision: "skip", total_score: 0, exclusion_reason: "Premium会員のため"

2. **人材関係者の除外（最優先）**
   - ヘッドラインまたは職歴に以下のキーワードが含まれる場合 → 即座に除外
   - キーワード例：
     * 採用系: 「採用」「リクルーター」「リクルート」「新卒採用」「中途採用」「エンジニア採用」「採用担当」「採用立ち上げ」
     * 転職・人材系: 「転職」「人材紹介」「人材派遣」「人材コンサルタント」「人材サービス」
     * 人事系: 「人事」「HR」「Human Resources」「人事コンサルタント」
     * その他: 「ヘッドハンター」「ヘッドハンティング」「キャリアアドバイザー」「キャリアコンサルタント」「Talent Acquisition」「TA」「スカウト」「RPO」「就活」「就職支援」
   - 人材系企業：リクルート、パーソル、マイナビ、エン・ジャパン、ビズリーチ、doda、パソナ、ランスタッド、アデコなど
   - decision: "skip", total_score: 0, exclusion_reason: "人材関係者のため"

3. **経営層の除外**
   - ヘッドラインまたは職歴に以下の役職が含まれる場合 → 即座に除外
   - CXO系：CEO、CTO、CIO、CFO、COO、CMO、CPO、CHRO、CSO
   - 役員系：社長、会長、副社長、代表取締役、取締役、執行役員、常務、専務、監査役
   - 創業者系：Founder、Co-founder、創業者、共同創業者
   - decision: "skip", total_score: 0, exclusion_reason: "経営層のため"

4. **41歳以上の除外**
   - 学歴から推定した年齢が41歳以上 → 即座に除外
   - decision: "skip", total_score: 0, exclusion_reason: "41歳以上のため"

5. **KPMG・フューチャー在籍者の除外**
   - 職歴に「KPMG」または「フューチャー」を含む企業名がある場合 → 即座に除外
   - decision: "skip", total_score: 0, exclusion_reason: "KPMG在籍のため" または "フューチャー在籍のため"

【具体例】
例1: ヘッドライン「株式会社ヤプリ←ディップ株式会社|新卒採用|中途採用|エンジニア採用|採用立ち上げ」
→ 「採用」が含まれるため、人材関係者として即座に除外

例2: is_premium = "True"
→ Premium会員として即座に除外

例3: 職歴に「KPMG税理士法人」が含まれる
→ KPMG在籍者として即座に除外

例4: 職歴に「代表取締役CEO @ ドビー・アンド株式会社」が含まれる
→ 「CEO」が含まれるため、経営層として即座に除外

例5: 職歴に「リクルートキャリア」が含まれる
→ 人材系企業のため、人材関係者として即座に除外

【評価基準（除外されなかった場合のみ）】

1. 年齢評価（0-30点）
   - 学歴の卒業年から年齢を推定（大学卒業を22歳と仮定）
   - 計算式: 現在年齢 = 2025年 - 卒業年 + 22歳
   - 22-40歳: 30点（一律）
   - 年齢不明の場合: 30点（年齢で不利にならないよう配慮）

2. IT業界経験評価（0-50点）
   - キーワード: SIer, ITコンサルタント, エンジニア, DXエンジニア, システム開発, クラウド, AI, データサイエンス
   - 現在のIT業界経験が3年以上: 50点
   - 現在のIT業界経験が1-3年: 30点
   - 過去にIT業界経験あり: 30点
   - IT業界経験なし: 0点

3. ポジション評価（0-30点）
   - エンジニア・開発者: 30点
   - ITコンサルタント: 30点
   - プロジェクトマネージャー（PM）: 30点
   - PMO: 30点
   - SIer: 30点
   - システムエンジニア（SE）: 30点

【出力形式】
以下のJSON形式で出力してください。他の説明は一切不要です。

{{
  "estimated_age": 推定年齢（数値、不明な場合はnull）,
  "age_reasoning": "年齢推定の根拠",
  "age_score": 年齢スコア（0-30、年齢不明の場合も30点）,
  "it_experience_score": IT経験スコア（0-50）,
  "position_score": ポジションスコア（0-30）,
  "total_score": 合計スコア（age_score + it_experience_score + position_score を正確に計算すること）,
  "decision": "send" または "skip",
  "reason": "スコアリングの理由（簡潔に1-2文）",
  "exclusion_reason": "除外理由（skipの場合のみ、1言で記載。例: Premium会員のため、人材関係者のため、経営層のため、41歳以上のため、KPMG在籍のため、フューチャー在籍のため、IT業界経験不足のため）"
}}

【重要：合計スコアの計算について】
- total_score は必ず age_score + it_experience_score + position_score の正確な合計値にすること
- 例: age_score=30, it_experience_score=0, position_score=0 の場合 → total_score=30（60ではない）

【最終チェック】
- 除外条件に該当する場合は、必ず decision: "skip", total_score: 0 にすること
- 合計スコアが60点以上で除外条件に該当しない場合のみ "send"
- それ未満は "skip"（exclusion_reason: "IT業界経験不足のため"）
- sendの場合は exclusion_reason に空文字 "" を設定
"""

# OpenAIクライアント
if not OPENAI_API_KEY:
    print("❌ エラー: OPENAI_API_KEYが設定されていません")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# profiles_master.csv 管理
# ==============================
def load_profiles_master(profiles_master_file):
    """profiles_master.csv を読み込む"""
    profiles_master = {}

    if os.path.exists(profiles_master_file):
        try:
            with open(profiles_master_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    profile_url = row.get('profile_url', '')
                    if profile_url:
                        profiles_master[profile_url] = row
        except Exception as e:
            print(f"⚠️ profiles_master.csv 読み込みエラー: {e}\n")

    return profiles_master

def save_profiles_master(profiles_master, profiles_master_file):
    """profiles_master.csv を保存"""
    fieldnames = [
        "profile_url", "name", "connected_date",
        "profile_fetched", "profile_fetched_at",
        "total_score", "scoring_decision", "exclusion_reason",
        "message_generated", "message_generated_at",
        "message_sent_status", "message_sent_at", "last_send_error"
    ]

    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # profile_url でソート
        sorted_profiles = sorted(profiles_master.values(), key=lambda x: x.get('profile_url', ''))
        writer.writerows(sorted_profiles)

def update_profile_master(profiles_master, profile_url, updates):
    """profiles_master の特定エントリを更新"""
    if profile_url not in profiles_master:
        profiles_master[profile_url] = {
            "profile_url": profile_url,
            "name": "",
            "connected_date": "",
            "profile_fetched": "no",
            "profile_fetched_at": "",
            "total_score": "",
            "scoring_decision": "",
            "exclusion_reason": "",
            "message_generated": "no",
            "message_generated_at": "",
            "message_sent_status": "pending",
            "message_sent_at": "",
            "last_send_error": ""
        }

    profiles_master[profile_url].update(updates)

# ==============================
# スコアリング
# ==============================
def score_candidate(candidate):
    """OpenAI APIで候補者をスコアリング"""

    name = candidate.get("name", "不明")
    headline = candidate.get("headline", "情報なし")
    location = candidate.get("location", "情報なし")
    is_premium = candidate.get("is_premium", False)
    is_premium_str = "yes" if str(is_premium).lower() in ['true', 'yes', '1'] else "no"
    experiences = candidate.get("experiences", "情報なし")
    education = candidate.get("education", "情報なし")
    skills = candidate.get("skills", "情報なし")

    prompt = SCORING_PROMPT.format(
        name=name,
        headline=headline,
        location=location,
        is_premium=is_premium_str,
        experiences=experiences,
        education=education,
        skills=skills
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはIT業界のリクルーターです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()

        # JSONを抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(result_text)

        return result

    except Exception as e:
        print(f"   ⚠️ APIエラー ({name}): {e}")
        return {
            "estimated_age": None,
            "age_reasoning": "",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": f"APIエラー: {e}",
            "exclusion_reason": "APIエラー"
        }

def validate_and_enforce_exclusion(candidate, scoring_result):
    """
    Python側でスコアリング結果を検証し、除外条件に該当する場合は強制的に除外する

    Args:
        candidate: 候補者情報
        scoring_result: OpenAI APIからのスコアリング結果

    Returns:
        検証後のスコアリング結果（必要に応じて上書き）
    """
    name = candidate.get("name", "不明")
    headline = candidate.get("headline", "").lower()
    experiences = candidate.get("experiences", "").lower()
    is_premium = candidate.get("is_premium", False)
    is_premium_bool = str(is_premium).lower() in ['true', 'yes', '1']

    # 1. Premium会員チェック
    if is_premium_bool:
        return {
            "estimated_age": None,
            "age_reasoning": "",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": "LinkedIn Premium会員のため除外",
            "exclusion_reason": "Premium会員のため"
        }

    # 2. 人材関係キーワードチェック
    hr_keywords = [
        # 採用系
        '採用', 'リクルーター', 'リクルート', '新卒採用', '中途採用', 'エンジニア採用', '採用担当', '採用立ち上げ',
        # 転職・人材系
        '転職', '人材紹介', '人材派遣', '人材コンサルタント', '人材サービス',
        # 人事系
        '人事', 'hr', 'human resources', '人事コンサルタント',
        # その他
        'ヘッドハンター', 'ヘッドハンティング', 'キャリアアドバイザー', 'キャリアコンサルタント',
        'talent acquisition', 'スカウト', 'rpo', '就活', '就職支援'
    ]

    # 単語境界を考慮すべき短いキーワード（誤検出を防ぐため）
    short_keywords_with_boundary = [
        'ta',  # "data"などに誤検出しないよう単語境界を考慮
    ]

    text_to_check = headline + " " + experiences

    # 通常のキーワードチェック
    for keyword in hr_keywords:
        if keyword in text_to_check:
            return {
                "estimated_age": scoring_result.get("estimated_age"),
                "age_reasoning": scoring_result.get("age_reasoning", ""),
                "age_score": 0,
                "it_experience_score": 0,
                "position_score": 0,
                "total_score": 0,
                "decision": "skip",
                "reason": f"人材関係キーワード「{keyword}」が検出されたため除外",
                "exclusion_reason": "人材関係者のため"
            }

    # 単語境界を考慮したキーワードチェック（正規表現使用）
    import re
    for keyword in short_keywords_with_boundary:
        # \b は単語境界を表す
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, text_to_check, re.IGNORECASE):
            return {
                "estimated_age": scoring_result.get("estimated_age"),
                "age_reasoning": scoring_result.get("age_reasoning", ""),
                "age_score": 0,
                "it_experience_score": 0,
                "position_score": 0,
                "total_score": 0,
                "decision": "skip",
                "reason": f"人材関係キーワード「{keyword}」が検出されたため除外",
                "exclusion_reason": "人材関係者のため"
            }

    # 3. CXO系・経営層チェック
    executive_keywords = [
        # CXO系
        'ceo', 'cto', 'cio', 'cfo', 'coo', 'cmo', 'cpo', 'chro', 'cso',
        # 役員系
        '代表取締役', '取締役', '執行役員', '常務', '専務', '監査役',
        # 創業者系
        'founder', 'co-founder', '創業者', '共同創業者',
        # その他
        '社長', '会長', '副社長'
    ]

    for keyword in executive_keywords:
        if keyword in text_to_check:
            return {
                "estimated_age": scoring_result.get("estimated_age"),
                "age_reasoning": scoring_result.get("age_reasoning", ""),
                "age_score": 0,
                "it_experience_score": 0,
                "position_score": 0,
                "total_score": 0,
                "decision": "skip",
                "reason": f"役職「{keyword}」が検出されたため除外",
                "exclusion_reason": "経営層のため"
            }

    # 4. 人材系企業チェック
    hr_companies = [
        # リクルート系
        'リクルート', 'リクルートホールディングス', 'リクルートキャリア', 'リクルートスタッフィング', 'リクルートジョブズ',
        'recruit', 'recruit holdings', 'recruit career',
        # パーソル系
        'パーソル', 'パーソルキャリア', 'パーソルテンプスタッフ', 'パーソルプロセス&テクノロジー', 'インテリジェンス',
        'persol', 'persol career', 'tempstaff', 'intelligence',
        # マイナビ系
        'マイナビ', 'mynavi',
        # エン・ジャパン系
        'エン・ジャパン', 'エン転職', 'en japan',
        # その他大手
        'ビズリーチ', 'bizreach', 'type', 'キャリアデザインセンター',
        'doda', 'ジェイエイシーリクルートメント', 'jac recruitment',
        'パソナ', 'pasona', 'ランスタッド', 'randstad',
        'アデコ', 'adecco', 'マンパワー', 'manpower',
        # 社名キーワード
        '人材', '採用支援', '転職支援', 'キャリア支援', '人事コンサル'
    ]

    for company in hr_companies:
        if company in text_to_check:
            return {
                "estimated_age": scoring_result.get("estimated_age"),
                "age_reasoning": scoring_result.get("age_reasoning", ""),
                "age_score": 0,
                "it_experience_score": 0,
                "position_score": 0,
                "total_score": 0,
                "decision": "skip",
                "reason": f"人材系企業「{company}」が検出されたため除外",
                "exclusion_reason": "人材関係者のため"
            }

    # 5. KPMG・フューチャー在籍者チェック
    kpmg_future_keywords = [
        'kpmg', 'フューチャー', 'future corporation', 'future architect', 'フューチャーアーキテクト'
    ]

    for keyword in kpmg_future_keywords:
        if keyword in text_to_check:
            # KPMGかフューチャーかを判定
            if 'kpmg' in keyword.lower():
                exclusion_msg = "KPMG在籍のため"
            else:
                exclusion_msg = "フューチャー在籍のため"

            return {
                "estimated_age": scoring_result.get("estimated_age"),
                "age_reasoning": scoring_result.get("age_reasoning", ""),
                "age_score": 0,
                "it_experience_score": 0,
                "position_score": 0,
                "total_score": 0,
                "decision": "skip",
                "reason": f"企業「{keyword}」が検出されたため除外",
                "exclusion_reason": exclusion_msg
            }

    # 6. 41歳以上チェック
    estimated_age = scoring_result.get("estimated_age")
    if estimated_age and estimated_age >= 41:
        return {
            "estimated_age": estimated_age,
            "age_reasoning": scoring_result.get("age_reasoning", ""),
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": f"推定年齢{estimated_age}歳（41歳以上）のため除外",
            "exclusion_reason": "41歳以上のため"
        }

    # 7. 合計スコアの再計算（OpenAIの計算ミスを修正）
    age_score = scoring_result.get("age_score", 0)
    it_experience_score = scoring_result.get("it_experience_score", 0)
    position_score = scoring_result.get("position_score", 0)

    # 除外条件に該当する場合（Premium会員、人材関係、経営層、41歳以上、KPMG等）
    decision = scoring_result.get("decision", "skip")
    exclusion_reason = scoring_result.get("exclusion_reason", "")

    if decision == "skip" and exclusion_reason and exclusion_reason != "IT業界経験不足のため":
        # 明確な除外理由がある場合は total_score = 0
        scoring_result["total_score"] = 0
    else:
        # それ以外は正確な合計値を計算
        correct_total = age_score + it_experience_score + position_score
        scoring_result["total_score"] = correct_total

        # 60点未満の場合はskipに変更
        if correct_total < 60:
            scoring_result["decision"] = "skip"
            scoring_result["exclusion_reason"] = "IT業界経験不足のため"
        else:
            scoring_result["decision"] = "send"
            scoring_result["exclusion_reason"] = ""

    # 検証済みの結果を返す
    return scoring_result

# ==============================
# メイン処理
# ==============================
def main(account_name, paths, use_scoring, min_score):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn スコアリング")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    try:
        # profiles_master.csv 読み込み
        print(f"{'='*70}")
        print(f"📂 profiles_master.csv 読み込み")
        print(f"{'='*70}\n")

        profiles_master = load_profiles_master(paths['profiles_master_file'])
        print(f"✅ 既存レコード: {len(profiles_master)} 件\n")

        # スコアリング
        if use_scoring:
            profiles_to_score = []

            # profiles_detailed.csv から詳細情報を読み込み
            profile_details_map = {}
            if os.path.exists(paths['profiles_file']):
                with open(paths['profiles_file'], "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profile_details_map[row['profile_url']] = row

            for profile_url, profile in profiles_master.items():
                # 送信済みの人はスコアリング不要
                if (profile.get('profile_fetched') == 'yes' and
                    not profile.get('scoring_decision') and
                    profile.get('message_sent_status') != 'success'):
                    if profile_url in profile_details_map:
                        detail = profile_details_map[profile_url]
                        profiles_to_score.append({
                            'profile_url': profile_url,
                            'name': profile['name'],
                            'headline': detail.get('headline', ''),
                            'location': detail.get('location', ''),
                            'is_premium': detail.get('is_premium', False),
                            'experiences': detail.get('experiences', ''),
                            'education': detail.get('education', ''),
                            'skills': detail.get('skills', '')
                        })

            if profiles_to_score:
                print(f"{'='*70}")
                print(f"📊 スコアリング実行")
                print(f"{'='*70}")
                print(f"対象者数: {len(profiles_to_score)} 件")
                print(f"最低スコア: {min_score} 点")
                print(f"{'='*70}\n")

                for idx, candidate in enumerate(profiles_to_score, start=1):
                    name = candidate['name']
                    profile_url = candidate['profile_url']

                    print(f"[{idx}/{len(profiles_to_score)}] 📊 {name} をスコアリング中...")

                    # プロフィール情報を表示
                    headline = candidate.get('headline', '情報なし')
                    location = candidate.get('location', '情報なし')
                    is_premium = candidate.get('is_premium', False)
                    is_premium_str = "Premium会員" if str(is_premium).lower() in ['true', 'yes', '1'] else "通常会員"
                    experiences = candidate.get('experiences', '')
                    education = candidate.get('education', '')

                    print(f"   📝 プロフィール情報:")
                    print(f"      ・ヘッドライン: {headline}")
                    print(f"      ・場所: {location}")
                    print(f"      ・LinkedIn: {is_premium_str}")

                    # 職歴（最初の2件のみ表示）
                    if experiences and experiences != '情報なし':
                        exp_lines = [line.strip() for line in experiences.split('\n') if line.strip()]
                        print(f"      ・職歴:")
                        for exp in exp_lines[:2]:
                            print(f"         - {exp}")
                        if len(exp_lines) > 2:
                            print(f"         - ... 他{len(exp_lines)-2}件")

                    # 学歴（最初の1件のみ表示）
                    if education and education != '情報なし':
                        edu_lines = [line.strip() for line in education.split('\n') if line.strip()]
                        if edu_lines:
                            print(f"      ・学歴: {edu_lines[0]}")
                            if len(edu_lines) > 1:
                                print(f"               ... 他{len(edu_lines)-1}件")
                    print()

                    # OpenAI APIでスコアリング
                    scored = score_candidate(candidate)

                    # Python側で除外条件を強制チェック（二重チェック）
                    scored = validate_and_enforce_exclusion(candidate, scored)

                    decision = scored.get('decision', 'skip')
                    total_score = scored.get('total_score', 0)
                    reason = scored.get('reason', '')
                    exclusion_reason = scored.get('exclusion_reason', '')
                    age_score = scored.get('age_score', 0)
                    it_experience_score = scored.get('it_experience_score', 0)
                    position_score = scored.get('position_score', 0)
                    estimated_age = scored.get('estimated_age', None)

                    if decision == "send":
                        print(f"   ✅ 送信対象: {total_score}点")
                    else:
                        print(f"   ⚪ スキップ: {total_score}点")
                        if exclusion_reason:
                            print(f"   除外理由: {exclusion_reason}")

                    # スコア内訳を表示
                    print(f"   📊 内訳: 年齢{age_score}点 + IT経験{it_experience_score}点 + ポジション{position_score}点 = {total_score}点")
                    if estimated_age:
                        print(f"   👤 推定年齢: {estimated_age}歳")
                    print(f"   理由: {reason}\n")

                    # profiles_master 更新（skipの場合はスコアを"-"にする）
                    update_profile_master(profiles_master, profile_url, {
                        'total_score': str(total_score) if decision == "send" else "-",
                        'scoring_decision': decision,
                        'exclusion_reason': exclusion_reason
                    })

                    import time
                    time.sleep(random.uniform(1, 2))

                save_profiles_master(profiles_master, paths['profiles_master_file'])
                print(f"💾 profiles_master.csv 更新完了\n")
            else:
                print("✅ すべてスコアリング済みです\n")
        else:
            # スコアリングなし: 全員を send に
            print(f"{'='*70}")
            print(f"⚠️  スコアリングをスキップ（全員に送信）")
            print(f"{'='*70}\n")

            for profile_url, profile in profiles_master.items():
                if profile.get('profile_fetched') == 'yes' and not profile.get('scoring_decision'):
                    update_profile_master(profiles_master, profile_url, {
                        'total_score': '0',
                        'scoring_decision': 'send'
                    })

            save_profiles_master(profiles_master, paths['profiles_master_file'])
            print(f"✅ 全員を送信対象に設定しました\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 スコアリング完了")
        print(f"{'='*70}")
        print(f"終了日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn スコアリング")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

    # スコアリング条件
    print("【スコアリング条件】")
    use_scoring_input = input("スコアリング条件を使用しますか？ (yes=使用, no=全員に送信, Enter=デフォルト「yes」): ").strip().lower()
    if use_scoring_input == 'no':
        use_scoring = False
        min_score = 0  # スコアリングしない場合は0
        print("⚠️ スコアリングをスキップします（全員に送信）")
    else:
        use_scoring = True
        # 最低スコア
        print("\n【最低スコア】")
        while True:
            min_score_input = input("最低スコアを入力 (Enter=デフォルト「60」): ").strip()
            if not min_score_input:
                min_score = 60
                break
            try:
                min_score = int(min_score_input)
                if min_score >= 0:
                    break
                else:
                    print("⚠️ 0以上の数値を入力してください")
            except ValueError:
                print("⚠️ 数値を入力してください")

    # 設定内容を確認
    print(f"\n{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"スコアリング条件: {'使用する' if use_scoring else '使用しない（全員に送信）'}")
    if use_scoring:
        print(f"最低スコア: {min_score}点")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, use_scoring, min_score)
