# aiagent/linkedin_prepare_messages.py
# プロフィール取得 → スコアリング → メッセージ生成 → CSV保存

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
        'connections_file': os.path.join(account_dir, "connections_list.csv"),
        'profiles_file': os.path.join(account_dir, "profiles_detailed.csv"),
        'scored_file': os.path.join(account_dir, "scored_connections.json"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv"),
        'message_log_file': os.path.join(account_dir, "message_logs.csv")
    }

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# メッセージテンプレート（アカウント別）
MESSAGE_TEMPLATES = {
    "依田": """{name}さん

いきなりすみません
KPMGコンサルティングの依田と申します。

将来的に人材領域にも関わりたいと考えており、IT・コンサル分野でご活躍されている方々のお話を伺いながら、知見を広げたいと思っています。

自分からは以下のようなトピックを共有できます：
・フューチャーアーキテクト／KPMGでのプロジェクト経験
・転職時に検討したBIG4＋アクセンチュア／BCGの比較や選考情報

もしご関心あれば、カジュアルにオンラインでお話できると嬉しいです！よろしくお願いします！""",

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
   - 現在以下の企業に勤務している者:
     * フューチャー株式会社
     * フューチャーアーキテクト株式会社

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
- フューチャー株式会社またはフューチャーアーキテクト株式会社に現在勤務している者は必ず除外（decision: "skip"、total_score: 0）
- 合計スコアが60点以上の場合は "send"、それ未満は "skip"
"""

# OpenAIクライアント
if not OPENAI_API_KEY:
    print("❌ エラー: OPENAI_API_KEYが設定されていません")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

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
        time.sleep(2)

        try:
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

            driver.get("https://www.linkedin.com/feed")
            time.sleep(5)

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
# Step 2: つながり取得
# ==============================
def get_connections(driver, start_date):
    """つながりリストを取得（日付フィルタ付き）"""

    print(f"{'='*70}")
    print(f"📋 Step 2: つながり取得")
    print(f"{'='*70}")
    print(f"開始日: {start_date} 以降")
    print(f"{'='*70}\n")

    # つながりページへ移動
    connections_url = "https://www.linkedin.com/mynetwork/invite-connect/connections/"
    driver.get(connections_url)
    time.sleep(5)

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
        if container:
            driver.execute_script("arguments[0].scrollBy(0, 500);", container)
        else:
            driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(3)

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
# Step 3: プロフィール詳細取得
# ==============================
def get_profile_details(driver, profile_url, name):
    """プロフィール詳細を取得"""
    try:
        driver.get(profile_url)
        time.sleep(4)

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

def get_all_profiles(driver, connections, profiles_file):
    """全プロフィールの詳細を取得（重複回避）"""

    print(f"{'='*70}")
    print(f"📊 Step 3: プロフィール詳細取得")
    print(f"{'='*70}")
    print(f"対象者数: {len(connections)} 件")
    print(f"{'='*70}\n")

    # 既存のプロフィールデータを読み込み
    existing_profiles = {}
    existing_count = 0

    if os.path.exists(profiles_file):
        try:
            with open(profiles_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    profile_url = row.get('profile_url', '')
                    if profile_url:
                        existing_profiles[profile_url] = row
                        existing_count += 1

            print(f"📂 既存データ読み込み: {existing_count} 件\n")
        except Exception as e:
            print(f"⚠️ 既存データ読み込みエラー: {e}\n")

    # 新規取得が必要なつながりをフィルタリング
    new_connections = []
    skipped_count = 0

    for conn in connections:
        profile_url = conn.get('profile_url', '')
        if profile_url and profile_url not in existing_profiles:
            new_connections.append(conn)
        elif profile_url:
            skipped_count += 1

    print(f"📋 取得状況:")
    print(f"   既存: {existing_count} 件")
    print(f"   スキップ: {skipped_count} 件")
    print(f"   新規取得: {len(new_connections)} 件\n")

    # 新規プロフィールを取得
    new_profiles = []

    for idx, conn in enumerate(new_connections, start=1):
        name = conn.get('name', '不明')
        profile_url = conn.get('profile_url', '')

        if not profile_url:
            print(f"[{idx}/{len(new_connections)}] ⚠️ {name} - URLなし、スキップ\n")
            continue

        print(f"[{idx}/{len(new_connections)}] 🔍 {name} のプロフィールを取得中...")

        details = get_profile_details(driver, profile_url, name)
        new_profiles.append(details)

        if details.get('is_premium'):
            print(f"   🔶 LinkedIn Premium会員")
        print(f"   ✅ 取得完了\n")

        # 遅延
        if idx < len(new_connections):
            time.sleep(random.uniform(3, 6))

    # 既存 + 新規を結合
    all_profiles = list(existing_profiles.values()) + new_profiles

    # CSV保存
    with open(profiles_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "profile_url", "headline", "location", "is_premium", "experiences", "education", "skills"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_profiles)

    print(f"💾 保存完了: {profiles_file}")
    print(f"   合計: {len(all_profiles)} 件（既存 {existing_count} + 新規 {len(new_profiles)}）\n")

    return all_profiles

# ==============================
# Step 4: AIスコアリング
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

        return {
            **candidate,
            **result
        }

    except Exception as e:
        print(f"   ⚠️ APIエラー ({name}): {e}")
        return {
            **candidate,
            "estimated_age": None,
            "age_reasoning": "",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": f"APIエラー: {e}"
        }

def score_all_candidates(profiles, min_score):
    """全候補者をスコアリング"""

    print(f"{'='*70}")
    print(f"🧠 Step 4: AIスコアリング")
    print(f"{'='*70}")
    print(f"候補者数: {len(profiles)} 件")
    print(f"最低スコア: {min_score} 点")
    print(f"{'='*70}\n")

    results = []

    for idx, profile in enumerate(profiles, start=1):
        name = profile.get('name', '不明')
        print(f"[{idx}/{len(profiles)}] 📊 {name} をスコアリング中...")

        scored = score_candidate(profile)
        results.append(scored)

        decision = scored.get('decision', 'skip')
        total_score = scored.get('total_score', 0)
        reason = scored.get('reason', '')

        if decision == "send":
            print(f"   ✅ 送信対象: {total_score}点")
        else:
            print(f"   ⚪ スキップ: {total_score}点")
        print(f"   理由: {reason}\n")

        time.sleep(1)

    # 送信対象を抽出
    send_targets = [r for r in results if r.get('decision') == 'send' and r.get('total_score', 0) >= min_score]

    print(f"✅ 送信対象: {len(send_targets)} 件\n")

    return send_targets

# ==============================
# Step 5: 送信済み除外
# ==============================
def filter_already_sent(targets, message_log_file):
    """送信済みを除外（result="success"のみ）"""

    print(f"{'='*70}")
    print(f"🔍 Step 5: 送信済みチェック")
    print(f"{'='*70}\n")

    # 送信済みのprofile_urlをセット化
    sent_urls = set()

    if os.path.exists(message_log_file):
        try:
            with open(message_log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = row.get('result', '')
                    profile_url = row.get('profile_url', '')
                    # result="success"のみ除外（失敗者は再送信対象）
                    if result == "success" and profile_url:
                        sent_urls.add(profile_url)

            print(f"📂 送信済みデータ読み込み: {len(sent_urls)} 件（success のみ）\n")
        except Exception as e:
            print(f"⚠️ 送信ログ読み込みエラー: {e}\n")

    # 送信済みを除外
    filtered_targets = []
    skipped_count = 0

    for target in targets:
        profile_url = target.get('profile_url', '')
        if profile_url not in sent_urls:
            filtered_targets.append(target)
        else:
            skipped_count += 1

    print(f"📋 フィルタリング結果:")
    print(f"   元の送信対象: {len(targets)} 件")
    print(f"   既送信スキップ: {skipped_count} 件")
    print(f"   最終送信対象: {len(filtered_targets)} 件\n")

    return filtered_targets

# ==============================
# Step 6: メッセージ生成
# ==============================
def generate_message(name, account_name):
    """メッセージを生成（アカウント別）"""
    # アカウント別のテンプレートを取得
    template = MESSAGE_TEMPLATES.get(account_name, MESSAGE_TEMPLATES["依田"])
    base_message = template.format(name=name)

    # 桜井・田中の場合はシンプルなメッセージなのでテンプレートをそのまま使用
    if account_name in ["桜井", "田中"]:
        return base_message

    # 依田の場合のみOpenAI APIでバリエーションを生成
    prompt = f"""
以下のメッセージテンプレートを元に、自然で親しみやすいメッセージを生成してください。
大幅な変更は不要です。語尾や表現を少しだけ変えてください。

【テンプレート】
{base_message}

【要件】
- 名前は必ず「{name}さん」で始める
- 内容の構造は基本的にテンプレート通り
- 語尾や接続詞を少しだけ自然にバリエーションを付ける
- 箇条書き（・）はそのまま維持
- 全体の長さはテンプレートと同程度
- 他の説明は一切不要、メッセージ本文のみ出力
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはメッセージ生成アシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=400
        )

        message = response.choices[0].message.content.strip()
        return message

    except Exception as e:
        print(f"   ⚠️ メッセージ生成エラー: {e}")
        return base_message

def generate_all_messages(targets, generated_messages_file, account_name):
    """全メッセージを生成してCSV保存"""

    print(f"{'='*70}")
    print(f"💬 Step 6: メッセージ生成")
    print(f"{'='*70}")
    print(f"対象者数: {len(targets)} 件")
    print(f"{'='*70}\n")

    messages_to_save = []

    for idx, target in enumerate(targets, start=1):
        name = target.get('name', '不明')
        profile_url = target.get('profile_url', '')
        score = target.get('total_score', 0)

        if not profile_url:
            print(f"[{idx}/{len(targets)}] ⚠️ {name} - URLなし、スキップ\n")
            continue

        print(f"[{idx}/{len(targets)}] 💬 {name} (スコア: {score}点) のメッセージを生成中...")
        message = generate_message(name, account_name)
        print(f"   ✅ 生成完了\n")

        messages_to_save.append({
            'profile_url': profile_url,
            'name': name,
            'total_score': score,
            'message': message,
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        # 依田の場合のみAPI呼び出しがあるので待機
        if account_name == "依田":
            time.sleep(1)

    # CSV保存
    with open(generated_messages_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["profile_url", "name", "total_score", "message", "generated_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(messages_to_save)

    print(f"{'='*70}")
    print(f"💾 メッセージ保存完了")
    print(f"{'='*70}")
    print(f"ファイル: {generated_messages_file}")
    print(f"件数: {len(messages_to_save)} 件")
    print(f"{'='*70}\n")

    return messages_to_save

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
        # Step 2: つながり取得
        connections = get_connections(driver, start_date)

        if not connections:
            print("⚠️ つながりが見つかりません。処理を終了します。\n")
            return

        # Step 3: プロフィール詳細取得
        profiles = get_all_profiles(driver, connections, paths['profiles_file'])

        if not profiles:
            print("⚠️ プロフィールが取得できませんでした。処理を終了します。\n")
            return

        # Step 4: AIスコアリング（オプション）
        if use_scoring:
            send_targets = score_all_candidates(profiles, min_score)

            if not send_targets:
                print("⚠️ 送信対象が0件です。処理を終了します。\n")
                return
        else:
            # スコアリングなし: 全員を送信対象とする
            print(f"{'='*70}")
            print(f"⚠️  スコアリングをスキップ（全員に送信）")
            print(f"{'='*70}\n")

            send_targets = []
            for profile in profiles:
                send_targets.append({
                    'name': profile.get('name', '不明'),
                    'profile_url': profile.get('profile_url', ''),
                    'total_score': 0,  # スコアなし
                    'decision': 'send'
                })

            print(f"✅ 送信対象: {len(send_targets)} 件（スコアリングなし）\n")

        # Step 5: 送信済みを除外
        send_targets = filter_already_sent(send_targets, paths['message_log_file'])

        if not send_targets:
            print("⚠️ 送信対象が0件です（全て送信済み）。処理を終了します。\n")
            return

        # Step 6: メッセージ生成・保存
        generated_messages = generate_all_messages(send_targets, paths['generated_messages_file'], account_name)

        # 生成されたメッセージを一覧表示
        print(f"{'='*70}")
        print(f"📋 生成されたメッセージ一覧")
        print(f"{'='*70}\n")

        for idx, msg_data in enumerate(generated_messages, start=1):
            print(f"--- [{idx}/{len(generated_messages)}] {msg_data['name']} (スコア: {msg_data['total_score']}点) ---")
            print(f"{msg_data['message']}")
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

    confirm = input("この設定で実行しますか？ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, start_date, use_scoring, min_score)
