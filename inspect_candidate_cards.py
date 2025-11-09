#!/usr/bin/env python3
# 候補者カード内部の詳細HTML構造を調査

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
print("\n" + "="*70)
print("📋 LinkedInアカウント選択")
print("="*70)
print("1. 依田\n2. 桜井\n3. 田中")
print("="*70 + "\n")

account_choice = input("アカウント番号 (1-3): ").strip()
account_map = {"1": "依田", "2": "桜井", "3": "田中"}
account_name = account_map.get(account_choice, "依田")
print(f"\n✅ 選択: {account_name}\n")

# Cookie ファイル
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
for i in range(5):
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
    time.sleep(2)
print("✅ スクロール完了\n")
time.sleep(3)

# 候補者カードの詳細調査
script = """
// 候補者カードと思われる<li>要素を取得
const candidateCards = Array.from(document.querySelectorAll('li'))
    .filter(li => {
        const className = li.className;
        // ナビゲーション以外のli要素
        return className.includes('_74bba5ac') ||
               className.includes('b65ab7f3') ||
               (li.querySelector('button') && !li.closest('header'));
    });

const results = {
    totalCandidateCards: candidateCards.length,
    cardDetails: []
};

// 最初の5件の候補者カードを詳細調査
candidateCards.slice(0, 5).forEach((card, idx) => {
    const cardInfo = {
        index: idx,
        className: card.className,
        outerHTML: card.outerHTML.substring(0, 2000),

        // ボタン検出
        buttons: Array.from(card.querySelectorAll('button')).map(btn => ({
            text: btn.textContent.trim(),
            className: btn.className,
            ariaLabel: btn.getAttribute('aria-label') || '',
            innerHTML: btn.innerHTML.substring(0, 300)
        })),

        // リンク検出
        links: Array.from(card.querySelectorAll('a')).slice(0, 5).map(a => ({
            text: a.textContent.trim().substring(0, 50),
            href: a.href,
            className: a.className
        })),

        // span要素検出
        spans: Array.from(card.querySelectorAll('span')).slice(0, 10).map(span => ({
            text: span.textContent.trim().substring(0, 50),
            className: span.className
        }))
    };

    results.cardDetails.push(cardInfo);
});

return results;
"""

try:
    result = driver.execute_script(script)

    print("="*70)
    print("🔍 候補者カード詳細分析")
    print("="*70 + "\n")

    print(f"候補者カード数: {result['totalCandidateCards']}件\n")

    for card in result['cardDetails']:
        print(f"【カード {card['index'] + 1}】")
        print(f"クラス: {card['className'][:100]}")

        if card['buttons']:
            print(f"\n  🔘 ボタン（{len(card['buttons'])}個）:")
            for btn in card['buttons']:
                print(f"    - テキスト: '{btn['text']}'")
                print(f"      クラス: {btn['className'][:80]}")
                if btn['ariaLabel']:
                    print(f"      aria-label: '{btn['ariaLabel']}'")
                print(f"      HTML: {btn['innerHTML'][:150]}...")
        else:
            print("\n  ⚠️ ボタンなし")

        if card['links']:
            print(f"\n  🔗 リンク（最初の5個）:")
            for link in card['links'][:3]:
                print(f"    - テキスト: '{link['text']}'")
                print(f"      URL: {link['href'][:80]}")

        print(f"\n  📄 outerHTML（最初の500文字）:")
        print(f"    {card['outerHTML'][:500]}...")
        print("\n" + "-"*70 + "\n")

    # HTMLファイルに保存
    with open("candidate_card_details.html", "w", encoding="utf-8") as f:
        for card in result['cardDetails']:
            f.write(f"\n{'='*70}\n")
            f.write(f"Card {card['index'] + 1}\n")
            f.write(f"{'='*70}\n")
            f.write(card['outerHTML'])
            f.write("\n\n")

    print("💾 詳細HTMLを保存: candidate_card_details.html")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
