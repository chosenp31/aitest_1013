# aiagent/linkedin_button_debugger.py
# 「つながりを申請」ボタン検出のデバッグ専用スクリプト
# 実行すると詳細なログとスクリーンショットを保存します

import os
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG_DIR = os.path.join(BASE_DIR, "debug_output")
os.makedirs(DEBUG_DIR, exist_ok=True)

# テスト用プロフィールURL（実行時に変更してください）
TEST_PROFILE_URL = "https://www.linkedin.com/in/example-profile/"

# ==============================
# デバッグ用JavaScriptコード
# ==============================
_JS_DEBUG_BUTTONS = r"""
(function(){
  const results = {
    timestamp: new Date().toISOString(),
    windowSize: {
      width: window.innerWidth,
      height: window.innerHeight
    },
    main: null,
    h1: null,
    allButtons: [],
    connectButtons: [],
    leftButtons: [],
    selectedButton: null
  };

  // 1) <main>タグチェック
  const main = document.querySelector('main');
  if (!main) {
    results.main = {found: false, reason: '<main>タグが見つかりません'};
    return results;
  }
  results.main = {found: true};

  // 2) <h1>タグチェック
  const h1 = main.querySelector('h1');
  if (!h1) {
    results.h1 = {found: false, reason: '<h1>が見つかりません'};
    return results;
  }
  const h1Rect = h1.getBoundingClientRect();
  results.h1 = {
    found: true,
    text: h1.innerText.trim(),
    position: {x: h1Rect.x, y: h1Rect.y, width: h1Rect.width, height: h1Rect.height}
  };

  // 3) すべてのボタンを収集
  const allButtons = Array.from(main.querySelectorAll('button, [role="button"]'));
  results.allButtons = allButtons.map((btn, idx) => {
    const rect = btn.getBoundingClientRect();
    return {
      index: idx,
      text: btn.innerText.trim().substring(0, 50),
      ariaLabel: btn.getAttribute('aria-label') || '',
      className: btn.className.substring(0, 100),
      position: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      visible: rect.width > 0 && rect.height > 0,
      display: window.getComputedStyle(btn).display,
      visibility: window.getComputedStyle(btn).visibility
    };
  });

  // 4) 「つながりを申請」候補を抽出
  function isConnect(el) {
    const text = (el.innerText || '').trim().toLowerCase();
    const aria = (el.getAttribute('aria-label') || '').trim().toLowerCase();
    return text.includes('つながりを申請') || text.includes('connect') ||
           aria.includes('つながりを申請') || aria.includes('connect');
  }

  const connectButtons = allButtons.filter(isConnect);
  results.connectButtons = connectButtons.map((btn, idx) => {
    const rect = btn.getBoundingClientRect();
    return {
      index: idx,
      text: btn.innerText.trim().substring(0, 50),
      ariaLabel: btn.getAttribute('aria-label') || '',
      position: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
      distance_from_h1: Math.abs((rect.y + rect.height/2) - (h1Rect.y + h1Rect.height/2))
    };
  });

  // 5) 左半分領域フィルタ
  const W = window.innerWidth;
  const leftButtons = connectButtons.filter(el => {
    const rect = el.getBoundingClientRect();
    const centerX = rect.x + rect.width / 2;
    return centerX < W * 0.50;
  });

  results.leftButtons = leftButtons.map((btn, idx) => {
    const rect = btn.getBoundingClientRect();
    return {
      index: idx,
      text: btn.innerText.trim().substring(0, 50),
      ariaLabel: btn.getAttribute('aria-label') || '',
      position: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
    };
  });

  // 6) h1に最も近いボタンを選択
  if (leftButtons.length > 0) {
    let bestButton = null;
    let minDistance = Infinity;

    leftButtons.forEach(btn => {
      const rect = btn.getBoundingClientRect();
      const btnCenterY = rect.y + rect.height / 2;
      const h1CenterY = h1Rect.y + h1Rect.height / 2;
      const distance = Math.abs(btnCenterY - h1CenterY);

      if (distance < minDistance) {
        minDistance = distance;
        bestButton = btn;
      }
    });

    if (bestButton) {
      const rect = bestButton.getBoundingClientRect();
      results.selectedButton = {
        found: true,
        text: bestButton.innerText.trim().substring(0, 50),
        ariaLabel: bestButton.getAttribute('aria-label') || '',
        position: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
        distance: minDistance,
        outerHTML: bestButton.outerHTML.substring(0, 500)
      };
    }
  }

  return results;
})();
"""

# ==============================
# 手動ログイン
# ==============================
def manual_login():
    """手動でLinkedInにログイン"""
    print("🔑 LinkedIn 手動ログインモード開始...")

    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")
    print("💡 ログイン後、feedページが表示されるまで待機します...")

    # ログイン完了待機
    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了を検出。デバッグを開始します。")
    return driver

# ==============================
# デバッグ実行
# ==============================
def debug_profile(driver, profile_url):
    """指定したプロフィールページでボタン検出をデバッグ"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*70}")
    print(f"🔍 デバッグ対象: {profile_url}")
    print(f"{'='*70}")

    # プロフィールページに遷移
    print("🌐 プロフィールページに遷移中...")
    driver.get(profile_url)

    # 完全な読み込み待機
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(3.0)  # React再描画待機

    print("✅ ページ読み込み完了")

    # スクリーンショット保存
    screenshot_path = os.path.join(DEBUG_DIR, f"screenshot_{timestamp}.png")
    driver.save_screenshot(screenshot_path)
    print(f"📸 スクリーンショット保存: {screenshot_path}")

    # HTML保存
    html_path = os.path.join(DEBUG_DIR, f"page_source_{timestamp}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print(f"📄 HTMLソース保存: {html_path}")

    # JavaScriptデバッグ実行
    print("🔍 ボタン検出JavaScriptを実行中...")
    debug_result = driver.execute_script(_JS_DEBUG_BUTTONS)

    # 結果をJSON保存
    json_path = os.path.join(DEBUG_DIR, f"debug_result_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(debug_result, f, indent=2, ensure_ascii=False)
    print(f"📊 デバッグ結果保存: {json_path}")

    # コンソールに要約表示
    print(f"\n{'='*70}")
    print("📊 デバッグ結果サマリー")
    print(f"{'='*70}")
    print(f"ウィンドウサイズ: {debug_result['windowSize']}")
    print(f"<main>タグ: {debug_result['main']}")
    print(f"<h1>タグ: {debug_result['h1']}")
    print(f"全ボタン数: {len(debug_result['allButtons'])}")
    print(f"「つながりを申請」候補: {len(debug_result['connectButtons'])}")
    print(f"左半分領域ボタン: {len(debug_result['leftButtons'])}")

    if debug_result.get('selectedButton') and debug_result['selectedButton'].get('found'):
        btn = debug_result['selectedButton']
        print(f"\n✅ 選択されたボタン:")
        print(f"   テキスト: {btn['text']}")
        print(f"   aria-label: {btn['ariaLabel']}")
        print(f"   位置: {btn['position']}")
        print(f"   h1からの距離: {btn['distance']:.1f}px")
    else:
        print(f"\n❌ 適切なボタンが見つかりませんでした")

    print(f"\n{'='*70}")
    print(f"📁 すべてのデバッグファイルは {DEBUG_DIR} に保存されています")
    print(f"{'='*70}")

    return debug_result

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print("🐛 LinkedIn ボタン検出デバッグツール")
    print(f"{'='*70}\n")

    # プロフィールURL入力
    profile_url = input("デバッグしたいLinkedInプロフィールURLを入力してください\n> ").strip()

    if not profile_url.startswith("https://www.linkedin.com/in/"):
        print("⚠️ 有効なLinkedInプロフィールURLを入力してください")
        exit(1)

    # ログインとデバッグ実行
    driver = manual_login()
    debug_result = debug_profile(driver, profile_url)

    print("\n🪄 デバッグ完了。ブラウザは開いたままにしてあります。")
    print("手動でページを確認してから閉じてください。")
