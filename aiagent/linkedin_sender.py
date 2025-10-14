# aiagent/linkedin_sender.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import csv
import random
import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 他モジュール
from aiagent.linkedin_login import linkedin_login
from aiagent.message_generator import generate_message
from aiagent.analyzer import analyze_candidates  # ← 統合ポイント

# パス定義
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data")
LOG_PATH = os.path.join(os.path.dirname(__file__), "../logs")
SENT_LOG_PATH = os.path.join(DATA_PATH, "sent_log.csv")


# ---------------------------------------
# 送信履歴の読み込み・書き込み
# ---------------------------------------
def load_sent_log():
    sent = set()
    if os.path.exists(SENT_LOG_PATH):
        with open(SENT_LOG_PATH, newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sent.add(row["profile_url"])
    return sent


def append_sent_log(profile_url, name, message, score):
    fieldnames = ["date", "profile_url", "name", "message", "score"]
    new_row = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "profile_url": profile_url,
        "name": name,
        "message": message,
        "score": score
    }
    file_exists = os.path.exists(SENT_LOG_PATH)
    with open(SENT_LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(new_row)


# ---------------------------------------
# 実際の送信ロジック
# ---------------------------------------
def send_connection_requests():
    """
    AIスコアリング済みの候補者を対象に、
    自動で接続リクエスト＋メッセージを送信する。
    """

    # 🔍 候補者のAIスコアリング実行
    print("\n🧠 候補者のAIスコアリングを実施中...")
    candidates = analyze_candidates()  # → decision=send のみ返る
    if not candidates:
        print("🚫 送信対象が見つかりません。")
        return

    print(f"🎯 送信対象: {len(candidates)} 名\n")

    # ログイン（Cookie利用）
    driver = linkedin_login()
    wait = WebDriverWait(driver, 15)

    # 送信済みリスト読み込み
    sent_log = load_sent_log()
    print(f"📚 既送信件数: {len(sent_log)}")

    sent_count = 0
    today = datetime.date.today()

    for candidate in candidates:
        name = candidate.get("name")
        url = candidate.get("profile_url")
        score = candidate.get("score", "?")

        if url in sent_log:
            print(f"⏭️ {name} は既に送信済み。スキップ。")
            continue

        if sent_count >= 30:
            print("📈 本日の上限（30件）に達しました。終了します。")
            break

        message = generate_message(name=name, role=candidate.get("role", ""))
        print(f"\n🔹 [{sent_count+1}] {name}（AIスコア: {score}）に送信開始...")

        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2)

            # 接続ボタン探索
            connect_selectors = [
                "//button[contains(., '接続')]",
                "//button[contains(., 'Connect')]",
                "//button[@aria-label='Connect']",
                "//button[@data-control-name='connect']",
            ]

            connect_btn = None
            for selector in connect_selectors:
                try:
                    connect_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if connect_btn:
                        break
                except Exception:
                    continue

            if not connect_btn:
                raise NoSuchElementException("接続ボタンが見つかりません。")

            connect_btn.click()
            time.sleep(2)

            # 「メッセージを追加」
            add_note_selectors = [
                "//button[contains(., 'メッセージを追加')]",
                "//button[contains(., 'Add a note')]"
            ]
            add_note_btn = None
            for selector in add_note_selectors:
                try:
                    add_note_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    if add_note_btn:
                        break
                except Exception:
                    continue

            if not add_note_btn:
                raise NoSuchElementException("メッセージ追加ボタンが見つかりません。")

            add_note_btn.click()
            time.sleep(2)

            # メッセージ入力
            msg_box = wait.until(
                EC.presence_of_element_located((By.XPATH, "//textarea[contains(@id, 'custom-message')]"))
            )
            msg_box.clear()
            msg_box.send_keys(message)
            time.sleep(1)

            # 「送信」
            send_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '送信') or contains(., 'Send')]"))
            )
            send_btn.click()
            print(f"✅ {name} に送信完了！（スコア: {score}）")

            append_sent_log(url, name, message, score)
            sent_count += 1

            # 次の送信までランダム待機
            delay = random.uniform(7, 15)
            print(f"⏳ 次まで {delay:.1f} 秒待機中...")
            time.sleep(delay)

        except Exception as e:
            print(f"⚠️ {name} への送信中にエラー: {e}")
            try:
                os.makedirs(LOG_PATH, exist_ok=True)
                filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}.png"
                driver.save_screenshot(os.path.join(LOG_PATH, filename))
                print(f"🖼 スクリーンショット保存: {filename}")
            except Exception as ss_e:
                print(f"スクリーンショット保存エラー: {ss_e}")
            continue

    print(f"\n🎯 本日合計 {sent_count} 件送信完了。")

    # デバッグモード設定
    debug_mode = os.getenv("DEBUG_MODE", "False").lower() == "true"
    if debug_mode:
        print("🧩 DEBUG_MODE=True → ブラウザを開いたまま保持中。")
    else:
        driver.quit()
        print("✅ ブラウザを自動終了しました。")


# --- スクリプトとして直接実行された場合 ---
if __name__ == "__main__":
    send_connection_requests()
