# aiagent/linkedin_get_profiles.py
# つながりリストからプロフィール詳細を取得

import os
import time
import csv
import pickle
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "new_connections.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "profile_details.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

DELAY_RANGE = (3, 5)  # プロフィール間の遅延（秒）

# ==============================
# ログイン
# ==============================
def login():
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
    if os.path.exists(COOKIE_FILE):
        print("🔑 保存されたCookieを使用して自動ログイン中...")
        driver.get("https://www.linkedin.com")
        time.sleep(2)

        try:
            with open(COOKIE_FILE, "rb") as f:
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
                print("✅ 自動ログイン成功！")
                return driver
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(COOKIE_FILE)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)

    # 手動ログイン
    print("🔑 LinkedIn 手動ログインモード開始...")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}")

    return driver

# ==============================
# プロフィール詳細取得
# ==============================
def get_profile_details(driver, profile_url, name):
    """
    プロフィールページから詳細情報を取得

    Args:
        driver: Selenium WebDriver
        profile_url: プロフィールURL
        name: 候補者名

    Returns:
        dict: プロフィール詳細
    """
    try:
        # プロフィールページへ移動
        driver.get(profile_url)
        time.sleep(4)

        # JavaScriptで情報を抽出
        script = """
        const result = {
            headline: '',
            location: '',
            is_premium: false,
            experiences: [],
            education: [],
            skills: []
        };

        // LinkedIn Premiumバッジを検出（複数の方法を試行）
        // 方法1: Premium関連のimg要素
        const premiumImg = document.querySelector('img[alt*="Premium"], img[src*="premium"]');
        if (premiumImg) {
            result.is_premium = true;
        }

        // 方法2: Premium関連のテキスト
        if (!result.is_premium) {
            const allText = document.body.textContent;
            if (allText.includes('Premium') && allText.includes('会員')) {
                result.is_premium = true;
            }
        }

        // 方法3: オレンジ色の"in"バッジ（SVG）
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

        // 方法4: プロフィールカード内のバッジアイコン
        if (!result.is_premium) {
            const profileCard = document.querySelector('.pv-top-card');
            if (profileCard) {
                const badge = profileCard.querySelector('[data-test-premium-badge], .premium-badge, .artdeco-entity-lockup__badge');
                if (badge) {
                    result.is_premium = true;
                }
            }
        }

        // ヘッドライン（現在の職歴・役職）
        const headlineEl = document.querySelector('.text-body-medium.break-words');
        if (headlineEl) {
            result.headline = headlineEl.textContent.trim();
        }

        // 場所
        const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words');
        if (locationEl) {
            result.location = locationEl.textContent.trim();
        }

        // 職歴（Experience section）
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

        // 学歴（Education section）
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

        // スキル（Skills section - 最大10件）
        const skillsSection = document.querySelector('#skills');
        if (skillsSection) {
            const skillParent = skillsSection.closest('section');
            if (skillParent) {
                const skillItems = skillParent.querySelectorAll('.hoverable-link-text span[aria-hidden="true"]');
                skillItems.forEach((skill, idx) => {
                    if (idx < 10) {  // 最大10件
                        result.skills.push(skill.textContent.trim());
                    }
                });
            }
        }

        return result;
        """

        details = driver.execute_script(script)

        # 職歴を文字列化（改行区切り）
        experiences_str = "\n".join([
            f"{exp['title']} @ {exp['company']} ({exp['date']})"
            for exp in details.get('experiences', [])
        ])

        # 学歴を文字列化（改行区切り）
        education_str = "\n".join([
            f"{edu['school']} - {edu['degree']} ({edu['date']})"
            for edu in details.get('education', [])
        ])

        # スキルを文字列化（カンマ区切り）
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
# メイン処理
# ==============================
def main():
    """メイン処理（既存プロフィールはスキップ）"""

    if not os.path.exists(INPUT_FILE):
        print(f"❌ エラー: つながりリストが見つかりません: {INPUT_FILE}")
        print(f"💡 先に linkedin_get_connections.py を実行してください")
        return

    # CSV読み込み
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        connections = list(reader)

    if not connections:
        print("⚠️ つながりデータが空です")
        return

    print(f"\n{'='*70}")
    print(f"📊 プロフィール詳細取得開始")
    print(f"{'='*70}")

    # 既存プロフィールを読み込み
    existing_profiles = []
    existing_urls = set()

    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_profiles.append(row)
                    existing_urls.add(row.get('profile_url', ''))
            print(f"📂 既存プロフィール: {len(existing_profiles)} 件")
        except Exception as e:
            print(f"⚠️ 既存ファイル読み込みエラー: {e}")

    # 新規取得対象を抽出
    new_connections = [
        conn for conn in connections
        if conn.get('profile_url', '') and conn.get('profile_url', '') not in existing_urls
    ]

    skipped_count = len(connections) - len(new_connections)

    print(f"👥 今回のつながり総数: {len(connections)} 件")
    print(f"✅ 既にプロフィール取得済み: {skipped_count} 件")
    print(f"🆕 新規取得対象: {len(new_connections)} 件")
    print(f"{'='*70}\n")

    if not new_connections:
        print("⚠️ 新規取得対象が0件です。既存データをそのまま使用します。\n")
        print(f"\n{'='*70}")
        print(f"🎯 完了サマリー")
        print(f"{'='*70}")
        print(f"既存プロフィール: {len(existing_profiles)} 件")
        print(f"新規取得: 0 件")
        print(f"保存先: {OUTPUT_FILE}")
        print(f"{'='*70}\n")
        return

    # ログイン
    driver = login()

    new_results = []

    for idx, conn in enumerate(new_connections, start=1):
        name = conn.get('name', '不明')
        profile_url = conn.get('profile_url', '')

        if not profile_url:
            print(f"[{idx}/{len(new_connections)}] ⚠️ {name} - URLなし、スキップ")
            continue

        print(f"[{idx}/{len(new_connections)}] 🔍 {name} のプロフィールを取得中...")

        # プロフィール詳細取得
        details = get_profile_details(driver, profile_url, name)
        new_results.append(details)

        # 簡易表示
        premium_badge = "🔶 Premium会員" if details.get('is_premium') else ""
        print(f"   ✅ ヘッドライン: {details['headline'][:50]}...")
        print(f"   📍 場所: {details['location']}")
        if details.get('is_premium'):
            print(f"   🔶 LinkedIn Premium会員")
        print(f"   💼 職歴: {len(details['experiences'].split(chr(10)) if details['experiences'] else [])} 件")
        print(f"   🎓 学歴: {len(details['education'].split(chr(10)) if details['education'] else [])} 件")
        print(f"   🔧 スキル: {len(details['skills'].split(',') if details['skills'] else [])} 件\n")

        # 遅延
        if idx < len(new_connections):
            delay = random.uniform(*DELAY_RANGE)
            time.sleep(delay)

    # 既存データと新規データを結合
    all_profiles = existing_profiles + new_results

    # CSV保存（既存データ + 新規データ）
    print(f"\n{'='*70}")
    print(f"💾 結果を保存中...")
    print(f"{'='*70}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "profile_url", "headline", "location", "is_premium", "experiences", "education", "skills"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_profiles)

    print(f"✅ 保存完了: {OUTPUT_FILE}")
    print(f"   既存: {len(existing_profiles)} 件 + 新規: {len(new_results)} 件 = 合計: {len(all_profiles)} 件")

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"既存プロフィール: {len(existing_profiles)} 件")
    print(f"新規取得: {len(new_results)} 件")
    print(f"合計プロフィール: {len(all_profiles)} 件")
    print(f"保存先: {OUTPUT_FILE}")
    print(f"{'='*70}\n")

    print(f"💡 次のステップ: python3 aiagent/linkedin_scorer_v2.py でAIスコアリングを実行")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    main()
