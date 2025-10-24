import os
import time
import random
import csv
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# =====================================================
# LinkedIn 自動ログイン＋接続送信（統合・安定版）
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
COOKIE_PATH = os.path.join(DATA_DIR, "cookies.pkl")
MESSAGE_CSV = os.path.join(DATA_DIR, "messages.csv")

# -----------------------------------------------------
# Step 1. ドライバ初期化
# -----------------------------------------------------
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service("/usr/local/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


# -----------------------------------------------------
# Step 2. Cookieを使ってLinkedInにログイン
# -----------------------------------------------------
def linkedin_login(driver):
    print("🔑 LinkedInログイン処理開始...")

    driver.get("https://www.linkedin.com/")
    time.sleep(2)

    if os.path.exists(COOKIE_PATH):
        try:
            with open(COOKIE_PATH, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    # ドメイン補正
                    if "domain" in cookie and cookie["domain"].startswith("."):
                        cookie["domain"] = "www.linkedin.com"
                    driver.add_cookie(cookie)

            driver.refresh()
            time.sleep(4)

            if "feed" in driver.current_url:
                print("✅ Cookieで自動ログイン成功")
                return True
            else:
                print("⚠️ Cookieログイン失敗 → 手動ログインを待機します")

        except Exception as e:
            print(f"⚠️ Cookie適用エラー: {e}")

    # --- 手動ログイン fallback ---
    print("👋 手動ログインを行ってください。ログイン完了後、自動でCookieを保存します。")
    driver.get("https://www.linkedin.com/login")

    while "feed" not in driver.current_url:
        time.sleep(3)

    cookies = driver.get_cookies()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(COOKIE_PATH, "wb") as f:
        pickle.dump(cookies, f)
    print("💾 Cookieを保存しました。")

    return True


# -----------------------------------------------------
# Step 3. 接続リクエスト送信（上位2件のみ）
# -----------------------------------------------------
def send_connection_requests(driver, limit=2):
    if not os.path.exists(MESSAGE_CSV):
        print(f"❌ ファイルが見つかりません: {MESSAGE_CSV}")
        return

    with open(MESSAGE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    if not candidates:
        print("⚠️ メッセージ送信対象が空です。")
        return

    targets = candidates[:limit]
    print(f"📤 接続リクエスト対象: {len(targets)} 件（上限 {limit} 件）")

    success_count = 0

    for idx, row in enumerate(targets):
        name = row.get("name", "不明")
        url = row.get("url", "")
        message = row.get("message", "")
        print(f"\n[{idx+1}/{len(targets)}] {name} に接続リクエスト送信中...")

        try:
            driver.get(url)
            time.sleep(random.uniform(5, 8))

            connect_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'接続')] | //button[contains(text(),'Connect')]")
            if not connect_btns:
                print(f"⚪ {name}: 接続ボタンが見つかりません（既に接続済みまたは制限中）")
                continue

            driver.execute_script("arguments[0].click();", connect_btns[0])
            time.sleep(random.uniform(3, 5))

            add_note_btns = driver.find_elements(By.XPATH, "//button[contains(text(),'メッセージを追加')] | //button[contains(text(),'Add a note')]")
            if add_note_btns:
                driver.execute_script("arguments[0].click();", add_note_btns[0])
                time.sleep(2)
                textarea = driver.find_element(By.TAG_NAME, "textarea")
                textarea.send_keys(message)
                time.sleep(1)
                send_btn = driver.find_element(By.XPATH, "//button[contains(text(),'送信')] | //button[contains(text(),'Send')]")
                driver.execute_script("arguments[0].click();", send_btn)
                print(f"✅ {name} に接続リクエスト送信完了")
                success_count += 1
            else:
                print(f"⚠️ {name}: メッセージ入力欄が見つかりませんでした。")

            time.sleep(random.uniform(8, 15))

            if success_count >= limit:
                print(f"\n🎯 上限 {limit} 件に達したため終了します。")
                break

        except Exception as e:
            print(f"❌ {name}: エラー発生 - {e}")
            continue

    print(f"\n✅ 送信完了: {success_count} 件")


# -----------------------------------------------------
# Step 4. メインパイプライン実行
# -----------------------------------------------------
def main():
    print("🚀 LinkedIn 自動化パイプライン（統合・安定版）開始")

    driver = init_driver()
    if linkedin_login(driver):
        send_connection_requests(driver, limit=2)
    else:
        print("❌ ログインに失敗しました。")
    driver.quit()

    print("\n✅ 全処理完了")


if __name__ == "__main__":
    main()
