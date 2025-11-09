#!/usr/bin/env python3
# テスト用: LinkedInページ上のボタンを検出するデバッグスクリプト（スクロール付き）

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

print("\n📜 ページをスクロール中...")
last_height = driver.execute_script("return document.body.scrollHeight")

for i in range(10):  # 最大10回スクロール
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # 動的コンテンツの読み込みを待つ

    new_height = driver.execute_script("return document.body.scrollHeight")

    if new_height == last_height:
        print(f"✓ スクロール完了（{i+1}回目で到達）")
        break
    last_height = new_height

time.sleep(2)  # 最終的な読み込みを待つ

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

    // 全てのボタンテキストを記録
    if (text) {
        debugInfo.allButtonTexts.push({
            index: idx,
            text: text,
            inHeader: !!btn.closest('header')
        });
    }

    // つながりボタンの検出
    if ((text.includes('つながり') || text.includes('つながる') || textLower.includes('connect')) &&
        !btn.closest('header')) {

        // 親要素を遡る
        let card = btn.parentElement;
        let cardInfo = {index: idx, text: text, cardFound: false, cardText: ''};

        for (let i = 0; i < 8; i++) {
            if (card && card.innerText && card.innerText.includes('•')) {
                cardInfo.cardFound = true;
                cardInfo.cardText = card.innerText.substring(0, 200);
                break;
            }
            if (card) {
                card = card.parentElement;
            }
        }

        debugInfo.connectButtons.push(cardInfo);
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

    # つながり関連のボタンを抽出
    connect_related = [b for b in result['allButtonTexts']
                      if 'つながり' in b['text'] or 'つながる' in b['text'] or 'connect' in b['text'].lower()]

    if connect_related:
        print(f"\n🔗 つながり関連のボタン（全{len(connect_related)}個）:")
        for btn_info in connect_related:
            header_mark = " [ヘッダー]" if btn_info['inHeader'] else ""
            print(f"   [{btn_info['index']}] '{btn_info['text']}'{header_mark}")

    if result['connectButtons']:
        print(f"\n✅ 検出されたつながりボタン詳細:")
        for btn_info in result['connectButtons']:
            print(f"   [{btn_info['index']}] '{btn_info['text']}'")
            print(f"      カード検出: {btn_info['cardFound']}")
            if btn_info['cardFound']:
                print(f"      カード内容: {btn_info['cardText'][:100]}...")
    else:
        print(f"\n⚠️ つながりボタンが検出されませんでした")

    # サンプルボタンテキスト
    print(f"\n📋 全ボタンテキスト（最初の30個）:")
    for btn_info in result['allButtonTexts'][:30]:
        header_mark = " [ヘッダー]" if btn_info['inHeader'] else ""
        print(f"   [{btn_info['index']}] '{btn_info['text']}'{header_mark}")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
