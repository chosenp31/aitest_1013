#!/usr/bin/env python3
# ページ全体のHTMLを保存して手動確認

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
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
except:
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)

print("✅ スクロール完了\n")
time.sleep(3)

# ページ全体のHTMLを保存
print("💾 ページ全体のHTMLを保存中...")

# outerHTMLを取得
full_html = driver.execute_script("return document.documentElement.outerHTML;")

# ファイルに保存
output_file = f"linkedin_search_full_{account_name}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"✅ 保存完了: {output_file}")
print(f"   ファイルサイズ: {len(full_html):,} 文字")

# 候補者カードのセクションだけを抽出
try:
    main_content = driver.find_element(By.TAG_NAME, "main")
    main_html = main_content.get_attribute('outerHTML')

    main_file = f"linkedin_search_main_{account_name}.html"
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_html)

    print(f"✅ mainコンテンツも保存: {main_file}")
    print(f"   ファイルサイズ: {len(main_html):,} 文字")
except:
    print("⚠️ mainコンテンツの取得に失敗")

# 検索結果リストのHTML
try:
    results_list = driver.find_element(By.CSS_SELECTOR, "ul.reusable-search__entity-result-list")
    list_html = results_list.get_attribute('outerHTML')

    list_file = f"linkedin_search_list_{account_name}.html"
    with open(list_file, "w", encoding="utf-8") as f:
        f.write(list_html)

    print(f"✅ 検索結果リストも保存: {list_file}")
    print(f"   ファイルサイズ: {len(list_html):,} 文字")
except Exception as e:
    print(f"⚠️ 検索結果リストの取得に失敗: {e}")

# テキスト検索
print("\n" + "="*70)
print("🔍 HTMLファイル内での「つながる」検索")
print("="*70)

connect_count = full_html.count("つながる")
print(f"\n「つながる」の出現回数: {connect_count}回")

if connect_count > 0:
    print("\n💡 「つながる」は存在します。以下の可能性があります:")
    print("  1. ボタン要素ではなく、テキストとして埋め込まれている")
    print("  2. JavaScriptで動的に生成される")
    print("  3. 特殊なHTML構造（カスタム要素など）")
    print("\n🔍 ファイルをテキストエディタで開いて「つながる」で検索してください")
else:
    print("\n⚠️ HTMLファイル内に「つながる」が見つかりません")
    print("  表示されているテキストが画像またはCSSで生成されている可能性")

print("\n" + "="*70)
print("📝 次のステップ:")
print("="*70)
print(f"1. {output_file} をテキストエディタで開く")
print("2. Ctrl+F で「つながる」を検索")
print("3. 見つかった箇所のHTML構造を確認")
print("4. button、a、div などのタグ名を確認")
print("5. class名やaria-label属性を確認")

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
