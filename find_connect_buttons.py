#!/usr/bin/env python3
# 「つながる」ボタンを直接検索するスクリプト

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
time.sleep(8)

print("📜 スクロール中...")
try:
    container = driver.find_element(By.ID, "workspace")
    for i in range(5):
        driver.execute_script("arguments[0].scrollBy(0, 500);", container)
        time.sleep(2)
except:
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)

print("✅ スクロール完了\n")
time.sleep(3)

# すべてのボタンを検索
script = """
const allButtons = Array.from(document.querySelectorAll('button'));

const connectButtons = allButtons.filter(btn => {
    const text = btn.textContent.trim();
    const ariaLabel = btn.getAttribute('aria-label') || '';
    const textLower = text.toLowerCase();
    const ariaLower = ariaLabel.toLowerCase();

    // ヘッダー内のボタンは除外
    if (btn.closest('header')) return false;

    // ページネーションボタンは除外
    if (ariaLabel.includes('ページ')) return false;

    // つながる系のボタンを検出
    return text.includes('つながる') ||
           text.includes('つながり') ||
           text.includes('Connect') ||
           ariaLabel.includes('招待') ||
           ariaLabel.includes('つながり') ||
           ariaLower.includes('connect');
});

return {
    totalButtons: allButtons.length,
    connectButtonsCount: connectButtons.length,
    connectButtons: connectButtons.map((btn, idx) => {
        // 親要素を遡って候補者情報を取得
        let parentLi = btn.closest('li');
        let parentDiv = btn.closest('div[class*="entity"], div[class*="result"]');

        return {
            index: idx,
            text: btn.textContent.trim(),
            ariaLabel: btn.getAttribute('aria-label') || '',
            className: btn.className,
            parentLiClass: parentLi ? parentLi.className : 'none',
            parentDivClass: parentDiv ? parentDiv.className.substring(0, 100) : 'none',
            outerHTML: btn.outerHTML.substring(0, 500)
        };
    })
};
"""

try:
    result = driver.execute_script(script)

    print("="*70)
    print("🔍 つながるボタン検索結果")
    print("="*70 + "\n")

    print(f"全ボタン数: {result['totalButtons']}個")
    print(f"つながる系ボタン数: {result['connectButtonsCount']}個\n")

    if result['connectButtonsCount'] > 0:
        print("✅ つながるボタンを検出しました:\n")
        for btn in result['connectButtons']:
            print(f"【ボタン {btn['index'] + 1}】")
            print(f"  テキスト: '{btn['text']}'")
            print(f"  aria-label: '{btn['ariaLabel']}'")
            print(f"  クラス: {btn['className'][:80]}")
            print(f"  親li class: {btn['parentLiClass'][:80]}")
            print(f"  親div class: {btn['parentDivClass'][:80]}")
            print(f"  HTML: {btn['outerHTML'][:200]}...")
            print()
    else:
        print("⚠️ つながるボタンが見つかりませんでした")
        print("\n💡 ページ上のすべてのボタンテキストをチェックします...")

        all_texts_script = """
        return Array.from(document.querySelectorAll('button'))
            .filter(btn => !btn.closest('header'))
            .map(btn => ({
                text: btn.textContent.trim(),
                aria: btn.getAttribute('aria-label') || ''
            })).slice(0, 30);
        """

        all_buttons = driver.execute_script(all_texts_script)
        print("\nすべてのボタン（最初の30個）:")
        for i, btn in enumerate(all_buttons):
            print(f"  {i+1}. '{btn['text']}' / aria: '{btn['aria']}'")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
