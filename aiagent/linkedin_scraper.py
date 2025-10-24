# aiagent/linkedin_scraper.py
# ✅ LinkedIn 候補者抽出モジュール（手動ログイン・Cookie不使用・ページネーション対応版）
# ✅ 検索キーワードを「SIer」に変更済み

import os
import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# ======================================
# データディレクトリ設定
# ======================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
OUTPUT_FILE = os.path.join(DATA_DIR, "candidates_raw.csv")

# ======================================
# 手動ログイン
# ======================================
def linkedin_manual_login():
    print("🔑 手動ログインモードでブラウザを起動します...")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.linkedin.com/login")

    print("🌐 ご自身のアカウントでLinkedInにログインしてください。")
    print("💡 ログイン後、feedページ（https://www.linkedin.com/feed/）が表示されるまで待機します...")

    while True:
        try:
            if "feed" in driver.current_url:
                print("✅ ログイン完了を検出しました。")
                break
        except Exception:
            pass
        time.sleep(2)
    return driver

# ======================================
# プロフィール抽出関数
# ======================================
def extract_profiles(driver):
    """現在表示中の検索結果ページからプロフィールを抽出"""
    script = """
    function getAllProfileLinks() {
        const results = [];
        const anchors = Array.from(document.querySelectorAll('a[href*="/in/"]'));
        const seen = new Set();
        for (const a of anchors) {
            const url = (a.href || '').split('?')[0];
            if (!url || seen.has(url)) continue;
            seen.add(url);
            const container = a.closest("li") || a.closest("div");
            const nameEl = container ? (container.querySelector("span[dir='ltr'], span[aria-hidden='true']") || a) : a;
            const name = (nameEl.textContent || '').trim();
            if (!name) continue;
            results.push({ name, url });
        }
        return results;
    }
    return getAllProfileLinks();
    """
    return driver.execute_script(script) or []

# ======================================
# ページごとのスクロール
# ======================================
def scroll_page(driver):
    last_h = 0
    for _ in range(6):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(1.8)
        h = driver.execute_script("return document.body.scrollHeight")
        if h == last_h:
            break
        last_h = h

# ======================================
# メイン処理（3ページ分抽出）
# ======================================
def scrape_candidates():
    os.makedirs(DATA_DIR, exist_ok=True)
    driver = linkedin_manual_login()

    # 🔍 検索条件を「SIer」に固定
    keywords = "SIer"
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER"

    print(f"🔎 検索URL: {search_url}")
    driver.get(search_url)
    wait = WebDriverWait(driver, 20)
    try:
        wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    except TimeoutException:
        pass

    all_rows = []
    seen_urls = set()
    MAX_PAGES = 3

    for page in range(1, MAX_PAGES + 1):
        print(f"\n📄 ページ {page} の候補者を抽出中...")
        time.sleep(4)
        scroll_page(driver)
        time.sleep(2)

        data = extract_profiles(driver)
        print(f"📦 ページ {page} の抽出件数: {len(data)}")

        for item in data:
            name = (item.get("name") or "").strip()
            url = (item.get("url") or "").split("?")[0]
            if not name or not url or url in seen_urls:
                continue
            seen_urls.add(url)
            all_rows.append({"name": name, "url": url})

        # 「次へ」ボタンを押して次ページへ
        try:
            next_btn = driver.find_element(
                By.XPATH, "//button[contains(., '次へ')] | //button[contains(., 'Next')]"
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)
            next_btn.click()
            print("➡️ 次ページへ遷移します...")
            time.sleep(5)
        except NoSuchElementException:
            print("🚫 次ページが見つかりません。終了します。")
            break

    # CSV出力
    print(f"\n📊 全ページ合計の有効候補者数: {len(all_rows)}")
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "url"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"💾 CSV保存完了: {OUTPUT_FILE}")
    print("✅ 候補者抽出処理が完了しました。ブラウザは閉じてもOKです。")
    driver.quit()

# ======================================
# エントリーポイント
# ======================================
if __name__ == "__main__":
    scrape_candidates()
