# debug_manual_input_test.py
# メッセージボタン押下後に停止して、手動入力テストを実施

import os
import time
import pickle
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
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

def test_manual_input(driver):
    """メッセージボタン押下後に停止して手動入力テスト"""

    # スコアファイルから最初のプロフィールを取得
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
    print(f"🧪 手動入力テスト")
    print(f"{'='*70}\n")
    print(f"ターゲット: {name}")
    print(f"URL: {profile_url}\n")

    # プロフィールに移動
    driver.get(profile_url)
    time.sleep(3)

    # ページを下にスクロールしてボタンを表示領域に入れる
    driver.execute_script("window.scrollTo(0, 400);")
    time.sleep(1)

    print("1️⃣ プロフィールページに移動しました\n")

    # メッセージボタンを探す
    message_btn = None

    try:
        # 戦略1: WebDriverWaitでaria-labelを待機
        try:
            message_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
                ))
            )
            print("2️⃣ ✅ メッセージボタン検出（戦略1: aria-label）\n")
        except TimeoutException:
            pass

        # 戦略2: テキストで検索
        if not message_btn:
            try:
                message_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(., 'メッセージ') or contains(., 'Message')]"
                    ))
                )
                print("2️⃣ ✅ メッセージボタン検出（戦略2: テキスト）\n")
            except TimeoutException:
                pass

        if not message_btn:
            print("❌ メッセージボタンが見つかりません")
            return

        # ボタンが表示されるまで待機
        if not message_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
            time.sleep(1)

        # メッセージボタンをクリック
        try:
            message_btn.click()
        except Exception:
            # 通常クリックが失敗した場合、JavaScriptでクリック
            driver.execute_script("arguments[0].click();", message_btn)

        time.sleep(3)
        print("3️⃣ ✅ メッセージボタンをクリック\n")

    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return

    # ポップアップが表示されたか確認
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
        )
        print("4️⃣ ✅ ポップアップが表示されました\n")
    except TimeoutException:
        print("❌ ポップアップが表示されません")
        return

    # 送信ボタンの初期状態を確認
    try:
        send_btn = driver.find_element(
            By.XPATH,
            "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send') or contains(., '送信') or contains(., 'Send')]"
        )
        is_disabled = send_btn.get_attribute("disabled")
        aria_disabled = send_btn.get_attribute("aria-disabled")
        print(f"5️⃣ 送信ボタンの初期状態:")
        print(f"   disabled: {is_disabled}")
        print(f"   aria-disabled: {aria_disabled}")
        print()
    except:
        print("⚠️ 送信ボタンが見つかりません\n")

    # メッセージ入力欄を確認
    try:
        message_box = driver.find_element(
            By.CSS_SELECTOR,
            "[role='dialog'] [contenteditable='true']"
        )
        print(f"6️⃣ ✅ メッセージ入力欄を検出\n")
    except:
        print("⚠️ メッセージ入力欄が見つかりません\n")

    # ここで停止
    print(f"{'='*70}")
    print(f"🛑 自動処理を停止しました")
    print(f"{'='*70}\n")
    print("📝 手動でテキストを入力して、送信ボタンが活性化するか確認してください。\n")
    print("【確認手順】")
    print("1. ブラウザのポップアップ内のメッセージ入力欄をクリック")
    print("2. 適当なテキストを入力（例: 'テスト'）")
    print("3. 送信ボタンが活性化するか確認")
    print("   - 活性化する → 自動入力のアプローチに問題あり")
    print("   - 活性化しない → 別の原因（受信者選択など）\n")
    print("確認が終わったら、Enterキーを押してブラウザを閉じます。\n")

    input("Enterキーを押してブラウザを閉じます...")

    # 最終状態を確認
    try:
        send_btn = driver.find_element(
            By.XPATH,
            "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send') or contains(., '送信') or contains(., 'Send')]"
        )
        is_disabled = send_btn.get_attribute("disabled")
        aria_disabled = send_btn.get_attribute("aria-disabled")
        print(f"\n最終状態:")
        print(f"   disabled: {is_disabled}")
        print(f"   aria-disabled: {aria_disabled}\n")
    except:
        pass

    driver.quit()

if __name__ == "__main__":
    driver = login()
    test_manual_input(driver)
