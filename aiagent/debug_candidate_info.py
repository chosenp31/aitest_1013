# aiagent/debug_candidate_info.py
# 候補者情報の詳細なDOM構造を調査

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def debug_candidate_info():
    """候補者カード内の情報を詳細に調査"""

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # ログイン
    driver.get("https://www.linkedin.com/login")
    print("🌐 LinkedInにログインしてください...")

    while "feed" not in driver.current_url and "home" not in driver.current_url:
        time.sleep(1.5)

    print("✅ ログイン完了")

    # 検索実行
    search_url = "https://www.linkedin.com/search/results/people/?keywords=SIer"
    driver.get(search_url)
    time.sleep(5)

    # 候補者カード内の全要素を調査
    script = """
    const candidateCards = document.querySelectorAll('li.qTpSkRrerBcUqHivKtVbqVGnMhgMkDU');

    if (candidateCards.length === 0) {
        return {error: '候補者カードが見つかりません'};
    }

    const firstCard = candidateCards[0];

    // カード内の全てのspan, div要素を取得
    const allSpans = firstCard.querySelectorAll('span');
    const allDivs = firstCard.querySelectorAll('div');

    const result = {
        cardHTML: firstCard.innerHTML.substring(0, 2000), // 最初の2000文字
        totalSpans: allSpans.length,
        totalDivs: allDivs.length,
        spans: [],
        divs: []
    };

    // 各span要素の情報
    allSpans.forEach((span, idx) => {
        const text = span.textContent.trim();
        if (text.length > 0 && text.length < 200) {  // 空でなく、長すぎない
            result.spans.push({
                index: idx,
                class: span.className,
                text: text,
                ariaHidden: span.getAttribute('aria-hidden'),
                dir: span.getAttribute('dir')
            });
        }
    });

    // 各div要素の情報（テキストが含まれるもののみ）
    allDivs.forEach((div, idx) => {
        const text = div.textContent.trim();
        const directText = Array.from(div.childNodes)
            .filter(node => node.nodeType === 3)  // テキストノードのみ
            .map(node => node.textContent.trim())
            .join(' ');

        if (text.length > 0 && text.length < 200 && div.children.length < 10) {
            result.divs.push({
                index: idx,
                class: div.className,
                text: text,
                directText: directText
            });
        }
    });

    return result;
    """

    try:
        result = driver.execute_script(script)

        if 'error' in result:
            print(f"❌ {result['error']}")
            return

        print("\n" + "="*70)
        print("📊 候補者カード構造分析")
        print("="*70)
        print(f"総span要素数: {result['totalSpans']}")
        print(f"総div要素数: {result['totalDivs']}")

        print("\n" + "="*70)
        print("📝 span要素一覧（テキスト含むもの）")
        print("="*70)
        for span in result['spans'][:20]:  # 最初の20件
            print(f"\n[{span['index']}] class=\"{span['class'][:50]}...\"")
            print(f"    aria-hidden=\"{span['ariaHidden']}\"")
            print(f"    dir=\"{span['dir']}\"")
            print(f"    テキスト: {span['text']}")

        print("\n" + "="*70)
        print("📦 div要素一覧（テキスト含むもの）")
        print("="*70)
        for div in result['divs'][:20]:  # 最初の20件
            print(f"\n[{div['index']}] class=\"{div['class'][:50]}...\"")
            print(f"    テキスト: {div['text']}")

        print("\n" + "="*70)
        print("🔍 候補者カードのHTML（最初の2000文字）")
        print("="*70)
        print(result['cardHTML'])

    except Exception as e:
        print(f"❌ エラー: {e}")

    input("\n✅ 調査完了。Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    debug_candidate_info()