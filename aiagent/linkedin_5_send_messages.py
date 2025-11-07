# aiagent/linkedin_send_prepared_messages.py
# 生成済みメッセージを読み込んで送信
# profiles_master.csv で統合管理

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

# ==============================
# 人間らしい挙動のためのヘルパー関数
# ==============================
def human_sleep(min_sec, max_sec):
    """人間らしいランダムな待機時間"""
    wait_time = random.uniform(min_sec, max_sec)
    time.sleep(wait_time)

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
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv")
    }

# ==============================
# profiles_master.csv 管理
# ==============================
def load_profiles_master(profiles_master_file):
    """profiles_master.csv を読み込む"""
    profiles_master = {}

    if os.path.exists(profiles_master_file):
        try:
            with open(profiles_master_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    profile_url = row.get('profile_url', '')
                    if profile_url:
                        profiles_master[profile_url] = row
        except Exception as e:
            print(f"⚠️ profiles_master.csv 読み込みエラー: {e}\n")

    return profiles_master

def save_profiles_master(profiles_master, profiles_master_file):
    """profiles_master.csv を保存"""
    fieldnames = [
        "profile_url", "name", "connected_date",
        "profile_fetched", "profile_fetched_at",
        "total_score", "scoring_decision",
        "message_generated", "message_generated_at",
        "message_sent_status", "message_sent_at", "last_send_error"
    ]

    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # profile_url でソート
        sorted_profiles = sorted(profiles_master.values(), key=lambda x: x.get('profile_url', ''))
        writer.writerows(sorted_profiles)

def update_profile_master(profiles_master, profile_url, updates):
    """profiles_master の特定エントリを更新"""
    if profile_url in profiles_master:
        profiles_master[profile_url].update(updates)

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
        human_sleep(2, 4)

        try:
            with open(cookie_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    pass

            driver.get("https://www.linkedin.com/feed")
            human_sleep(4, 7)

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
# メッセージ送信
# ==============================
def send_message(driver, profile_url, name, message):
    """メッセージを送信"""
    try:
        # プロフィールページへ移動
        driver.get(profile_url)
        human_sleep(3, 6)
        driver.execute_script("window.scrollTo(0, 400);")
        human_sleep(1, 2)

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
            return "error", "メッセージボタン未検出"

        if not message_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
            human_sleep(0.5, 1.5)

        try:
            message_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", message_btn)

        human_sleep(2, 4)

        # ポップアップ待機
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
            )
            human_sleep(1, 2)
        except TimeoutException:
            return "error", "ポップアップ表示タイムアウト"

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
            return "error", "メッセージ入力欄が見つかりません"

        # メッセージを入力（JavaScriptで設定して絵文字に対応）
        driver.execute_script("arguments[0].focus();", message_box)
        human_sleep(0.5, 1)
        message_box.click()
        human_sleep(0.5, 1)

        try:
            # JavaScriptで直接テキストを設定（絵文字対応）+ より正確なInputEventをトリガー
            driver.execute_script("""
                const element = arguments[0];
                const text = arguments[1];

                // 要素をフォーカス
                element.focus();

                // テキストを設定
                element.textContent = text;

                // InputEventを適切なプロパティで作成（LinkedInのReactが期待する形式）
                const inputEvent = new InputEvent('input', {
                    bubbles: true,
                    cancelable: true,
                    inputType: 'insertText',
                    data: text,
                    composed: true
                });

                // イベントをディスパッチ
                element.dispatchEvent(inputEvent);

                // changeイベントも発火
                const changeEvent = new Event('change', {
                    bubbles: true,
                    cancelable: true
                });
                element.dispatchEvent(changeEvent);

                // カーソルを最後に移動
                const range = document.createRange();
                const sel = window.getSelection();
                range.selectNodeContents(element);
                range.collapse(false);
                sel.removeAllRanges();
                sel.addRange(range);
            """, message_box, message)
            human_sleep(2, 3)
        except Exception as e:
            return "error", f"メッセージ入力エラー: {e}"

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
            return "error", "送信ボタンが見つかりません"

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

        human_sleep(2, 4)

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

            return "success", ""
        else:
            return "error", "送信ボタンが活性化されませんでした"

    except Exception as e:
        return "error", f"予期しないエラー: {e}"

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

    # profiles_master.csv 読み込み
    print(f"{'='*70}")
    print(f"📂 profiles_master.csv 読み込み")
    print(f"{'='*70}\n")

    if not os.path.exists(paths['profiles_master_file']):
        print(f"❌ エラー: {paths['profiles_master_file']} が見つかりません")
        print("⚠️  先に linkedin_prepare_messages.py を実行してください\n")
        return

    profiles_master = load_profiles_master(paths['profiles_master_file'])
    print(f"✅ 既存レコード: {len(profiles_master)} 件\n")

    # 送信対象抽出（message_generated=yes かつ message_sent_status≠success）
    send_targets = []
    for profile_url, profile in profiles_master.items():
        if (profile.get('message_generated') == 'yes' and
            profile.get('message_sent_status') != 'success'):
            send_targets.append(profile)

    if not send_targets:
        print("⚠️ 送信対象のメッセージがありません。処理を終了します。\n")
        return

    print(f"{'='*70}")
    print(f"📋 送信対象")
    print(f"{'='*70}")
    print(f"対象者数: {len(send_targets)} 件")
    print(f"上限: {max_messages} 件")
    print(f"{'='*70}\n")

    # 上限件数まで絞り込み
    send_targets = send_targets[:max_messages]

    # generated_messages.csv からメッセージを読み込み
    messages_map = {}
    if os.path.exists(paths['generated_messages_file']):
        with open(paths['generated_messages_file'], "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                messages_map[row['profile_url']] = row

    # メッセージ一覧を表示
    print(f"{'='*70}")
    print(f"📋 送信予定メッセージ一覧")
    print(f"{'='*70}\n")

    for idx, profile in enumerate(send_targets, start=1):
        profile_url = profile['profile_url']
        if profile_url in messages_map:
            msg = messages_map[profile_url]
            print(f"--- [{idx}/{len(send_targets)}] {msg['name']} (スコア: {msg['total_score']}点) ---")
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

    # ログイン
    driver = login(account_name, paths['cookie_file'])

    try:
        # 1日の送信上限チェック
        DAILY_LIMIT = 30
        if len(send_targets) > DAILY_LIMIT:
            print(f"\n⚠️ 送信対象が{len(send_targets)}件ですが、1日の上限{DAILY_LIMIT}件に制限します\n")
            send_targets = send_targets[:DAILY_LIMIT]

        # メッセージ送信
        print(f"\n{'='*70}")
        print(f"📨 メッセージ送信開始")
        print(f"{'='*70}\n")

        success_count = 0
        error_count = 0
        batch_size = random.randint(5, 7)  # 最初のバッチサイズを決定

        for idx, profile in enumerate(send_targets, start=1):
            name = profile['name']
            profile_url = profile['profile_url']
            score = profile.get('total_score', '0')

            if profile_url not in messages_map:
                print(f"[{idx}/{len(send_targets)}] ⚠️ {name} のメッセージが見つかりません\n")
                continue

            message = messages_map[profile_url]['message']

            print(f"[{idx}/{len(send_targets)}] 📤 {name} (スコア: {score}点) へ送信中...")

            result, error = send_message(driver, profile_url, name, message)

            # profiles_master 更新
            if result == "success":
                update_profile_master(profiles_master, profile_url, {
                    'message_sent_status': 'success',
                    'message_sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'last_send_error': ''
                })
                success_count += 1
                print(f"   ✅ 送信成功\n")
            else:
                update_profile_master(profiles_master, profile_url, {
                    'message_sent_status': 'error',
                    'message_sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'last_send_error': error
                })
                error_count += 1
                print(f"   ❌ 送信失敗: {error}\n")
                # エラー時は長めの休憩
                if idx < len(send_targets):
                    print(f"   ⏸️  エラー後の休憩中...\n")
                    human_sleep(30, 60)
                    continue

            # バッチ休憩（5〜7人ごとに1〜3分休憩）
            if idx % batch_size == 0 and idx < len(send_targets):
                rest_time = random.randint(60, 180)
                print(f"   ☕ 休憩中... ({rest_time}秒)\n")
                time.sleep(rest_time)
                batch_size = random.randint(5, 7)  # 次のバッチサイズを決定
            # 通常の遅延（人間らしい間隔）
            elif idx < len(send_targets):
                human_sleep(10, 20)

        # profiles_master.csv を保存
        save_profiles_master(profiles_master, paths['profiles_master_file'])
        print(f"💾 profiles_master.csv 更新完了\n")

        # サマリー
        print(f"{'='*70}")
        print(f"🎯 完了サマリー")
        print(f"{'='*70}")
        print(f"✅ 送信成功: {success_count} 件")
        print(f"❌ 送信失敗: {error_count} 件")
        print(f"📝 ステータス: {paths['profiles_master_file']}")
        print(f"{'='*70}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
        # 途中経過を保存
        save_profiles_master(profiles_master, paths['profiles_master_file'])
        print(f"💾 profiles_master.csv を保存しました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
        # 途中経過を保存
        save_profiles_master(profiles_master, paths['profiles_master_file'])
        print(f"💾 profiles_master.csv を保存しました\n")
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

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, max_messages)
