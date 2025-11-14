#!/usr/bin/env python3
# Shadow DOM、iframe、すべての階層を探索するスクリプト

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
    for i in range(8):
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
    print("✅ #workspace スクロール完了")
except:
    for i in range(8):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
    print("✅ キーボードスクロール完了")

time.sleep(5)

# Shadow DOM、iframe、すべてを探索
script = """
const results = {
    regularDOM: {
        buttons: [],
        allElementsWithText: []
    },
    shadowDOMs: [],
    iframes: [],
    detailedAnalysis: []
};

// 1. 通常のDOM検索（再確認）
document.querySelectorAll('button').forEach((btn, idx) => {
    const text = btn.textContent.trim();
    if (text.includes('つながる') || text.includes('Connect')) {
        results.regularDOM.buttons.push({
            index: idx,
            text: text,
            className: btn.className,
            ariaLabel: btn.getAttribute('aria-label') || '',
            tagName: btn.tagName
        });
    }
});

// 2. XPathで「つながる」を含むすべての要素
const xpath = "//*[contains(text(), 'つながる')]";
const iterator = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
for (let i = 0; i < iterator.snapshotLength; i++) {
    const el = iterator.snapshotItem(i);
    results.regularDOM.allElementsWithText.push({
        tagName: el.tagName,
        text: el.textContent.trim().substring(0, 100),
        className: el.className.substring(0, 100),
        outerHTML: el.outerHTML.substring(0, 500)
    });
}

// 3. Shadow DOMを探索
function exploreShadowDOM(root, path = 'root') {
    const elements = root.querySelectorAll('*');
    elements.forEach((el, idx) => {
        if (el.shadowRoot) {
            const shadowInfo = {
                path: path + ' -> ' + el.tagName,
                buttons: [],
                allText: []
            };

            // Shadow root内のボタンを検索
            el.shadowRoot.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                shadowInfo.buttons.push({
                    text: text,
                    hasConnect: text.includes('つながる') || text.includes('Connect'),
                    className: btn.className,
                    outerHTML: btn.outerHTML.substring(0, 300)
                });
            });

            // Shadow root内の全要素でテキスト検索
            el.shadowRoot.querySelectorAll('*').forEach(shadowEl => {
                const text = shadowEl.textContent.trim();
                if (text.includes('つながる')) {
                    shadowInfo.allText.push({
                        tagName: shadowEl.tagName,
                        text: text.substring(0, 100),
                        outerHTML: shadowEl.outerHTML.substring(0, 300)
                    });
                }
            });

            if (shadowInfo.buttons.length > 0 || shadowInfo.allText.length > 0) {
                results.shadowDOMs.push(shadowInfo);
            }

            // 再帰的に探索
            exploreShadowDOM(el.shadowRoot, shadowInfo.path);
        }
    });
}

exploreShadowDOM(document);

// 4. iframeを探索
document.querySelectorAll('iframe').forEach((iframe, idx) => {
    try {
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        const iframeInfo = {
            index: idx,
            src: iframe.src,
            buttons: []
        };

        iframeDoc.querySelectorAll('button').forEach(btn => {
            const text = btn.textContent.trim();
            if (text.includes('つながる') || text.includes('Connect')) {
                iframeInfo.buttons.push({
                    text: text,
                    className: btn.className
                });
            }
        });

        if (iframeInfo.buttons.length > 0) {
            results.iframes.push(iframeInfo);
        }
    } catch (e) {
        // Cross-origin iframe
        results.iframes.push({
            index: idx,
            src: iframe.src,
            error: 'Cross-origin - アクセス不可'
        });
    }
});

// 5. 候補者カード内の詳細分析
const candidateCards = document.querySelectorAll('li');
let cardCount = 0;

candidateCards.forEach((card, idx) => {
    if (cardCount >= 3) return;  // 最初の3件のみ

    // カード内のすべての要素を分析
    const cardText = card.textContent;
    if (cardText.length > 50 && cardText.length < 1000) {  // 適切なサイズのカード
        const cardInfo = {
            index: cardCount,
            className: card.className.substring(0, 100),
            hasConnectText: cardText.includes('つながる'),
            buttons: [],
            links: [],
            divs: [],
            spans: [],
            allInteractive: []
        };

        // ボタン
        card.querySelectorAll('button').forEach(btn => {
            cardInfo.buttons.push({
                text: btn.textContent.trim().substring(0, 50),
                className: btn.className.substring(0, 80),
                type: btn.type,
                ariaLabel: btn.getAttribute('aria-label') || ''
            });
        });

        // リンク（ボタンスタイル）
        card.querySelectorAll('a').forEach(a => {
            const text = a.textContent.trim();
            if (text.includes('つながる')) {
                cardInfo.links.push({
                    text: text.substring(0, 50),
                    href: a.href,
                    className: a.className.substring(0, 80),
                    role: a.getAttribute('role') || ''
                });
            }
        });

        // div（クリッカブル）
        card.querySelectorAll('div[role="button"], div[onclick], div.button').forEach(div => {
            const text = div.textContent.trim();
            if (text.includes('つながる')) {
                cardInfo.divs.push({
                    text: text.substring(0, 50),
                    className: div.className.substring(0, 80),
                    role: div.getAttribute('role') || '',
                    onclick: !!div.onclick
                });
            }
        });

        // すべてのクリック可能要素
        card.querySelectorAll('[onclick], [role="button"]').forEach(el => {
            const text = el.textContent.trim();
            if (text.includes('つながる')) {
                cardInfo.allInteractive.push({
                    tagName: el.tagName,
                    text: text.substring(0, 50),
                    className: el.className.substring(0, 80),
                    outerHTML: el.outerHTML.substring(0, 300)
                });
            }
        });

        results.detailedAnalysis.push(cardInfo);
        cardCount++;
    }
});

return results;
"""

try:
    result = driver.execute_script(script)

    print("\n" + "="*70)
    print("🔍 深層DOM探索結果")
    print("="*70 + "\n")

    # 通常のDOM
    print("【通常のDOM】")
    print(f"  button要素で「つながる」: {len(result['regularDOM']['buttons'])}個")
    print(f"  XPathで「つながる」: {len(result['regularDOM']['allElementsWithText'])}個")

    if result['regularDOM']['buttons']:
        print("\n  検出されたボタン:")
        for btn in result['regularDOM']['buttons']:
            print(f"    - {btn['tagName']}: '{btn['text']}'")
            print(f"      クラス: {btn['className'][:60]}")

    if result['regularDOM']['allElementsWithText']:
        print("\n  XPathで検出された要素:")
        for el in result['regularDOM']['allElementsWithText'][:5]:
            print(f"    - {el['tagName']}: '{el['text']}'")
            print(f"      HTML: {el['outerHTML'][:150]}...")

    # Shadow DOM
    print(f"\n【Shadow DOM】")
    print(f"  Shadow root検出数: {len(result['shadowDOMs'])}個")

    if result['shadowDOMs']:
        print("\n  ⚠️ Shadow DOM内にコンテンツが見つかりました:")
        for shadow in result['shadowDOMs']:
            print(f"\n    パス: {shadow['path']}")
            print(f"    ボタン数: {len(shadow['buttons'])}")
            print(f"    「つながる」テキスト: {len(shadow['allText'])}個")

            for btn in shadow['buttons']:
                if btn['hasConnect']:
                    print(f"      🎯 見つかった: '{btn['text']}'")
                    print(f"         HTML: {btn['outerHTML'][:150]}...")

    # iframe
    print(f"\n【iframe】")
    print(f"  iframe検出数: {len(result['iframes'])}個")

    if result['iframes']:
        for iframe in result['iframes']:
            if 'error' in iframe:
                print(f"    iframe[{iframe['index']}]: {iframe['error']}")
            elif iframe['buttons']:
                print(f"    iframe[{iframe['index']}]: {len(iframe['buttons'])}個のボタン")

    # 詳細分析
    print(f"\n【候補者カード詳細分析】")
    print(f"  分析したカード数: {len(result['detailedAnalysis'])}件\n")

    for card in result['detailedAnalysis']:
        print(f"  カード {card['index'] + 1}:")
        print(f"    クラス: {card['className']}")
        print(f"    「つながる」テキストあり: {card['hasConnectText']}")
        print(f"    button要素: {len(card['buttons'])}個")
        print(f"    aタグ（つながる）: {len(card['links'])}個")
        print(f"    div（つながる）: {len(card['divs'])}個")
        print(f"    クリック可能要素: {len(card['allInteractive'])}個")

        if card['buttons']:
            print(f"\n    🔘 ボタン詳細:")
            for btn in card['buttons']:
                print(f"       - '{btn['text']}'")
                print(f"         クラス: {btn['className']}")
                print(f"         type: {btn['type']}")
                if btn['ariaLabel']:
                    print(f"         aria-label: {btn['ariaLabel']}")

        if card['links']:
            print(f"\n    🔗 つながるリンク:")
            for link in card['links']:
                print(f"       - '{link['text']}'")
                print(f"         role: {link['role']}")
                print(f"         HTML: {link['className']}")

        if card['allInteractive']:
            print(f"\n    ⚡ クリック可能要素（つながる）:")
            for el in card['allInteractive']:
                print(f"       - {el['tagName']}: '{el['text']}'")
                print(f"         HTML: {el['outerHTML'][:200]}...")

        print()

    # 結果のサマリー
    print("="*70)
    print("📊 結果サマリー")
    print("="*70)

    total_found = (len(result['regularDOM']['buttons']) +
                   len(result['regularDOM']['allElementsWithText']) +
                   len(result['shadowDOMs']) +
                   sum(len(card['links']) + len(card['divs']) + len(card['allInteractive'])
                       for card in result['detailedAnalysis']))

    if total_found == 0:
        print("❌ 「つながる」ボタンが一切検出できませんでした")
        print("\n💡 可能性:")
        print("  1. ボタンが動的にレンダリングされる（遅延読み込み）")
        print("  2. ボタンのテキストが「つながる」ではない")
        print("  3. Web Componentsやカスタム要素を使用")
        print("  4. ページ構造が大幅に変更された")
        print("\n🔍 次のステップ:")
        print("  - ブラウザの開発者ツールでボタンを手動で検査")
        print("  - 実際のHTML要素タイプを確認")
        print("  - class名やdata属性を確認")
    else:
        print(f"✅ 合計 {total_found} 件の関連要素を検出")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
