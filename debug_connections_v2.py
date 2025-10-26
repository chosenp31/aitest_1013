# debug_connections_v2.py
# プロフィールリンクから逆算してつながりカードを検出

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

def debug_connections_page_v2(driver):
    """プロフィールリンクから逆算してカード検出"""
    print(f"\n{'='*70}")
    print(f"🔍 つながりページの構造を調査中（改良版）...")
    print(f"{'='*70}\n")

    driver.get(CONNECTIONS_URL)
    time.sleep(5)

    # スクロールして全件読み込み
    print("📜 ページをスクロール中...")
    for i in range(5):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(2)
    print("✅ スクロール完了\n")

    # プロフィールリンクから逆算してカードを検出
    script = """
    // プロフィールリンクを検出
    const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'))
        .filter(a => {
            const href = a.getAttribute('href') || '';
            // /in/で始まるプロフィールリンクのみ
            return href.match(/\\/in\\/[^/]+\\/?$/);
        });

    console.log('プロフィールリンク数:', profileLinks.length);

    const results = [];

    for (let i = 0; i < Math.min(profileLinks.length, 10); i++) {
        const link = profileLinks[i];

        // 名前を取得
        const name = link.textContent.trim();
        const profileUrl = link.href;

        // 親要素を遡ってカードを探す（最大15階層）
        let card = link;
        for (let level = 0; level < 15; level++) {
            card = card.parentElement;
            if (!card) break;

            // カード全体のテキストを取得
            const cardText = card.textContent || '';

            // 「につながりました」を含むかチェック
            if (cardText.includes('につながりました')) {
                // 日付パターンを抽出
                const dateMatch = cardText.match(/(\\d{4})年(\\d{1,2})月(\\d{1,2})日につながりました/);

                results.push({
                    name: name,
                    profileUrl: profileUrl,
                    dateText: dateMatch ? dateMatch[0] : 'なし',
                    cardTagName: card.tagName,
                    cardClassName: card.className.substring(0, 100),
                    level: level
                });
                break;
            }
        }

        // 見つからなかった場合も記録
        if (!results.find(r => r.profileUrl === profileUrl)) {
            results.push({
                name: name,
                profileUrl: profileUrl,
                dateText: '検出不可',
                cardTagName: 'N/A',
                cardClassName: 'N/A',
                level: -1
            });
        }
    }

    return results;
    """

    try:
        results = driver.execute_script(script)

        print(f"{'='*70}")
        print(f"📊 検出結果")
        print(f"{'='*70}\n")
        print(f"✅ プロフィールリンク検出数: {len(results)} 件\n")

        for idx, result in enumerate(results[:10], start=1):
            print(f"--- つながり {idx} ---")
            print(f"名前: {result.get('name', '')}")
            print(f"URL: {result.get('profileUrl', '')}")
            print(f"日付: {result.get('dateText', '')}")
            print(f"カード要素: <{result.get('cardTagName', '')}> (親要素の階層: {result.get('level', -1)})")
            print(f"カードクラス: {result.get('cardClassName', '')[:80]}")
            print()

        # 日付が検出できたものをカウント
        with_date = [r for r in results if r.get('dateText') and r['dateText'] != '検出不可' and r['dateText'] != 'なし']
        print(f"\n{'='*70}")
        print(f"🎯 サマリー")
        print(f"{'='*70}")
        print(f"総検出数: {len(results)} 件")
        print(f"日付付き: {len(with_date)} 件")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"❌ エラー: {e}\n")
        import traceback
        traceback.print_exc()

    print("ブラウザを開いたまま維持しています。")
    print("確認後、Enterキーを押してブラウザを閉じます。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    driver = login()
    debug_connections_page_v2(driver)
