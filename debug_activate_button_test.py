# debug_activate_button_test.py
# 自動入力後に送信ボタンを活性化する方法を探すテスト

import os
import time
import pickle
import csv
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
MESSAGES_FILE = os.path.join(DATA_DIR, "messages_v2.csv")

TEST_MESSAGE = """小熊さん

いきなりすみません🙇
KPMGコンサルティングの依田と申します。

将来的に人材領域にも関わりたいと考えており、IT・コンサル分野でご活躍されている方々のお話を伺いながら、知見を広げたいと思っています。

自分からは以下のようなトピックを共有できます：
・フューチャーアーキテクト／KPMGでのプロジェクト経験
・転職時に検討したBIG4＋アクセンチュア／BCGの比較や選考情報

もしご関心あれば、カジュアルにオンラインでお話できると嬉しいです！よろしくお願いします！"""

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
                print("✅ 自動ログイン成功！\n")
                return driver
        except Exception as e:
            print(f"⚠️ エラー: {e}")

    print("⚠️ 手動ログインが必要です")
    return driver

def check_button_state(driver, label=""):
    """送信ボタンの状態を確認"""
    try:
        send_btn = driver.find_element(
            By.XPATH,
            "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send') or contains(., '送信') or contains(., 'Send')]"
        )
        is_disabled = send_btn.get_attribute("disabled")
        aria_disabled = send_btn.get_attribute("aria-disabled")

        if is_disabled is None and (aria_disabled is None or aria_disabled == "false"):
            print(f"   ✅ {label}: 送信ボタンが活性化されました！")
            return True
        else:
            print(f"   ❌ {label}: 送信ボタンは非活性（disabled={is_disabled}, aria-disabled={aria_disabled}）")
            return False
    except Exception as e:
        print(f"   ⚠️ {label}: 送信ボタンの確認エラー - {e}")
        return False

def test_activation_methods(driver):
    """送信ボタン活性化の様々な方法をテスト"""

    # 送信対象ファイルから最初のプロフィールを取得
    if not os.path.exists(MESSAGES_FILE):
        print("❌ messages_v2.csv が見つかりません")
        return

    with open(MESSAGES_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        targets = list(reader)
        if not targets:
            print("❌ 送信対象が見つかりません")
            return
        target = targets[0]
        profile_url = target.get("profile_url")
        name = target.get("name", "不明")

    print(f"{'='*70}")
    print(f"🧪 送信ボタン活性化テスト")
    print(f"{'='*70}\n")
    print(f"ターゲット: {name}")
    print(f"URL: {profile_url}\n")

    # プロフィールに移動
    driver.get(profile_url)
    time.sleep(3)
    driver.execute_script("window.scrollTo(0, 400);")
    time.sleep(1)

    print("1️⃣ プロフィールページに移動しました\n")

    # メッセージボタンをクリック
    try:
        message_btn = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
            ))
        )

        if not message_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
            time.sleep(1)

        try:
            message_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", message_btn)

        time.sleep(3)
        print("2️⃣ ✅ メッセージボタンをクリック\n")

    except Exception as e:
        print(f"❌ エラー: {e}")
        return

    # ポップアップ待機
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
        )
        print("3️⃣ ✅ ポップアップが表示されました\n")
    except TimeoutException:
        print("❌ ポップアップが表示されません")
        return

    # メッセージ入力欄を取得
    try:
        message_box = driver.find_element(
            By.CSS_SELECTOR,
            "[role='dialog'] [contenteditable='true']"
        )
        print("4️⃣ ✅ メッセージ入力欄を検出\n")
    except Exception as e:
        print(f"❌ メッセージ入力欄が見つかりません: {e}")
        return

    # 初期状態を確認
    print(f"{'='*70}")
    print(f"📊 初期状態")
    print(f"{'='*70}\n")
    check_button_state(driver, "初期状態")
    print()

    # 現在のアプローチ（1文字ずつ入力）で自動入力
    print(f"{'='*70}")
    print(f"🤖 自動入力を実行（1文字ずつ + InputEvent）")
    print(f"{'='*70}\n")

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

    driver.execute_script(script_input, message_box, TEST_MESSAGE)
    time.sleep(1.5)
    print("✅ 自動入力完了\n")

    # 状態確認1
    result1 = check_button_state(driver, "自動入力直後")
    print()

    if result1:
        print("🎉 自動入力だけで活性化されました！")
        input("\nEnterキーを押してブラウザを閉じます...")
        driver.quit()
        return

    # ここから様々な活性化方法を試す
    print(f"{'='*70}")
    print(f"🔬 追加の活性化方法をテスト")
    print(f"{'='*70}\n")

    # 方法1: 追加のclickイベント
    print("🧪 テスト1: メッセージ入力欄をクリック")
    driver.execute_script("arguments[0].click();", message_box)
    time.sleep(0.5)
    check_button_state(driver, "テスト1")
    print()

    # 方法2: focus/blurを繰り返す
    print("🧪 テスト2: focus/blurを複数回実行")
    for i in range(3):
        driver.execute_script("arguments[0].blur();", message_box)
        time.sleep(0.1)
        driver.execute_script("arguments[0].focus();", message_box)
        time.sleep(0.1)
    check_button_state(driver, "テスト2")
    print()

    # 方法3: 追加のInputEventを発火
    print("🧪 テスト3: 追加のInputEventを発火")
    script_event = """
    const element = arguments[0];
    const inputEvent = new InputEvent('input', { bubbles: true });
    element.dispatchEvent(inputEvent);
    const changeEvent = new Event('change', { bubbles: true });
    element.dispatchEvent(changeEvent);
    """
    driver.execute_script(script_event, message_box)
    time.sleep(0.5)
    check_button_state(driver, "テスト3")
    print()

    # 方法4: KeyboardEventをより詳細に発火
    print("🧪 テスト4: 詳細なKeyboardEventを発火")
    script_keyboard = """
    const element = arguments[0];

    const keydownEvent = new KeyboardEvent('keydown', {
        bubbles: true,
        cancelable: true,
        key: 'a',
        code: 'KeyA',
        keyCode: 65
    });
    element.dispatchEvent(keydownEvent);

    const keypressEvent = new KeyboardEvent('keypress', {
        bubbles: true,
        cancelable: true,
        key: 'a',
        code: 'KeyA',
        keyCode: 65
    });
    element.dispatchEvent(keypressEvent);

    const keyupEvent = new KeyboardEvent('keyup', {
        bubbles: true,
        cancelable: true,
        key: 'a',
        code: 'KeyA',
        keyCode: 65
    });
    element.dispatchEvent(keyupEvent);
    """
    driver.execute_script(script_keyboard, message_box)
    time.sleep(0.5)
    check_button_state(driver, "テスト4")
    print()

    # 方法5: 空白を追加してから削除
    print("🧪 テスト5: 空白を追加してから削除")
    script_space = """
    const element = arguments[0];
    const currentText = element.innerText;

    // 空白を追加
    element.innerText = currentText + ' ';
    const inputEvent1 = new InputEvent('input', {
        bubbles: true,
        inputType: 'insertText',
        data: ' '
    });
    element.dispatchEvent(inputEvent1);

    // すぐに削除
    element.innerText = currentText;
    const inputEvent2 = new InputEvent('input', {
        bubbles: true,
        inputType: 'deleteContentBackward'
    });
    element.dispatchEvent(inputEvent2);
    """
    driver.execute_script(script_space, message_box)
    time.sleep(0.5)
    check_button_state(driver, "テスト5")
    print()

    # 方法6: textContent vs innerText
    print("🧪 テスト6: textContentを使用")
    script_textcontent = """
    const element = arguments[0];
    const text = arguments[1];
    element.textContent = text;

    const inputEvent = new InputEvent('input', {
        bubbles: true,
        inputType: 'insertText'
    });
    element.dispatchEvent(inputEvent);

    const changeEvent = new Event('change', { bubbles: true });
    element.dispatchEvent(changeEvent);
    """
    driver.execute_script(script_textcontent, message_box, TEST_MESSAGE)
    time.sleep(0.5)
    check_button_state(driver, "テスト6")
    print()

    # 方法7: MutationObserverを無効化してから再度トリガー
    print("🧪 テスト7: 手動でMutationObserverをトリガー")
    script_mutation = """
    const element = arguments[0];

    // DOMの属性を変更してMutationObserverをトリガー
    element.setAttribute('data-test', 'trigger');
    element.removeAttribute('data-test');

    // 再度inputイベント
    const inputEvent = new InputEvent('input', {
        bubbles: true,
        composed: true,
        inputType: 'insertText'
    });
    element.dispatchEvent(inputEvent);
    """
    driver.execute_script(script_mutation, message_box)
    time.sleep(0.5)
    check_button_state(driver, "テスト7")
    print()

    # 最終結果
    print(f"{'='*70}")
    print(f"📊 最終結果")
    print(f"{'='*70}\n")
    final_result = check_button_state(driver, "最終状態")
    print()

    if not final_result:
        print("❌ どの方法でも送信ボタンを活性化できませんでした")
        print("💡 考えられる原因:")
        print("   - LinkedInが実際のユーザー入力を検知する別の仕組みを持っている")
        print("   - 受信者の選択やプロフィールカードの表示が必要")
        print("   - タイミングやイベントの順序が重要")
        print("   - セキュリティ上の理由で自動入力を検知している")
    else:
        print("✅ 送信ボタンの活性化に成功しました！")

    print()
    input("Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    test_activation_methods(driver)
