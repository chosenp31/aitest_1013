# aiagent/linkedin_sender.py
# ✅ 手動ログイン済みブラウザ再利用版（Cookie不使用・安全モード）

import time
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException

# ======================================
# 設定
# ======================================
DATA_PATH = "../data/messages.csv"
LIMIT = 2  # 安全モード：上位2件のみ送信


def send_connection_requests(driver):
    """
    既に手動ログイン済みの driver（Seleniumブラウザ）を使って
    メッセージ付き接続リクエストを送信する
    """
    print("🚀 LinkedIn 接続リクエスト送信モジュール（手動ログインモード）開始")

    # メッセージデータを読み込み
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            messages = list(reader)
    except FileNotFoundError:
        print(f"❌ ファイルが見つかりません: {DATA_PATH}")
        return

    if not messages:
        print("⚠️ メッセージ送信対象が空です。")
        return

    print(f"📤 接続リクエスト対象: {min(len(messages), LIMIT)} 件（上限 {LIMIT} 件）")

    sent_count = 0

    for idx, msg in enumerate(messages[:LIMIT], start=1):
        name = msg.get("name", "不明")
        profile_url = msg.get("url") or msg.get("profile_url")
        custom_message = msg.get("message", "")

        if not profile_url:
            print(f"⚠️ {name}: URLが指定されていません。スキップ。")
            continue

        print(f"\n[{idx}/{LIMIT}] {name} に接続リクエスト送信中...")

        try:
            driver.get(profile_url)
            time.sleep(3)

            # Step 1: 「つながりを申請」 or 「Connect」ボタン
            connect_btn = None
            connect_btns = driver.find_elements(
                By.XPATH,
                "//button[contains(text(),'つながりを申請')] | //button[contains(text(),'Connect')]"
            )

            if connect_btns:
                connect_btn = connect_btns[0]
            else:
                print(f"⚪ {name}: 接続ボタンが見つかりません（既に接続済み or 制限中）")
                continue

            try:
                connect_btn.click()
                time.sleep(2)
            except ElementClickInterceptedException:
                driver.execute_script("arguments[0].click();", connect_btn)
                time.sleep(2)

            # Step 2: 「メッセージを追加」
            try:
                message_add_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//button[contains(text(),'メッセージを追加')] | //button[contains(text(),'Add a note')]"
                    ))
                )
                message_add_btn.click()
                time.sleep(1)
            except TimeoutException:
                print(f"⚠️ {name}: 『メッセージを追加』ボタンが見つかりません。スキップ。")
                continue

            # Step 3: メッセージ入力と送信
            try:
                textarea = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
                textarea.clear()
                textarea.send_keys(custom_message)
                time.sleep(1)

                send_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(text(),'送信')] | //button[contains(text(),'Send')]"
                )
                send_btn.click()
                print(f"✅ {name}: メッセージ送信完了")

                sent_count += 1
                time.sleep(3)

            except Exception as e:
                print(f"⚠️ {name}: メッセージ送信処理でエラー → {e}")
                continue

        except Exception as e:
            print(f"❌ {name}: プロフィール処理中にエラー → {e}")
            continue

    print(f"\n✅ 送信完了: {sent_count} 件（最大 {LIMIT} 件中）")
    print("🪄 全処理完了。ウィンドウを閉じてもOKです。")
