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

    # デバッグ用JavaScript
    debug_script = """
    return {
        url: window.location.href,

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

        // ページのタイトル
        pageTitle: document.title,

        // 最初のliタグのクラス名を取得（サンプル）
        firstLiClass: document.querySelector('li') ? document.querySelector('li').className : 'No li found',

        // 検索結果のリストコンテナを探す
        resultList: document.querySelector('ul[class*="reusable-search"]') ? 'Found' : 'Not found',

        // HTMLの一部をサンプル取得
        bodyText: document.body.innerText.substring(0, 300)
    };
    """

    result = driver.execute_script(debug_script)

    print(f"\n📍 現在のURL: {result['url']}")
    print(f"📄 ページタイトル: {result['pageTitle']}")
    print(f"\n🔍 検索結果の検出状況:")
    print(f"   検索結果コンテナ: {result['searchContainer']}")
    print(f"   結果リスト: {result['resultList']}")
    print(f"\n📊 リストアイテムの検出:")
    print(f"   パターン1 (li.reusable-search__result-container): {result['listItems1']} 件")
    print(f"   パターン2 (li[class*='search-result']): {result['listItems2']} 件")
    print(f"   パターン3 (li[class*='result']): {result['listItems3']} 件")
    print(f"   パターン4 (div.entity-result): {result['listItems4']} 件")
    print(f"   パターン5 (ul.reusable-search__entity-result-list li): {result['listItems5']} 件")
    print(f"\n📋 その他:")
    print(f"   全<li>タグ: {result['allLi']} 件")
    print(f"   プロフィールリンク: {result['profileLinks']} 件")
    print(f"   最初の<li>のクラス名: {result['firstLiClass']}")
    print(f"\n📝 ページ本文（先頭300文字）:")
    print(f"{result['bodyText']}")

    print("\n" + "="*70)
    print("✅ デバッグ完了")
    print("💡 ブラウザは開いたままです。手動で確認してください。")
    print("="*70)

if __name__ == "__main__":
    debug_search()
