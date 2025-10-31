# aiagent/linkedin_send_connections.py
# 検索結果ページ上で直接つながり申請を送信（プロフィール遷移なし）

import os
import time
import csv
import random
import pickle
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "connection_logs.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

DELAY_RANGE = (2, 4)  # クリック間隔（秒）

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
# ログ記録
# ==============================
def log_request(name, result, error=""):
    """送信結果をログに記録"""
    file_exists = os.path.exists(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "name", "result", "error"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "result": result,
            "error": error
        })

# ==============================
# 検索結果ページ上でつながり申請
# ==============================
def send_connections_on_page(driver, current_total=0, max_requests=50):
    """現在の検索結果ページ上で全ての候補者につながり申請"""

    # ページを下までスクロール
    for _ in range(3):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(1)

    # 候補者カードを取得してボタンをクリック
    script = """
    const allLis = document.querySelectorAll('li');
    const results = [];
    let candidateIndex = 0;

    allLis.forEach((li) => {
        // ナビゲーション要素やフィルター要素を除外
        const classes = li.className || '';
        if (classes.includes('global-nav') ||
            classes.includes('search-reusables__filter') ||
            classes.includes('search-reusables__collection-values')) {
            return;
        }

        // 名前要素（span[aria-hidden="true"]）があるかチェック
        const nameEl = li.querySelector('span[aria-hidden="true"]');
        if (!nameEl) return;

        const name = nameEl.textContent.trim();
        if (!name || name.length < 2) return;

        // ボタンがあるかチェック
        const buttons = li.querySelectorAll('button');
        if (buttons.length === 0) return;

        // つながり申請ボタンまたはメッセージボタンがあるか確認
        let hasConnectButton = false;
        let hasMessageButton = false;

        for (const btn of buttons) {
            const text = btn.textContent.trim();
            const ariaLabel = btn.getAttribute('aria-label') || '';

            if (text.includes('つながりを申請') || text.includes('Connect')) {
                hasConnectButton = true;
                break;
            }
            if (text.includes('メッセージ') || text.includes('Message') ||
                ariaLabel.includes('メッセージ') || ariaLabel.includes('message')) {
                hasMessageButton = true;
            }
        }

        // つながり申請ボタンまたはメッセージボタンがある場合のみ候補者カードとして扱う
        if (hasConnectButton || hasMessageButton) {
            results.push({
                index: candidateIndex,
                name: name,
                hasConnectButton: hasConnectButton,
                classes: classes
            });
            candidateIndex++;
        }
    });

    return results;
    """

    try:
        candidates = driver.execute_script(script)

        # 検出結果を表示
        connect_count = sum(1 for c in candidates if c['hasConnectButton'])
        already_connected_count = len(candidates) - connect_count

        print(f"   🔍 検出: 候補者{len(candidates)}件")
        print(f"      - つながり申請可能: {connect_count}件")
        print(f"      - 既接続: {already_connected_count}件")

        success_count = 0
        skip_count = 0

        for candidate in candidates:
            # 上限に達したらループを抜ける
            if current_total + success_count >= max_requests:
                print(f"\n   ⚠️  上限{max_requests}件に達しました。処理を終了します。")
                break

            name = candidate['name']
            has_button = candidate['hasConnectButton']

            if not has_button:
                print(f"   ⏭️  {name} - つながり申請ボタンなし（既接続または保留中）")
                skip_count += 1
                log_request(name, "skip", "no_connect_button")
                continue

            # ボタンをクリック
            try:
                # JavaScriptで直接クリック（詳細情報付き）
                click_script = f"""
                const allLis = document.querySelectorAll('li');
                let candidateIndex = 0;
                let targetCard = null;

                // 候補者カードを再検索
                for (const li of allLis) {{
                    const classes = li.className || '';
                    if (classes.includes('global-nav') ||
                        classes.includes('search-reusables__filter') ||
                        classes.includes('search-reusables__collection-values')) {{
                        continue;
                    }}

                    const nameEl = li.querySelector('span[aria-hidden="true"]');
                    if (!nameEl) continue;

                    const name = nameEl.textContent.trim();
                    if (!name || name.length < 2) continue;

                    const buttons = li.querySelectorAll('button');
                    if (buttons.length === 0) continue;

                    let hasRelevantButton = false;
                    for (const btn of buttons) {{
                        const text = btn.textContent.trim();
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        if (text.includes('つながりを申請') || text.includes('Connect') ||
                            text.includes('メッセージ') || text.includes('Message') ||
                            ariaLabel.includes('メッセージ') || ariaLabel.includes('message')) {{
                            hasRelevantButton = true;
                            break;
                        }}
                    }}

                    if (hasRelevantButton) {{
                        if (candidateIndex === {candidate['index']}) {{
                            targetCard = li;
                            break;
                        }}
                        candidateIndex++;
                    }}
                }}

                // デバッグ情報を含む結果オブジェクト
                const result = {{
                    success: false,
                    cardFound: !!targetCard,
                    buttonCount: 0,
                    buttonTexts: [],
                    connectButtonFound: false
                }};

                if (!targetCard) {{
                    return result;
                }}

                // つながり申請ボタンを探してクリック
                const buttons = targetCard.querySelectorAll('button');
                result.buttonCount = buttons.length;

                for (const btn of buttons) {{
                    const text = btn.textContent.trim();
                    result.buttonTexts.push(text);

                    if (text.includes('つながりを申請') || text.includes('Connect')) {{
                        result.connectButtonFound = true;

                        // ボタンをスクロールして表示
                        btn.scrollIntoView({{ block: 'center', behavior: 'instant' }});

                        // クリック
                        btn.click();
                        result.success = true;
                        break;
                    }}
                }}

                return result;
                """

                result = driver.execute_script(click_script)

                if result['success']:
                    time.sleep(1)

                    # モーダルが出た場合は「送信」をクリック
                    try:
                        send_btn = driver.find_element(By.XPATH, "//button[contains(@aria-label, '送信') or contains(., 'Send') or contains(., '送信')]")
                        send_btn.click()
                        time.sleep(1)
                    except NoSuchElementException:
                        # モーダルなしでもOK
                        pass

                    print(f"   ✅ {name} - つながり申請を送信")
                    success_count += 1
                    log_request(name, "success", "")

                    # 遅延
                    delay = random.uniform(*DELAY_RANGE)
                    time.sleep(delay)
                else:
                    # 失敗の詳細を表示
                    if not result['cardFound']:
                        error_msg = "候補者カードが見つからない"
                    elif result['buttonCount'] == 0:
                        error_msg = "ボタンが0個"
                    elif not result['connectButtonFound']:
                        error_msg = f"つながり申請ボタンなし (ボタン: {', '.join(result['buttonTexts'][:3])})"
                    else:
                        error_msg = "クリック実行失敗"

                    print(f"   ❌ {name} - {error_msg}")
                    log_request(name, "error", error_msg)

            except Exception as e:
                print(f"   ❌ {name} - エラー: {e}")
                log_request(name, "error", str(e))

        return success_count, skip_count

    except Exception as e:
        print(f"⚠️ ページ処理エラー: {e}")
        return 0, 0

# ==============================
# メイン処理
# ==============================
def send_connections(keywords, location="Japan", max_pages=1, max_requests=5):
    """
    検索結果ページ上で直接つながり申請を送信

    Args:
        keywords: 検索キーワード
        location: 地域
        max_pages: 検索ページ数
        max_requests: 最大申請件数
    """
    driver = login()

    # 検索URL構築
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"
    if location:
        search_url += f"&location={location}"

    print(f"\n🔎 検索条件:")
    print(f"   キーワード: {keywords}")
    print(f"   地域: {location}")
    print(f"   ページ数: {max_pages}")
    print(f"   最大申請件数: {max_requests}")

    driver.get(search_url)
    time.sleep(5)

    print(f"\n{'='*70}")
    print(f"📊 つながり申請開始")
    print(f"{'='*70}")

    total_success = 0
    total_skip = 0

    for page in range(1, max_pages + 1):
        print(f"\n📄 ページ {page}/{max_pages} を処理中...")

        # 現在のページで申請
        success, skip = send_connections_on_page(driver, total_success, max_requests)
        total_success += success
        total_skip += skip

        print(f"   このページ: 成功{success}件、スキップ{skip}件")

        # 上限に達したらループを抜ける
        if total_success >= max_requests:
            print(f"\n✅ 目標{max_requests}件に達しました。")
            break

        # 次ページへ
        if page < max_pages:
            try:
                # ページネーションボタンを探す
                next_btn = None
                try:
                    next_btn = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'artdeco-pagination')]//button[contains(@aria-label, '次') or contains(@aria-label, 'Next')]"
                    )
                except NoSuchElementException:
                    pass

                if next_btn:
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(1)
                    next_btn.click()
                    print("   ✓ 次ページへ遷移")
                    time.sleep(4)
                else:
                    print("   ⚠️ 次ページボタンなし。終了します。")
                    break
            except Exception as e:
                print(f"   ⚠️ ページ遷移エラー: {e}")
                break

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 送信成功: {total_success}件")
    print(f"⏭️  スキップ: {total_skip}件")
    print(f"📝 ログ: {LOG_FILE}")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🤝 LinkedIn つながり申請")
    print(f"{'='*70}\n")

    # 検索キーワード
    print("【検索キーワード】")
    keywords = input("検索キーワードを入力 (Enter=デフォルト「SIer OR エンジニア OR ITコンサルタント」): ").strip()
    if not keywords:
        keywords = "SIer OR エンジニア OR ITコンサルタント"

    # 地域
    print("\n【地域】")
    location = input("地域を入力 (Enter=デフォルト「Japan」): ").strip()
    if not location:
        location = "Japan"

    # 最大ページ数
    print("\n【最大ページ数】")
    while True:
        max_pages_input = input("検索結果の最大ページ数を入力 (Enter=デフォルト「5」): ").strip()
        if not max_pages_input:
            max_pages = 5
            break
        try:
            max_pages = int(max_pages_input)
            if max_pages > 0:
                break
            else:
                print("⚠️ 1以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 最大申請件数
    print("\n【最大申請件数】")
    while True:
        max_requests_input = input("最大申請件数を入力 (Enter=デフォルト「40」): ").strip()
        if not max_requests_input:
            max_requests = 40
            break
        try:
            max_requests = int(max_requests_input)
            if max_requests > 0:
                break
            else:
                print("⚠️ 1以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 確認
    print(f"\n{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"キーワード: {keywords}")
    print(f"地域: {location}")
    print(f"最大ページ数: {max_pages}")
    print(f"最大申請件数: {max_requests}")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    send_connections(keywords, location, max_pages, max_requests)
