#!/usr/bin/env python3
# 「つながる」テキストを含むすべての要素を検索（button以外も）

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
time.sleep(10)  # より長い待機時間

print("📜 スクロール中...")
try:
    container = driver.find_element(By.ID, "workspace")
    for i in range(8):
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
    print("✅ #workspace スクロール完了")
except:
    for i in range(8):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
    print("✅ キーボードスクロール完了")

time.sleep(5)  # さらに待機

# すべての要素で「つながる」を検索
script = """
const results = {
    // すべての要素（button, a, div, span）で「つながる」を検索
    allElements: [],
    buttons: [],
    links: [],
    divs: [],
    spans: []
};

// 方法1: XPathで「つながる」テキストを含むすべての要素を検索
const xpath = "//*[contains(text(), 'つながる')]";
const iterator = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);

for (let i = 0; i < iterator.snapshotLength; i++) {
    const el = iterator.snapshotItem(i);
    results.allElements.push({
        tagName: el.tagName,
        textContent: el.textContent.trim().substring(0, 100),
        className: el.className.substring(0, 100),
        ariaLabel: el.getAttribute('aria-label') || '',
        outerHTML: el.outerHTML.substring(0, 500)
    });
}

// 方法2: button要素を直接検索
document.querySelectorAll('button').forEach(btn => {
    const text = btn.textContent.trim();
    if (text.includes('つながる')) {
        results.buttons.push({
            text: text,
            className: btn.className.substring(0, 100),
            ariaLabel: btn.getAttribute('aria-label') || '',
            outerHTML: btn.outerHTML.substring(0, 500)
        });
    }
});

// 方法3: aタグを検索
document.querySelectorAll('a').forEach(a => {
    const text = a.textContent.trim();
    if (text.includes('つながる')) {
        results.links.push({
            text: text,
            href: a.href,
            className: a.className.substring(0, 100),
            outerHTML: a.outerHTML.substring(0, 500)
        });
    }
});

// 方法4: div要素を検索
document.querySelectorAll('div').forEach(div => {
    const text = div.textContent.trim();
    if (text === 'つながる' || text === '👤 つながる') {
        results.divs.push({
            text: text.substring(0, 50),
            className: div.className.substring(0, 100),
            role: div.getAttribute('role') || '',
            outerHTML: div.outerHTML.substring(0, 500)
        });
    }
});

return results;
"""

try:
    result = driver.execute_script(script)

    print("\n" + "="*70)
    print("🔍 「つながる」テキストを含む要素の検索結果")
    print("="*70 + "\n")

    print(f"XPathで検出された要素: {len(result['allElements'])}個")
    print(f"button要素: {len(result['buttons'])}個")
    print(f"aタグ: {len(result['links'])}個")
    print(f"div要素: {len(result['divs'])}個\n")

    if result['allElements']:
        print("【XPathで検出された要素】")
        for i, el in enumerate(result['allElements'][:10]):  # 最初の10個
            print(f"\n  要素 {i+1}:")
            print(f"    タグ: {el['tagName']}")
            print(f"    テキスト: {el['textContent']}")
            print(f"    クラス: {el['className']}")
            print(f"    aria-label: {el['ariaLabel']}")
            print(f"    HTML: {el['outerHTML'][:250]}...")

    if result['buttons']:
        print("\n【button要素】")
        for i, btn in enumerate(result['buttons']):
            print(f"\n  ボタン {i+1}:")
            print(f"    テキスト: {btn['text']}")
            print(f"    クラス: {btn['className']}")
            print(f"    HTML: {btn['outerHTML'][:250]}...")

    if result['links']:
        print("\n【aタグ】")
        for i, link in enumerate(result['links']):
            print(f"\n  リンク {i+1}:")
            print(f"    テキスト: {link['text']}")
            print(f"    URL: {link['href']}")
            print(f"    HTML: {link['outerHTML'][:250]}...")

    if result['divs']:
        print("\n【div要素（完全一致）】")
        for i, div in enumerate(result['divs'][:5]):
            print(f"\n  div {i+1}:")
            print(f"    テキスト: {div['text']}")
            print(f"    クラス: {div['className']}")
            print(f"    role: {div['role']}")
            print(f"    HTML: {div['outerHTML'][:250]}...")

    if not result['allElements'] and not result['buttons'] and not result['links'] and not result['divs']:
        print("⚠️ 「つながる」テキストを含む要素が1つも見つかりませんでした")
        print("\n💡 これは以下の可能性があります:")
        print("  1. ページの読み込みが完了していない")
        print("  2. Shadow DOM内にボタンがある")
        print("  3. 検索結果に候補者が表示されていない")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("ブラウザを開いたまま確認してください")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
