#!/usr/bin/env python3
# ボタン構造とSPAN要素の親を詳細調査

import time
import os
import pickle
import json
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
    for i in range(5):
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
    print("✅ スクロール完了")
except:
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
    print("✅ スクロール完了")

time.sleep(5)

# 詳細診断スクリプト
script = """
const result = {
    allButtons: [],
    spanParents: [],
    candidateCardStructure: [],
    linkButtons: [],
    statistics: {
        totalButtons: 0,
        buttonsWithText: 0,
        spanWithConnect: 0,
        liElements: 0,
        possibleCards: 0
    }
};

// 1. すべてのボタンを調査（フィルターなし）
const allButtons = document.querySelectorAll('button');
result.statistics.totalButtons = allButtons.length;

allButtons.forEach((btn, index) => {
    const text = btn.textContent;
    const trimmed = text.trim();

    // 最初の30個のボタンと、「つながる」を含む可能性のあるボタンを詳細記録
    if (index < 30 ||
        trimmed.includes('つながる') ||
        trimmed.includes('つながり') ||
        trimmed.includes('Connect') ||
        trimmed.includes('connect')) {

        result.allButtons.push({
            index: index,
            textContent: text,
            trimmed: trimmed,
            length: text.length,
            trimmedLength: trimmed.length,
            className: btn.className.substring(0, 100),
            ariaLabel: btn.getAttribute('aria-label') || '',
            type: btn.type || '',
            role: btn.getAttribute('role') || '',
            // 特殊文字チェック
            hasNewline: text.includes('\\n'),
            hasTab: text.includes('\\t'),
            charCodes: Array.from(text.substring(0, 50)).map(c => c.charCodeAt(0)),
            outerHTML: btn.outerHTML.substring(0, 300)
        });

        if (trimmed.length > 0) {
            result.statistics.buttonsWithText++;
        }
    }
});

// 2. XPathで見つかったSPAN要素の親を辿る
const xpath = "//span[contains(text(), 'つながる')]";
const spanIterator = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);

result.statistics.spanWithConnect = spanIterator.snapshotLength;

for (let i = 0; i < Math.min(spanIterator.snapshotLength, 10); i++) {
    const span = spanIterator.snapshotItem(i);
    const parentInfo = {
        spanText: span.textContent,
        spanClass: span.className.substring(0, 100),
        parents: []
    };

    // 親要素を5階層まで辿る
    let current = span;
    for (let level = 0; level < 5; level++) {
        current = current.parentElement;
        if (!current) break;

        parentInfo.parents.push({
            level: level + 1,
            tagName: current.tagName,
            className: current.className.substring(0, 100),
            id: current.id || '',
            role: current.getAttribute('role') || '',
            ariaLabel: current.getAttribute('aria-label') || '',
            href: current.tagName === 'A' ? current.href : '',
            type: current.tagName === 'BUTTON' ? current.type : '',
            textContent: current.textContent.trim().substring(0, 100),
            outerHTML: current.outerHTML.substring(0, 400),
            // クリック可能か
            hasOnclick: !!current.onclick,
            isClickable: current.tagName === 'BUTTON' ||
                        current.tagName === 'A' ||
                        current.getAttribute('role') === 'button' ||
                        !!current.onclick
        });
    }

    result.spanParents.push(parentInfo);
}

// 3. <a> タグでボタンの役割をしている可能性のある要素
const links = document.querySelectorAll('a[role="button"], a.button, a[class*="button"]');
links.forEach((link, index) => {
    const text = link.textContent.trim();
    if (text.includes('つながる') || text.includes('つながり') || text.toLowerCase().includes('connect')) {
        result.linkButtons.push({
            index: index,
            text: text.substring(0, 100),
            href: link.href,
            className: link.className.substring(0, 100),
            role: link.getAttribute('role') || '',
            ariaLabel: link.getAttribute('aria-label') || '',
            outerHTML: link.outerHTML.substring(0, 400)
        });
    }
});

// 4. 候補者カードの構造を調査
const liElements = document.querySelectorAll('li');
result.statistics.liElements = liElements.length;

// サイズと内容で候補者カードらしきものをフィルター
liElements.forEach((li, index) => {
    const text = li.textContent.trim();
    const textLen = text.length;

    // 候補者カードっぽい条件
    if (textLen > 50 && textLen < 2000 && index < 15) {
        result.statistics.possibleCards++;

        const cardInfo = {
            index: index,
            textLength: textLen,
            className: li.className.substring(0, 150),
            hasConnectText: text.includes('つながる'),
            hasConnectButton: false,
            buttons: [],
            links: [],
            interactiveElements: []
        };

        // カード内のボタン
        li.querySelectorAll('button').forEach(btn => {
            const btnText = btn.textContent.trim();
            cardInfo.buttons.push({
                text: btnText.substring(0, 50),
                className: btn.className.substring(0, 80),
                ariaLabel: btn.getAttribute('aria-label') || ''
            });

            if (btnText.includes('つながる')) {
                cardInfo.hasConnectButton = true;
            }
        });

        // カード内のリンク
        li.querySelectorAll('a[role="button"]').forEach(a => {
            cardInfo.links.push({
                text: a.textContent.trim().substring(0, 50),
                href: a.href,
                role: a.getAttribute('role') || ''
            });
        });

        // クリック可能な要素全般
        li.querySelectorAll('[onclick], [role="button"]').forEach(el => {
            const elText = el.textContent.trim();
            if (elText.includes('つながる')) {
                cardInfo.interactiveElements.push({
                    tagName: el.tagName,
                    text: elText.substring(0, 50),
                    className: el.className.substring(0, 80)
                });
            }
        });

        // テキストの先頭100文字（デバッグ用）
        cardInfo.sampleText = text.substring(0, 150).replace(/\\n/g, ' ');

        result.candidateCardStructure.push(cardInfo);
    }
});

return result;
"""

try:
    result = driver.execute_script(script)

    print("\n" + "="*70)
    print("📊 詳細診断結果")
    print("="*70 + "\n")

    # 統計情報
    stats = result['statistics']
    print("【統計】")
    print(f"  総ボタン数: {stats['totalButtons']}")
    print(f"  テキストありボタン: {stats['buttonsWithText']}")
    print(f"  「つながる」SPAN要素: {stats['spanWithConnect']}")
    print(f"  li要素数: {stats['liElements']}")
    print(f"  候補者カードらしきもの: {stats['possibleCards']}")

    # すべてのボタン詳細
    print("\n" + "="*70)
    print("【全ボタン詳細】（最初の30個 + つながる関連）")
    print("="*70)

    for btn in result['allButtons'][:15]:  # 最初の15個を表示
        print(f"\nボタン #{btn['index']}:")
        print(f"  テキスト（生）: {repr(btn['textContent'][:50])}")
        print(f"  テキスト（trim）: {repr(btn['trimmed'][:50])}")
        print(f"  長さ: {btn['length']} → trim後: {btn['trimmedLength']}")
        print(f"  改行含む: {btn['hasNewline']}, タブ含む: {btn['hasTab']}")
        print(f"  文字コード（最初10文字）: {btn['charCodes'][:10]}")
        print(f"  クラス: {btn['className'][:60]}")
        print(f"  aria-label: {btn['ariaLabel'][:60]}")
        print(f"  HTML: {btn['outerHTML'][:150]}...")

    # SPAN要素の親情報
    print("\n" + "="*70)
    print("【「つながる」SPAN要素の親要素】")
    print("="*70)

    for span_info in result['spanParents']:
        print(f"\nSPAN: {span_info['spanText']}")
        print(f"  クラス: {span_info['spanClass'][:80]}")
        print("  親要素の階層:")

        for parent in span_info['parents']:
            print(f"\n    レベル{parent['level']}: <{parent['tagName']}>")
            print(f"      クリック可能: {parent['isClickable']}")
            if parent['isClickable']:
                print(f"      ★★★ これがクリック対象の可能性が高い ★★★")
            print(f"      クラス: {parent['className'][:70]}")
            if parent['role']:
                print(f"      role: {parent['role']}")
            if parent['ariaLabel']:
                print(f"      aria-label: {parent['ariaLabel'][:60]}")
            if parent['href']:
                print(f"      href: {parent['href'][:60]}")
            print(f"      テキスト: {parent['textContent'][:80]}")
            print(f"      HTML: {parent['outerHTML'][:200]}...")

    # リンクボタン
    if result['linkButtons']:
        print("\n" + "="*70)
        print("【<a>タグのボタン（「つながる」含む）】")
        print("="*70)

        for link in result['linkButtons']:
            print(f"\nリンクボタン #{link['index']}:")
            print(f"  テキスト: {link['text']}")
            print(f"  href: {link['href']}")
            print(f"  role: {link['role']}")
            print(f"  クラス: {link['className'][:80]}")
            print(f"  HTML: {link['outerHTML'][:200]}...")

    # 候補者カード構造
    print("\n" + "="*70)
    print("【候補者カード構造分析】")
    print("="*70)

    for card in result['candidateCardStructure'][:5]:  # 最初の5件
        print(f"\nカード #{card['index']}:")
        print(f"  クラス: {card['className']}")
        print(f"  テキスト長: {card['textLength']}")
        print(f"  「つながる」テキスト: {card['hasConnectText']}")
        print(f"  「つながる」ボタン: {card['hasConnectButton']}")
        print(f"  ボタン数: {len(card['buttons'])}")
        print(f"  リンク数: {len(card['links'])}")
        print(f"  クリック可能要素数: {len(card['interactiveElements'])}")
        print(f"  サンプルテキスト: {card['sampleText']}")

        if card['buttons']:
            print("  📌 ボタン:")
            for btn in card['buttons']:
                print(f"     - {btn['text'][:40]}")
                print(f"       クラス: {btn['className'][:60]}")

        if card['interactiveElements']:
            print("  ⚡ クリック可能要素（つながる）:")
            for el in card['interactiveElements']:
                print(f"     - {el['tagName']}: {el['text'][:40]}")
                print(f"       クラス: {el['className'][:60]}")

    # 結果をJSONファイルにも保存
    output_file = f"button_diagnosis_{account_name}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print(f"✅ 詳細結果を保存: {output_file}")
    print("="*70)

    # 重要な発見をハイライト
    print("\n" + "="*70)
    print("💡 重要な発見")
    print("="*70)

    if result['spanParents']:
        print("\n✅ 「つながる」SPAN要素が見つかりました")
        print("   → 上記の「親要素の階層」でクリック可能な要素を確認してください")
        print("   → その要素のクラス名やセレクタを使って修正できます")

    if result['linkButtons']:
        print(f"\n✅ <a>タグのボタンが{len(result['linkButtons'])}個見つかりました")
        print("   → ボタンではなくリンク要素として実装されている可能性")

    if stats['totalButtons'] > 0 and not any('つながる' in btn['trimmed'] for btn in result['allButtons']):
        print("\n⚠️ ボタンは存在するが、textContentに「つながる」が含まれていない")
        print("   → ボタン内のSPANやテキストが別構造になっている")

    if stats['possibleCards'] == 0:
        print("\n⚠️ 候補者カードが検出できていません")
        print("   → li要素ではない構造に変更されている可能性")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます...")
driver.quit()
