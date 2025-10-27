# debug_scroll_container.py
# スクロール可能な要素を特定

import os
import time
import pickle
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

def find_scroll_container(driver):
    """スクロール可能なコンテナを特定"""

    driver.get(CONNECTIONS_URL)
    time.sleep(8)

    print("\n" + "="*70)
    print("🔍 スクロール可能な要素を調査")
    print("="*70 + "\n")

    # スクロール可能な要素を検出
    script = """
    const scrollableElements = [];

    // すべての要素を取得
    const allElements = document.querySelectorAll('*');

    for (let el of allElements) {
        const style = window.getComputedStyle(el);
        const overflowY = style.overflowY;
        const scrollHeight = el.scrollHeight;
        const clientHeight = el.clientHeight;

        // overflow-y が scroll または auto で、スクロール可能な高さがある要素
        if ((overflowY === 'scroll' || overflowY === 'auto') && scrollHeight > clientHeight) {
            scrollableElements.push({
                tagName: el.tagName,
                className: el.className,
                id: el.id,
                scrollHeight: scrollHeight,
                clientHeight: clientHeight,
                overflowY: overflowY
            });
        }
    }

    return scrollableElements;
    """

    scrollable = driver.execute_script(script)

    print(f"✅ スクロール可能な要素: {len(scrollable)} 件\n")

    for idx, el in enumerate(scrollable, start=1):
        print(f"--- 要素 {idx} ---")
        print(f"タグ: {el['tagName']}")
        print(f"クラス: {el['className'][:100]}")
        print(f"ID: {el['id']}")
        print(f"スクロール高さ: {el['scrollHeight']}px")
        print(f"表示高さ: {el['clientHeight']}px")
        print(f"overflow-y: {el['overflowY']}")
        print()

    # つながりカードを含む親要素を探す
    print("="*70)
    print("🔍 つながりカードの親コンテナを調査")
    print("="*70 + "\n")

    parent_script = """
    const profileLinks = document.querySelectorAll('a[href*="/in/"]');
    if (profileLinks.length === 0) return null;

    let container = profileLinks[0];

    // 上に遡ってスクロール可能な親を探す
    for (let i = 0; i < 20; i++) {
        container = container.parentElement;
        if (!container) break;

        const style = window.getComputedStyle(container);
        const overflowY = style.overflowY;
        const scrollHeight = container.scrollHeight;
        const clientHeight = container.clientHeight;

        if ((overflowY === 'scroll' || overflowY === 'auto') && scrollHeight > clientHeight) {
            return {
                tagName: container.tagName,
                className: container.className,
                id: container.id,
                scrollHeight: scrollHeight,
                clientHeight: clientHeight,
                overflowY: overflowY,
                level: i
            };
        }
    }

    return null;
    """

    parent_container = driver.execute_script(parent_script)

    if parent_container:
        print("✅ つながりカードを含むスクロールコンテナを発見！\n")
        print(f"タグ: {parent_container['tagName']}")
        print(f"クラス: {parent_container['className'][:100]}")
        print(f"ID: {parent_container['id']}")
        print(f"親要素の階層: {parent_container['level']}")
        print(f"スクロール高さ: {parent_container['scrollHeight']}px")
        print(f"表示高さ: {parent_container['clientHeight']}px")
    else:
        print("⚠️ スクロールコンテナが見つかりませんでした")

    print("\n" + "="*70)
    print("🎯 調査完了")
    print("="*70 + "\n")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    find_scroll_container(driver)
