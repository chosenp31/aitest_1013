#!/usr/bin/env python3
# テスト用: LinkedInページ上のボタンを検出するデバッグスクリプト

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Chromeドライバー設定
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-notifications")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

print("LinkedInの検索結果ページを開いてください...")
print("準備ができたら Enter キーを押してください")
input()

# デバッグスクリプト
script = """
const allButtons = document.querySelectorAll('button');
const debugInfo = {
    totalButtons: allButtons.length,
    connectButtons: [],
    allButtonTexts: []
};

allButtons.forEach((btn, idx) => {
    const text = btn.textContent.trim();
    const textLower = text.toLowerCase();

    // 全てのボタンテキストを記録（最初の50個）
    if (idx < 50 && text) {
        debugInfo.allButtonTexts.push({index: idx, text: text});
    }

    // つながりボタンの検出
    if ((text.includes('つながり') || text.includes('つながる') || textLower.includes('connect')) &&
        !btn.closest('header')) {
        debugInfo.connectButtons.push({
            index: idx,
            text: text,
            hasParent: !!btn.parentElement,
            parentTag: btn.parentElement ? btn.parentElement.tagName : null
        });
    }
});

return debugInfo;
"""

try:
    result = driver.execute_script(script)

    print(f"\n{'='*70}")
    print(f"🔍 ボタン検出結果")
    print(f"{'='*70}")
    print(f"全ボタン数: {result['totalButtons']}")
    print(f"つながりボタン数: {len(result['connectButtons'])}")

    print(f"\n📋 全ボタンテキスト（最初の50個）:")
    for btn_info in result['allButtonTexts']:
        print(f"   [{btn_info['index']}] '{btn_info['text']}'")

    if result['connectButtons']:
        print(f"\n🔗 つながりボタン詳細:")
        for btn_info in result['connectButtons']:
            print(f"   [{btn_info['index']}] '{btn_info['text']}' - Parent: {btn_info['parentTag']}")
    else:
        print(f"\n⚠️ つながりボタンが検出されませんでした")

except Exception as e:
    print(f"❌ エラー: {e}")

print(f"\n{'='*70}")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
