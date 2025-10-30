# aiagent/linkedin_send_messages.py
# AIでメッセージを生成し、送信

import os
import time
import csv
import pickle
import random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_FILE = os.path.join(DATA_DIR, "messages_v2.csv")
LOG_FILE = os.path.join(DATA_DIR, "message_logs.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# 送信設定
MAX_MESSAGES = 2  # テスト用: 2件（本番は50件）
DELAY_RANGE = (3, 6)  # メッセージ間隔（秒）

# メッセージテンプレート（絵文字なし）
MESSAGE_TEMPLATE = """{name}さん

いきなりすみません
KPMGコンサルティングの依田と申します。

将来的に人材領域にも関わりたいと考えており、IT・コンサル分野でご活躍されている方々のお話を伺いながら、知見を広げたいと思っています。

自分からは以下のようなトピックを共有できます：
・フューチャーアーキテクト／KPMGでのプロジェクト経験
・転職時に検討したBIG4＋アクセンチュア／BCGの比較や選考情報

もしご関心あれば、カジュアルにオンラインでお話できると嬉しいです！よろしくお願いします！"""

# ==============================
# OpenAIクライアント
# ==============================
if not OPENAI_API_KEY:
    print("❌ エラー: OPENAI_API_KEYが設定されていません")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# ログイン
# ==============================
def login():
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
    if os.path.exists(COOKIE_FILE):
        print("🔑 保存されたCookieを使用して自動ログイン中...")
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
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(COOKIE_FILE)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)

    # 手動ログイン
    print("🔑 LinkedIn 手動ログインモード開始...")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}")

    return driver

# ==============================
# メッセージ生成
# ==============================
def generate_message(name):
    """
    OpenAI APIでメッセージを生成（テンプレートに軽微なバリエーション）

    Args:
        name: 候補者名

    Returns:
        str: 生成されたメッセージ
    """
    # テンプレートベースで生成
    base_message = MESSAGE_TEMPLATE.format(name=name)

    # AIで軽微なバリエーション追加
    prompt = f"""
以下のメッセージテンプレートを元に、自然で親しみやすいメッセージを生成してください。
大幅な変更は不要です。語尾や表現を少しだけ変えてください。

【テンプレート】
{base_message}

【要件】
- 名前は必ず「{name}さん」で始める
- 内容の構造は基本的にテンプレート通り
- 語尾や接続詞を少しだけ自然にバリエーションを付ける
- 絵文字（🙇）は残す
- 箇条書き（・）はそのまま維持
- 全体の長さはテンプレートと同程度
- 他の説明は一切不要、メッセージ本文のみ出力
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはメッセージ生成アシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=400
        )

        message = response.choices[0].message.content.strip()
        return message

    except Exception as e:
        print(f"   ⚠️ メッセージ生成エラー: {e}")
        # エラー時はテンプレートをそのまま使用
        return base_message

# ==============================
# メッセージ送信
# ==============================
def send_message(driver, profile_url, name, message):
    """
    プロフィールページでメッセージを送信

    Args:
        driver: Selenium WebDriver
        profile_url: プロフィールURL
        name: 候補者名
        message: 送信するメッセージ

    Returns:
        tuple: (result, error, details)
    """
    try:
        # プロフィールページへ移動
        driver.get(profile_url)

        # ページの読み込み完了を待機
        time.sleep(3)

        # ページを下にスクロールしてボタンを表示領域に入れる
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1)

        # 「メッセージ」ボタンを探す（明示的な待機付き）
        try:
            message_btn = None

            # 戦略1: WebDriverWaitでaria-labelを待機
            try:
                message_btn = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
                    ))
                )
                print(f"   ✅ メッセージボタン検出（戦略1: aria-label）")
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
                    print(f"   ✅ メッセージボタン検出（戦略2: テキスト）")
                except TimeoutException:
                    pass

            # 戦略3: 全ボタンをスキャンしてメッセージボタンを探す
            if not message_btn:
                print(f"   ⚠️ 標準戦略で検出できず、全ボタンスキャン開始...")
                script = """
                const buttons = Array.from(document.querySelectorAll('button'));
                for (const btn of buttons) {
                    const text = btn.textContent.trim();
                    const ariaLabel = btn.getAttribute('aria-label') || '';
                    if ((text.includes('メッセージ') || text.includes('Message')) ||
                        (ariaLabel.includes('メッセージ') || ariaLabel.includes('Message'))) {
                        return btn;
                    }
                }
                return null;
                """
                message_btn = driver.execute_script(script)
                if message_btn:
                    print(f"   ✅ メッセージボタン検出（戦略3: 全スキャン）")

            if not message_btn:
                return "error", "メッセージボタン未検出（全戦略失敗）", "button_not_found"

            # ボタンが表示されるまで待機
            if not message_btn.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
                time.sleep(1)

            # クリック可能になるまで待機
            try:
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(message_btn)
                )
            except TimeoutException:
                print(f"   ⚠️ ボタンがクリック可能になるまで待機タイムアウト、強制的にクリック試行")

            # メッセージボタンをクリック
            try:
                message_btn.click()
            except Exception:
                # 通常クリックが失敗した場合、JavaScriptでクリック
                driver.execute_script("arguments[0].click();", message_btn)

            time.sleep(3)
            print(f"   ✅ メッセージボタンをクリック")

        except Exception as e:
            return "error", f"ボタンクリックエラー: {e}", "button_click_failed"

        # メッセージ入力欄を探す（ポップアップ内）
        try:
            # ポップアップのダイアログが表示されるまで待機
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
            )
            time.sleep(1)

            # ポップアップ内のcontenteditable要素を探す
            # 複数の戦略を試行
            message_box = None

            # 戦略1: role="dialog"内のcontenteditable
            try:
                message_box = driver.find_element(
                    By.CSS_SELECTOR,
                    "[role='dialog'] [contenteditable='true']"
                )
            except NoSuchElementException:
                pass

            # 戦略2: div[contenteditable="true"][role="textbox"]
            if not message_box:
                try:
                    message_box = driver.find_element(
                        By.CSS_SELECTOR,
                        "div[contenteditable='true'][role='textbox']"
                    )
                except NoSuchElementException:
                    pass

            # 戦略3: XPathで探す
            if not message_box:
                try:
                    message_box = driver.find_element(
                        By.XPATH,
                        "//div[@contenteditable='true' and @role='textbox']"
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

            print(f"   💬 メッセージを入力中...")

            try:
                # send_keysで実際のキーボード入力を模倣（これが最も確実）
                message_box.send_keys(message)
                time.sleep(0.5)
                print(f"   ✅ send_keysでメッセージを入力")

            except Exception as e:
                print(f"   ⚠️ send_keys失敗: {e}、JavaScriptにフォールバック")

                # フォールバック: JavaScriptで入力（以前の方法）
                script_input = """
                const element = arguments[0];
                const text = arguments[1];

                element.focus();
                element.innerText = '';

                let currentText = '';
                const chars = Array.from(text);

                for (let i = 0; i < chars.length; i++) {
                    currentText += chars[i];
                    element.innerText = currentText;

                    const inputEvent = new InputEvent('input', {
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertText',
                        data: chars[i]
                    });
                    element.dispatchEvent(inputEvent);

                    if (i === chars.length - 1) {
                        const changeEvent = new Event('change', { bubbles: true });
                        element.dispatchEvent(changeEvent);
                    }
                }

                const keyupEvent = new KeyboardEvent('keyup', { bubbles: true });
                element.dispatchEvent(keyupEvent);

                element.blur();
                element.focus();

                return true;
                """

                result = driver.execute_script(script_input, message_box, message)
                if result:
                    print(f"   ✅ JavaScriptでメッセージを入力")

            # 送信ボタンが活性化されるまで少し待つ
            time.sleep(1.5)

        except TimeoutException:
            return "error", "ポップアップのタイムアウト", "popup_timeout"
        except Exception as e:
            return "error", f"メッセージ入力エラー: {e}", "message_input_failed"

        # 送信ボタンをクリック（ポップアップ内）
        try:
            # ポップアップ内の送信ボタンを探す
            send_btn = None

            # 戦略1: ポップアップ内のaria-labelで検索
            try:
                send_btn = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send')]"
                )
            except NoSuchElementException:
                pass

            # 戦略2: テキストで検索
            if not send_btn:
                try:
                    send_btn = driver.find_element(
                        By.XPATH,
                        "//div[@role='dialog']//button[contains(., '送信') or contains(., 'Send')]"
                    )
                except NoSuchElementException:
                    pass

            # 戦略3: クラス名で検索（フォールバック）
            if not send_btn:
                try:
                    send_btn = driver.find_element(
                        By.XPATH,
                        "//button[contains(@class, 'msg-form__send-button')]"
                    )
                except NoSuchElementException:
                    pass

            if not send_btn:
                return "error", "送信ボタンが見つかりません", "send_button_not_found"

            # 送信ボタンが活性化されるまで待機（最大10秒）
            print(f"   🔍 送信ボタンの状態を確認中...")
            button_enabled = False

            for i in range(20):  # 0.5秒 × 20回 = 最大10秒
                is_disabled = send_btn.get_attribute("disabled")
                aria_disabled = send_btn.get_attribute("aria-disabled")

                if is_disabled is None and (aria_disabled is None or aria_disabled == "false"):
                    button_enabled = True
                    print(f"   ✅ 送信ボタンが活性化されました（{i * 0.5:.1f}秒後）")
                    break

                time.sleep(0.5)

            if not button_enabled:
                # 活性化されなくても状態を記録して続行
                print(f"   ⚠️ 送信ボタンが活性化されません（disabled={is_disabled}, aria-disabled={aria_disabled}）")
                print(f"   ⚠️ 強制的にクリックを試みます")

            # 送信ボタンをクリック
            try:
                send_btn.click()
                print(f"   ✅ 送信ボタンをクリック")
            except Exception as click_error:
                print(f"   ⚠️ 通常クリック失敗: {click_error}")
                # JavaScriptで強制クリック
                driver.execute_script("arguments[0].click();", send_btn)
                print(f"   ✅ JavaScriptで送信ボタンをクリック")

            # 送信処理が完了するまで少し待機
            time.sleep(2)

            # 送信が成功したとみなす（ボタンが活性化してクリックできた）
            if button_enabled:
                print(f"   ✅ 送信処理完了")

                # ポップアップを明示的に閉じる（次の送信のため）
                try:
                    # 戦略1: Escapeキーでポップアップを閉じる
                    from selenium.webdriver.common.keys import Keys
                    message_box.send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    print(f"   ✅ ポップアップを閉じました（Escape）")
                except Exception as e1:
                    print(f"   ⚠️ Escapeで閉じる失敗: {e1}")

                    # 戦略2: 閉じるボタン（X）をクリック
                    try:
                        close_btn = driver.find_element(
                            By.XPATH,
                            "//div[@role='dialog']//button[contains(@aria-label, '閉じる') or contains(@aria-label, 'Dismiss') or contains(@aria-label, 'Close')]"
                        )
                        close_btn.click()
                        time.sleep(1)
                        print(f"   ✅ ポップアップを閉じました（閉じるボタン）")
                    except Exception as e2:
                        print(f"   ⚠️ 閉じるボタンでの終了失敗: {e2}")
                        # ポップアップを閉じられなくてもエラーにはしない（次のプロフィール移動で自動的に閉じる可能性）

                return "success", "", "sent"
            else:
                return "error", "送信ボタンが活性化されませんでした", "button_not_enabled"

        except NoSuchElementException:
            return "error", "送信ボタン未検出", "send_button_not_found"
        except Exception as e:
            return "error", f"送信エラー: {e}", "send_failed"

    except Exception as e:
        return "error", f"予期しないエラー: {e}", "unexpected_error"

# ==============================
# ログ記録
# ==============================
def log_message(name, profile_url, result, error="", details=""):
    """送信結果をログに記録"""
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
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
# メイン処理
# ==============================
def main():
    """メイン処理"""

    if not os.path.exists(INPUT_FILE):
        print(f"❌ エラー: 送信対象リストが見つかりません: {INPUT_FILE}")
        print(f"💡 先に linkedin_scorer_v2.py を実行してください")
        return

    # CSV読み込み
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        targets = list(reader)

    if not targets:
        print("⚠️ 送信対象データが空です")
        return

    # 上限件数まで絞り込み
    targets = targets[:MAX_MESSAGES]
    total = len(targets)

    print(f"\n{'='*70}")
    print(f"📨 メッセージ生成開始")
    print(f"{'='*70}")
    print(f"送信対象: {total} 件")
    print(f"上限: {MAX_MESSAGES} 件")
    print(f"{'='*70}\n")

    # まず全メッセージを生成して表示
    messages_to_send = []

    for idx, target in enumerate(targets, start=1):
        name = target.get('name', '不明')
        profile_url = target.get('profile_url', '')
        score = target.get('total_score', '0')

        if not profile_url:
            print(f"[{idx}/{total}] ⚠️ {name} - URLなし、スキップ")
            continue

        print(f"[{idx}/{total}] 💬 {name} (スコア: {score}点) のメッセージを生成中...")
        message = generate_message(name)

        messages_to_send.append({
            'name': name,
            'profile_url': profile_url,
            'score': score,
            'message': message
        })

    # 生成したメッセージを全て表示
    print(f"\n{'='*70}")
    print(f"📋 生成されたメッセージ一覧")
    print(f"{'='*70}\n")

    for idx, msg_data in enumerate(messages_to_send, start=1):
        print(f"--- [{idx}/{len(messages_to_send)}] {msg_data['name']} (スコア: {msg_data['score']}点) ---")
        print(f"{msg_data['message']}")
        print()

    # ユーザーに確認
    print(f"{'='*70}")
    print(f"これらのメッセージを送信しますか？")
    print(f"{'='*70}")
    confirm = input("送信する場合は 'yes' と入力してください: ").strip().lower()

    if confirm != 'yes':
        print("\n❌ 送信をキャンセルしました")
        return

    # ログイン
    print(f"\n{'='*70}")
    print(f"📨 メッセージ送信開始")
    print(f"{'='*70}\n")

    driver = login()

    success_count = 0
    error_count = 0

    for idx, msg_data in enumerate(messages_to_send, start=1):
        name = msg_data['name']
        profile_url = msg_data['profile_url']
        score = msg_data['score']
        message = msg_data['message']

        print(f"[{idx}/{len(messages_to_send)}] 📤 {name} (スコア: {score}点) へ送信中...")

        # メッセージ送信
        result, error, details = send_message(driver, profile_url, name, message)

        # ログ記録
        log_message(name, profile_url, result, error, details)

        # 結果表示
        if result == "success":
            success_count += 1
            print(f"   ✅ 送信成功\n")
        else:
            error_count += 1
            print(f"   ❌ 送信失敗: {error}\n")

        # 遅延
        if idx < total:
            delay = random.uniform(*DELAY_RANGE)
            time.sleep(delay)

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 送信成功: {success_count} 件")
    print(f"❌ 送信失敗: {error_count} 件")
    print(f"📝 ログ: {LOG_FILE}")
    print(f"{'='*70}\n")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    main()
