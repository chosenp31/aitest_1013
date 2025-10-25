# aiagent/debug_search_v2.py
# より詳細な親要素構造の調査

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def manual_login():
    print("🔑 LinkedIn 手動ログインモード開始...")
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.linkedin.com/login")

    print("🌐 ご自身でLinkedInにログインしてください...")
    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了")
    return driver

def debug_search_v2():
    driver = manual_login()

    search_url = "https://www.linkedin.com/search/results/people/?keywords=SIer"
    print(f"\n🔗 検索URL: {search_url}")
    driver.get(search_url)
    time.sleep(5)

    print("\n" + "="*70)
    print("親要素構造を詳細調査中...")
    print("="*70)

    # 親要素を10階層まで遡って調査
    script = """
    const links = Array.from(document.querySelectorAll('a[href*="/in/"]'));
    const profileLinks = links.filter(a => a.href.includes('/in/') && !a.href.includes('/company/'));

    if (profileLinks.length === 0) {
        return { error: 'プロフィールリンクが見つかりません' };
    }

    const firstLink = profileLinks[0];
    const parentChain = [];

    let current = firstLink;
    for (let i = 0; i < 15; i++) {
        current = current.parentElement;
        if (!current) break;

        parentChain.push({
            level: i + 1,
            tag: current.tagName.toLowerCase(),
            className: current.className,
            id: current.id || '',
            // innerTextの長さで候補者カード全体かを判定
            textLength: (current.innerText || '').length,
            // 最初の50文字
            textPreview: (current.innerText || '').substring(0, 100).replace(/\\n/g, ' ')
        });
    }

    // 名前を取得（リンクのテキスト）
    const name = firstLink.textContent.trim();

    // さらに3件のサンプルも取得
    const samples = profileLinks.slice(0, 3).map((link, idx) => {
        // この人の情報を含むコンテナを探す
        let container = link;
        for (let i = 0; i < 15; i++) {
            container = container.parentElement;
            if (!container) break;

            const text = container.innerText || '';
            // テキストが50〜1000文字なら候補者カード全体の可能性が高い
            if (text.length > 50 && text.length < 1000) {
                return {
                    index: idx,
                    name: link.textContent.trim(),
                    containerTag: container.tagName.toLowerCase(),
                    containerClass: container.className,
                    textLength: text.length,
                    fullText: text
                };
            }
        }
        return null;
    }).filter(x => x !== null);

    return {
        totalProfileLinks: profileLinks.length,
        firstName: name,
        parentChain: parentChain,
        samples: samples
    };
    """

    result = driver.execute_script(script)

    if 'error' in result:
        print(f"❌ エラー: {result['error']}")
        return

    print(f"\n📊 プロフィールリンク総数: {result['totalProfileLinks']} 件")
    print(f"📝 最初の人の名前: {result['firstName']}")

    print(f"\n🔗 親要素チェーン（15階層）:")
    print(f"{'Level':<6} {'Tag':<10} {'Text長':<8} {'Class Name'}")
    print("-" * 70)

    for parent in result['parentChain']:
        class_name = parent['className'][:50] if parent['className'] else '(なし)'
        print(f"{parent['level']:<6} {parent['tag']:<10} {parent['textLength']:<8} {class_name}")

        # テキスト長が100〜500文字の親要素は候補者カード全体の可能性が高い
        if 100 < parent['textLength'] < 500:
            print(f"       ⭐ 候補者カード全体の可能性: {parent['textPreview']}")

    print(f"\n👤 サンプル候補者情報（最大3件）:")
    for sample in result['samples']:
        print(f"\n   [{sample['index']}] {sample['name']}")
        print(f"   コンテナ: <{sample['containerTag']}> class=\"{sample['containerClass'][:60]}\"")
        print(f"   テキスト長: {sample['textLength']} 文字")
        print(f"   内容プレビュー:")
        # 改行で分割して最初の5行を表示
        lines = sample['fullText'].split('\n')[:5]
        for line in lines:
            if line.strip():
                print(f"      {line.strip()[:80]}")

    print("\n" + "="*70)
    print("✅ 調査完了")
    print("="*70)

if __name__ == "__main__":
    debug_search_v2()
