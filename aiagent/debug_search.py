# aiagent/debug_search.py
# 検索結果抽出のデバッグスクリプト

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
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

def debug_search():
    driver = manual_login()

    # 検索URLに移動
    search_url = "https://www.linkedin.com/search/results/people/?keywords=SIer"
    print(f"\n🔗 検索URL: {search_url}")
    driver.get(search_url)

    # ページ読み込み待機
    time.sleep(5)

    print("\n" + "="*70)
    print("デバッグ情報を取得中...")
    print("="*70)

    # デバッグ用JavaScript（改良版：プロフィールリンクの親要素を調査）
    debug_script = """
    (function() {
        const result = {
            url: window.location.href,
            pageTitle: document.title,

            // 検索結果コンテナを探す
            searchContainer: document.querySelector('.search-results-container') ? 'Found' : 'Not found',

            // リストアイテムを探す（複数のパターン）
            listItems1: document.querySelectorAll('li.reusable-search__result-container').length,
            listItems2: document.querySelectorAll('li[class*="search-result"]').length,
            listItems3: document.querySelectorAll('li[class*="result"]').length,
            listItems4: document.querySelectorAll('div.entity-result').length,
            listItems5: document.querySelectorAll('ul.reusable-search__entity-result-list li').length,

            // すべてのliタグ
            allLi: document.querySelectorAll('li').length,

            // プロフィールリンク
            profileLinks: document.querySelectorAll('a[href*="/in/"]').length,

            // 検索結果のリストコンテナを探す
            resultList: document.querySelector('ul[class*="reusable-search"]') ? 'Found' : 'Not found',

            // プロフィールリンクの親要素を調査
            profileLinkParents: [],

            // 実際のプロフィールデータをサンプル取得
            sampleProfiles: []
        };

        // プロフィールリンクを取得して親要素を調査
        const profileLinks = Array.from(document.querySelectorAll('a[href*="/in/"]'));
        const mainProfileLinks = profileLinks.filter(a => {
            const href = a.href || '';
            return href.includes('/in/') && !href.includes('/company/') && !href.includes('/school/');
        });

        // 最初の5件の親要素のクラス名を取得
        mainProfileLinks.slice(0, 5).forEach((link, idx) => {
            let parent = link.parentElement;
            let depth = 0;
            const path = [];

            // 5階層まで親をたどる
            while (parent && depth < 5) {
                path.push({
                    tag: parent.tagName.toLowerCase(),
                    className: parent.className.substring(0, 100),
                    id: parent.id
                });
                parent = parent.parentElement;
                depth++;
            }

            result.profileLinkParents.push({
                index: idx,
                linkText: link.textContent.trim().substring(0, 50),
                linkHref: link.href.substring(0, 100),
                parentPath: path
            });
        });

        // 実際のプロフィール情報を抽出（試験的）
        mainProfileLinks.slice(0, 3).forEach((link, idx) => {
            // リンクから遡って候補者情報を含む親要素を探す
            let container = link;
            for (let i = 0; i < 10; i++) {
                container = container.parentElement;
                if (!container) break;

                // この要素内のテキストを取得
                const text = container.innerText || '';
                if (text.length > 50 && text.length < 500) {
                    result.sampleProfiles.push({
                        index: idx,
                        containerTag: container.tagName,
                        containerClass: container.className.substring(0, 100),
                        text: text.substring(0, 200)
                    });
                    break;
                }
            }
        });

        return result;
    })();
    """

    try:
        result = driver.execute_script(debug_script)
    except Exception as e:
        print(f"❌ JavaScript実行エラー: {e}")
        result = None

    if result is None:
        print("\n❌ JavaScriptの実行結果がNoneです")
        print("代わりにシンプルな方法で調査します...\n")

        # シンプルなJavaScriptで再試行
        simple_script = """
        const links = Array.from(document.querySelectorAll('a[href*="/in/"]'));
        const profileLinks = links.filter(a => a.href.includes('/in/') && !a.href.includes('/company/'));

        return {
            totalLinks: links.length,
            profileLinks: profileLinks.length,
            firstLinkHtml: profileLinks[0] ? profileLinks[0].outerHTML.substring(0, 200) : 'None',
            firstLinkParentHtml: profileLinks[0] && profileLinks[0].parentElement ?
                profileLinks[0].parentElement.outerHTML.substring(0, 300) : 'None'
        };
        """

        simple_result = driver.execute_script(simple_script)
        print(f"総リンク数: {simple_result['totalLinks']}")
        print(f"プロフィールリンク数: {simple_result['profileLinks']}")
        print(f"\n最初のリンクHTML:")
        print(simple_result['firstLinkHtml'])
        print(f"\n親要素のHTML:")
        print(simple_result['firstLinkParentHtml'])

    else:
        print(f"\n📍 現在のURL: {result.get('url', 'N/A')}")
        print(f"📄 ページタイトル: {result.get('pageTitle', 'N/A')}")
        print(f"\n🔍 検索結果の検出状況:")
        print(f"   検索結果コンテナ: {result.get('searchContainer', 'N/A')}")
        print(f"   結果リスト: {result.get('resultList', 'N/A')}")
        print(f"\n📊 リストアイテムの検出:")
        print(f"   パターン1: {result.get('listItems1', 0)} 件")
        print(f"   パターン2: {result.get('listItems2', 0)} 件")
        print(f"   パターン3: {result.get('listItems3', 0)} 件")
        print(f"   パターン4: {result.get('listItems4', 0)} 件")
        print(f"   パターン5: {result.get('listItems5', 0)} 件")
        print(f"\n📋 その他:")
        print(f"   全<li>タグ: {result.get('allLi', 0)} 件")
        print(f"   プロフィールリンク: {result.get('profileLinks', 0)} 件")

        # 親要素の情報を表示
        if 'profileLinkParents' in result and result['profileLinkParents']:
            print(f"\n🔗 プロフィールリンクの親要素構造:")
            import json
            for parent_info in result['profileLinkParents'][:2]:  # 最初の2件のみ
                print(f"\n   [{parent_info['index']}] {parent_info['linkText']}")
                print(f"   URL: {parent_info['linkHref']}")
                print(f"   親要素パス:")
                for p in parent_info['parentPath'][:3]:  # 3階層まで
                    print(f"      {p['tag']}.{p['className'][:50]}")

        # サンプルプロフィール情報
        if 'sampleProfiles' in result and result['sampleProfiles']:
            print(f"\n👤 サンプルプロフィール:")
            for profile in result['sampleProfiles']:
                print(f"\n   [{profile['index']}] コンテナ: {profile['containerTag']}.{profile['containerClass'][:50]}")
                print(f"   テキスト: {profile['text'][:100]}...")

    print("\n" + "="*70)
    print("✅ デバッグ完了")
    print("💡 ブラウザは開いたままです。手動で確認してください。")
    print("="*70)

if __name__ == "__main__":
    debug_search()
