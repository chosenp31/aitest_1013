# debug_search_candidates.py
# 候補者カードの詳細な構造を調査

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

def debug_candidates():
    """候補者カードの詳細構造を調査"""
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

    # 候補者カードの詳細を調査
    print("="*70)
    print("🔍 候補者カード詳細調査")
    print("="*70)

    script = """
    const results = {
        method1: { name: 'メッセージボタンから逆引き', candidates: [] },
        method2: { name: 'ul.reusable-search__entity-result-list内のli', candidates: [] },
        method3: { name: 'div.entity-result', candidates: [] },
        method4: { name: 'すべてのli（ボタンを含む）', candidates: [] }
    };

    // 方法1: メッセージボタンから親要素を遡って候補者カードを特定
    const messageButtons = document.querySelectorAll('button[aria-label*="メッセージ"], button[aria-label*="message" i]');
    console.log('メッセージボタン数:', messageButtons.length);

    messageButtons.forEach((btn, index) => {
        if (index < 5) {
            let parent = btn;
            let cardFound = false;

            // 最大20階層まで親を遡る
            for (let level = 0; level < 20; level++) {
                parent = parent.parentElement;
                if (!parent) break;

                const tagName = parent.tagName.toLowerCase();
                const classes = parent.className || '';

                // li要素かつクラス名にentityやresultが含まれる
                if (tagName === 'li' && (classes.includes('entity') || classes.includes('result'))) {
                    // 名前を探す
                    const nameEl = parent.querySelector('span[aria-hidden="true"]');
                    const name = nameEl ? nameEl.textContent.trim() : '名前不明';

                    // つながり申請ボタンを探す
                    const buttons = parent.querySelectorAll('button');
                    const buttonTexts = [];
                    buttons.forEach(b => {
                        const text = b.textContent.trim();
                        if (text) buttonTexts.push(text);
                    });

                    results.method1.candidates.push({
                        index: index,
                        name: name,
                        tagName: tagName,
                        classes: classes,
                        buttonTexts: buttonTexts
                    });

                    cardFound = true;
                    break;
                }
            }

            if (!cardFound) {
                results.method1.candidates.push({
                    index: index,
                    name: '親カード見つからず',
                    ariaLabel: btn.getAttribute('aria-label')
                });
            }
        }
    });

    // 方法2: ul.reusable-search__entity-result-list内のli要素
    const resultList = document.querySelector('ul.reusable-search__entity-result-list');
    if (resultList) {
        const listItems = resultList.querySelectorAll('li');
        listItems.forEach((li, index) => {
            if (index < 5) {
                const nameEl = li.querySelector('span[aria-hidden="true"]');
                const name = nameEl ? nameEl.textContent.trim() : '名前不明';

                const buttons = li.querySelectorAll('button');
                const buttonTexts = [];
                buttons.forEach(b => {
                    const text = b.textContent.trim();
                    if (text) buttonTexts.push(text);
                });

                results.method2.candidates.push({
                    index: index,
                    name: name,
                    classes: li.className || '',
                    buttonCount: buttons.length,
                    buttonTexts: buttonTexts
                });
            }
        });
    }

    // 方法3: div.entity-result
    const entityResults = document.querySelectorAll('div.entity-result');
    entityResults.forEach((div, index) => {
        if (index < 5) {
            const nameEl = div.querySelector('span[aria-hidden="true"]');
            const name = nameEl ? nameEl.textContent.trim() : '名前不明';

            const buttons = div.querySelectorAll('button');
            const buttonTexts = [];
            buttons.forEach(b => {
                const text = b.textContent.trim();
                if (text) buttonTexts.push(text);
            });

            results.method3.candidates.push({
                index: index,
                name: name,
                classes: div.className || '',
                buttonTexts: buttonTexts
            });
        }
    });

    // 方法4: すべてのli要素の中でボタンを2個以上持つもの
    const allLis = document.querySelectorAll('li');
    allLis.forEach((li, index) => {
        const buttons = li.querySelectorAll('button');
        if (buttons.length >= 2) {
            const nameEl = li.querySelector('span[aria-hidden="true"]');
            const name = nameEl ? nameEl.textContent.trim() : '名前不明';

            const buttonTexts = [];
            buttons.forEach(b => {
                const text = b.textContent.trim();
                if (text) buttonTexts.push(text);
            });

            // ナビゲーション要素を除外
            const classes = li.className || '';
            if (!classes.includes('global-nav') && buttonTexts.length > 0) {
                results.method4.candidates.push({
                    index: index,
                    name: name,
                    classes: classes,
                    buttonTexts: buttonTexts
                });
            }
        }
    });

    // 最大5件に制限
    results.method4.candidates = results.method4.candidates.slice(0, 5);

    return results;
    """

    results = driver.execute_script(script)

    # 結果を表示
    for method_key, method_data in results.items():
        print(f"\n{'='*70}")
        print(f"📊 【{method_data['name']}】")
        print(f"{'='*70}")

        candidates = method_data.get('candidates', [])
        print(f"検出数: {len(candidates)} 件\n")

        if candidates:
            for candidate in candidates:
                print(f"【候補者 {candidate.get('index', '?')}】")
                print(f"   名前: {candidate.get('name', '不明')}")
                if 'classes' in candidate:
                    print(f"   クラス: {candidate['classes'][:150]}")
                if 'buttonCount' in candidate:
                    print(f"   ボタン数: {candidate['buttonCount']}")
                if 'buttonTexts' in candidate:
                    print(f"   ボタンテキスト: {candidate['buttonTexts']}")
                if 'ariaLabel' in candidate:
                    print(f"   aria-label: {candidate['ariaLabel']}")
                print()
        else:
            print("⚠️ 候補者が見つかりませんでした\n")

    print("="*70)
    print("✅ 調査完了")
    print("="*70)
    print("\nこの結果をコピーして共有してください。")

    input("\nEnterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    debug_candidates()
