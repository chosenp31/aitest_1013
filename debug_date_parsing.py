# debug_date_parsing.py
# 日付パースとフィルタリングのデバッグ

import os
import time
import pickle
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")
CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

def parse_connection_date(date_text):
    """日付をパース"""
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', date_text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None

def login():
    """LinkedInにログイン"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    if os.path.exists(COOKIE_FILE):
        print("🔑 Cookie自動ログイン...")
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
        except Exception as e:
            print(f"⚠️ エラー: {e}")

    return driver

def debug_date_parsing(driver):
    """日付パースとフィルタリングをデバッグ"""

    driver.get(CONNECTIONS_URL)
    time.sleep(5)

    # スクロール
    print("📜 スクロール中...")
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)

    print("\n" + "="*70)
    print("🔍 日付パース・フィルタリングのデバッグ")
    print("="*70 + "\n")

    # JavaScriptでつながり取得
    script = """
    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'))
        .filter(a => {
            const href = a.getAttribute('href') || '';
            return href.match(/\\/in\\/[^/]+\\/?$/);
        });

    const connectionsMap = new Map();

    for (const link of profileLinks) {
        const profileUrl = link.href;
        if (connectionsMap.has(profileUrl)) continue;

        const name = link.textContent.trim();
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

        if (name && dateText) {
            connectionsMap.set(profileUrl, {
                name: name,
                profileUrl: profileUrl,
                dateText: dateText
            });
        }
    }

    return Array.from(connectionsMap.values());
    """

    connections = driver.execute_script(script)

    print(f"✅ JavaScript検出数: {len(connections)} 件\n")

    # 日付パースとフィルタリングのデバッグ
    start_date = "2025-10-27"
    print(f"📅 フィルタ条件: {start_date} 以降\n")

    filtered = []

    for idx, conn in enumerate(connections, start=1):
        name = conn['name']
        date_text = conn['dateText']

        # 日付パース
        parsed_date = parse_connection_date(date_text)

        # フィルタ判定
        passes_filter = False
        if parsed_date and parsed_date >= start_date:
            passes_filter = True
            filtered.append(conn)

        # 詳細表示
        status = "✅ 含む" if passes_filter else "❌ 除外"
        print(f"[{idx}] {status}")
        print(f"    名前: {name[:30]}...")
        print(f"    元の日付: {date_text}")
        print(f"    パース後: {parsed_date}")
        print(f"    比較: {parsed_date} >= {start_date} → {passes_filter}")
        print()

    print("="*70)
    print(f"🎯 サマリー")
    print("="*70)
    print(f"全つながり数: {len(connections)} 件")
    print(f"フィルタ後: {len(filtered)} 件")
    print(f"除外: {len(connections) - len(filtered)} 件")
    print("="*70 + "\n")

    input("Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_date_parsing(driver)
