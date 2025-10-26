# aiagent/debug_candidate_info_v2.py
# 複数の候補者を調査＆HTML全体を取得

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def debug_multiple_candidates():
    """複数の候補者カードを詳細に調査"""

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.linkedin.com/login")
    print("🌐 LinkedInにログインしてください...")

    while "feed" not in driver.current_url and "home" not in driver.current_url:
        time.sleep(1.5)

    print("✅ ログイン完了")

    search_url = "https://www.linkedin.com/search/results/people/?keywords=SIer"
    driver.get(search_url)
    time.sleep(5)

    # 最初の3件の候補者を調査
    script = """
    const candidateCards = document.querySelectorAll('li.qTpSkRrerBcUqHivKtVbqVGnMhgMkDU');
    
    const results = [];
    
    for (let i = 0; i < Math.min(3, candidateCards.length); i++) {
        const card = candidateCards[i];
        
        // 全てのクラス名に「primary」「secondary」「location」を含む要素を探す
        const allElements = card.querySelectorAll('*');
        const relevantElements = [];
        
        allElements.forEach((el, idx) => {
            const className = el.className || '';
            const text = el.textContent.trim();
            
            // primary-subtitle, secondary-subtitle, location などを含む
            if (className.includes('primary') || 
                className.includes('secondary') || 
                className.includes('location') ||
                className.includes('headline') ||
                className.includes('subtitle')) {
                
                if (text.length > 0 && text.length < 300) {
                    relevantElements.push({
                        tag: el.tagName.toLowerCase(),
                        class: className,
                        text: text
                    });
                }
            }
        });
        
        results.push({
            index: i,
            fullHTML: card.innerHTML,  // 全HTML
            relevantElements: relevantElements
        });
    }
    
    return results;
    """

    try:
        results = driver.execute_script(script)

        for result in results:
            print(f"\n{'='*70}")
            print(f"📋 候補者 {result['index'] + 1}")
            print(f"{'='*70}")
            
            print("\n🔍 関連要素（primary/secondary/location/headline含む）:")
            if result['relevantElements']:
                for el in result['relevantElements']:
                    print(f"\n  <{el['tag']}> class=\"{el['class'][:60]}...\"")
                    print(f"    テキスト: {el['text']}")
            else:
                print("  ❌ 該当する要素が見つかりませんでした")
            
            print(f"\n📄 完全なHTML（最初の3000文字）:")
            print(result['fullHTML'][:3000])
            print("\n...")

    except Exception as e:
        print(f"❌ エラー: {e}")

    input("\n✅ 調査完了。Enterキーを押してブラウザを閉じます...")
    driver.quit()

if __name__ == "__main__":
    debug_multiple_candidates()