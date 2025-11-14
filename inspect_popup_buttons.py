#!/usr/bin/env python3
# ポップアップ内のボタンを調査

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
    for i in range(3):
        driver.execute_script("arguments[0].scrollBy(0, 400);", container)
        time.sleep(2)
except:
    for i in range(3):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(2)
print("✅ スクロール完了\n")
time.sleep(3)

# 最初の「つながる」ボタンを探してクリック
script = """
const connectLinks = document.querySelectorAll('a[aria-label*="つながりを申請"]');
if (connectLinks.length > 0) {
    const firstLink = connectLinks[0];
    const ariaLabel = firstLink.getAttribute('aria-label');

    firstLink.scrollIntoView({ block: 'center', behavior: 'instant' });
    firstLink.click();

    return {
        success: true,
        ariaLabel: ariaLabel,
        linkCount: connectLinks.length
    };
}
return { success: false };
"""

try:
    result = driver.execute_script(script)

    if result['success']:
        print(f"✅ 「つながる」ボタンをクリックしました")
        print(f"   候補者: {result['ariaLabel']}")
        print(f"   検出数: {result['linkCount']}件\n")

        print("⏳ ポップアップの読み込みを待機中...")
        time.sleep(5)  # ポップアップが完全に表示されるまで待つ

        # ポップアップ内の全ボタンを調査
        print("\n" + "="*70)
        print("🔍 ポップアップ内のボタンを調査")
        print("="*70 + "\n")

        button_info = driver.execute_script("""
            const result = {
                allButtons: [],
                allLinks: [],
                modalInfo: {
                    found: false,
                    className: '',
                    html: ''
                }
            };

            // モーダル/ダイアログを検出
            const modals = document.querySelectorAll('[role="dialog"], [role="modal"], .modal, .artdeco-modal');
            if (modals.length > 0) {
                const modal = modals[0];
                result.modalInfo.found = true;
                result.modalInfo.className = modal.className.substring(0, 100);
                result.modalInfo.html = modal.outerHTML.substring(0, 500);

                // モーダル内のボタン
                modal.querySelectorAll('button').forEach((btn, idx) => {
                    result.allButtons.push({
                        index: idx,
                        text: btn.textContent.trim(),
                        className: btn.className.substring(0, 100),
                        ariaLabel: btn.getAttribute('aria-label') || '',
                        type: btn.type || '',
                        disabled: btn.disabled,
                        outerHTML: btn.outerHTML.substring(0, 300)
                    });
                });

                // モーダル内のリンク
                modal.querySelectorAll('a').forEach((link, idx) => {
                    const text = link.textContent.trim();
                    if (text.length > 0 && text.length < 100) {
                        result.allLinks.push({
                            index: idx,
                            text: text,
                            href: link.href,
                            className: link.className.substring(0, 100),
                            role: link.getAttribute('role') || ''
                        });
                    }
                });
            } else {
                // モーダルが見つからない場合、全ボタンを調査
                document.querySelectorAll('button').forEach((btn, idx) => {
                    result.allButtons.push({
                        index: idx,
                        text: btn.textContent.trim(),
                        className: btn.className.substring(0, 100),
                        ariaLabel: btn.getAttribute('aria-label') || '',
                        type: btn.type || '',
                        disabled: btn.disabled,
                        outerHTML: btn.outerHTML.substring(0, 300)
                    });
                });
            }

            return result;
        """)

        # 結果を表示
        if button_info['modalInfo']['found']:
            print("✅ モーダル/ダイアログを検出しました")
            print(f"   クラス: {button_info['modalInfo']['className']}")
            print(f"   HTML: {button_info['modalInfo']['html'][:200]}...\n")
        else:
            print("⚠️ モーダル/ダイアログが見つかりません\n")

        print(f"検出されたボタン数: {len(button_info['allButtons'])}個\n")

        if button_info['allButtons']:
            print("【ボタン一覧】")
            for btn in button_info['allButtons']:
                print(f"\nボタン #{btn['index']}:")
                print(f"  テキスト: {repr(btn['text'][:60])}")
                print(f"  aria-label: {repr(btn['ariaLabel'][:60])}")
                print(f"  クラス: {btn['className'][:70]}")
                print(f"  type: {btn['type']}")
                print(f"  disabled: {btn['disabled']}")

                # 「挨拶なしで送信」に一致するか
                if ('挨拶なしで送信' in btn['text'] or
                    'Send without a note' in btn['text'] or
                    '挨拶なしで送信' in btn['ariaLabel'] or
                    'Send without a note' in btn['ariaLabel']):
                    print("  🎯 ★★★ これが目的のボタンです！★★★")

                print(f"  HTML: {btn['outerHTML'][:150]}...")

        if button_info['allLinks']:
            print(f"\n\n検出されたリンク数: {len(button_info['allLinks'])}個\n")
            print("【リンク一覧】")
            for link in button_info['allLinks'][:10]:
                print(f"\nリンク #{link['index']}:")
                print(f"  テキスト: {repr(link['text'][:60])}")
                print(f"  href: {link['href'][:80]}")
                print(f"  role: {link['role']}")

        print("\n" + "="*70)
        print("💡 診断結果")
        print("="*70)

        # 「挨拶なしで送信」ボタンが見つかったか
        found_send_button = any(
            '挨拶なしで送信' in btn['text'] or
            'Send without a note' in btn['text'] or
            '挨拶なしで送信' in btn['ariaLabel'] or
            'Send without a note' in btn['ariaLabel']
            for btn in button_info['allButtons']
        )

        if found_send_button:
            print("\n✅ 「挨拶なしで送信」ボタンが見つかりました！")
            print("   → コードは正しく動作するはずです")
        else:
            print("\n❌ 「挨拶なしで送信」ボタンが見つかりません")
            print("\n考えられる原因:")
            print("  1. ボタンのテキストが異なる（上記の一覧を確認）")
            print("  2. 待機時間が足りない（5秒以上必要）")
            print("  3. ボタンが<button>ではなく<a>タグ")
            print("  4. モーダルがiframe内にある")

            if button_info['allButtons']:
                print("\n💡 実際のボタンテキスト:")
                for btn in button_info['allButtons'][:5]:
                    if btn['text']:
                        print(f"   - \"{btn['text'][:50]}\"")

    else:
        print("❌ 「つながる」ボタンが見つかりませんでした")

except Exception as e:
    print(f"❌ エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
input("\nEnter キーを押してブラウザを閉じます（ポップアップを目視確認してください）...")
driver.quit()
