# aiagent/linkedin_manual_pipeline.py
# ✅ 統合版：メインプロフィールボタン特定 + 挨拶なしで送信 + ログ出力
# ・<main>タグ内 + 左半分領域フィルタ + h1からの距離計算
# ・詳細ログでデバッグ情報出力
# ・logs.csvに送信結果を記録

import os
import time
import csv
import random
from datetime import datetime
from textwrap import shorten

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 定数
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
TARGET_CSV = os.path.join(DATA_DIR, "messages.csv")
LOG_CSV = os.path.join(DATA_DIR, "logs.csv")

LIMIT = 10  # 送信上限
DELAY_RANGE = (3, 7)  # 送信間隔（秒）

# ==============================
# ログ記録関数
# ==============================
def append_log(name, url, result, error=""):
    """送信結果をCSVに記録"""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(LOG_CSV)
    
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "name", "url", "result", "error"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "url": url,
            "result": result,
            "error": error
        })

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
    
    print("✅ ログイン完了を検出。リクエスト送信を開始します。")
    return driver

# ==============================
# メインプロフィールボタン探索JS
# ==============================
_JS_FIND_MAIN_BUTTON = r"""
(function(){
  const W = window.innerWidth || document.documentElement.clientWidth || 1200;
  
  // 1) <main>タグ取得
  const main = document.querySelector('main');
  if (!main) {
    console.log('❌ <main>タグが見つかりません');
    return {found:false, reason:'<main>タグなし'};
  }
  
  // 2) <main>内の<h1>（プロフィール名）取得
  const h1 = main.querySelector('h1');
  if (!h1) {
    console.log('❌ <main>内に<h1>が見つかりません');
    return {found:false, reason:'<h1>なし'};
  }
  
  const h1Rect = h1.getBoundingClientRect();
  console.log('✅ プロフィール名位置:', h1Rect);
  
  // 3) <main>内のボタンのみ対象
  const buttonsInMain = Array.from(main.querySelectorAll('button, [role="button"]'));
  console.log(`📊 <main>内ボタン総数: ${buttonsInMain.length}`);
  
  // 4) 「つながりを申請」フィルタ
  function isConnect(el){
    const text = (el.innerText || '').trim();
    const aria = (el.getAttribute('aria-label') || '').trim();
    return text.includes('つながりを申請') || text.includes('Connect') ||
           aria.includes('つながりを申請') || aria.includes('Connect');
  }
  
  const connectButtons = buttonsInMain.filter(isConnect);
  console.log(`🔍 つながりを申請候補: ${connectButtons.length}個`);
  
  if (connectButtons.length === 0) {
    return {found:false, reason:'つながりを申請ボタンなし'};
  }
  
  // 5) 左半分領域フィルタ（画面幅50%以内）
  const leftButtons = connectButtons.filter(el => {
    const rect = el.getBoundingClientRect();
    const centerX = rect.x + rect.width / 2;
    return centerX < W * 0.50;
  });
  
  console.log(`📍 左半分領域ボタン: ${leftButtons.length}個`);
  
  if (leftButtons.length === 0) {
    return {found:false, reason:'左半分にボタンなし'};
  }
  
  // 6) h1に最も近いボタンを選択（垂直距離）
  let bestButton = null;
  let minDistance = Infinity;
  
  leftButtons.forEach(btn => {
    const rect = btn.getBoundingClientRect();
    const btnCenterY = rect.y + rect.height / 2;
    const h1CenterY = h1Rect.y + h1Rect.height / 2;
    const distance = Math.abs(btnCenterY - h1CenterY);
    
    console.log(`🔹 候補: "${btn.innerText.slice(0,20)}", 距離=${distance.toFixed(1)}px`);
    
    if (distance < minDistance) {
      minDistance = distance;
      bestButton = btn;
    }
  });
  
  if (!bestButton) {
    return {found:false, reason:'最適ボタン選択失敗'};
  }
  
  const finalRect = bestButton.getBoundingClientRect();
  return {
    found: true,
    x: finalRect.x,
    y: finalRect.y,
    w: finalRect.width,
    h: finalRect.height,
    distance: minDistance,
    text: bestButton.innerText.trim().slice(0, 50),
    outer: bestButton.outerHTML.slice(0, 300)
  };
})();
"""

def find_connect_button(driver):
    """メインプロフィールの「つながりを申請」ボタンを特定"""
    print("\n🔍 メインプロフィールボタン探索中...")
    
    # JavaScript実行
    res = driver.execute_script(_JS_FIND_MAIN_BUTTON)
    
    if not res or not isinstance(res, dict):
        print("⚠️ JS探索の戻り値が不正")
        return None
    
    if not res.get("found"):
        reason = res.get("reason", "不明")
        print(f"❌ ボタン未検出: {reason}")
        return None
    
    # 成功ログ
    x, y, w, h = res.get("x"), res.get("y"), res.get("w"), res.get("h")
    distance = res.get("distance")
    text = res.get("text", "")
    outer = shorten(res.get("outer", "").replace("\n", " "), width=150, placeholder="…")
    
    print(f"✅ メインボタン検出成功!")
    print(f"   📍 位置: x={int(x)}, y={int(y)}, 幅={int(w)}, 高={int(h)}")
    print(f"   📏 h1からの距離: {distance:.1f}px")
    print(f"   📝 テキスト: {text}")
    print(f"   🧾 HTML: {outer}")
    
    # 座標から実DOM要素を取得
    js_pick = r"""
      (function(targetX, targetY){
        const main = document.querySelector('main');
        if (!main) return null;
        
        const buttons = Array.from(main.querySelectorAll('button, [role="button"]'));
        
        function isConnect(el){
          const t = (el.innerText || '').trim();
          const a = (el.getAttribute('aria-label') || '').trim();
          return t.includes('つながりを申請') || t.includes('Connect') ||
                 a.includes('つながりを申請') || a.includes('Connect');
        }
        
        let best = null;
        let minDist = 1e9;
        
        buttons.forEach(btn => {
          if (!isConnect(btn)) return;
          const r = btn.getBoundingClientRect();
          const cx = r.x + r.width / 2;
          const cy = r.y + r.height / 2;
          const dist = Math.hypot(cx - targetX, cy - targetY);
          
          if (dist < minDist) {
            best = btn;
            minDist = dist;
          }
        });
        
        return best;
      })(arguments[0], arguments[1]);
    """
    
    cx = x + w / 2
    cy = y + h / 2
    element = driver.execute_script(js_pick, cx, cy)
    
    return element

# ==============================
# 送信処理
# ==============================
def send_requests(driver):
    """接続リクエスト送信（挨拶なしで送信）"""
    
    # CSV読み込み
    if not os.path.exists(TARGET_CSV):
        print(f"❌ メッセージファイルが見つかりません: {TARGET_CSV}")
        return
    
    with open(TARGET_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        messages = list(reader)
    
    if not messages:
        print("⚠️ メッセージ送信対象が空です。")
        return
    
    total = min(len(messages), LIMIT)
    print(f"\n{'='*70}")
    print(f"📤 接続リクエスト対象: {total} 件（上限 {LIMIT} 件）")
    print(f"{'='*70}")
    
    success = 0
    
    for idx, msg in enumerate(messages[:LIMIT], start=1):
        name = msg.get("name", "不明")
        url = msg.get("url") or msg.get("profile_url")
        
        print(f"\n{'='*70}")
        print(f"[{idx}/{total}] 👤 {name}")
        print(f"🔗 {url}")
        print(f"{'='*70}")
        
        if not url:
            print(f"⚠️ URLが見つかりません。スキップします。")
            append_log(name, url, "skip", "URLなし")
            continue
        
        try:
            # プロフィールページへ遷移
            print(f"🌐 プロフィールページに遷移中...")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(2.0)
            print(f"✅ ページ読み込み完了: {driver.current_url}")
            
            # メインボタン探索
            btn = find_connect_button(driver)
            
            if not btn:
                print(f"⚪ {name}: メインプロフィールの『つながりを申請』が見つかりません。")
                append_log(name, url, "skip", "ボタン未検出")
                continue
            
            # クリック
            driver.execute_script(
                "arguments[0].scrollIntoView({behavior:'smooth', block:'center'});", 
                btn
            )
            time.sleep(0.8)
            driver.execute_script("arguments[0].click();", btn)
            print(f"✅ 『つながりを申請』クリック成功")
            
            # ダイアログ待機
            time.sleep(1.5)
            
            # 「挨拶なしで送信」ボタン探索
            no_note = driver.find_elements(
                By.XPATH,
                "//button[contains(., '挨拶なしで送信')] | //button[contains(., 'Send without a note')]"
            )
            
            if no_note:
                driver.execute_script("arguments[0].click();", no_note[0])
                print(f"💬 『挨拶なしで送信』押下成功")
                append_log(name, url, "success", "")
                success += 1
            else:
                print(f"⚠️ 『挨拶なしで送信』ボタンが見つかりません。")
                append_log(name, url, "skip", "挨拶なしボタンなし")
            
            # 次の送信までの待機
            wait_time = random.uniform(*DELAY_RANGE)
            print(f"⏳ {wait_time:.1f}秒待機...")
            time.sleep(wait_time)
        
        except TimeoutException:
            print(f"⏱ {name}: ページ読み込みタイムアウト")
            append_log(name, url, "error", "タイムアウト")
        except Exception as e:
            print(f"❌ {name}: エラー発生 - {e}")
            append_log(name, url, "error", str(e))
    
    print(f"\n{'='*70}")
    print(f"🎯 送信完了: {success} 件 / {total} 件")
    print(f"📝 ログ保存先: {LOG_CSV}")
    print(f"{'='*70}")
    print("🪄 全処理完了。ブラウザを閉じてもOKです。")

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    driver = manual_login()
    send_requests(driver)