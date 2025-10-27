# debug_all_links.py
# すべてのプロフィールリンクを詳細に調査

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")
CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

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
                print("✅ 自動ログイン成功！")
                return driver
        except Exception as e:
            print(f"⚠️ エラー: {e}")

    return driver

def debug_all_links(driver):
    """すべてのプロフィールリンクを詳細調査"""

    driver.get(CONNECTIONS_URL)
    time.sleep(5)

    # スクロール処理（本番と同じ）
    print("📜 スクロール中...")
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < 20:
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1

    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(2)

    print("\n" + "="*70)
    print("🔍 全プロフィールリンクの詳細調査")
    print("="*70 + "\n")

    # すべてのプロフィールリンクを取得
    script = """
    const allLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'));

    const results = [];

    for (let i = 0; i < allLinks.length; i++) {
        const link = allLinks[i];
        const href = link.href;
        const text = link.textContent.trim();
        const isProfile = href.match(/\\/in\\/[^/]+\\/?$/);

        results.push({
            index: i + 1,
            href: href,
            text: text.substring(0, 100),
            textLength: text.length,
            isProfileLink: !!isProfile
        });
    }

    return results;
    """

    links = driver.execute_script(script)

    print(f"✅ 検出されたリンク総数: {len(links)} 件\n")

    # プロフィールリンクのみフィルタ
    profile_links = [l for l in links if l['isProfileLink']]
    print(f"✅ プロフィールリンク数: {len(profile_links)} 件\n")

    print("="*70)
    print("📋 すべてのプロフィールリンク一覧")
    print("="*70 + "\n")

    for link in profile_links[:20]:  # 最初の20件
        print(f"[{link['index']}] 名前の長さ: {link['textLength']} 文字")
        print(f"    テキスト: {link['text']}")
        print(f"    URL: {link['href']}")
        print()

    # Rio Ishido や Zhen YAN を検索
    print("="*70)
    print("🔍 特定の名前を検索")
    print("="*70 + "\n")

    search_names = ["Rio", "Ishido", "Zhen", "YAN", "鈴木"]

    for name in search_names:
        found = [l for l in profile_links if name.lower() in l['text'].lower()]
        print(f"'{name}' を含むリンク: {len(found)} 件")
        for l in found[:3]:
            print(f"  - {l['text'][:50]}... ({l['href']})")
        print()

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_all_links(driver)
