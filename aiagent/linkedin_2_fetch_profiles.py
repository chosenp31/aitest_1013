# aiagent/linkedin_2_fetch_profiles.py
# プロフィール情報取得のみ（つながりリスト取得 + プロフィール詳細取得）
# profiles_master.csv で統合管理

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
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
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
        'profiles_file': os.path.join(account_dir, "profiles_detailed.csv")
    }

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
    // プロフィールリンクを全て取得
    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'))
        .filter(link => link.href.match(/\\/in\\/[^\\/]+\\/?$/))
        .map(link => link.href.replace(/\\/$/, ''));

    const uniqueLinks = [...new Set(profileLinks)];

    // 日付情報をマップに格納
    const dateElements = document.querySelectorAll('time');
    const dateMap = {};
    dateElements.forEach(el => {
        const datetime = el.getAttribute('datetime');
        if (datetime) {
            const card = el.closest('[data-view-name]');
            if (card) {
                const link = card.querySelector('a[href*="/in/"]');
                if (link) {
                    const url = link.href.replace(/\\/$/, '');
                    dateMap[url] = datetime.split('T')[0];
                }
            }
        }
    });

    // デバッグ: 最初のプロフィールリンクのDOM構造を確認
    const debugInfo = {};
    if (uniqueLinks.length > 0) {
        const firstUrl = uniqueLinks[0];
        const firstLink = document.querySelector(`a[href="${firstUrl}"], a[href="${firstUrl}/"]`);
        if (firstLink) {
            debugInfo.found = true;
            debugInfo.innerHTML = firstLink.innerHTML.substring(0, 500);
            debugInfo.textContent = firstLink.textContent.trim().substring(0, 200);
            debugInfo.hasAriaSpan = !!firstLink.querySelector('span[aria-hidden="true"]');
            if (firstLink.querySelector('span[aria-hidden="true"]')) {
                debugInfo.ariaSpanText = firstLink.querySelector('span[aria-hidden="true"]').textContent.trim();
            }
        } else {
            debugInfo.found = false;
            debugInfo.message = 'querySelector did not find the element';
        }
    }

    // 各URLに対して名前を取得
    const result = uniqueLinks.map(url => {
        const linkEl = document.querySelector(`a[href="${url}"], a[href="${url}/"]`);
        let name = "名前不明";

        if (linkEl) {
            // 方法1: リンク内のaria-hidden spanから取得
            const ariaSpan = linkEl.querySelector('span[aria-hidden="true"]');
            if (ariaSpan && ariaSpan.textContent.trim()) {
                name = ariaSpan.textContent.trim();
            }
            // 方法2: リンクのtextContentから取得
            else if (linkEl.textContent && linkEl.textContent.trim()) {
                name = linkEl.textContent.trim();
            }
        }

        return {
            profile_url: url,
            name: name,
            connected_date: dateMap[url] || ""
        };
    });

    return {result: result, debug: debugInfo};
    """

    try:
        script_result = driver.execute_script(script)
        connections = script_result.get('result', [])
        debug_info = script_result.get('debug', {})

        print(f"✅ 検出されたつながり: {len(connections)}件\n")

        # デバッグ: DOM構造情報を表示
        if debug_info:
            print("🔍 デバッグ: 最初のプロフィールリンクのDOM構造")
            print(f"   リンク要素が見つかった: {debug_info.get('found', False)}")
            if debug_info.get('found'):
                print(f"   textContent: '{debug_info.get('textContent', '')}'")
                print(f"   aria-hidden span あり: {debug_info.get('hasAriaSpan', False)}")
                if debug_info.get('hasAriaSpan'):
                    print(f"   aria-hidden span text: '{debug_info.get('ariaSpanText', '')}'")
                print(f"   innerHTML (最初の500文字): {debug_info.get('innerHTML', '')[:500]}")
            else:
                print(f"   エラー: {debug_info.get('message', '')}")
            print()

        # デバッグ: 最初の5件の名前と日付を表示
        print("🔍 デバッグ: 最初の5件の情報")
        for i, conn in enumerate(connections[:5]):
            print(f"  {i+1}. {conn['name']}: connected_date='{conn['connected_date']}'")
        print()

        # 日付フィルタリング
        filtered = []
        date_missing_count = 0
        for conn in connections:
            # 日付が空の場合は、すべて対象に含める
            if not conn['connected_date']:
                filtered.append(conn)
                date_missing_count += 1
            elif conn['connected_date'] >= start_date:
                filtered.append(conn)

        if date_missing_count > 0:
            print(f"⚠️ 日付情報なし: {date_missing_count}件（全て対象に含めました）")

        print(f"✅ {start_date}以降のつながり: {len(filtered)}件\n")
        return filtered

    except Exception as e:
        print(f"❌ つながり取得エラー: {e}\n")
        return []

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
        const headlineEl = document.querySelector('.text-body-medium');
        if (headlineEl) {
            result.headline = headlineEl.textContent.trim();
        }

        // 場所
        const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words');
        if (locationEl) {
            result.location = locationEl.textContent.trim();
        }

        // 職歴
        const expSection = document.querySelector('#experience');
        if (expSection) {
            const expParent = expSection.closest('section');
            if (expParent) {
                const expItems = expParent.querySelectorAll('li');
                expItems.forEach(item => {
                    const text = item.textContent.trim();
                    if (text && text.length > 10) {
                        result.experiences.push(text);
                    }
                });
            }
        }

        // 学歴
        const eduSection = document.querySelector('#education');
        if (eduSection) {
            const eduParent = eduSection.closest('section');
            if (eduParent) {
                const eduItems = eduParent.querySelectorAll('li');
                eduItems.forEach(item => {
                    const text = item.textContent.trim();
                    if (text && text.length > 10) {
                        result.education.push(text);
                    }
                });
            }
        }

        // スキル
        const skillSection = document.querySelector('#skills');
        if (skillSection) {
            const skillParent = skillSection.closest('section');
            if (skillParent) {
                const skillItems = skillParent.querySelectorAll('li');
                skillItems.forEach(item => {
                    const text = item.textContent.trim();
                    if (text && text.length > 2 && text.length < 100) {
                        result.skills.push(text);
                    }
                });
            }
        }

        return result;
        """

        profile_data = driver.execute_script(script)

        return {
            'name': name,
            'profile_url': profile_url,
            'headline': profile_data.get('headline', ''),
            'location': profile_data.get('location', ''),
            'is_premium': profile_data.get('is_premium', False),
            'experiences': '\n'.join(profile_data.get('experiences', [])),
            'education': '\n'.join(profile_data.get('education', [])),
            'skills': ', '.join(profile_data.get('skills', []))
        }

    except Exception as e:
        print(f"   ⚠️ エラー: {e}")
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
def main(account_name, paths, start_date, max_profiles):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn プロフィール情報取得")
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
            print("⚠️ つながりが0件です。処理を終了します。\n")
            driver.quit()
            return

        # 新規つながりを profiles_master に追加
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

        # 取得数制限
        if max_profiles > 0 and len(profiles_to_fetch) > max_profiles:
            print(f"⚠️ 対象者が{len(profiles_to_fetch)}件ですが、上限{max_profiles}件に制限します\n")
            profiles_to_fetch = profiles_to_fetch[:max_profiles]

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
        else:
            print("✅ すべてのプロフィール情報は取得済みです\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 プロフィール情報取得完了")
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
    print(f"🚀 LinkedIn プロフィール情報取得")
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

    # 最大取得数
    print("\n【最大取得数】")
    while True:
        max_profiles_input = input("プロフィール情報の最大取得数を入力 (Enter=デフォルト「全件」, 0=全件): ").strip()
        if not max_profiles_input:
            max_profiles = 0  # 0は全件
            break
        try:
            max_profiles = int(max_profiles_input)
            if max_profiles >= 0:
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
    print(f"最大取得数: {'全件' if max_profiles == 0 else f'{max_profiles}件'}")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, start_date, max_profiles)
