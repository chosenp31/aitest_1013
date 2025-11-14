#!/usr/bin/env python3
# 修正版の検出ロジックをテスト（クリックはしない）

import time
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

print("\n" + "="*70)
print("📋 LinkedInアカウント選択")
print("="*70)
print("1. 依田\n2. 桜井\n3. 田中")
print("="*70 + "\n")

account_choice = input("アカウント番号 (1-3): ").strip()
account_map = {"1": "依田", "2": "桜井", "3": "田中"}
account_name = account_map.get(account_choice, "依田")
print(f"\n✅ 選択: {account_name}\n")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", account_name)
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# 自動ログイン
if os.path.exists(COOKIE_FILE):
    print(f"🔑 Cookie自動ログイン中...")
    driver.get("https://www.linkedin.com")
    time.sleep(2)

    with open(COOKIE_FILE, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except:
            pass

    driver.get("https://www.linkedin.com/feed")
    time.sleep(5)

    if "feed" in driver.current_url or "home" in driver.current_url:
        print("✅ ログイン成功！\n")
    else:
        print("⚠️ 手動ログインしてください...")
        input("Enter を押してください")
else:
    print("🔑 手動ログインしてください...")
    driver.get("https://www.linkedin.com/login")
    input("ログイン後、Enter を押してください")

# 検索
print("🔎 検索中: エンジニア（2次のつながり）...")
search_url = "https://www.linkedin.com/search/results/people/?keywords=エンジニア&network=%5B%22S%22%5D&origin=FACETED_SEARCH"
driver.get(search_url)
time.sleep(10)

print("📜 スクロール中...")
try:
    container = driver.find_element(By.ID, "workspace")
    for i in range(5):
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
    print("✅ スクロール完了")
except:
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
    print("✅ スクロール完了")

time.sleep(3)

# 修正版の検出スクリプト（linkedin_1_connections.pyと同じロジック）
script = """
const candidates = [];

// <a>タグで aria-label に「つながりを申請」を含むものを検索
const connectLinks = document.querySelectorAll('a[aria-label*="つながりを申請"]');

connectLinks.forEach((link) => {
    const ariaLabel = link.getAttribute('aria-label') || '';

    // aria-labelから候補者名を抽出
    // 例: "奈良 明久さんにつながりを申請する" → "奈良 明久"
    const match = ariaLabel.match(/(.+?)さんにつながりを申請/);

    if (match && match[1]) {
        const name = match[1].trim();

        // 有効な名前かチェック
        if (name && name.length >= 2 &&
            name !== 'つながる' &&
            name !== 'つながり' &&
            name !== 'ホーム' &&
            name !== 'メッセージ') {
            candidates.push({
                name: name,
                buttonText: 'つながる',
                ariaLabel: ariaLabel,
                href: link.href.substring(0, 80)
            });
        }
    }
});

return candidates;
"""

try:
    candidates = driver.execute_script(script)

    print("\n" + "="*70)
    print("🎯 検出結果（修正版）")
    print("="*70 + "\n")

    print(f"検出された候補者数: {len(candidates)}件\n")

    if len(candidates) > 0:
        print("✅ 成功！候補者を検出できました：\n")

        for i, candidate in enumerate(candidates[:10], 1):  # 最初の10件を表示
            print(f"{i}. {candidate['name']}")
            print(f"   aria-label: {candidate['ariaLabel']}")
            print(f"   href: {candidate['href']}")
            print()

        if len(candidates) > 10:
            print(f"... 他 {len(candidates) - 10}件\n")

        print("="*70)
        print("💡 次のステップ")
        print("="*70)
        print("検出が成功したので、以下のスクリプトで実際に申請できます:")
        print("  python3 aiagent/linkedin_1_connections.py")
        print()

    else:
        print("❌ 候補者が検出できませんでした")
        print("\n考えられる原因:")
        print("  1. ページにまだ「つながる」ボタンが表示されていない")
        print("  2. aria-labelのテキストが「つながりを申請」ではない")
        print("  3. すでに全員とつながっている")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
