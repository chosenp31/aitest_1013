#!/usr/bin/env python3
# DOM構造の完全分析スクリプト

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

print("LinkedInの検索結果ページを開いてください...")
print("準備ができたら Enter キーを押してください")
input()

print("\n📜 スクロール中...")
# スクロール
for i in range(5):
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys(Keys.PAGE_DOWN)
    time.sleep(2)

print("✅ スクロール完了\n")
time.sleep(3)

# 詳細なDOM分析
script = """
const analysis = {
    // 候補者カード検出（複数パターン）
    cards: {
        'reusable-search__result-container': document.querySelectorAll('.reusable-search__result-container').length,
        'entity-result': document.querySelectorAll('.entity-result').length,
        'search-result': document.querySelectorAll('[class*="search-result"]').length,
        'li elements': document.querySelectorAll('li').length
    },

    // ボタン検出（複数パターン）
    buttons: {
        'artdeco-button': document.querySelectorAll('button.artdeco-button').length,
        'contains つながる': Array.from(document.querySelectorAll('button')).filter(b => b.textContent.includes('つながる')).length,
        'contains connect': Array.from(document.querySelectorAll('button')).filter(b => b.textContent.toLowerCase().includes('connect')).length,
        'aria-label 招待': document.querySelectorAll('button[aria-label*="招待"]').length
    },

    // サンプルデータ
    sampleCards: [],
    sampleButtons: []
};

// 候補者カードのサンプル（最初の3件）
const cards = document.querySelectorAll('.reusable-search__result-container, .entity-result, li[class*="result"]');
Array.from(cards).slice(0, 3).forEach((card, idx) => {
    analysis.sampleCards.push({
        index: idx,
        tagName: card.tagName,
        className: card.className,
        hasButton: !!card.querySelector('button'),
        innerHTML: card.innerHTML.substring(0, 500)
    });
});

// ボタンのサンプル（つながる系）
const connectButtons = Array.from(document.querySelectorAll('button')).filter(b =>
    b.textContent.includes('つながる') ||
    b.textContent.toLowerCase().includes('connect') ||
    (b.getAttribute('aria-label') && b.getAttribute('aria-label').includes('招待'))
);

connectButtons.slice(0, 5).forEach((btn, idx) => {
    analysis.sampleButtons.push({
        index: idx,
        text: btn.textContent.trim(),
        ariaLabel: btn.getAttribute('aria-label') || '',
        className: btn.className,
        parentClassName: btn.parentElement ? btn.parentElement.className : ''
    });
});

return analysis;
"""

try:
    result = driver.execute_script(script)

    print(f"{'='*70}")
    print(f"🔍 DOM構造分析結果")
    print(f"{'='*70}\n")

    print("📦 候補者カード検出結果:")
    for selector, count in result['cards'].items():
        print(f"   {selector}: {count}件")

    print(f"\n🔘 ボタン検出結果:")
    for selector, count in result['buttons'].items():
        print(f"   {selector}: {count}件")

    if result['sampleCards']:
        print(f"\n📋 候補者カードのサンプル:")
        for card in result['sampleCards']:
            print(f"\n   [{card['index']}] {card['tagName']}")
            print(f"      クラス: {card['className'][:100]}")
            print(f"      ボタンあり: {card['hasButton']}")
            print(f"      HTML（一部）: {card['innerHTML'][:200]}...")

    if result['sampleButtons']:
        print(f"\n🔗 つながるボタンのサンプル:")
        for btn in result['sampleButtons']:
            print(f"\n   [{btn['index']}] '{btn['text']}'")
            print(f"      aria-label: '{btn['ariaLabel']}'")
            print(f"      クラス: {btn['className'][:80]}")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
