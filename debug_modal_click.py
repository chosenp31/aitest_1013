#!/usr/bin/env python3
# モーダルボタンのクリック処理をデバッグ

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

# 未申請の候補者を探してクリック
click_result = driver.execute_script("""
    const candidates = [];
    const connectLinks = document.querySelectorAll('a[aria-label*="つながりを申請"]');

    connectLinks.forEach((link) => {
        const ariaLabel = link.getAttribute('aria-label') || '';
        const match = ariaLabel.match(/(.+?)さんにつながりを申請/);

        if (match && match[1]) {
            const name = match[1].trim();

            // 承認待ちかチェック
            let card = link.closest('li');
            let isPending = false;

            if (card) {
                const buttons = card.querySelectorAll('button');
                for (const btn of buttons) {
                    const btnText = btn.textContent.trim();
                    const btnAria = btn.getAttribute('aria-label') || '';
                    if (btnText.includes('承認待ち') || btnText.includes('Pending') ||
                        btnAria.includes('承認待ち') || btnAria.includes('Pending')) {
                        isPending = true;
                        break;
                    }
                }
            }

            if (!isPending) {
                candidates.push({
                    name: name,
                    link: link,
                    ariaLabel: ariaLabel
                });
            }
        }
    });

    if (candidates.length > 0) {
        // 最初の未申請候補者をクリック
        const first = candidates[0];
        first.link.scrollIntoView({ block: 'center', behavior: 'instant' });
        first.link.click();

        return {
            success: true,
            name: first.name,
            ariaLabel: first.ariaLabel,
            totalCandidates: candidates.length
        };
    }

    return {
        success: false,
        totalCandidates: 0
    };
""")

if not click_result['success']:
    print("❌ 未申請の候補者が見つかりませんでした")
    print("   検索結果に未申請の候補者がいるページに移動してください")
    input("\nEnter キーを押してブラウザを閉じます...")
    driver.quit()
    exit()

print(f"✅ 「つながる」をクリックしました")
print(f"   候補者: {click_result['name']}")
print(f"   未申請候補者数: {click_result['totalCandidates']}件\n")

print("⏳ モーダルの読み込みを待機中（3秒）...")
time.sleep(3)

# モーダルとボタンを詳細調査
print("\n" + "="*70)
print("🔍 モーダルボタン検出のデバッグ")
print("="*70 + "\n")

debug_result = driver.execute_script("""
    const result = {
        modal: {
            found: false,
            selector: '',
            html: ''
        },
        method1: { name: 'data-control-name', found: false, button: null },
        method2: { name: 'aria-label', found: false, button: null },
        method3: { name: 'modal primary button', found: false, button: null },
        method4: { name: 'text search', found: false, button: null },
        allButtons: []
    };

    // モーダル検出
    const modalSelectors = [
        'div[role="dialog"]',
        'div[role="modal"]',
        '.artdeco-modal',
        'div[data-test-modal]',
        'div.send-invite'
    ];

    let modal = null;
    for (const selector of modalSelectors) {
        const found = document.querySelector(selector);
        if (found) {
            modal = found;
            result.modal.found = true;
            result.modal.selector = selector;
            result.modal.html = found.outerHTML.substring(0, 500);
            break;
        }
    }

    // 方法1: data-control-name
    let btn1 = document.querySelector('button[data-control-name="send_without_note"]');
    if (btn1) {
        result.method1.found = true;
        result.method1.button = {
            text: btn1.textContent.trim(),
            className: btn1.className.substring(0, 100),
            ariaLabel: btn1.getAttribute('aria-label') || '',
            html: btn1.outerHTML.substring(0, 300)
        };
    }

    // 方法2: aria-label
    const buttons = document.querySelectorAll('button');
    for (const btn of buttons) {
        const ariaLabel = btn.getAttribute('aria-label') || '';
        if (ariaLabel.includes('Send without') || ariaLabel.includes('挨拶なしで')) {
            result.method2.found = true;
            result.method2.button = {
                text: btn.textContent.trim(),
                className: btn.className.substring(0, 100),
                ariaLabel: ariaLabel,
                dataControlName: btn.getAttribute('data-control-name') || '',
                html: btn.outerHTML.substring(0, 300)
            };
            break;
        }
    }

    // 方法3: モーダル内のプライマリボタン
    if (modal) {
        const primaryBtn = modal.querySelector('button.artdeco-button--primary:last-child');
        if (primaryBtn) {
            result.method3.found = true;
            result.method3.button = {
                text: primaryBtn.textContent.trim(),
                className: primaryBtn.className.substring(0, 100),
                ariaLabel: primaryBtn.getAttribute('aria-label') || '',
                dataControlName: primaryBtn.getAttribute('data-control-name') || '',
                html: primaryBtn.outerHTML.substring(0, 300)
            };
        }
    }

    // 方法4: テキスト検索
    for (const btn of buttons) {
        const text = btn.textContent.trim();
        if (text.includes('挨拶なしで送信') || text.includes('Send without')) {
            result.method4.found = true;
            result.method4.button = {
                text: text,
                className: btn.className.substring(0, 100),
                ariaLabel: btn.getAttribute('aria-label') || '',
                dataControlName: btn.getAttribute('data-control-name') || '',
                html: btn.outerHTML.substring(0, 300)
            };
            break;
        }
    }

    // モーダル内の全ボタン
    if (modal) {
        const modalButtons = modal.querySelectorAll('button');
        modalButtons.forEach((btn, idx) => {
            result.allButtons.push({
                index: idx,
                text: btn.textContent.trim(),
                className: btn.className.substring(0, 100),
                ariaLabel: btn.getAttribute('aria-label') || '',
                dataControlName: btn.getAttribute('data-control-name') || '',
                type: btn.type || '',
                disabled: btn.disabled
            });
        });
    }

    return result;
""")

# 結果を表示
print(f"【モーダル検出】")
if debug_result['modal']['found']:
    print(f"  ✅ 検出成功")
    print(f"  セレクタ: {debug_result['modal']['selector']}")
    print(f"  HTML: {debug_result['modal']['html'][:200]}...\n")
else:
    print(f"  ❌ 検出失敗\n")

print(f"【検出方法1: data-control-name】")
if debug_result['method1']['found']:
    print(f"  ✅ 検出成功")
    print(f"  テキスト: {debug_result['method1']['button']['text']}")
    print(f"  aria-label: {debug_result['method1']['button']['ariaLabel']}")
else:
    print(f"  ❌ 検出失敗")

print(f"\n【検出方法2: aria-label】")
if debug_result['method2']['found']:
    print(f"  ✅ 検出成功")
    print(f"  テキスト: {debug_result['method2']['button']['text']}")
    print(f"  aria-label: {debug_result['method2']['button']['ariaLabel']}")
    print(f"  data-control-name: {debug_result['method2']['button']['dataControlName']}")
else:
    print(f"  ❌ 検出失敗")

print(f"\n【検出方法3: モーダル内プライマリボタン】")
if debug_result['method3']['found']:
    print(f"  ✅ 検出成功")
    print(f"  テキスト: {debug_result['method3']['button']['text']}")
    print(f"  aria-label: {debug_result['method3']['button']['ariaLabel']}")
    print(f"  data-control-name: {debug_result['method3']['button']['dataControlName']}")
else:
    print(f"  ❌ 検出失敗")

print(f"\n【検出方法4: テキスト検索】")
if debug_result['method4']['found']:
    print(f"  ✅ 検出成功")
    print(f"  テキスト: {debug_result['method4']['button']['text']}")
    print(f"  data-control-name: {debug_result['method4']['button']['dataControlName']}")
else:
    print(f"  ❌ 検出失敗")

print(f"\n【モーダル内の全ボタン】")
print(f"ボタン数: {len(debug_result['allButtons'])}個\n")

for btn in debug_result['allButtons']:
    print(f"ボタン #{btn['index']}:")
    print(f"  テキスト: {repr(btn['text'][:50])}")
    print(f"  aria-label: {repr(btn['ariaLabel'][:60])}")
    print(f"  data-control-name: {btn['dataControlName']}")
    print(f"  クラス: {btn['className'][:70]}")
    print(f"  disabled: {btn['disabled']}\n")

print("="*70)
print("💡 診断結果")
print("="*70)

success_methods = []
if debug_result['method1']['found']:
    success_methods.append('方法1 (data-control-name)')
if debug_result['method2']['found']:
    success_methods.append('方法2 (aria-label)')
if debug_result['method3']['found']:
    success_methods.append('方法3 (modal primary)')
if debug_result['method4']['found']:
    success_methods.append('方法4 (text)')

if success_methods:
    print(f"\n✅ ボタン検出成功: {', '.join(success_methods)}")
    print("\n推奨アクション:")
    print("  現在のコードは正しく動作するはずです")
    print("  もし動作しない場合:")
    print("  1. 待機時間を5秒に延長")
    print("  2. モーダルが完全にレンダリングされるまで待機")
else:
    print(f"\n❌ 全ての方法でボタン検出失敗")
    print("\n原因:")
    print("  - モーダル内にボタンが存在しない")
    print("  - ボタンのテキスト/属性が異なる")
    print("  - 待機時間が不足している")
    print("\n上記の「モーダル内の全ボタン」を確認して、")
    print("実際のボタンのテキストや属性を教えてください")

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます（モーダルを目視確認してください）...")
driver.quit()
