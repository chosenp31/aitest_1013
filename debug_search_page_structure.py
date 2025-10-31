# debug_search_page_structure.py
# 検索結果ページのDOM構造を調査

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

def login():
    """LinkedInにログイン"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

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
                print("✅ 自動ログイン成功！\n")
                return driver
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")

    print("⚠️ 自動ログインに失敗しました。手動でログインしてください。")
    driver.get("https://www.linkedin.com/login")
    input("ログイン後、Enterキーを押してください...")
    return driver

def debug_search_page():
    """検索結果ページのDOM構造を調査"""
    driver = login()

    # 検索を実行
    keywords = "SIer OR エンジニア OR ITコンサルタント"
    location = "Japan"
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={keywords}&origin=GLOBAL_SEARCH_HEADER&location={location}"

    print(f"🔎 検索URL: {search_url}\n")
    driver.get(search_url)
    time.sleep(5)

    # ページをスクロール
    print("📜 ページをスクロール中...")
    for _ in range(3):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(1)
    print("✅ スクロール完了\n")

    # DOM構造を調査
    print("="*70)
    print("🔍 DOM構造調査開始")
    print("="*70)

    script = """
    const results = {
        totalLiElements: 0,
        candidateCards: [],
        allLiClasses: [],
        buttonTexts: []
    };

    // 1. すべてのli要素をカウント
    const allLis = document.querySelectorAll('li');
    results.totalLiElements = allLis.length;

    // 2. 候補者カードっぽいli要素を探す
    allLis.forEach((li, index) => {
        const classes = li.className || '';

        // クラス名をリストに追加
        if (classes && index < 20) {
            results.allLiClasses.push({
                index: index,
                classes: classes,
                textContent: li.textContent.substring(0, 100)
            });
        }

        // span[aria-hidden="true"]を含むliを候補者カードとみなす
        const nameEl = li.querySelector('span[aria-hidden="true"]');
        if (nameEl && index < 10) {
            const buttons = li.querySelectorAll('button');
            const buttonInfo = [];

            buttons.forEach(btn => {
                const text = btn.textContent.trim();
                const ariaLabel = btn.getAttribute('aria-label') || '';
                buttonInfo.push({
                    text: text.substring(0, 50),
                    ariaLabel: ariaLabel.substring(0, 50)
                });
            });

            results.candidateCards.push({
                index: index,
                name: nameEl.textContent.trim(),
                classes: classes,
                buttonCount: buttons.length,
                buttons: buttonInfo
            });
        }
    });

    // 3. すべてのボタンのテキストを取得（最初の30個）
    const allButtons = document.querySelectorAll('button');
    allButtons.forEach((btn, index) => {
        if (index < 30) {
            results.buttonTexts.push({
                index: index,
                text: btn.textContent.trim().substring(0, 50),
                ariaLabel: btn.getAttribute('aria-label') || ''
            });
        }
    });

    return results;
    """

    results = driver.execute_script(script)

    # 結果を表示
    print(f"\n📊 調査結果:")
    print(f"   総li要素数: {results['totalLiElements']} 個")
    print(f"   候補者カード数: {len(results['candidateCards'])} 個")

    print(f"\n" + "="*70)
    print("🎯 検出された候補者カード（最大10件）")
    print("="*70)

    if results['candidateCards']:
        for card in results['candidateCards']:
            print(f"\n【カード {card['index']}】")
            print(f"   名前: {card['name']}")
            print(f"   クラス: {card['classes'][:100]}")
            print(f"   ボタン数: {card['buttonCount']}")
            for btn in card['buttons']:
                print(f"      - テキスト: {btn['text']}")
                print(f"        aria-label: {btn['ariaLabel']}")
    else:
        print("⚠️ 候補者カードが1件も見つかりませんでした")

    print(f"\n" + "="*70)
    print("📋 最初の20個のli要素のクラス名")
    print("="*70)

    for li_info in results['allLiClasses'][:20]:
        print(f"\n【li {li_info['index']}】")
        print(f"   クラス: {li_info['classes'][:150]}")
        print(f"   テキスト: {li_info['textContent'][:80]}...")

    print(f"\n" + "="*70)
    print("🔘 最初の30個のボタン情報")
    print("="*70)

    for btn_info in results['buttonTexts'][:30]:
        print(f"\n【ボタン {btn_info['index']}】")
        print(f"   テキスト: {btn_info['text']}")
        print(f"   aria-label: {btn_info['ariaLabel']}")

    print(f"\n" + "="*70)
    print("✅ 調査完了")
    print("="*70)
    print("\nこの結果をコピーして共有してください。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    debug_search_page()
