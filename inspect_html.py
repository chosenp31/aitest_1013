#!/usr/bin/env python3
# HTML構造を完全にダンプして確認

import time
import os
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# アカウント選択
print("\n======================================================================")
print("📋 使用するLinkedInアカウントを選択")
print("======================================================================")
print("1. 依田")
print("2. 桜井")
print("3. 田中")
print("======================================================================\n")

account_choice = input("アカウント番号を入力 (1-3): ").strip()
account_map = {"1": "依田", "2": "桜井", "3": "田中"}
account_name = account_map.get(account_choice, "依田")

print(f"\n✅ 選択: {account_name}\n")

# Cookie ファイルパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", account_name)
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

# Chrome設定
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# 自動ログイン
if os.path.exists(COOKIE_FILE):
    print(f"🔑 Cookie自動ログイン中（アカウント: {account_name}）...")
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
            print("✅ 自動ログイン成功！\n")
        else:
            print("⚠️ 手動ログインしてください...")
            input("ログイン後、Enter キーを押してください")
    except Exception as e:
        print(f"⚠️ エラー: {e}")
        print("手動でログインしてください...")
        driver.get("https://www.linkedin.com/login")
        input("ログイン後、Enter キーを押してください")
else:
    print("🔑 手動ログインモード...")
    driver.get("https://www.linkedin.com/login")
    print("ブラウザでLinkedInにログインしてください...")
    input("ログイン後、Enter キーを押してください")

# 検索結果ページに移動
keywords = "エンジニア"
print(f"🔎 検索中: {keywords}（2次のつながり）...")
search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&network=%5B%22S%22%5D&origin=FACETED_SEARCH"
driver.get(search_url)
time.sleep(8)

print("📜 スクロール中...")
for i in range(5):
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys(Keys.PAGE_DOWN)
    time.sleep(2)

print("✅ スクロール完了\n")
time.sleep(3)

# HTML構造を取得
script = """
const info = {
    url: window.location.href,
    title: document.title,

    // すべての<li>要素のクラス名を取得
    liElements: Array.from(document.querySelectorAll('li')).map((li, idx) => ({
        index: idx,
        className: li.className,
        hasButton: !!li.querySelector('button'),
        text: li.textContent.substring(0, 100)
    })),

    // すべてのボタンのクラス名を取得
    buttonElements: Array.from(document.querySelectorAll('button')).map((btn, idx) => ({
        index: idx,
        className: btn.className,
        text: btn.textContent.trim(),
        ariaLabel: btn.getAttribute('aria-label') || ''
    })),

    // メインコンテンツのHTML（最初の5000文字）
    mainHTML: document.querySelector('main') ? document.querySelector('main').innerHTML.substring(0, 5000) : 'main not found'
};

return info;
"""

try:
    result = driver.execute_script(script)

    print(f"{'='*70}")
    print(f"🔍 HTML構造詳細分析")
    print(f"{'='*70}\n")

    print(f"URL: {result['url']}")
    print(f"Title: {result['title']}")

    print(f"\n📋 <li> 要素（全{len(result['liElements'])}件）:")
    for li in result['liElements'][:20]:  # 最初の20件
        button_mark = " [ボタンあり]" if li['hasButton'] else ""
        print(f"   [{li['index']}] class='{li['className'][:80]}'{button_mark}")
        print(f"        テキスト: {li['text'][:80]}...")

    print(f"\n🔘 <button> 要素（全{len(result['buttonElements'])}件）:")
    for btn in result['buttonElements'][:20]:  # 最初の20件
        print(f"   [{btn['index']}] '{btn['text']}'")
        print(f"        class='{btn['className'][:80]}'")
        if btn['ariaLabel']:
            print(f"        aria-label='{btn['ariaLabel']}'")

    # HTMLをファイルに保存
    output_file = "linkedin_search_page.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result['mainHTML'])

    print(f"\n💾 mainコンテンツのHTMLを保存しました: {output_file}")
    print(f"   このファイルを開いて、実際のDOM構造を確認してください")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
