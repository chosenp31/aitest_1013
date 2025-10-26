# debug_connections.py
# つながりページのDOM構造をデバッグ

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
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(COOKIE_FILE)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)

    print("🔑 LinkedIn 手動ログインモード開始...")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了")

    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}")

    return driver

def debug_connections_page(driver):
    """つながりページのDOM構造をデバッグ"""
    print(f"\n{'='*70}")
    print(f"🔍 つながりページのDOM構造を調査中...")
    print(f"{'='*70}\n")

    driver.get(CONNECTIONS_URL)
    time.sleep(5)

    # スクロールして全件読み込み
    print("📜 ページをスクロール中...")
    for i in range(3):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
    print("✅ スクロール完了\n")

    # 複数のセレクター戦略を試す
    strategies = [
        ("li.mn-connection-card", "mn-connection-card"),
        ("li[class*='connection-card']", "connection-card (wildcard)"),
        ("ul.mn-connections__cards-list li", "mn-connections__cards-list > li"),
        ("div.mn-connection-card", "div.mn-connection-card"),
        ("li.reusable-search__result-container", "reusable-search__result-container"),
        ("li", "すべてのli要素（上限10件）")
    ]

    for selector, description in strategies:
        print(f"{'='*70}")
        print(f"🧪 テスト: {description}")
        print(f"   セレクター: {selector}")
        print(f"{'='*70}")

        script = f"""
        const elements = document.querySelectorAll('{selector}');
        const results = [];

        for (let i = 0; i < Math.min(elements.length, 10); i++) {{
            const el = elements[i];
            results.push({{
                tagName: el.tagName,
                className: el.className,
                innerHTML: el.innerHTML.substring(0, 300)
            }});
        }}

        return {{
            count: elements.length,
            samples: results
        }};
        """

        try:
            result = driver.execute_script(script)
            count = result.get('count', 0)
            samples = result.get('samples', [])

            print(f"✅ マッチ数: {count} 件\n")

            if samples:
                for idx, sample in enumerate(samples[:3], start=1):
                    print(f"   --- サンプル {idx} ---")
                    print(f"   タグ: {sample.get('tagName')}")
                    print(f"   クラス: {sample.get('className', '')[:100]}")
                    print(f"   HTML（最初の300文字）:")
                    print(f"   {sample.get('innerHTML', '')[:300]}")
                    print()

        except Exception as e:
            print(f"❌ エラー: {e}\n")

    # 特定の要素を探す
    print(f"\n{'='*70}")
    print(f"🔍 特定要素の検索")
    print(f"{'='*70}\n")

    # 日付を含む要素を探す
    date_script = """
    const allElements = document.querySelectorAll('*');
    const dateElements = [];

    for (let el of allElements) {
        const text = el.textContent || '';
        if (text.includes('につながりました') || text.includes('年') && text.includes('月')) {
            dateElements.push({
                tagName: el.tagName,
                className: el.className,
                text: text.substring(0, 100)
            });
            if (dateElements.length >= 5) break;
        }
    }

    return dateElements;
    """

    try:
        date_elements = driver.execute_script(date_script)
        print(f"📅 日付を含む要素: {len(date_elements)} 件\n")

        for idx, el in enumerate(date_elements[:5], start=1):
            print(f"   --- 日付要素 {idx} ---")
            print(f"   タグ: {el.get('tagName')}")
            print(f"   クラス: {el.get('className', '')[:100]}")
            print(f"   テキスト: {el.get('text', '')}")
            print()

    except Exception as e:
        print(f"❌ エラー: {e}\n")

    print(f"\n{'='*70}")
    print(f"🎯 調査完了")
    print(f"{'='*70}\n")
    print("ブラウザを開いたまま維持しています。")
    print("手動でページのHTML構造を確認してください。")
    print("確認後、Enterキーを押してブラウザを閉じます。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_connections_page(driver)
