# debug_all_buttons_detailed.py
# 候補者カード内の全ボタンを詳細調査

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

def debug_all_buttons():
    """全ボタンの詳細情報を調査"""
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

    print("="*70)
    print("🔍 全ボタン詳細調査")
    print("="*70)

    script = """
    const results = {
        candidateCards: [],
        allButtons: []
    };

    // 新しいクラス名で候補者カードを取得
    const candidateCards = document.querySelectorAll('li.MncIJcOwiPSwDWyDUNKbbTLtLTlFRKZQLU');

    candidateCards.forEach((card, cardIndex) => {
        // 名前を取得
        const nameEl = card.querySelector('span[aria-hidden="true"]');
        const name = nameEl ? nameEl.textContent.trim() : '名前不明';

        // カード内の全ボタンを取得
        const buttons = card.querySelectorAll('button');
        const buttonDetails = [];

        buttons.forEach((btn, btnIndex) => {
            const text = btn.textContent.trim();
            const ariaLabel = btn.getAttribute('aria-label') || '';
            const classes = btn.className || '';
            const disabled = btn.disabled;
            const ariaDisabled = btn.getAttribute('aria-disabled');

            buttonDetails.push({
                index: btnIndex,
                text: text,
                ariaLabel: ariaLabel,
                classes: classes.substring(0, 100),
                disabled: disabled,
                ariaDisabled: ariaDisabled
            });
        });

        results.candidateCards.push({
            cardIndex: cardIndex,
            name: name,
            buttonCount: buttons.length,
            buttons: buttonDetails
        });
    });

    // ページ内の全ボタン（候補者カード以外も含む）
    const allButtons = document.querySelectorAll('button');
    allButtons.forEach((btn, index) => {
        const text = btn.textContent.trim();
        const ariaLabel = btn.getAttribute('aria-label') || '';

        // 「つながり」「Connect」を含むボタンのみ
        if (text.includes('つながり') || text.includes('Connect') ||
            ariaLabel.includes('つながり') || ariaLabel.includes('Connect')) {
            results.allButtons.push({
                index: index,
                text: text,
                ariaLabel: ariaLabel,
                classes: btn.className.substring(0, 100)
            });
        }
    });

    return results;
    """

    results = driver.execute_script(script)

    # 候補者カード内のボタン情報を表示
    print(f"\n📊 検出された候補者カード: {len(results['candidateCards'])} 件\n")

    for card in results['candidateCards'][:10]:
        print(f"{'='*70}")
        print(f"【候補者カード {card['cardIndex']}】")
        print(f"{'='*70}")
        print(f"名前: {card['name']}")
        print(f"ボタン数: {card['buttonCount']}")
        print()

        for btn in card['buttons']:
            print(f"   【ボタン {btn['index']}】")
            print(f"      テキスト: {btn['text']}")
            print(f"      aria-label: {btn['ariaLabel']}")
            print(f"      クラス: {btn['classes']}")
            print(f"      disabled: {btn['disabled']}")
            print(f"      aria-disabled: {btn['ariaDisabled']}")
            print()

    # つながり申請ボタンの検索結果
    print(f"\n{'='*70}")
    print(f"🔍 「つながり」「Connect」を含むボタン検索結果")
    print(f"{'='*70}")
    print(f"検出数: {len(results['allButtons'])} 件\n")

    if results['allButtons']:
        for btn in results['allButtons'][:20]:
            print(f"【ボタン {btn['index']}】")
            print(f"   テキスト: {btn['text']}")
            print(f"   aria-label: {btn['ariaLabel']}")
            print(f"   クラス: {btn['classes']}")
            print()
    else:
        print("⚠️ 「つながり」「Connect」を含むボタンが見つかりませんでした")
        print("→ 検索結果がすべて1次つながり（既接続）の可能性があります\n")

    print("="*70)
    print("✅ 調査完了")
    print("="*70)
    print("\n【推奨】")
    print("もし「つながり」ボタンが0件の場合：")
    print("1. LinkedInの検索画面で「つながり」フィルターを確認")
    print("2. 「2次」または「3次+」を選択")
    print("3. このスクリプトを再実行")
    print("\nこの結果をコピーして共有してください。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    debug_all_buttons()
