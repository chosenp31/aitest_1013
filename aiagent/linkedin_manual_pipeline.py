# aiagent/linkedin_manual_pipeline.py
# ✅ 「挨拶なしで送信」専用フロー（Add a note/メッセージを追加は押さない）
# ✅ 手動ログイン、Shadow DOM/iframe対応、ランダム待機、ログ出力対応

import os
import time
import csv
import random
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 定数
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
TARGET_CSV = os.path.join(DATA_DIR, "messages.csv")  # 送信対象
LOG_CSV = os.path.join(DATA_DIR, "logs.csv")         # 実行ログ

LIMIT = 10                       # 上位N件だけ送る
DELAY_RANGE = (7, 15)            # 送信間隔（秒）
PAGE_READY_TIMEOUT = 15          # ページロード待機
DIALOG_TIMEOUT = 10              # ダイアログ待機

# ==============================
# ユーティリティ
# ==============================
def wait_page_ready(driver, timeout=PAGE_READY_TIMEOUT):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def js_click(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.3)
    try:
        element.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", element)

def append_log(name, url, result, error=""):
    os.makedirs(DATA_DIR, exist_ok=True)
    exists = os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "name", "url", "result", "error"])
        if not exists:
            w.writeheader()
        w.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "url": url,
            "result": result,
            "error": error,
        })

def find_button_by_texts(driver, texts):
    """
    ボタン候補（button / [role="button"] / aria-label）を
    テキスト部分一致（大文字小文字無視）で1つ返す。
    Shadow DOM 風の要素にもJSでアプローチ。
    """
    # 1) 通常XPath
    xpath = " | ".join(
        [f"//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{t.lower()}')]" for t in texts]
        + [f"//*[@role='button'][contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{t.lower()}')]" for t in texts]
    )
    if xpath:
        elems = driver.find_elements(By.XPATH, xpath)
        if elems:
            return elems[0]

    # 2) aria-label / innerText を JS で総当り
    try:
        el = driver.execute_script(
            """
            const texts = arguments[0].map(t => t.toLowerCase());
            function match(el) {
                const label = (el.getAttribute('aria-label') || '').toLowerCase();
                const text  = (el.innerText || '').toLowerCase();
                return texts.some(t => label.includes(t) || text.includes(t));
            }
            const all = document.querySelectorAll('button, [role="button"], [aria-label]');
            for (const el of all) {
                if (match(el)) return el;
            }
            return null;
            """,
            texts,
        )
        if el:
            return el
    except Exception:
        pass

    # 3) iframe 内も走査（深追いはしない）
    try:
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for fr in frames:
            driver.switch_to.frame(fr)
            elems = driver.find_elements(By.XPATH, xpath) if xpath else []
            if elems:
                btn = elems[0]
                driver.switch_to.default_content()
                return btn
            driver.switch_to.default_content()
    except Exception:
        driver.switch_to.default_content()

    return None

# ==============================
# 手動ログイン
# ==============================
def manual_login():
    print("🔑 LinkedIn 手動ログインモード開始...")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でログインしてください（feedページに遷移するまで待機）...")
    while "feed" not in driver.current_url:
        time.sleep(2)
    print("✅ ログイン完了を検出。送信処理を開始します。")
    return driver

# ==============================
# 送信本体（挨拶なしのみ）
# ==============================
def send_without_note_flow(driver):
    # 入力CSV読み込み
    if not os.path.exists(TARGET_CSV):
        print(f"❌ 送信対象CSVが見つかりません: {TARGET_CSV}")
        return
    with open(TARGET_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("⚠️ 送信対象が空です。終了します。")
        return

    targets = rows[:LIMIT]
    print(f"📤 接続リクエスト対象: {len(targets)} 件（上限 {LIMIT} 件）")

    success = 0
    for idx, r in enumerate(targets, start=1):
        name = (r.get("name") or "不明").strip()
        url  = (r.get("url") or r.get("profile_url") or "").strip()
        if not url:
            print(f"⚠️ [{idx}] {name}: URLなし → skip")
            append_log(name, url, "skip", "no_url")
            continue

        print(f"\n[{idx}/{len(targets)}] {name} に送信処理中...")
        try:
            driver.get(url)
            wait_page_ready(driver)
            time.sleep(1.5)

            # Step1: 「つながりを申請 / Connect」
            connect_btn = find_button_by_texts(driver, ["つながりを申請", "connect", "接続"])
            if not connect_btn:
                print(f"⚪ {name}: 『つながりを申請/Connect』が見つからず → skip（接続済み/制限の可能性）")
                append_log(name, url, "skip", "no_connect_button")
                continue
            js_click(driver, connect_btn)
            time.sleep(1.0)

            # 可能な限りダイアログの出現を待つ
            try:
                WebDriverWait(driver, DIALOG_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(@role,'dialog') or contains(@class,'artdeco-modal')]"))
                )
            except TimeoutException:
                # ダイアログがないパターン（即時送信UI）が稀にあるが、明示的に送らない
                print(f"⚠️ {name}: 接続ダイアログ未検出 → skip（安全重視）")
                append_log(name, url, "skip", "no_dialog_after_connect")
                continue

            # Step2: 「挨拶なしで送信 / Send without a note」だけを押す
            send_wo_note = find_button_by_texts(driver, ["挨拶なしで送信", "send without a note"])
            if send_wo_note:
                js_click(driver, send_wo_note)
                print(f"✅ {name}: 挨拶なしで送信 完了")
                append_log(name, url, "success", "")
                success += 1
            else:
                # 明示的に“Add a note/メッセージを追加”が見つかっても触らない
                print(f"⚠️ {name}: 『挨拶なしで送信/Send without a note』なし → skip")
                append_log(name, url, "skip", "no_send_without_note_button")
                # ダイアログを閉じる（次ターゲットへの影響防止）
                close_btn = find_button_by_texts(driver, ["閉じる", "close"])
                if close_btn:
                    js_click(driver, close_btn)

            # レート制御
            time.sleep(random.uniform(*DELAY_RANGE))

        except Exception as e:
            print(f"❌ {name}: 例外発生 → {e}")
            append_log(name, url, "error", str(e))
            time.sleep(random.uniform(3, 6))
            continue

    print(f"\n🎯 送信結果: {success} 件 / {len(targets)} 件（logs.csv を参照）")
    print("🪄 全処理完了。ブラウザを閉じてもOKです。")

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    driver = manual_login()
    send_without_note_flow(driver)
