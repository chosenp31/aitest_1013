# aiagent/linkedin_prepare_messages.py
# プロフィール取得 → スコアリング → メッセージ生成 → CSV保存
# profiles_master.csv で統合管理

import os
import sys
import time
import csv
import json
import pickle
import random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==============================
# 人間らしい挙動のためのヘルパー関数
# ==============================
def human_sleep(min_sec, max_sec):
    """人間らしいランダムな待機時間"""
    wait_time = random.uniform(min_sec, max_sec)
    time.sleep(wait_time)

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
        'cookie_file': os.path.join(account_dir, "linkedin_cookies.pkl"),
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'profiles_file': os.path.join(account_dir, "profiles_detailed.csv"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv")
    }

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# メッセージテンプレート（アカウント別）
MESSAGE_TEMPLATES = {
    "依田": """{name}さん

突然のご連絡失礼いたします。
KPMGコンサルティングの依田と申します🙇‍♂️

異なるバックグラウンドを持つ方々との情報交換の機会を探しており、
もしよろしければ、お互いのキャリアや業界の話をざっくばらんにお話しできればと思いご連絡させていただきました。

私からは以下のようなトピックをお話しできるかと思います。
・KPMG/フューチャーアーキテクトでのプロジェクト経験
デジタル戦略におけるロードマップ策定、AX人材確保計画策定、IoTシステム導入計画策定・実行支援、基幹システム刷新におけるPMOなど
・転職時に検討したBIG4、アクセンチュアの比較や選考情報

ご興味があれば、30分程度のオンラインでのカジュアルな
お話の機会をいただけますと嬉しいです！
よろしくお願いいたします🙇‍♂️""",

    "桜井": """{name}さん

桜井と申します。

よろしくお願いいたします。""",

    "田中": """{name}さん

田中と申します。

よろしくお願いいたします。"""
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

【評価基準】

1. 年齢評価（0-30点）
   - 学歴の卒業年から年齢を推定（大学卒業を22歳と仮定）
   - 計算式: 現在年齢 = 2025年 - 卒業年 + 22歳
   - 22-40歳: 30点（一律）
   - 41歳以上: **即座に除外（スコア0、decision: "skip"）**
   - **年齢不明の場合: 除外せず、年齢スコア0点として扱う（他の項目でスコアリング）**

2. IT業界経験評価（0-35点）
   - キーワード: SIer, ITコンサルタント, エンジニア, DXエンジニア, システム開発, クラウド, AI, データサイエンス
   - 現在のIT業界経験が3年以上: 35点
   - 現在のIT業界経験が1-3年: 25点
   - 過去にIT業界経験あり: 15点
   - IT業界経験なし: 0点

3. ポジション評価（-30 〜 +20点）
   - エンジニア・開発者: +20点
   - ITコンサルタント: +20点
   - プロジェクトマネージャー: +20点
   - 以下は**即座に除外（スコア0、decision: "skip"）**:
     - 経営層: 社長, CEO, CIO, CTO, CFO, 代表取締役, 執行役員, 取締役
     - HR・人材関係: 人材紹介, 人材派遣, リクルーター, 採用担当, ヘッドハンター, キャリアアドバイザー, 人事コンサルタント

4. その他の除外条件（即座にスコア0、decision: "skip"）
   - LinkedIn Premium会員（is_premium: "True"または"yes"の場合）
   - 学生（在学中）
   - IT業界と無関係（飲食、販売、製造、小売など）
   - これまでの職歴に以下の企業名が含まれる者（現在・過去問わず）:
     * 「フューチャー」を含む企業（フューチャー株式会社、フューチャーアーキテクト株式会社など）
     * 「KPMG」を含む企業（KPMGコンサルティング、KPMG税理士法人など）

【出力形式】
以下のJSON形式で出力してください。他の説明は一切不要です。

{{
  "estimated_age": 推定年齢（数値、不明な場合はnull）,
  "age_reasoning": "年齢推定の根拠",
  "age_score": 年齢スコア（0-30）,
  "it_experience_score": IT経験スコア（0-35）,
  "position_score": ポジションスコア（-30 〜 +35）,
  "total_score": 合計スコア（age_score + it_experience_score + position_score）,
  "decision": "send" または "skip",
  "reason": "スコアリングの理由（簡潔に1-2文）"
}}

【重要な注意事項】
- LinkedIn Premium会員（is_premium: "True"または"yes"）は必ず除外（decision: "skip"、total_score: 0）
- 41歳以上は必ず除外（decision: "skip"、total_score: 0）
- 経営層（社長、CEO、取締役等）は必ず除外（decision: "skip"、total_score: 0）
- HR・人材関係（リクルーター、採用担当等）は必ず除外（decision: "skip"、total_score: 0）
- 職歴に「フューチャー」または「KPMG」を含む企業がある者は必ず除外（現在・過去問わず）（decision: "skip"、total_score: 0）
- 合計スコアが60点以上の場合は "send"、それ未満は "skip"
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
        "total_score", "scoring_decision",
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
        # 新規エントリ
        profiles_master[profile_url] = {
            "profile_url": profile_url,
            "name": "",
            "connected_date": "",
            "profile_fetched": "no",
            "profile_fetched_at": "",
            "total_score": "",
            "scoring_decision": "",
            "message_generated": "no",
            "message_generated_at": "",
            "message_sent_status": "pending",
            "message_sent_at": "",
            "last_send_error": ""
        }

    # 更新
    profiles_master[profile_url].update(updates)

# ==============================
# ログイン
# ==============================
def login(account_name, cookie_file):
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
    if os.path.exists(cookie_file):
        print(f"🔑 保存されたCookieを使用して自動ログイン中（アカウント: {account_name}）...")
        driver.get("https://www.linkedin.com")
        human_sleep(2, 4)

        try:
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

            driver.get("https://www.linkedin.com/feed")
            human_sleep(4, 7)

            current_url = driver.current_url
            if ("feed" in current_url or "home" in current_url) and "login" not in current_url:
                print("✅ 自動ログイン成功！\n")
                return driver
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(cookie_file)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(cookie_file):
                os.remove(cookie_file)

    # 手動ログイン
    print(f"🔑 LinkedIn 手動ログインモード開始（アカウント: {account_name}）...")
    print(f"⚠️  必ず '{account_name}' アカウントでログインしてください！")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了\n")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました（{account_name}用）\n")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}\n")

    return driver

# ==============================
# Step 1: つながり取得
# ==============================
def get_connections(driver, start_date):
    """つながりリストを取得（日付フィルタ付き）"""

    print(f"{'='*70}")
    print(f"📋 Step 1: つながり取得")
    print(f"{'='*70}")
    print(f"開始日: {start_date} 以降")
    print(f"{'='*70}\n")

    # つながりページへ移動
    connections_url = "https://www.linkedin.com/mynetwork/invite-connect/connections/"
    driver.get(connections_url)
    human_sleep(4, 7)

    # スクロールコンテナを取得
    try:
        container = driver.find_element(By.ID, "workspace")
        print("✅ スクロールコンテナ（#workspace）を検出\n")
    except:
        container = None
        print("⚠️ スクロールコンテナが見つかりません\n")

    # スクロールして全てのつながりを読み込む
    print("📜 スクロールしてつながりを読み込み中...")
    for i in range(30):
        scroll_amount = random.randint(300, 800)
        if container:
            driver.execute_script(f"arguments[0].scrollBy(0, {scroll_amount});", container)
        else:
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        human_sleep(2, 6)

    print("✅ スクロール完了\n")

    # プロフィールリンクと日付を取得
    print("🔍 つながり情報を抽出中...\n")

    script = """
    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'))
        .filter(a => {
            const href = a.getAttribute('href') || '';
            return href.match(/\\/in\\/[^/]+\\/?$/);
        });

    const connectionsMap = new Map();

    for (const link of profileLinks) {
        const profileUrl = link.href;
        const name = link.textContent.trim();

        if (!name) continue;

        let card = link;
        let dateText = '';
        for (let level = 0; level < 15; level++) {
            card = card.parentElement;
            if (!card) break;

            const cardText = card.textContent || '';
            if (cardText.includes('につながりました')) {
                const dateMatch = cardText.match(/(\\d{4})年(\\d{1,2})月(\\d{1,2})日につながりました/);
                if (dateMatch) {
                    dateText = dateMatch[0];
                }
                break;
            }
        }

        if (dateText) {
            const existing = connectionsMap.get(profileUrl);
            if (!existing || name.length < existing.name.length) {
                connectionsMap.set(profileUrl, {
                    name: name,
                    profileUrl: profileUrl,
                    dateText: dateText
                });
            }
        }
    }

    return Array.from(connectionsMap.values());
    """

    connections = driver.execute_script(script)

    # 日付でフィルタリング
    from datetime import datetime
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")

    filtered_connections = []
    for conn in connections:
        date_text = conn['dateText']
        match = __import__('re').search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            conn_date = datetime(year, month, day)

            if conn_date >= start_date_obj:
                filtered_connections.append({
                    'name': conn['name'],
                    'profile_url': conn['profileUrl'],
                    'connected_date': f"{year}-{month:02d}-{day:02d}"
                })

    print(f"✅ {len(filtered_connections)} 件のつながりを取得（{start_date}以降）\n")

    return filtered_connections

# ==============================
# Step 2: プロフィール詳細取得
# ==============================
def get_profile_details(driver, profile_url, name):
    """プロフィール詳細を取得"""
    try:
        driver.get(profile_url)
        human_sleep(5, 12)

        script = """
        const result = {
            headline: '',
            location: '',
            is_premium: false,
            experiences: [],
            education: [],
            skills: []
        };

        // LinkedIn Premiumバッジを検出
        const premiumImg = document.querySelector('img[alt*="Premium"], img[src*="premium"]');
        if (premiumImg) {
            result.is_premium = true;
        }

        if (!result.is_premium) {
            const allText = document.body.textContent;
            if (allText.includes('Premium') && allText.includes('会員')) {
                result.is_premium = true;
            }
        }

        if (!result.is_premium) {
            const badges = document.querySelectorAll('svg, [role="img"]');
            badges.forEach(badge => {
                const ariaLabel = badge.getAttribute('aria-label') || '';
                const title = badge.getAttribute('title') || '';
                if (ariaLabel.toLowerCase().includes('premium') ||
                    title.toLowerCase().includes('premium')) {
                    result.is_premium = true;
                }
            });
        }

        if (!result.is_premium) {
            const profileCard = document.querySelector('.pv-top-card');
            if (profileCard) {
                const badge = profileCard.querySelector('[data-test-premium-badge], .premium-badge, .artdeco-entity-lockup__badge');
                if (badge) {
                    result.is_premium = true;
                }
            }
        }

        // ヘッドライン
        const headlineEl = document.querySelector('.text-body-medium.break-words');
        if (headlineEl) {
            result.headline = headlineEl.textContent.trim();
        }

        // 場所
        const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words');
        if (locationEl) {
            result.location = locationEl.textContent.trim();
        }

        // 職歴
        const experienceSection = document.querySelector('#experience');
        if (experienceSection) {
            const expParent = experienceSection.closest('section');
            if (expParent) {
                const expItems = expParent.querySelectorAll('li.artdeco-list__item');
                expItems.forEach(item => {
                    const titleEl = item.querySelector('.t-bold span[aria-hidden="true"]');
                    const companyEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"]');
                    const dateEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"]');

                    if (titleEl) {
                        result.experiences.push({
                            title: titleEl.textContent.trim(),
                            company: companyEl ? companyEl.textContent.trim() : '',
                            date: dateEl ? dateEl.textContent.trim() : ''
                        });
                    }
                });
            }
        }

        // 学歴
        const educationSection = document.querySelector('#education');
        if (educationSection) {
            const eduParent = educationSection.closest('section');
            if (eduParent) {
                const eduItems = eduParent.querySelectorAll('li.artdeco-list__item');
                eduItems.forEach(item => {
                    const schoolEl = item.querySelector('.t-bold span[aria-hidden="true"]');
                    const degreeEl = item.querySelector('.t-14.t-normal span[aria-hidden="true"]');
                    const dateEl = item.querySelector('.t-14.t-normal.t-black--light span[aria-hidden="true"]');

                    if (schoolEl) {
                        result.education.push({
                            school: schoolEl.textContent.trim(),
                            degree: degreeEl ? degreeEl.textContent.trim() : '',
                            date: dateEl ? dateEl.textContent.trim() : ''
                        });
                    }
                });
            }
        }

        // スキル
        const skillsSection = document.querySelector('#skills');
        if (skillsSection) {
            const skillParent = skillsSection.closest('section');
            if (skillParent) {
                const skillItems = skillParent.querySelectorAll('.hoverable-link-text span[aria-hidden="true"]');
                skillItems.forEach((skill, idx) => {
                    if (idx < 10) {
                        result.skills.push(skill.textContent.trim());
                    }
                });
            }
        }

        return result;
        """

        details = driver.execute_script(script)

        experiences_str = "\n".join([
            f"{exp['title']} @ {exp['company']} ({exp['date']})"
            for exp in details.get('experiences', [])
        ])

        education_str = "\n".join([
            f"{edu['school']} - {edu['degree']} ({edu['date']})"
            for edu in details.get('education', [])
        ])

        skills_str = ", ".join(details.get('skills', []))

        return {
            'name': name,
            'profile_url': profile_url,
            'headline': details.get('headline', ''),
            'location': details.get('location', ''),
            'is_premium': details.get('is_premium', False),
            'experiences': experiences_str,
            'education': education_str,
            'skills': skills_str
        }

    except Exception as e:
        print(f"   ❌ エラー: {e}")
        return {
            'name': name,
            'profile_url': profile_url,
            'headline': '',
            'location': '',
            'is_premium': False,
            'experiences': '',
            'education': '',
            'skills': ''
        }

# ==============================
# Step 3: AIスコアリング
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
            "reason": f"APIエラー: {e}"
        }

# ==============================
# Step 4: メッセージ生成
# ==============================
def generate_message(name, account_name):
    """メッセージを生成（アカウント別・固定テンプレート）"""
    # アカウント別のテンプレートを取得
    template = MESSAGE_TEMPLATES.get(account_name, MESSAGE_TEMPLATES["依田"])
    message = template.format(name=name)
    return message

# ==============================
# メイン処理
# ==============================
def main(account_name, paths, start_date, use_scoring, min_score):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ準備パイプライン")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # ログイン
    driver = login(account_name, paths['cookie_file'])

    try:
        # profiles_master.csv 読み込み
        print(f"{'='*70}")
        print(f"📂 profiles_master.csv 読み込み")
        print(f"{'='*70}\n")

        profiles_master = load_profiles_master(paths['profiles_master_file'])
        print(f"✅ 既存レコード: {len(profiles_master)} 件\n")

        # Step 1: つながり取得
        connections = get_connections(driver, start_date)

        if not connections:
            print("⚠️ つながりが見つかりません。処理を終了します。\n")
            driver.quit()
            return

        # 新規つながりを profiles_master に追加
        print(f"{'='*70}")
        print(f"🆕 新規つながりを profiles_master に登録")
        print(f"{'='*70}\n")

        new_count = 0
        for conn in connections:
            profile_url = conn['profile_url']
            if profile_url not in profiles_master:
                update_profile_master(profiles_master, profile_url, {
                    'name': conn['name'],
                    'connected_date': conn['connected_date'],
                    'profile_fetched': 'no'
                })
                new_count += 1

        print(f"✅ 新規追加: {new_count} 件\n")
        save_profiles_master(profiles_master, paths['profiles_master_file'])

        # Step 2: プロフィール詳細取得（profile_fetched=no のみ）
        profiles_to_fetch = [p for p in profiles_master.values() if p.get('profile_fetched') == 'no']

        if profiles_to_fetch:
            print(f"{'='*70}")
            print(f"📊 Step 2: プロフィール詳細取得")
            print(f"{'='*70}")
            print(f"対象者数: {len(profiles_to_fetch)} 件")
            print(f"{'='*70}\n")

            for idx, profile in enumerate(profiles_to_fetch, start=1):
                name = profile['name']
                profile_url = profile['profile_url']

                print(f"[{idx}/{len(profiles_to_fetch)}] 🔍 {name} のプロフィールを取得中...")

                details = get_profile_details(driver, profile_url, name)

                if details.get('is_premium'):
                    print(f"   🔶 LinkedIn Premium会員")
                print(f"   ✅ 取得完了\n")

                # profiles_detailed.csv に保存（参照用）
                profiles_file = paths['profiles_file']
                file_exists = os.path.exists(profiles_file)
                with open(profiles_file, "a", newline="", encoding="utf-8") as f:
                    fieldnames = ["name", "profile_url", "headline", "location", "is_premium", "experiences", "education", "skills"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(details)

                # profiles_master 更新
                update_profile_master(profiles_master, profile_url, {
                    'profile_fetched': 'yes',
                    'profile_fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                # 遅延（人間らしい間隔）
                if idx < len(profiles_to_fetch):
                    human_sleep(4, 8)

            save_profiles_master(profiles_master, paths['profiles_master_file'])
            print(f"💾 profiles_master.csv 更新完了\n")

        # Step 3: AIスコアリング（scoring_decision が未設定のみ）
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
                if profile.get('profile_fetched') == 'yes' and not profile.get('scoring_decision'):
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
                print(f"🧠 Step 3: AIスコアリング")
                print(f"{'='*70}")
                print(f"候補者数: {len(profiles_to_score)} 件")
                print(f"最低スコア: {min_score} 点")
                print(f"{'='*70}\n")

                for idx, candidate in enumerate(profiles_to_score, start=1):
                    name = candidate['name']
                    profile_url = candidate['profile_url']

                    print(f"[{idx}/{len(profiles_to_score)}] 📊 {name} をスコアリング中...")

                    scored = score_candidate(candidate)

                    decision = scored.get('decision', 'skip')
                    total_score = scored.get('total_score', 0)
                    reason = scored.get('reason', '')

                    if decision == "send":
                        print(f"   ✅ 送信対象: {total_score}点")
                    else:
                        print(f"   ⚪ スキップ: {total_score}点")
                    print(f"   理由: {reason}\n")

                    # profiles_master 更新
                    update_profile_master(profiles_master, profile_url, {
                        'total_score': str(total_score),
                        'scoring_decision': decision
                    })

                    human_sleep(1, 2)

                save_profiles_master(profiles_master, paths['profiles_master_file'])
                print(f"💾 profiles_master.csv 更新完了\n")
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

        # Step 4: 送信対象抽出（scoring_decision=send かつ message_sent_status≠success）
        send_targets = []
        for profile_url, profile in profiles_master.items():
            if (profile.get('scoring_decision') == 'send' and
                profile.get('message_sent_status') != 'success'):
                send_targets.append(profile)

        if not send_targets:
            print("⚠️ 送信対象が0件です。処理を終了します。\n")
            driver.quit()
            return

        print(f"{'='*70}")
        print(f"📋 送信対象")
        print(f"{'='*70}")
        print(f"対象者数: {len(send_targets)} 件")
        print(f"{'='*70}\n")

        # Step 5: メッセージ生成（message_generated=no のみ）
        messages_to_generate = [p for p in send_targets if p.get('message_generated') != 'yes']

        if messages_to_generate:
            print(f"{'='*70}")
            print(f"💬 Step 4: メッセージ生成")
            print(f"{'='*70}")
            print(f"対象者数: {len(messages_to_generate)} 件")
            print(f"{'='*70}\n")

            # generated_messages.csv に保存
            messages_data = []

            for idx, profile in enumerate(messages_to_generate, start=1):
                name = profile['name']
                profile_url = profile['profile_url']
                score = profile.get('total_score', '0')

                print(f"[{idx}/{len(messages_to_generate)}] 💬 {name} (スコア: {score}点) のメッセージを生成中...")
                message = generate_message(name, account_name)
                print(f"   ✅ 生成完了\n")

                messages_data.append({
                    'profile_url': profile_url,
                    'name': name,
                    'total_score': score,
                    'message': message,
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # profiles_master 更新
                update_profile_master(profiles_master, profile_url, {
                    'message_generated': 'yes',
                    'message_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # generated_messages.csv に追記
            file_exists = os.path.exists(paths['generated_messages_file'])
            with open(paths['generated_messages_file'], "a", newline="", encoding="utf-8") as f:
                fieldnames = ["profile_url", "name", "total_score", "message", "generated_at"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(messages_data)

            save_profiles_master(profiles_master, paths['profiles_master_file'])
            print(f"💾 メッセージ保存完了: {paths['generated_messages_file']}\n")

        # 生成済みメッセージを一覧表示
        print(f"{'='*70}")
        print(f"📋 生成済みメッセージ一覧")
        print(f"{'='*70}\n")

        # generated_messages.csv から送信対象のメッセージを読み込み
        messages_map = {}
        if os.path.exists(paths['generated_messages_file']):
            with open(paths['generated_messages_file'], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    messages_map[row['profile_url']] = row

        for idx, profile in enumerate(send_targets, start=1):
            profile_url = profile['profile_url']
            if profile_url in messages_map:
                msg = messages_map[profile_url]
                print(f"--- [{idx}/{len(send_targets)}] {msg['name']} (スコア: {msg['total_score']}点) ---")
                print(f"{msg['message']}")
                print()

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 メッセージ準備パイプライン完了")
        print(f"{'='*70}")
        print(f"終了日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        input("\nEnterキーを押してブラウザを閉じます...")
        driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ準備パイプライン")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

    # つながり取得の開始日
    print("【つながり取得の開始日】")
    start_date_input = input("開始日を入力 (YYYY-MM-DD形式、Enter=デフォルト「2025-10-27」): ").strip()
    if not start_date_input:
        start_date = "2025-10-27"
    else:
        # 日付形式を検証
        try:
            datetime.strptime(start_date_input, "%Y-%m-%d")
            start_date = start_date_input
        except ValueError:
            print("⚠️ 日付形式が正しくありません。デフォルト値を使用します。")
            start_date = "2025-10-27"

    # スコアリング条件
    print("\n【スコアリング条件】")
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
    print(f"つながり取得開始日: {start_date}")
    print(f"スコアリング条件: {'使用する' if use_scoring else '使用しない（全員に送信）'}")
    if use_scoring:
        print(f"最低スコア: {min_score}点")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, start_date, use_scoring, min_score)
