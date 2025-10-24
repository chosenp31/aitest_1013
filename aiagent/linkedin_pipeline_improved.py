# aiagent/linkedin_pipeline_improved.py
# 改善版：「つながりを申請」ボタン検出の複数戦略 + 詳細ログ + エラーハンドリング強化

import os
import time
import csv
import random
from datetime import datetime
from textwrap import shorten

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 定数
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DEBUG_DIR = os.path.join(BASE_DIR, "debug_output")
TARGET_CSV = os.path.join(DATA_DIR, "messages.csv")
LOG_CSV = os.path.join(DATA_DIR, "logs.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DEBUG_DIR, exist_ok=True)

LIMIT = 10  # 送信上限
DELAY_RANGE = (5, 10)  # 送信間隔（秒）

# ==============================
# ログ記録関数
# ==============================
def append_log(name, url, result, error="", details=""):
    """送信結果をCSVに記録"""
    file_exists = os.path.exists(LOG_CSV)

    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "name", "url", "result", "error", "details"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "url": url,
            "result": result,
            "error": error,
            "details": details
        })

def save_debug_screenshot(driver, name, reason):
    """デバッグ用スクリーンショット保存"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in name)
    filename = f"error_{timestamp}_{safe_name}_{reason}.png"
    filepath = os.path.join(DEBUG_DIR, filename)
    driver.save_screenshot(filepath)
    print(f"📸 デバッグ用スクリーンショット保存: {filename}")
    return filepath

# ==============================
# 手動ログイン
# ==============================
def manual_login():
    """手動でLinkedInにログイン"""
    print("🔑 LinkedIn 手動ログインモード開始...")

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")
    print("💡 ログイン後、feedページが表示されるまで待機します...")

    # ログイン完了待機
    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了を検出。リクエスト送信を開始します。")
    return driver

# ==============================
# 状態チェック
# ==============================
def check_connection_status(driver):
    """現在の接続状態を確認（つながり済み、保留中など）"""

    # 「つながっています」「メッセージ」などのボタンがある場合は既接続
    try:
        connected_patterns = [
            "//button[contains(., 'つながっています')]",
            "//button[contains(., 'Connected')]",
            "//button[contains(., 'メッセージ')]",
            "//button[contains(., 'Message')]",
        ]

        for pattern in connected_patterns:
            elements = driver.find_elements(By.XPATH, pattern)
            if elements:
                return "already_connected"

        # 「保留中」パターン
        pending_patterns = [
            "//button[contains(., '保留中')]",
            "//button[contains(., 'Pending')]",
        ]

        for pattern in pending_patterns:
            elements = driver.find_elements(By.XPATH, pattern)
            if elements:
                return "pending"

        return "not_connected"

    except Exception as e:
        print(f"⚠️ 接続状態チェックでエラー: {e}")
        return "unknown"

# ==============================
# ボタン検出（複数戦略）
# ==============================
def find_connect_button_strategy1(driver):
    """戦略1: JavaScript による詳細検出（元のロジック）"""
    print("   🔍 戦略1: JavaScript詳細検出を試行...")

    _JS_FIND_MAIN_BUTTON = r"""
    (function(){
      const W = window.innerWidth || document.documentElement.clientWidth || 1200;

      const main = document.querySelector('main');
      if (!main) return {found:false, reason:'<main>タグなし'};

      const h1 = main.querySelector('h1');
      if (!h1) return {found:false, reason:'<h1>なし'};

      const h1Rect = h1.getBoundingClientRect();
      const buttonsInMain = Array.from(main.querySelectorAll('button, [role="button"]'));

      function isConnect(el){
        const text = (el.innerText || '').trim().toLowerCase();
        const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
        return text.includes('つながりを申請') || text.includes('connect') ||
               aria.includes('つながりを申請') || aria.includes('connect');
      }

      const connectButtons = buttonsInMain.filter(isConnect);
      if (connectButtons.length === 0) return {found:false, reason:'つながりを申請ボタンなし'};

      const leftButtons = connectButtons.filter(el => {
        const rect = el.getBoundingClientRect();
        const centerX = rect.x + rect.width / 2;
        return centerX < W * 0.50;
      });

      if (leftButtons.length === 0) return {found:false, reason:'左半分にボタンなし'};

      let bestButton = null;
      let minDistance = Infinity;

      leftButtons.forEach(btn => {
        const rect = btn.getBoundingClientRect();
        const btnCenterY = rect.y + rect.height / 2;
        const h1CenterY = h1Rect.y + h1Rect.height / 2;
        const distance = Math.abs(btnCenterY - h1CenterY);

        if (distance < minDistance) {
          minDistance = distance;
          bestButton = btn;
        }
      });

      if (!bestButton) return {found:false, reason:'最適ボタン選択失敗'};

      const finalRect = bestButton.getBoundingClientRect();
      return {
        found: true,
        x: finalRect.x,
        y: finalRect.y,
        w: finalRect.width,
        h: finalRect.height,
        distance: minDistance
      };
    })();
    """

    res = driver.execute_script(_JS_FIND_MAIN_BUTTON)

    if not res or not isinstance(res, dict) or not res.get("found"):
        reason = res.get("reason", "不明") if res else "不明"
        print(f"      ❌ 戦略1失敗: {reason}")
        return None

    # 座標から要素を取得
    js_pick = r"""
      (function(targetX, targetY){
        const main = document.querySelector('main');
        if (!main) return null;

        const buttons = Array.from(main.querySelectorAll('button, [role="button"]'));

        function isConnect(el){
          const t = (el.innerText || '').trim().toLowerCase();
          const a = (el.getAttribute('aria-label') || '').trim().toLowerCase();
          return t.includes('つながりを申請') || t.includes('connect') ||
                 a.includes('つながりを申請') || a.includes('connect');
        }

        let best = null;
        let minDist = 1e9;

        buttons.forEach(btn => {
          if (!isConnect(btn)) return;
          const r = btn.getBoundingClientRect();
          const cx = r.x + r.width / 2;
          const cy = r.y + r.height / 2;
          const dist = Math.hypot(cx - targetX, cy - targetY);

          if (dist < minDist) {
            best = btn;
            minDist = dist;
          }
        });

        return best;
      })(arguments[0], arguments[1]);
    """

    cx = res["x"] + res["w"] / 2
    cy = res["y"] + res["h"] / 2
    element = driver.execute_script(js_pick, cx, cy)

    if element:
        print(f"      ✅ 戦略1成功: h1からの距離 {res['distance']:.1f}px")
        return element

    print(f"      ❌ 戦略1: 要素取得失敗")
    return None

def find_connect_button_strategy2(driver):
    """戦略2: XPath直接検索（シンプル）"""
    print("   🔍 戦略2: XPath直接検索を試行...")

    xpaths = [
        "//main//button[contains(., 'つながりを申請')]",
        "//main//button[contains(., 'Connect')]",
        "//main//button[contains(@aria-label, 'つながりを申請')]",
        "//main//button[contains(@aria-label, 'Connect')]",
    ]

    for xpath in xpaths:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            if elements:
                # 最初の表示されている要素を返す
                for elem in elements:
                    if elem.is_displayed():
                        print(f"      ✅ 戦略2成功: XPath検索")
                        return elem
        except Exception as e:
            continue

    print(f"      ❌ 戦略2失敗")
    return None

def find_connect_button_strategy3(driver):
    """戦略3: 全ボタンをスキャンして判定"""
    print("   🔍 戦略3: 全ボタンスキャンを試行...")

    try:
        all_buttons = driver.find_elements(By.TAG_NAME, "button")

        for btn in all_buttons:
            try:
                text = btn.text.lower()
                aria = (btn.get_attribute("aria-label") or "").lower()

                if ("つながりを申請" in text or "connect" in text or
                    "つながりを申請" in aria or "connect" in aria):

                    if btn.is_displayed() and btn.is_enabled():
                        print(f"      ✅ 戦略3成功: 全スキャン")
                        return btn
            except:
                continue

        print(f"      ❌ 戦略3失敗")
        return None

    except Exception as e:
        print(f"      ❌ 戦略3エラー: {e}")
        return None

def find_connect_button(driver):
    """複数戦略でボタンを検出"""
    print("\n🔍 「つながりを申請」ボタン検出開始...")

    strategies = [
        find_connect_button_strategy1,
        find_connect_button_strategy2,
        find_connect_button_strategy3,
    ]

    for strategy in strategies:
        try:
            btn = strategy(driver)
            if btn:
                return btn
        except Exception as e:
            print(f"      ⚠️ 戦略実行中にエラー: {e}")
            continue

    print("❌ すべての戦略でボタン検出失敗")
    return None

# ==============================
# 送信処理
# ==============================
def send_requests(driver):
    """接続リクエスト送信（挨拶なしで送信）"""

    # CSV読み込み
    if not os.path.exists(TARGET_CSV):
        print(f"❌ メッセージファイルが見つかりません: {TARGET_CSV}")
        return

    with open(TARGET_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        messages = list(reader)

    if not messages:
        print("⚠️ メッセージ送信対象が空です。")
        return

    total = min(len(messages), LIMIT)
    print(f"\n{'='*70}")
    print(f"📤 接続リクエスト対象: {total} 件（上限 {LIMIT} 件）")
    print(f"{'='*70}")

    success = 0
    skip = 0
    error = 0

    for idx, msg in enumerate(messages[:LIMIT], start=1):
        name = msg.get("name", "不明")
        url = msg.get("url") or msg.get("profile_url")

        print(f"\n{'='*70}")
        print(f"[{idx}/{total}] 👤 {name}")
        print(f"🔗 {url}")
        print(f"{'='*70}")

        if not url:
            print(f"⚠️ URLが見つかりません。スキップします。")
            append_log(name, url, "skip", "URLなし")
            skip += 1
            continue

        try:
            # プロフィールページへ遷移
            print(f"🌐 プロフィールページに遷移中...")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(3.0)  # React再描画待機
            print(f"✅ ページ読み込み完了")

            # 接続状態チェック
            status = check_connection_status(driver)
            if status == "already_connected":
                print(f"ℹ️ {name}: 既につながっています。スキップします。")
                append_log(name, url, "skip", "既接続", "already_connected")
                skip += 1
                continue
            elif status == "pending":
                print(f"ℹ️ {name}: 既にリクエスト送信済み（保留中）。スキップします。")
                append_log(name, url, "skip", "保留中", "pending")
                skip += 1
                continue

            # ボタン検出
            btn = find_connect_button(driver)

            if not btn:
                print(f"❌ {name}: 『つながりを申請』ボタンが見つかりません。")
                save_debug_screenshot(driver, name, "button_not_found")
                append_log(name, url, "error", "ボタン未検出")
                error += 1
                continue

            # スクロール&クリック
            print(f"📍 ボタンをスクロール表示中...")
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});",
                btn
            )
            time.sleep(1.0)

            print(f"🖱️ 『つながりを申請』をクリック...")
            driver.execute_script("arguments[0].click();", btn)
            print(f"✅ クリック成功")

            # ダイアログ待機
            time.sleep(2.0)

            # 「挨拶なしで送信」ボタン探索
            no_note_xpaths = [
                "//button[contains(., '挨拶なしで送信')]",
                "//button[contains(., 'Send without a note')]",
                "//button[contains(@aria-label, '挨拶なしで送信')]",
                "//button[contains(@aria-label, 'Send without a note')]",
            ]

            no_note_btn = None
            for xpath in no_note_xpaths:
                elements = driver.find_elements(By.XPATH, xpath)
                if elements:
                    no_note_btn = elements[0]
                    break

            if no_note_btn:
                driver.execute_script("arguments[0].click();", no_note_btn)
                print(f"💬 『挨拶なしで送信』押下成功")
                append_log(name, url, "success", "", "sent_without_note")
                success += 1
            else:
                print(f"⚠️ 『挨拶なしで送信』ボタンが見つかりません。")
                save_debug_screenshot(driver, name, "no_note_button_not_found")
                append_log(name, url, "error", "挨拶なしボタンなし")
                error += 1

            # 次の送信までの待機
            wait_time = random.uniform(*DELAY_RANGE)
            print(f"⏳ {wait_time:.1f}秒待機...")
            time.sleep(wait_time)

        except TimeoutException:
            print(f"⏱ {name}: ページ読み込みタイムアウト")
            append_log(name, url, "error", "タイムアウト")
            error += 1
        except Exception as e:
            print(f"❌ {name}: エラー発生 - {e}")
            save_debug_screenshot(driver, name, "exception")
            append_log(name, url, "error", str(e))
            error += 1

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 送信完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 成功: {success} 件")
    print(f"⚪ スキップ: {skip} 件")
    print(f"❌ エラー: {error} 件")
    print(f"📝 ログ保存先: {LOG_CSV}")
    print(f"📸 デバッグファイル: {DEBUG_DIR}")
    print(f"{'='*70}")
    print("🪄 全処理完了。ブラウザを閉じてもOKです。")

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    driver = manual_login()
    send_requests(driver)
