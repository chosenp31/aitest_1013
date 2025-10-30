# debug_message_popup.py
# メッセージ送信ポップアップの構造を詳細調査

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")
SCORED_FILE = os.path.join(DATA_DIR, "scored_connections.json")

def login():
    """LinkedInにログイン"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    if os.path.exists(COOKIE_FILE):
        print("🔑 Cookie自動ログイン...")
        driver.get("https://www.linkedin.com")
        time.sleep(2)

        try:
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

            driver.get("https://www.linkedin.com/feed")
            time.sleep(5)

            current_url = driver.current_url
            if ("feed" in current_url or "home" in current_url) and "login" not in current_url:
                print("✅ 自動ログイン成功！")
                return driver
        except Exception as e:
            print(f"⚠️ エラー: {e}")

    print("⚠️ 手動ログインが必要です")
    return driver

def debug_message_popup(driver):
    """メッセージポップアップの構造を調査"""

    # スコアファイルから最初のプロフィールを取得
    import json

    if not os.path.exists(SCORED_FILE):
        print("❌ scored_connections.json が見つかりません")
        return

    with open(SCORED_FILE, "r", encoding="utf-8") as f:
        scored = json.load(f)

    # "send" のターゲットを取得
    targets = [s for s in scored if s.get("decision") == "send"]

    if not targets:
        print("❌ 送信対象が見つかりません")
        return

    target = targets[0]
    profile_url = target.get("profile_url")
    name = target.get("name", "不明")

    print(f"\n{'='*70}")
    print(f"🔍 メッセージポップアップの構造を調査")
    print(f"{'='*70}\n")
    print(f"ターゲット: {name}")
    print(f"URL: {profile_url}\n")

    # プロフィールに移動
    driver.get(profile_url)
    time.sleep(4)

    print("1️⃣ プロフィールページに移動しました")

    # メッセージボタンを探す
    try:
        message_btn = driver.find_element(
            By.XPATH,
            "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
        )
        print(f"2️⃣ メッセージボタンを検出: {message_btn.get_attribute('aria-label')}")

        message_btn.click()
        time.sleep(3)
        print("3️⃣ メッセージボタンをクリックしました\n")

    except Exception as e:
        print(f"❌ メッセージボタンの検出に失敗: {e}")
        return

    # ポップアップの構造を調査
    print(f"{'='*70}")
    print(f"📊 ポップアップDOM構造の分析")
    print(f"{'='*70}\n")

    script = """
    // ポップアップのダイアログを検出
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));

    const results = [];

    for (let i = 0; i < dialogs.length; i++) {
        const dialog = dialogs[i];

        // contenteditable を探す
        const editables = dialog.querySelectorAll('[contenteditable="true"]');

        for (let j = 0; j < editables.length; j++) {
            const editable = editables[j];

            results.push({
                dialogIndex: i,
                editableIndex: j,
                tagName: editable.tagName,
                className: editable.className,
                id: editable.id || 'N/A',
                ariaLabel: editable.getAttribute('aria-label') || 'N/A',
                placeholder: editable.getAttribute('placeholder') || 'N/A',
                role: editable.getAttribute('role') || 'N/A',
                parentClassName: editable.parentElement ? editable.parentElement.className : 'N/A',
                parentTagName: editable.parentElement ? editable.parentElement.tagName : 'N/A'
            });
        }
    }

    return results;
    """

    try:
        editables = driver.execute_script(script)

        if editables:
            print(f"✅ contenteditable 要素を {len(editables)} 個検出しました\n")

            for idx, ed in enumerate(editables, start=1):
                print(f"--- contenteditable {idx} ---")
                print(f"ダイアログ番号: {ed['dialogIndex']}")
                print(f"タグ: {ed['tagName']}")
                print(f"クラス: {ed['className'][:100]}")
                print(f"ID: {ed['id']}")
                print(f"aria-label: {ed['ariaLabel']}")
                print(f"placeholder: {ed['placeholder']}")
                print(f"role: {ed['role']}")
                print(f"親要素タグ: {ed['parentTagName']}")
                print(f"親要素クラス: {ed['parentClassName'][:100]}")
                print()
        else:
            print("⚠️ contenteditable 要素が見つかりません\n")

        # 送信ボタンを探す
        print(f"{'='*70}")
        print(f"🔍 送信ボタンの検出")
        print(f"{'='*70}\n")

        button_script = """
        const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
        const results = [];

        for (let i = 0; i < dialogs.length; i++) {
            const dialog = dialogs[i];

            // 送信ボタンを探す（複数パターン）
            const buttons = dialog.querySelectorAll('button');

            for (const btn of buttons) {
                const text = btn.textContent.trim();
                const ariaLabel = btn.getAttribute('aria-label') || '';

                if (text.includes('送信') || text.includes('Send') ||
                    ariaLabel.includes('送信') || ariaLabel.includes('Send')) {
                    results.push({
                        dialogIndex: i,
                        text: text,
                        ariaLabel: ariaLabel,
                        className: btn.className,
                        disabled: btn.disabled
                    });
                }
            }
        }

        return results;
        """

        send_buttons = driver.execute_script(button_script)

        if send_buttons:
            print(f"✅ 送信ボタンを {len(send_buttons)} 個検出しました\n")

            for idx, btn in enumerate(send_buttons, start=1):
                print(f"--- 送信ボタン {idx} ---")
                print(f"ダイアログ番号: {btn['dialogIndex']}")
                print(f"テキスト: {btn['text']}")
                print(f"aria-label: {btn['ariaLabel']}")
                print(f"クラス: {btn['className'][:100]}")
                print(f"無効化: {btn['disabled']}")
                print()
        else:
            print("⚠️ 送信ボタンが見つかりません\n")

        # 推奨セレクタを提示
        print(f"{'='*70}")
        print(f"💡 推奨セレクタ")
        print(f"{'='*70}\n")

        if editables:
            best_editable = editables[0]
            print("【メッセージ入力エリア】")

            # セレクタのパターンを提示
            if best_editable['className']:
                print(f"  CSS: [role=\"dialog\"] [contenteditable=\"true\"]")
                print(f"  または: div[contenteditable=\"true\"][role=\"textbox\"]")

            if best_editable['ariaLabel'] != 'N/A':
                print(f"  XPath: //div[@contenteditable='true'][@aria-label='{best_editable['ariaLabel']}']")

            print()

        if send_buttons:
            print("【送信ボタン】")
            print(f"  XPath: //button[contains(text(), '送信') or contains(@aria-label, '送信')]")
            print(f"  または: [role=\"dialog\"] button[aria-label*='送信']")
            print()

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*70}")
    print(f"🎯 調査完了")
    print(f"{'='*70}\n")
    print("ブラウザはそのまま開いています。")
    print("ポップアップを確認し、Enterキーを押してブラウザを閉じます。\n")

    input("Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_message_popup(driver)
