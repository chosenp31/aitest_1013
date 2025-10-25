# aiagent/linkedin_search.py
# LinkedIn候補者検索スクリプト（検索条件を柔軟に設定可能）

import os
import csv
import time
import pickle
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
OUTPUT_FILE = os.path.join(DATA_DIR, "candidates_raw.csv")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")

os.makedirs(DATA_DIR, exist_ok=True)

# ==============================
# ログイン（自動/手動）
# ==============================
def login():
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie保存ファイルが存在するか確認
    if os.path.exists(COOKIE_FILE):
        print("🔑 保存されたCookieを使用して自動ログイン中...")

        # まずLinkedInにアクセス（Cookieを設定するため）
        driver.get("https://www.linkedin.com")
        time.sleep(2)

        # Cookieを読み込み
        try:
            with open(COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)

            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception:
                    # 無効なCookieはスキップ
                    pass

            # Cookieを設定後、再度アクセス
            driver.get("https://www.linkedin.com/feed")
            time.sleep(5)  # 待機時間を延長

            # 現在のURLをデバッグ出力
            current_url = driver.current_url
            print(f"   📍 現在のURL: {current_url}")

            # ログイン成功確認（より厳密に）
            if ("feed" in current_url or "home" in current_url) and "login" not in current_url:
                print("✅ 自動ログイン成功！")
                return driver
            else:
                print("⚠️ Cookieが期限切れ、または無効です。手動ログインに切り替えます...")
                print(f"   リダイレクト先: {current_url}")
                os.remove(COOKIE_FILE)  # 古いCookieを削除

        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            print("   手動ログインに切り替えます...")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)

    # 手動ログイン
    print("🔑 LinkedIn 手動ログインモード開始...")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")
    print("💡 ログイン後、feedページが表示されるまで待機します...")

    # ログイン完了待機
    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了を検出しました。")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました: {COOKIE_FILE}")
        print("   次回から自動ログインが使用されます。")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}")

    return driver

# ==============================
# プロフィール抽出
# ==============================
def extract_profiles(driver):
    """現在表示中の検索結果ページからプロフィールを抽出"""

    # より詳細な情報を取得するJavaScript
    script = """
    function extractProfiles() {
        const results = [];
        const seen = new Set();

        // 検索結果のリストアイテムを取得（複数の戦略を試す）
        let items = [];

        // 戦略1: 新しいクラス名（2025年1月時点）
        items = document.querySelectorAll('li.qTpSkRrerBcUqHivKtVbqVGnMhgMkDU');
        console.log('戦略1（新クラス名）:', items.length, '件');

        // 戦略2: フォールバック - 検索結果のul内のli要素
        if (items.length === 0) {
            const ul = document.querySelector('ul.gXgHtWXGAynxZWGGYQtgBMtLnHWPyXyPsSuyEH');
            if (ul) {
                items = ul.querySelectorAll('li');
                console.log('戦略2（ul内のli）:', items.length, '件');
            }
        }

        // 戦略3: さらなるフォールバック - プロフィールリンクから親のliを取得
        if (items.length === 0) {
            const profileLinks = document.querySelectorAll('a[href*="/in/"]');
            const liSet = new Set();
            profileLinks.forEach(link => {
                let current = link;
                for (let i = 0; i < 10; i++) {
                    current = current.parentElement;
                    if (!current) break;
                    if (current.tagName === 'LI') {
                        liSet.add(current);
                        break;
                    }
                }
            });
            items = Array.from(liSet);
            console.log('戦略3（リンクから親li）:', items.length, '件');
        }

        items.forEach(item => {
            try {
                // プロフィールURL
                const profileLink = item.querySelector('a[href*="/in/"]');
                if (!profileLink) return;

                const url = profileLink.href.split('?')[0];
                if (seen.has(url)) return;
                seen.add(url);

                // 名前（複数パターンを試す）
                let name = '';
                const nameEl1 = item.querySelector('span[aria-hidden="true"]');
                const nameEl2 = item.querySelector('span.entity-result__title-text span[dir="ltr"]');
                const nameEl3 = profileLink.querySelector('span[dir="ltr"]');
                name = (nameEl1 || nameEl2 || nameEl3)?.textContent.trim() || '';

                // 見出し（職種・役職）
                const headlineEl = item.querySelector('.entity-result__primary-subtitle, [class*="primary-subtitle"]');
                const headline = headlineEl ? headlineEl.textContent.trim() : '';

                // 会社・学校
                const secondaryEl = item.querySelector('.entity-result__secondary-subtitle, [class*="secondary-subtitle"]');
                const secondary = secondaryEl ? secondaryEl.textContent.trim() : '';

                // 場所
                const locationEl = item.querySelector('.entity-result__location, [class*="location"]');
                const location = locationEl ? locationEl.textContent.trim() : '';

                if (name && url) {
                    results.push({
                        name: name,
                        url: url,
                        headline: headline,
                        company: secondary,
                        location: location
                    });
                }
            } catch (e) {
                console.error('Error extracting profile:', e);
            }
        });

        console.log('最終抽出件数:', results.length, '件');
        return results;
    }
    return extractProfiles();
    """

    try:
        return driver.execute_script(script) or []
    except Exception as e:
        print(f"⚠️ プロフィール抽出エラー: {e}")
        return []

# ==============================
# ページスクロール
# ==============================
def scroll_page(driver):
    """ページを下までスクロール"""
    last_height = 0
    for _ in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2.0)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# ==============================
# メイン検索処理
# ==============================
def search_candidates(keywords, location="Japan", max_pages=3):
    """
    LinkedIn候補者検索

    Args:
        keywords: 検索キーワード（例: "SIer OR エンジニア OR ITコンサル"）
        location: 地域（例: "Japan", "東京"）
        max_pages: 検索するページ数（デフォルト3）

    Returns:
        抽出した候補者数
    """

    driver = login()

    # 検索URLを構築
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"
    if location:
        search_url += f"&location={location}"

    print(f"\n🔎 検索条件:")
    print(f"   キーワード: {keywords}")
    print(f"   地域: {location}")
    print(f"   ページ数: {max_pages}")
    print(f"\n🔗 検索URL: {search_url}")

    driver.get(search_url)

    # ページ読み込み待機
    wait = WebDriverWait(driver, 20)
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except TimeoutException:
        print("⚠️ ページ読み込みタイムアウト")

    all_candidates = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        print(f"\n{'='*70}")
        print(f"📄 ページ {page}/{max_pages} を処理中...")
        print(f"{'='*70}")

        time.sleep(3.0)
        scroll_page(driver)
        time.sleep(2.0)

        # プロフィール抽出
        profiles = extract_profiles(driver)
        print(f"📦 抽出件数: {len(profiles)} 件")

        # 重複除外して追加
        new_count = 0
        for profile in profiles:
            url = profile.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_candidates.append(profile)
                new_count += 1

        print(f"✅ 新規候補者: {new_count} 件（累計: {len(all_candidates)} 件）")

        # 次ページへ
        if page < max_pages:
            try:
                # ページネーションボタンを探す（「1次」「2次」などのフィルターボタンと区別）
                # 戦略1: ページネーションエリア内のボタンに限定
                next_btn = None
                try:
                    next_btn = driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'artdeco-pagination')]//button[contains(@aria-label, '次') or contains(@aria-label, 'Next')]"
                    )
                    print("   ✓ 戦略1: ページネーションエリア内のボタンを検出")
                except NoSuchElementException:
                    pass

                # 戦略2: aria-labelが「次へ」で始まるボタン
                if not next_btn:
                    try:
                        next_btn = driver.find_element(
                            By.XPATH,
                            "//button[starts-with(@aria-label, '次へ') or starts-with(@aria-label, 'Next')]"
                        )
                        print("   ✓ 戦略2: aria-label前方一致で検出")
                    except NoSuchElementException:
                        pass

                # 戦略3: ページ下部のボタンのみ（上部のフィルターを除外）
                if not next_btn:
                    buttons = driver.find_elements(
                        By.XPATH,
                        "//button[contains(@aria-label, '次') or contains(@aria-label, 'Next')]"
                    )
                    # Y座標が大きい（ページ下部）のボタンを選択
                    if buttons:
                        next_btn = max(buttons, key=lambda btn: btn.location['y'])
                        print("   ✓ 戦略3: ページ下部のボタンを検出")

                if next_btn:
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(1.0)
                    next_btn.click()
                    print("➡️ 次ページへ遷移...")
                    time.sleep(4.0)
                else:
                    print("⚠️ 次ページボタンが見つかりません。検索終了。")
                    break

            except NoSuchElementException:
                print("⚠️ 次ページボタンが見つかりません。検索終了。")
                break

    # CSV保存
    print(f"\n{'='*70}")
    print(f"📊 検索完了サマリー")
    print(f"{'='*70}")
    print(f"総候補者数: {len(all_candidates)} 件")
    print(f"保存先: {OUTPUT_FILE}")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["name", "url", "headline", "company", "location"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_candidates)

    print(f"✅ 候補者リストを保存しました")
    print(f"\n💡 次のステップ: python3 aiagent/linkedin_scorer.py でスコアリングを実行")

    return len(all_candidates)

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    import sys

    # コマンドライン引数から検索条件を取得
    if len(sys.argv) > 1:
        keywords = sys.argv[1]
    else:
        # デフォルト: 複数キーワードをOR検索
        keywords = "SIer OR エンジニア OR ITコンサルタント OR ITエンジニア OR DXエンジニア"

    location = sys.argv[2] if len(sys.argv) > 2 else "Japan"
    max_pages = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    search_candidates(keywords, location, max_pages)
