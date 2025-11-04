# aiagent/linkedin_send_prepared_messages.py
# 生成済みメッセージを読み込んで送信

import os
import sys
import time
import csv
import pickle
import random
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# アカウント名の定義
AVAILABLE_ACCOUNTS = ["依田", "桜井", "田中"]

def select_account():
    """アカウントを選択"""
    print(f"\n{'='*70}")
    print(f"📋 使用するLinkedInアカウントを選択")
    print(f"{'='*70}")
    for idx, account in enumerate(AVAILABLE_ACCOUNTS, start=1):
        print(f"{idx}. {account}")
    print(f"{'='*70}\n")

    while True:
        choice = input(f"アカウント番号を入力 (1-{len(AVAILABLE_ACCOUNTS)}): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_ACCOUNTS):
                selected = AVAILABLE_ACCOUNTS[choice_num - 1]
                print(f"\n✅ 選択: {selected}\n")
                return selected
            else:
                print(f"⚠️ 1-{len(AVAILABLE_ACCOUNTS)}の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

def get_account_paths(account_name):
    """アカウント毎のディレクトリとファイルパスを取得"""
    account_dir = os.path.join(BASE_DIR, "data", account_name)
    os.makedirs(account_dir, exist_ok=True)

    return {
        'account_dir': account_dir,
        'cookie_file': os.path.join(account_dir, "linkedin_cookies.pkl"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv"),
        'message_log_file': os.path.join(account_dir, "message_logs.csv")
    }

# ==============================
# ログイン
# ==============================
def login(account_name, cookie_file):
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
    if os.path.exists(cookie_file):
        print(f"🔑 保存されたCookieを使用して自動ログイン中（アカウント: {account_name}）...")
        driver.get("https://www.linkedin.com")
        time.sleep(2)

        try:
            with open(cookie_file, "rb") as f:
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
                print("✅ 自動ログイン成功！\n")
                return driver
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(cookie_file)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(cookie_file):
                os.remove(cookie_file)

    # 手動ログイン
    print(f"🔑 LinkedIn 手動ログインモード開始（アカウント: {account_name}）...")
    print(f"⚠️  必ず '{account_name}' アカウントでログインしてください！")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了\n")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました（{account_name}用）\n")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}\n")

    return driver

# ==============================
# 生成済みメッセージ読み込み
# ==============================
def load_generated_messages(generated_messages_file, message_log_file):
    """生成済みメッセージを読み込み（未送信のみ）"""

    print(f"{'='*70}")
    print(f"📂 Step 1: 生成済みメッセージ読み込み")
    print(f"{'='*70}\n")

    if not os.path.exists(generated_messages_file):
        print(f"❌ エラー: {generated_messages_file} が見つかりません")
        print("⚠️  先に linkedin_prepare_messages.py を実行してメッセージを生成してください\n")
        return []

    # 生成済みメッセージを読み込み
    messages = []
    with open(generated_messages_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages.append(row)

    print(f"📋 生成済みメッセージ: {len(messages)} 件\n")

    # 送信済みのURLをセット化
    sent_urls = set()
    if os.path.exists(message_log_file):
        try:
            with open(message_log_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    result = row.get('result', '')
                    profile_url = row.get('profile_url', '')
                    # result="success"のみ除外
                    if result == "success" and profile_url:
                        sent_urls.add(profile_url)

            print(f"📂 送信済みデータ読み込み: {len(sent_urls)} 件（success のみ）\n")
        except Exception as e:
            print(f"⚠️ 送信ログ読み込みエラー: {e}\n")

    # 未送信メッセージをフィルタリング
    unsent_messages = []
    skipped_count = 0

    for msg in messages:
        profile_url = msg.get('profile_url', '')
        if profile_url not in sent_urls:
            unsent_messages.append(msg)
        else:
            skipped_count += 1

    print(f"📋 フィルタリング結果:")
    print(f"   生成済み: {len(messages)} 件")
    print(f"   既送信スキップ: {skipped_count} 件")
    print(f"   未送信: {len(unsent_messages)} 件\n")

    return unsent_messages

# ==============================
# メッセージ送信
# ==============================
def send_message(driver, profile_url, name, message):
    """メッセージを送信"""
    try:
        # プロフィールページへ移動
        driver.get(profile_url)
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1)

        # メッセージボタンを探す
        message_btn = None

        try:
            message_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
                ))
            )
        except TimeoutException:
            pass

        if not message_btn:
            try:
                message_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(., 'メッセージ') or contains(., 'Message')]"
                    ))
                )
            except TimeoutException:
                pass

        if not message_btn:
            return "error", "メッセージボタン未検出", "button_not_found"

        if not message_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
            time.sleep(1)

        try:
            message_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", message_btn)

        time.sleep(3)

        # ポップアップ待機
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
            )
            time.sleep(1)
        except TimeoutException:
            return "error", "ポップアップ表示タイムアウト", "popup_timeout"

        # メッセージ入力欄を探す
        message_box = None

        try:
            message_box = driver.find_element(
                By.CSS_SELECTOR,
                "[role='dialog'] [contenteditable='true']"
            )
        except NoSuchElementException:
            try:
                message_box = driver.find_element(
                    By.CSS_SELECTOR,
                    "div[contenteditable='true'][role='textbox']"
                )
            except NoSuchElementException:
                pass

        if not message_box:
            return "error", "メッセージ入力欄が見つかりません", "message_box_not_found"

        # メッセージを入力
        driver.execute_script("arguments[0].focus();", message_box)
        time.sleep(0.5)
        message_box.click()
        time.sleep(0.5)

        try:
            message_box.send_keys(message)
            time.sleep(0.5)
        except Exception as e:
            return "error", f"メッセージ入力エラー: {e}", "message_input_failed"

        # 送信ボタンを探す
        send_btn = None

        try:
            send_btn = driver.find_element(
                By.XPATH,
                "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send')]"
            )
        except NoSuchElementException:
            try:
                send_btn = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//button[contains(., '送信') or contains(., 'Send')]"
                )
            except NoSuchElementException:
                pass

        if not send_btn:
            return "error", "送信ボタンが見つかりません", "send_button_not_found"

        # 送信ボタンが活性化されるまで待機
        button_enabled = False

        for i in range(20):
            is_disabled = send_btn.get_attribute("disabled")
            aria_disabled = send_btn.get_attribute("aria-disabled")

            if is_disabled is None and (aria_disabled is None or aria_disabled == "false"):
                button_enabled = True
                break

            time.sleep(0.5)

        # 送信ボタンをクリック
        try:
            send_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", send_btn)

        time.sleep(2)

        if button_enabled:
            # ポップアップを確実に閉じる（複数の方法を試す）
            # 方法1: 新鮮なbody要素にESCAPEキーを送信
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(1)
            except Exception:
                pass

            # 方法2: dialogにESCAPEキーを送信
            try:
                dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
                dialog.send_keys(Keys.ESCAPE)
                time.sleep(1)
            except Exception:
                pass

            # 方法3: 閉じるボタンをクリック
            try:
                close_btn = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//button[contains(@aria-label, '閉じる') or contains(@aria-label, 'Dismiss') or contains(@aria-label, 'Close')]"
                )
                close_btn.click()
                time.sleep(1)
            except Exception:
                pass

            # 方法4: 15秒間ポーリングでポップアップの消失を確認
            popup_closed = False
            for i in range(15):
                try:
                    driver.find_element(By.XPATH, "//div[@role='dialog']")
                    time.sleep(1)
                except NoSuchElementException:
                    popup_closed = True
                    break

            # 方法5: JavaScriptで強制的にダイアログとオーバーレイを削除
            if not popup_closed:
                driver.execute_script("""
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    dialogs.forEach(d => d.remove());

                    const overlays = document.querySelectorAll('[class*="msg-overlay"]');
                    overlays.forEach(o => o.remove());
                """)
                time.sleep(1)

            # 次の送信前に2秒待機
            time.sleep(2)

            return "success", "", "sent"
        else:
            return "error", "送信ボタンが活性化されませんでした", "button_not_enabled"

    except Exception as e:
        return "error", f"予期しないエラー: {e}", "unexpected_error"

def log_message(name, profile_url, result, message_log_file, error="", details=""):
    """送信結果をログに記録"""
    file_exists = os.path.exists(message_log_file)

    with open(message_log_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "name", "profile_url", "result", "error", "details"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "profile_url": profile_url,
            "result": result,
            "error": error,
            "details": details
        })

# ==============================
# メッセージ送信処理
# ==============================
def send_all_messages(driver, messages, max_messages, message_log_file):
    """全メッセージを送信"""

    print(f"{'='*70}")
    print(f"📨 Step 2: メッセージ送信")
    print(f"{'='*70}")
    print(f"送信対象: {len(messages)} 件")
    print(f"上限: {max_messages} 件")
    print(f"{'='*70}\n")

    # 上限件数まで絞り込み
    messages = messages[:max_messages]

    # メッセージ一覧を表示
    print(f"{'='*70}")
    print(f"📋 送信予定メッセージ一覧")
    print(f"{'='*70}\n")

    for idx, msg in enumerate(messages, start=1):
        print(f"--- [{idx}/{len(messages)}] {msg['name']} (スコア: {msg['total_score']}点) ---")
        print(f"{msg['message']}")
        print()

    # ユーザーに確認
    print(f"{'='*70}")
    print(f"これらのメッセージを送信しますか？")
    print(f"{'='*70}")
    confirm = input("送信する場合は 'yes' と入力してください: ").strip().lower()

    if confirm != 'yes':
        print("\n❌ 送信をキャンセルしました\n")
        return

    # メッセージ送信
    print(f"\n{'='*70}")
    print(f"📨 メッセージ送信開始")
    print(f"{'='*70}\n")

    success_count = 0
    error_count = 0

    for idx, msg in enumerate(messages, start=1):
        name = msg['name']
        profile_url = msg['profile_url']
        score = msg['total_score']
        message = msg['message']

        print(f"[{idx}/{len(messages)}] 📤 {name} (スコア: {score}点) へ送信中...")

        result, error, details = send_message(driver, profile_url, name, message)

        log_message(name, profile_url, result, message_log_file, error, details)

        if result == "success":
            success_count += 1
            print(f"   ✅ 送信成功\n")
        else:
            error_count += 1
            print(f"   ❌ 送信失敗: {error}\n")

        # 遅延
        if idx < len(messages):
            delay = random.uniform(3, 6)
            time.sleep(delay)

    # サマリー
    print(f"{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 送信成功: {success_count} 件")
    print(f"❌ 送信失敗: {error_count} 件")
    print(f"📝 ログ: {message_log_file}")
    print(f"{'='*70}\n")

# ==============================
# メイン処理
# ==============================
def main(account_name, paths, max_messages):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ送信")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # Step 1: 生成済みメッセージ読み込み
    messages = load_generated_messages(paths['generated_messages_file'], paths['message_log_file'])

    if not messages:
        print("⚠️ 送信対象のメッセージがありません。処理を終了します。\n")
        return

    # ログイン
    driver = login(account_name, paths['cookie_file'])

    try:
        # Step 2: メッセージ送信
        send_all_messages(driver, messages, max_messages, paths['message_log_file'])

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 メッセージ送信完了")
        print(f"{'='*70}")
        print(f"終了日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        input("\nEnterキーを押してブラウザを閉じます...")
        driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ送信")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

    # 最大メッセージ送信数
    print("【最大メッセージ送信数】")
    while True:
        max_messages_input = input("最大メッセージ送信数を入力 (Enter=デフォルト「50」): ").strip()
        if not max_messages_input:
            max_messages = 50
            break
        try:
            max_messages = int(max_messages_input)
            if max_messages > 0:
                break
            else:
                print("⚠️ 1以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 設定内容を確認
    print(f"\n{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"最大メッセージ送信数: {max_messages}件")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, max_messages)
