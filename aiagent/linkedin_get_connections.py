# aiagent/linkedin_get_connections.py
# つながりリストを取得し、日付でフィルタリング

import os
import time
import csv
import pickle
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "new_connections.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

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
# 日付解析
# ==============================
def parse_connection_date(date_text):
    """
    つながり日付をパース
    例: "2025年10月24日につながりました" → "2025-10-24"
    """
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None

# ==============================
# つながりリスト取得
# ==============================
def get_connections(driver, start_date=None):
    """
    つながりリストを取得して日付でフィルタリング

    Args:
        driver: Selenium WebDriver
        start_date: フィルタ開始日（YYYY-MM-DD形式、Noneの場合は全件）

    Returns:
        list: つながりリスト
    """
    print(f"\n{'='*70}")
    print(f"📋 つながりリスト取得開始")
    print(f"{'='*70}")

    # つながりページへ移動
    driver.get(CONNECTIONS_URL)
    time.sleep(5)

    # ページを下までスクロールして全件読み込み
    print("📜 ページをスクロール中（全件読み込み）...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < 20:  # 最大20回スクロール
        # 下までスクロール
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)

        # 新しい高さを取得
        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            print("   ✓ すべてのつながりを読み込みました")
            break

        last_height = new_height
        scroll_count += 1
        print(f"   スクロール {scroll_count} 回目...")

    # つながりカードを取得（プロフィールリンクから逆算）
    print("\n📊 つながり情報を抽出中...")

    script = """
    // プロフィールリンクを検出
    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'))
        .filter(a => {
            const href = a.getAttribute('href') || '';
            // /in/で始まるプロフィールリンクのみ
            return href.match(/\\/in\\/[^/]+\\/?$/);
        });

    const connectionsMap = new Map();

    for (const link of profileLinks) {
        const profileUrl = link.href;

        // 名前を取得
        const name = link.textContent.trim();

        // 名前が空のリンク（画像リンクなど）はスキップ
        if (!name) continue;

        // 親要素を遡ってカードを探す（最大15階層）
        let card = link;
        let dateText = '';

        for (let level = 0; level < 15; level++) {
            card = card.parentElement;
            if (!card) break;

            const cardText = card.textContent || '';

            // 「につながりました」を含むかチェック
            if (cardText.includes('につながりました')) {
                // 日付パターンを抽出
                const dateMatch = cardText.match(/(\\d{4})年(\\d{1,2})月(\\d{1,2})日につながりました/);
                if (dateMatch) {
                    dateText = dateMatch[0];
                }
                break;
            }
        }

        // 日付が見つかった場合のみ登録
        if (dateText) {
            // 既存エントリがない、または既存の名前より短い名前の場合は登録/上書き
            // （短い名前 = "鈴木 祐美子" を優先、長い名前 = "鈴木 祐美子HRBP|..." は除外）
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

    print(f"✅ 全つながり数: {len(connections)} 件")

    # 日付でフィルタリング
    filtered_connections = []

    for conn in connections:
        name = conn['name']
        profile_url = conn['profileUrl']
        date_text = conn['dateText']

        # 日付をパース
        connection_date = parse_connection_date(date_text)

        if not connection_date:
            # 日付が取れない場合はスキップ
            continue

        # フィルタ処理
        if start_date:
            if connection_date >= start_date:
                filtered_connections.append({
                    'name': name,
                    'profile_url': profile_url,
                    'connection_date': connection_date
                })
        else:
            # フィルタなしの場合は全件
            filtered_connections.append({
                'name': name,
                'profile_url': profile_url,
                'connection_date': connection_date
            })

    return filtered_connections

# ==============================
# メイン処理
# ==============================
def main():
    """メイン処理"""

    # 日付入力（対話式）
    print(f"\n{'='*70}")
    print(f"📅 フィルタ条件設定")
    print(f"{'='*70}")
    print("いつからのつながりを取得しますか？")
    print("形式: YYYY-MM-DD（例: 2025-10-24）")
    print("全件取得する場合は Enter キーを押してください。\n")

    start_date_input = input("開始日: ").strip()

    if start_date_input:
        # 日付の妥当性チェック
        try:
            datetime.strptime(start_date_input, "%Y-%m-%d")
            start_date = start_date_input
            print(f"✅ {start_date} 以降のつながりを取得します")
        except ValueError:
            print("❌ 日付形式が不正です。全件取得します。")
            start_date = None
    else:
        start_date = None
        print("✅ 全件取得します")

    # ログイン
    driver = login()

    # つながり取得
    connections = get_connections(driver, start_date)

    # CSV保存
    print(f"\n{'='*70}")
    print(f"💾 結果を保存中...")
    print(f"{'='*70}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "profile_url", "connection_date"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(connections)

    print(f"✅ 保存完了: {OUTPUT_FILE}")

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"抽出件数: {len(connections)} 件")
    if start_date:
        print(f"期間: {start_date} 以降")
    else:
        print(f"期間: 全期間")
    print(f"保存先: {OUTPUT_FILE}")
    print(f"{'='*70}\n")

    if connections:
        print(f"💡 次のステップ: python3 aiagent/linkedin_get_profiles.py でプロフィール詳細を取得")
    else:
        print(f"⚠️ 該当するつながりが0件です。日付を確認してください。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    main()
