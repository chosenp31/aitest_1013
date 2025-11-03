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
        'log_file': os.path.join(account_dir, "connection_logs.csv")
    }

DELAY_RANGE = (2, 4)  # クリック間隔（秒）

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
# ログ記録
# ==============================
def log_request(name, result, log_file, error=""):
    """送信結果をログに記録"""
    file_exists = os.path.exists(log_file)

    with open(log_file, "a", newline="", encoding="utf-8") as f:
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
def send_connections_on_page(driver, log_file, current_total=0, max_requests=50):
    """現在の検索結果ページ上で全ての候補者につながり申請"""

    # ページを下までスクロール（改善版：より確実に全候補者を読み込む）
    print("   📜 ページをスクロール中...")
    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(10):  # 最大10回スクロール
        # JavaScriptで段階的にスクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # 動的コンテンツの読み込みを待つ

        # 新しい高さを取得
        new_height = driver.execute_script("return document.body.scrollHeight")

        # ページの高さが変わらなくなったら終了
        if new_height == last_height:
            print(f"   ✓ スクロール完了（{i+1}回目で到達）")
            break
        last_height = new_height

    time.sleep(2)  # 最終的な読み込みを待つ

    # つながり申請ボタンを検出（「つながり申請」「つながる」「Connect」全対応）
    script = """
    const allButtons = document.querySelectorAll('button');
    const candidates = [];

    allButtons.forEach((btn) => {
        const text = btn.textContent.trim();
        const textLower = text.toLowerCase();

        // 「つながり申請」「つながる」「Connect」など全パターンに対応
        if ((text.includes('つながり') || text.includes('つながる') || textLower.includes('connect')) &&
            !btn.closest('header')) {

            // ボタンの親要素を遡って候補者カードを特定
            let card = btn.parentElement;
            for (let i = 0; i < 8; i++) {
                if (card && card.innerText && card.innerText.includes('•')) {
                    break;
                }
                if (card) {
                    card = card.parentElement;
                }
            }

            if (card && card.innerText) {
                const lines = card.innerText.split('\\n');
                if (lines[0]) {
                    let name = lines[0].split('•')[0].trim();

                    if (name && name.length >= 2 &&
                        name !== 'つながる' &&
                        name !== 'つながり' &&
                        name !== 'ホーム' &&
                        name !== 'メッセージ') {
                        candidates.push({
                            name: name,
                            buttonText: text
                        });
                    }
                }
            }
        }
    });

    return candidates;
    """

    try:
        candidates = driver.execute_script(script)

        # 検出結果を表示
        print(f"   🔍 検出: 候補者{len(candidates)}件")
        if len(candidates) > 0:
            print(f"   候補者: {', '.join([c['name'] for c in candidates[:5]])}{'...' if len(candidates) > 5 else ''}")

        success_count = 0
        skip_count = 0

        for candidate in candidates:
            # 上限に達したらループを抜ける
            if current_total + success_count >= max_requests:
                print(f"\n   ⚠️  上限{max_requests}件に達しました。処理を終了します。")
                break

            name = candidate['name']

            # ボタンをクリック
            try:
                # JavaScriptで直接クリック（名前ベース検索）
                safe_name = name.replace("'", "\\'").replace('"', '\\"')

                click_script = f"""
                const allButtons = document.querySelectorAll('button');
                let targetButton = null;

                for (const btn of allButtons) {{
                    const text = btn.textContent.trim();
                    const textLower = text.toLowerCase();

                    // 「つながり申請」「つながる」「Connect」など全パターンに対応
                    if ((text.includes('つながり') || text.includes('つながる') || textLower.includes('connect')) &&
                        !btn.closest('header')) {{

                        let card = btn.parentElement;
                        for (let i = 0; i < 8; i++) {{
                            if (card && card.innerText && card.innerText.includes('•')) {{
                                break;
                            }}
                            if (card) {{
                                card = card.parentElement;
                            }}
                        }}

                        if (card && card.innerText) {{
                            const lines = card.innerText.split('\\n');
                            if (lines[0]) {{
                                let cardName = lines[0].split('•')[0].trim();

                                if (cardName === '{safe_name}') {{
                                    targetButton = btn;
                                    break;
                                }}
                            }}
                        }}
                    }}
                }}

                if (targetButton) {{
                    targetButton.scrollIntoView({{ block: 'center', behavior: 'instant' }});
                    targetButton.click();
                    return {{ success: true }};
                }}
                return {{ success: false }};
                """

                result = driver.execute_script(click_script)

                if result['success']:
                    time.sleep(2)

                    # モーダルが出た場合は「送信」をJavaScriptでクリック
                    send_clicked = driver.execute_script("""
                        const buttons = document.querySelectorAll('button');
                        for (const btn of buttons) {
                            const text = btn.textContent.trim();
                            const ariaLabel = btn.getAttribute('aria-label') || '';
                            if (text.includes('送信') || text.includes('Send') ||
                                ariaLabel.includes('送信') || ariaLabel.includes('Send')) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    """)

                    if send_clicked:
                        time.sleep(1)

                    print(f"   ✅ {name} - つながり申請を送信")
                    success_count += 1
                    log_request(name, "success", log_file, "")

                    # 遅延
                    delay = random.uniform(*DELAY_RANGE)
                    time.sleep(delay)
                else:
                    print(f"   ❌ {name} - クリック失敗")
                    log_request(name, "error", log_file, "click_failed")

            except Exception as e:
                print(f"   ❌ {name} - エラー: {e}")
                log_request(name, "error", log_file, str(e))

        return success_count, skip_count

    except Exception as e:
        print(f"⚠️ ページ処理エラー: {e}")
        return 0, 0

# ==============================
# メイン処理
# ==============================
def send_connections(account_name, paths, keywords, location="Japan", max_pages=1, max_requests=5):
    """
    検索結果ページ上で直接つながり申請を送信

    Args:
        account_name: アカウント名
        paths: アカウント毎のパス情報
        keywords: 検索キーワード
        location: 地域
        max_pages: 検索ページ数
        max_requests: 最大申請件数
    """
    driver = login(account_name, paths['cookie_file'])

    # 検索URLベース構築（2次のつながりのみに絞る）
    search_url_base = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"
    if location:
        search_url_base += f"&location={location}"

    # 2次のつながりフィルターを追加（1次のつながりを除外）
    search_url_base += "&network=%5B%22S%22%5D"

    print(f"\n🔎 検索条件:")
    print(f"   アカウント: {account_name}")
    print(f"   キーワード: {keywords}")
    print(f"   地域: {location}")
    print(f"   つながりレベル: 2次のみ（1次は除外）")
    print(f"   ページ数: {max_pages}")
    print(f"   最大申請件数: {max_requests}")

    # 最初のページにアクセス
    driver.get(search_url_base)
    time.sleep(5)

    print(f"\n{'='*70}")
    print(f"📊 つながり申請開始")
    print(f"{'='*70}")

    total_success = 0
    total_skip = 0

    for page in range(1, max_pages + 1):
        print(f"\n📄 ページ {page}/{max_pages} を処理中...")

        # 現在のページで申請
        success, skip = send_connections_on_page(driver, paths['log_file'], total_success, max_requests)
        total_success += success
        total_skip += skip

        print(f"   このページ: 成功{success}件、スキップ{skip}件")

        # 上限に達したらループを抜ける
        if total_success >= max_requests:
            print(f"\n✅ 目標{max_requests}件に達しました。")
            break

        # 次ページへ遷移（2つの方式を試す）
        if page < max_pages:
            transitioned = False

            # 方式1: ボタンクリック（「つながり申請」ボタンアカウント向け）
            try:
                next_clicked = driver.execute_script("""
                    const buttons = document.querySelectorAll('button');
                    for (const btn of buttons) {
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        const text = btn.textContent.trim();

                        // フィルタボタン（1次、2次、3次）を除外
                        if (text === '1次' || text === '2次' || text === '3次' ||
                            text === '1次のつながり' || text === '2次のつながり' || text === '3次のつながり') {
                            continue;
                        }

                        // ページネーションボタンを検出
                        // aria-labelで「次へ」「次のページ」「Next」などを探す
                        if (ariaLabel.includes('次へ') || ariaLabel.includes('次のページ') ||
                            ariaLabel.toLowerCase().includes('next page') ||
                            (ariaLabel.toLowerCase().includes('next') && !ariaLabel.includes('1次') && !ariaLabel.includes('2次') && !ariaLabel.includes('3次'))) {
                            btn.scrollIntoView({ block: 'center', behavior: 'instant' });
                            btn.click();
                            return true;
                        }

                        // aria-labelがない場合、テキストで判定（ただし厳密に）
                        if (!ariaLabel && (text === '次へ' || text.toLowerCase() === 'next')) {
                            btn.scrollIntoView({ block: 'center', behavior: 'instant' });
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                """)

                if next_clicked:
                    print("   ✓ 次ページへ遷移（ボタンクリック方式）")
                    time.sleep(5)
                    transitioned = True
            except Exception as e:
                print(f"   ⚠️ ボタンクリック方式失敗: {e}")

            # 方式2: URLパラメータ（「つながる」ボタンアカウント向け、またはフォールバック）
            if not transitioned:
                try:
                    next_page_url = search_url_base + f"&page={page + 1}"
                    driver.get(next_page_url)
                    print(f"   ✓ 次ページへ遷移（URLパラメータ方式: page={page + 1}）")
                    time.sleep(5)
                    transitioned = True
                except Exception as e:
                    print(f"   ⚠️ URLパラメータ方式失敗: {e}")

            # どちらの方式も失敗した場合
            if not transitioned:
                print("   ⚠️ ページ遷移できませんでした。終了します。")
                break

    # サマリー
    print(f"\n{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 送信成功: {total_success}件")
    print(f"⏭️  スキップ: {total_skip}件")
    print(f"📝 ログ: {paths['log_file']}")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🤝 LinkedIn つながり申請")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

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
    print(f"アカウント: {account_name}")
    print(f"キーワード: {keywords}")
    print(f"地域: {location}")
    print(f"最大ページ数: {max_pages}")
    print(f"最大申請件数: {max_requests}")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    send_connections(account_name, paths, keywords, location, max_pages, max_requests)
