# debug_message_button.py
# メッセージボタンの検出問題を調査

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

def debug_message_button(driver):
    """メッセージボタンの検出を調査"""

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
    print(f"🔍 メッセージボタンの検出を調査")
    print(f"{'='*70}\n")
    print(f"ターゲット: {name}")
    print(f"URL: {profile_url}\n")

    # プロフィールに移動
    driver.get(profile_url)
    print("1️⃣ プロフィールページに移動しました")

    # 段階的に待機時間を増やして確認
    for wait_time in [2, 4, 6, 8]:
        print(f"\n{'='*70}")
        print(f"⏱️  待機時間: {wait_time}秒後の状態")
        print(f"{'='*70}\n")

        if wait_time > 2:
            time.sleep(wait_time - 2)
        else:
            time.sleep(wait_time)

        # 全てのボタンを列挙
        script = """
        const buttons = Array.from(document.querySelectorAll('button'));
        const results = [];

        for (let i = 0; i < buttons.length; i++) {
            const btn = buttons[i];
            const text = btn.textContent.trim();
            const ariaLabel = btn.getAttribute('aria-label') || '';

            // メッセージ関連のボタンだけ抽出
            if (text.includes('メッセージ') || text.includes('Message') ||
                ariaLabel.includes('メッセージ') || ariaLabel.includes('Message')) {

                const rect = btn.getBoundingClientRect();
                const computedStyle = window.getComputedStyle(btn);

                results.push({
                    index: i,
                    text: text.substring(0, 50),
                    ariaLabel: ariaLabel.substring(0, 100),
                    className: btn.className.substring(0, 100),
                    disabled: btn.disabled,
                    visible: computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden',
                    inViewport: rect.top >= 0 && rect.left >= 0 &&
                                rect.bottom <= window.innerHeight &&
                                rect.right <= window.innerWidth,
                    top: Math.round(rect.top),
                    left: Math.round(rect.left),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                });
            }
        }

        return results;
        """

        try:
            buttons = driver.execute_script(script)

            if buttons:
                print(f"✅ メッセージ関連ボタンを {len(buttons)} 個検出しました\n")

                for idx, btn in enumerate(buttons, start=1):
                    print(f"--- ボタン {idx} ---")
                    print(f"テキスト: {btn['text']}")
                    print(f"aria-label: {btn['ariaLabel']}")
                    print(f"クラス: {btn['className']}")
                    print(f"無効化: {btn['disabled']}")
                    print(f"表示状態: {btn['visible']}")
                    print(f"ビューポート内: {btn['inViewport']}")
                    print(f"位置: top={btn['top']}px, left={btn['left']}px")
                    print(f"サイズ: {btn['width']}x{btn['height']}px")
                    print()
            else:
                print("⚠️ メッセージ関連ボタンが見つかりません\n")

        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()

    # Seleniumの各戦略で試行
    print(f"\n{'='*70}")
    print(f"🎯 Selenium戦略テスト")
    print(f"{'='*70}\n")

    strategies = [
        ("XPath: aria-label contains 'メッセージ'", By.XPATH, "//button[contains(@aria-label, 'メッセージ')]"),
        ("XPath: aria-label contains 'Message'", By.XPATH, "//button[contains(@aria-label, 'Message')]"),
        ("XPath: text contains 'メッセージ'", By.XPATH, "//button[contains(., 'メッセージ')]"),
        ("XPath: text contains 'Message'", By.XPATH, "//button[contains(., 'Message')]"),
        ("CSS: [aria-label*='メッセージ']", By.CSS_SELECTOR, "button[aria-label*='メッセージ']"),
        ("CSS: [aria-label*='Message']", By.CSS_SELECTOR, "button[aria-label*='Message']"),
    ]

    for strategy_name, by_type, selector in strategies:
        try:
            elements = driver.find_elements(by_type, selector)
            if elements:
                print(f"✅ {strategy_name}: {len(elements)} 個検出")
                for idx, elem in enumerate(elements, start=1):
                    try:
                        aria_label = elem.get_attribute('aria-label') or ''
                        text = elem.text[:30] if elem.text else ''
                        is_displayed = elem.is_displayed()
                        is_enabled = elem.is_enabled()
                        print(f"   [{idx}] aria-label='{aria_label[:50]}' text='{text}' displayed={is_displayed} enabled={is_enabled}")
                    except:
                        print(f"   [{idx}] 属性取得エラー")
            else:
                print(f"❌ {strategy_name}: 検出できず")
        except Exception as e:
            print(f"❌ {strategy_name}: エラー - {e}")

    print(f"\n{'='*70}")
    print(f"🎯 調査完了")
    print(f"{'='*70}\n")
    print("ブラウザはそのまま開いています。")
    print("画面を確認し、Enterキーを押してブラウザを閉じます。\n")

    input("Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_message_button(driver)
