#!/usr/bin/env python3
# テスト用: LinkedInページ上のボタンを検出するデバッグスクリプト（スクロール改善版）

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
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

print("\n📜 スクロール可能なコンテナを探索中...")

# スクロール可能なコンテナを検出
container_script = """
const containers = [
    document.querySelector('.search-results-container'),
    document.querySelector('[class*="search-results"]'),
    document.querySelector('main'),
    document.querySelector('#main'),
    document.querySelector('[role="main"]'),
    document.body
];

for (const container of containers) {
    if (container) {
        return {
            found: true,
            tag: container.tagName,
            className: container.className,
            id: container.id,
            scrollHeight: container.scrollHeight,
            clientHeight: container.clientHeight
        };
    }
}

return {found: false};
"""

container_info = driver.execute_script(container_script)
print(f"コンテナ情報: {container_info}")

if container_info.get('found'):
    print(f"✅ スクロール可能なコンテナを検出:")
    print(f"   タグ: {container_info.get('tag')}")
    print(f"   クラス: {container_info.get('className')}")
    print(f"   ID: {container_info.get('id')}")
    print(f"   スクロール高さ: {container_info.get('scrollHeight')}")
    print(f"   表示高さ: {container_info.get('clientHeight')}")

print("\n📜 ページをスクロール中...")

# 複数の方法でスクロールを試行
for attempt in range(3):
    print(f"\nスクロール試行 {attempt + 1}/3")

    # 方法1: 検索結果コンテナをスクロール
    driver.execute_script("""
        const container = document.querySelector('.search-results-container')
                       || document.querySelector('[class*="search-results"]')
                       || document.querySelector('main');
        if (container) {
            container.scrollTo(0, container.scrollHeight);
        }
    """)
    time.sleep(2)

    # 方法2: ページ全体をスクロール
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # 方法3: キーボードでスクロール
    try:
        from selenium.webdriver.common.keys import Keys
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)
    except:
        pass

print("\n✓ スクロール完了")
time.sleep(3)  # 最終的な読み込みを待つ

# デバッグスクリプト
script = """
const allButtons = document.querySelectorAll('button');
const allSpans = document.querySelectorAll('span');
const allDivs = document.querySelectorAll('div');

const debugInfo = {
    totalButtons: allButtons.length,
    totalSpans: allSpans.length,
    totalDivs: allDivs.length,
    connectButtons: [],
    allButtonTexts: [],
    peopleCards: 0
};

// 候補者カードを探す
const cards = document.querySelectorAll('[class*="search-result"], [class*="entity-result"], [data-chameleon-result-urn]');
debugInfo.peopleCards = cards.length;

allButtons.forEach((btn, idx) => {
    const text = btn.textContent.trim();
    const textLower = text.toLowerCase();

    // 全てのボタンテキストを記録
    if (text) {
        debugInfo.allButtonTexts.push({
            index: idx,
            text: text,
            inHeader: !!btn.closest('header'),
            ariaLabel: btn.getAttribute('aria-label') || ''
        });
    }

    // つながりボタンの検出（複数パターン）
    const isConnectButton =
        text.includes('つながり') ||
        text.includes('つながる') ||
        textLower.includes('connect') ||
        (btn.getAttribute('aria-label') && btn.getAttribute('aria-label').toLowerCase().includes('connect'));

    if (isConnectButton && !btn.closest('header')) {
        debugInfo.connectButtons.push({
            index: idx,
            text: text,
            ariaLabel: btn.getAttribute('aria-label') || '',
            classes: btn.className
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
    print(f"全要素数:")
    print(f"  - ボタン: {result['totalButtons']}")
    print(f"  - span: {result['totalSpans']}")
    print(f"  - div: {result['totalDivs']}")
    print(f"  - 候補者カード: {result['peopleCards']}")
    print(f"\nつながりボタン数: {len(result['connectButtons'])}")

    if result['connectButtons']:
        print(f"\n✅ 検出されたつながりボタン:")
        for btn_info in result['connectButtons']:
            print(f"   [{btn_info['index']}] テキスト: '{btn_info['text']}'")
            print(f"      aria-label: '{btn_info['ariaLabel']}'")
            print(f"      classes: {btn_info['classes']}")
    else:
        print(f"\n⚠️ つながりボタンが検出されませんでした")

    # 全ボタンテキスト
    print(f"\n📋 全ボタンテキスト:")
    for btn_info in result['allButtonTexts']:
        header_mark = " [ヘッダー]" if btn_info['inHeader'] else ""
        aria_info = f" aria-label='{btn_info['ariaLabel']}'" if btn_info['ariaLabel'] else ""
        print(f"   [{btn_info['index']}] '{btn_info['text']}'{header_mark}{aria_info}")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
