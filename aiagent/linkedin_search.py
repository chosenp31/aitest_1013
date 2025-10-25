# aiagent/linkedin_search.py
# LinkedIn候補者検索スクリプト（検索条件を柔軟に設定可能）

import os
import csv
import time
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

os.makedirs(DATA_DIR, exist_ok=True)

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

    print("✅ ログイン完了を検出しました。")
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

        // 検索結果のリストアイテムを取得
        const items = document.querySelectorAll('li.reusable-search__result-container');

        items.forEach(item => {
            try {
                // プロフィールURL
                const profileLink = item.querySelector('a.app-aware-link[href*="/in/"]');
                if (!profileLink) return;

                const url = profileLink.href.split('?')[0];
                if (seen.has(url)) return;
                seen.add(url);

                // 名前
                const nameEl = item.querySelector('span[aria-hidden="true"]');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // 見出し（職種・役職）
                const headlineEl = item.querySelector('.entity-result__primary-subtitle');
                const headline = headlineEl ? headlineEl.textContent.trim() : '';

                // 会社・学校
                const secondaryEl = item.querySelector('.entity-result__secondary-subtitle');
                const secondary = secondaryEl ? secondaryEl.textContent.trim() : '';

                // 場所
                const locationEl = item.querySelector('.entity-result__location');
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

    driver = manual_login()

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
                next_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(@aria-label, '次')] | //button[contains(@aria-label, 'Next')]"
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                time.sleep(1.0)
                next_btn.click()
                print("➡️ 次ページへ遷移...")
                time.sleep(4.0)
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
