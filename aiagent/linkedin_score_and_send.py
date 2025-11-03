# aiagent/linkedin_score_and_send.py
# プロフィール情報取得済みのCSVから、スコアリング→メッセージ送信を実行

import os
import sys
import time
import csv
import json
import pickle
import random
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ファイルパス
COOKIE_FILE = os.path.join(DATA_DIR, "cookies.pkl")
PROFILES_FILE = os.path.join(DATA_DIR, "profiles_detailed.csv")
SCORED_FILE = os.path.join(DATA_DIR, "scored_connections.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages_v2.csv")
MESSAGE_LOG_FILE = os.path.join(DATA_DIR, "message_logs.csv")

os.makedirs(DATA_DIR, exist_ok=True)

# OpenAI設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# メッセージテンプレート（絵文字なし）
MESSAGE_TEMPLATE = """{name}さん

いきなりすみません
KPMGコンサルティングの依田と申します。

将来的に人材領域にも関わりたいと考えており、IT・コンサル分野でご活躍されている方々のお話を伺いながら、知見を広げたいと思っています。

自分からは以下のようなトピックを共有できます：
・フューチャーアーキテクト／KPMGでのプロジェクト経験
・転職時に検討したBIG4＋アクセンチュア／BCGの比較や選考情報

もしご関心あれば、カジュアルにオンラインでお話できると嬉しいです！よろしくお願いします！"""

# スコアリングプロンプト
SCORING_PROMPT = """
あなたはIT業界のリクルーターです。以下の候補者の詳細プロフィールを分析して、スコアリングしてください。

【候補者情報】
名前: {name}
ヘッドライン: {headline}
場所: {location}
LinkedIn Premium会員: {is_premium}
職歴:
{experiences}

学歴:
{education}

スキル: {skills}

【評価基準】

1. 年齢評価（0-25点）
   - 学歴の卒業年から年齢を推定（大学卒業を22歳と仮定）
   - 計算式: 現在年齢 = 2025年 - 卒業年 + 22歳
   - 25-30歳: 25点
   - 31-35歳: 20点
   - 36-40歳: 15点
   - 41歳以上: **即座に除外（スコア0、decision: "skip"）**
   - **年齢不明（推定不可）の場合: 0点だが除外しない（他の項目でスコアリング）**

2. IT業界経験評価（0-40点）
   - キーワード: SIer, ITコンサルタント, エンジニア, DXエンジニア, システム開発, クラウド, AI, データサイエンス
   - 現在のIT業界経験が3年以上: 40点
   - 現在のIT業界経験が1-3年: 30点
   - 過去にIT業界経験あり: 20点
   - IT業界経験なし: 0点

3. ポジション評価（-30 〜 +20点）
   - エンジニア・開発者: +20点
   - ITコンサルタント: +15点
   - プロジェクトマネージャー: +10点
   - 以下は**即座に除外（スコア0、decision: "skip"）**:
     - 経営層: 社長, CEO, CIO, CTO, CFO, 代表取締役, 執行役員, 取締役
     - HR・人材関係: 人材紹介, 人材派遣, リクルーター, 採用担当, ヘッドハンター, キャリアアドバイザー, 人事コンサルタント

4. その他の除外条件（即座にスコア0、decision: "skip"）
   - LinkedIn Premium会員（is_premium: "True"または"yes"の場合）
   - 学生（在学中）
   - IT業界と無関係（飲食、販売、製造、小売など）
   - 現在以下の企業に勤務している者:
     * フューチャー株式会社
     * フューチャーアーキテクト株式会社

【出力形式】
以下のJSON形式で出力してください。他の説明は一切不要です。

{{
  "estimated_age": 推定年齢（数値、不明な場合はnull）,
  "age_reasoning": "年齢推定の根拠",
  "age_score": 年齢スコア（0-25）,
  "it_experience_score": IT経験スコア（0-40）,
  "position_score": ポジションスコア（-30 〜 +20）,
  "total_score": 合計スコア（age_score + it_experience_score + position_score）,
  "decision": "send" または "skip",
  "reason": "スコアリングの理由（簡潔に1-2文）"
}}

【重要な注意事項】
- LinkedIn Premium会員（is_premium: "True"または"yes"）は必ず除外（decision: "skip"、total_score: 0）
- 41歳以上は必ず除外（decision: "skip"、total_score: 0）
- **年齢不明（estimated_age: null）の場合は除外しない。age_score: 0 として他の項目でスコアリング**
- 経営層（社長、CEO、取締役等）は必ず除外（decision: "skip"、total_score: 0）
- HR・人材関係（リクルーター、採用担当等）は必ず除外（decision: "skip"、total_score: 0）
- フューチャー株式会社またはフューチャーアーキテクト株式会社に現在勤務している者は必ず除外（decision: "skip"、total_score: 0）
- 合計スコアが60点以上の場合は "send"、それ未満は "skip"
"""

# OpenAIクライアント
if not OPENAI_API_KEY:
    print("❌ エラー: OPENAI_API_KEYが設定されていません")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

# ==============================
# ログイン
# ==============================
def login():
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
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
            else:
                print("⚠️ Cookieが期限切れです。手動ログインに切り替えます...")
                os.remove(COOKIE_FILE)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(COOKIE_FILE):
                os.remove(COOKIE_FILE)

    # 手動ログイン
    print("🔑 LinkedIn 手動ログインモード開始...")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了\n")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました\n")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}\n")

    return driver

# ==============================
# Step 4: AIスコアリング
# ==============================
def score_candidate(candidate):
    """OpenAI APIで候補者をスコアリング"""

    name = candidate.get("name", "不明")
    headline = candidate.get("headline", "情報なし")
    location = candidate.get("location", "情報なし")
    is_premium = candidate.get("is_premium", False)
    is_premium_str = "yes" if str(is_premium).lower() in ['true', 'yes', '1'] else "no"
    experiences = candidate.get("experiences", "情報なし")
    education = candidate.get("education", "情報なし")
    skills = candidate.get("skills", "情報なし")

    prompt = SCORING_PROMPT.format(
        name=name,
        headline=headline,
        location=location,
        is_premium=is_premium_str,
        experiences=experiences,
        education=education,
        skills=skills
    )

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはIT業界のリクルーターです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()

        # JSONを抽出
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(result_text)

        return {
            **candidate,
            **result
        }

    except Exception as e:
        print(f"   ⚠️ APIエラー ({name}): {e}")
        return {
            **candidate,
            "estimated_age": None,
            "age_reasoning": "",
            "age_score": 0,
            "it_experience_score": 0,
            "position_score": 0,
            "total_score": 0,
            "decision": "skip",
            "reason": f"APIエラー: {e}"
        }

def score_all_candidates(profiles, min_score):
    """全候補者をスコアリング"""

    print(f"{'='*70}")
    print(f"🧠 Step 4: AIスコアリング")
    print(f"{'='*70}")
    print(f"候補者数: {len(profiles)} 件")
    print(f"最低スコア: {min_score} 点")
    print(f"{'='*70}\n")

    results = []

    for idx, profile in enumerate(profiles, start=1):
        name = profile.get('name', '不明')
        print(f"[{idx}/{len(profiles)}] 📊 {name} をスコアリング中...")

        scored = score_candidate(profile)
        results.append(scored)

        decision = scored.get('decision', 'skip')
        total_score = scored.get('total_score', 0)
        reason = scored.get('reason', '')

        if decision == "send":
            print(f"   ✅ 送信対象: {total_score}点")
        else:
            print(f"   ⚪ スキップ: {total_score}点")
        print(f"   理由: {reason}\n")

        time.sleep(1)

    # JSON保存
    with open(SCORED_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"💾 保存完了: {SCORED_FILE}\n")

    # 送信対象を抽出してCSV保存
    send_targets = [r for r in results if r.get('decision') == 'send' and r.get('total_score', 0) >= min_score]

    if send_targets:
        with open(MESSAGES_FILE, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["name", "profile_url", "total_score"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for target in send_targets:
                writer.writerow({
                    'name': target.get('name', ''),
                    'profile_url': target.get('profile_url', ''),
                    'total_score': target.get('total_score', 0)
                })

        print(f"✅ 送信対象: {len(send_targets)} 件\n")
    else:
        print(f"⚠️ 送信対象が0件です\n")

    return send_targets

# ==============================
# Step 5-6: メッセージ生成・送信
# ==============================
def generate_message(name):
    """メッセージを生成"""
    base_message = MESSAGE_TEMPLATE.format(name=name)

    prompt = f"""
以下のメッセージテンプレートを元に、自然で親しみやすいメッセージを生成してください。
大幅な変更は不要です。語尾や表現を少しだけ変えてください。

【テンプレート】
{base_message}

【要件】
- 名前は必ず「{name}さん」で始める
- 内容の構造は基本的にテンプレート通り
- 語尾や接続詞を少しだけ自然にバリエーションを付ける
- 箇条書き（・）はそのまま維持
- 全体の長さはテンプレートと同程度
- 他の説明は一切不要、メッセージ本文のみ出力
"""

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "あなたはメッセージ生成アシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=400
        )

        message = response.choices[0].message.content.strip()
        return message

    except Exception as e:
        print(f"   ⚠️ メッセージ生成エラー: {e}")
        return base_message

def send_message(driver, profile_url, name, message):
    """メッセージを送信"""
    try:
        # プロフィールページへ移動
        driver.get(profile_url)
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 400);")
        time.sleep(1)

        # メッセージボタンを探す
        message_btn = None

        try:
            message_btn = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//button[contains(@aria-label, 'メッセージ') or contains(@aria-label, 'Message')]"
                ))
            )
        except TimeoutException:
            pass

        if not message_btn:
            try:
                message_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//button[contains(., 'メッセージ') or contains(., 'Message')]"
                    ))
                )
            except TimeoutException:
                pass

        if not message_btn:
            return "error", "メッセージボタン未検出", "button_not_found"

        if not message_btn.is_displayed():
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", message_btn)
            time.sleep(1)

        try:
            message_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", message_btn)

        time.sleep(3)

        # ポップアップ待機
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='dialog']"))
            )
            time.sleep(1)
        except TimeoutException:
            return "error", "ポップアップ表示タイムアウト", "popup_timeout"

        # メッセージ入力欄を探す
        message_box = None

        try:
            message_box = driver.find_element(
                By.CSS_SELECTOR,
                "[role='dialog'] [contenteditable='true']"
            )
        except NoSuchElementException:
            try:
                message_box = driver.find_element(
                    By.CSS_SELECTOR,
                    "div[contenteditable='true'][role='textbox']"
                )
            except NoSuchElementException:
                pass

        if not message_box:
            return "error", "メッセージ入力欄が見つかりません", "message_box_not_found"

        # メッセージを入力
        driver.execute_script("arguments[0].focus();", message_box)
        time.sleep(0.5)
        message_box.click()
        time.sleep(0.5)

        try:
            message_box.send_keys(message)
            time.sleep(0.5)
        except Exception as e:
            return "error", f"メッセージ入力エラー: {e}", "message_input_failed"

        # 送信ボタンを探す
        send_btn = None

        try:
            send_btn = driver.find_element(
                By.XPATH,
                "//div[@role='dialog']//button[contains(@aria-label, '送信') or contains(@aria-label, 'Send')]"
            )
        except NoSuchElementException:
            try:
                send_btn = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//button[contains(., '送信') or contains(., 'Send')]"
                )
            except NoSuchElementException:
                pass

        if not send_btn:
            return "error", "送信ボタンが見つかりません", "send_button_not_found"

        # 送信ボタンが活性化されるまで待機
        button_enabled = False

        for i in range(20):
            is_disabled = send_btn.get_attribute("disabled")
            aria_disabled = send_btn.get_attribute("aria-disabled")

            if is_disabled is None and (aria_disabled is None or aria_disabled == "false"):
                button_enabled = True
                break

            time.sleep(0.5)

        # 送信ボタンをクリック
        try:
            send_btn.click()
        except Exception:
            driver.execute_script("arguments[0].click();", send_btn)

        # 送信処理の完了を待つ（LinkedInの処理時間）
        time.sleep(3)

        if button_enabled:
            # ポップアップを明示的に閉じる（次の送信のため）
            popup_closed = False

            print(f"   🔄 ポップアップを閉じています...")

            # 戦略1: ページ全体（body）にEscapeキーを送信（stale参照を回避）
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                time.sleep(1)
                print(f"   ✓ Escapeキー送信（body）")
            except Exception as e:
                print(f"   ⚠️ Escapeキー失敗（body）: {e}")

            # 戦略2: ポップアップ内の新しい要素にEscapeキーを送信
            try:
                dialog = driver.find_element(By.CSS_SELECTOR, "[role='dialog']")
                dialog.send_keys(Keys.ESCAPE)
                time.sleep(1)
                print(f"   ✓ Escapeキー送信（dialog）")
            except Exception as e:
                print(f"   ⚠️ Escapeキー失敗（dialog）: {e}")

            # 戦略3: 閉じるボタンをクリック
            try:
                close_btn = driver.find_element(
                    By.XPATH,
                    "//div[@role='dialog']//button[contains(@aria-label, '閉じる') or contains(@aria-label, 'Dismiss') or contains(@aria-label, 'Close')]"
                )
                close_btn.click()
                time.sleep(1)
                print(f"   ✓ 閉じるボタンクリック")
            except Exception as e:
                print(f"   ⚠️ 閉じるボタン失敗: {e}")

            # ポップアップが実際に閉じるまで待機（最大15秒）
            for i in range(30):  # 0.5秒 × 30回 = 最大15秒
                time.sleep(0.5)
                try:
                    driver.find_element(By.CSS_SELECTOR, "[role='dialog']")
                    # まだ存在する
                except NoSuchElementException:
                    # ポップアップが閉じた
                    popup_closed = True
                    print(f"   ✅ ポップアップが閉じました（{(i + 1) * 0.5:.1f}秒後）")
                    break

            # それでも閉じない場合は強制削除
            if not popup_closed:
                print(f"   ⚠️ ポップアップが閉じません。強制削除を実行します...")

                # 戦略4: より強力なJavaScript削除
                try:
                    driver.execute_script("""
                        // すべてのダイアログを削除
                        const dialogs = document.querySelectorAll('[role="dialog"]');
                        dialogs.forEach(d => {
                            d.remove();
                            console.log('Dialog removed');
                        });

                        // モーダルのオーバーレイも削除
                        const overlays = document.querySelectorAll('.msg-overlay-bubble-header, .msg-overlay-list-bubble, [class*="msg-overlay"]');
                        overlays.forEach(o => {
                            o.remove();
                            console.log('Overlay removed');
                        });

                        // bodyのスタイルをリセット（モーダル表示時に変更されることがある）
                        document.body.style.overflow = 'auto';
                    """)
                    time.sleep(1)
                    print(f"   🔄 JavaScript強制削除完了")

                    # 再度確認
                    try:
                        driver.find_element(By.CSS_SELECTOR, "[role='dialog']")
                        print(f"   ❌ 強制削除後もポップアップが残っています")
                    except NoSuchElementException:
                        popup_closed = True
                        print(f"   ✅ 強制削除成功")

                except Exception as e:
                    print(f"   ❌ 強制削除失敗: {e}")

            # 次のメッセージ送信前の追加待機
            time.sleep(2)

            return "success", "", "sent"
        else:
            return "error", "送信ボタンが活性化されませんでした", "button_not_enabled"

    except Exception as e:
        return "error", f"予期しないエラー: {e}", "unexpected_error"

def log_message(name, profile_url, result, error="", details=""):
    """送信結果をログに記録"""
    file_exists = os.path.exists(MESSAGE_LOG_FILE)

    with open(MESSAGE_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "name", "profile_url", "result", "error", "details"])
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "profile_url": profile_url,
            "result": result,
            "error": error,
            "details": details
        })

def send_all_messages(driver, targets, max_messages):
    """全メッセージを送信（既送信者を除外）"""

    print(f"{'='*70}")
    print(f"📨 Step 5-6: メッセージ生成・送信")
    print(f"{'='*70}")

    # 既送信者を確認（result="success"のみ除外、失敗は再送可能）
    already_sent_urls = set()

    if os.path.exists(MESSAGE_LOG_FILE):
        try:
            with open(MESSAGE_LOG_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('result') == 'success':
                        already_sent_urls.add(row.get('profile_url', ''))
            print(f"📂 過去の送信履歴: {len(already_sent_urls)} 件（成功のみ）")
        except Exception as e:
            print(f"⚠️ 送信履歴読み込みエラー: {e}")

    # 既送信者を除外
    original_count = len(targets)
    targets = [t for t in targets if t.get('profile_url', '') not in already_sent_urls]
    excluded_count = original_count - len(targets)

    print(f"👥 スコアリング通過者: {original_count} 件")
    print(f"✅ 既にメッセージ送信済み: {excluded_count} 件")
    print(f"🆕 今回の送信対象: {len(targets)} 件")
    print(f"📊 上限設定: {max_messages} 件")
    print(f"{'='*70}\n")

    if not targets:
        print("⚠️ 送信対象が0件です（全員送信済み）\n")
        return

    # 上限件数まで絞り込み
    targets = targets[:max_messages]

    # メッセージを生成
    print("💬 メッセージを生成中...\n")

    messages_to_send = []

    for idx, target in enumerate(targets, start=1):
        name = target.get('name', '不明')
        profile_url = target.get('profile_url', '')
        score = target.get('total_score', 0)

        if not profile_url:
            print(f"[{idx}/{len(targets)}] ⚠️ {name} - URLなし、スキップ\n")
            continue

        print(f"[{idx}/{len(targets)}] 💬 {name} (スコア: {score}点) のメッセージを生成中...")
        message = generate_message(name)
        print(f"   ✅ 生成完了\n")

        messages_to_send.append({
            'name': name,
            'profile_url': profile_url,
            'score': score,
            'message': message
        })

    # 生成したメッセージを全て表示
    print(f"{'='*70}")
    print(f"📋 生成されたメッセージ一覧")
    print(f"{'='*70}\n")

    for idx, msg_data in enumerate(messages_to_send, start=1):
        print(f"--- [{idx}/{len(messages_to_send)}] {msg_data['name']} (スコア: {msg_data['score']}点) ---")
        print(f"{msg_data['message']}")
        print()

    # ユーザーに確認
    print(f"{'='*70}")
    print(f"これらのメッセージを送信しますか？")
    print(f"{'='*70}")
    confirm = input("送信する場合は 'yes' と入力してください: ").strip().lower()

    if confirm != 'yes':
        print("\n❌ 送信をキャンセルしました\n")
        return

    # メッセージ送信
    print(f"\n{'='*70}")
    print(f"📨 メッセージ送信開始")
    print(f"{'='*70}\n")

    success_count = 0
    error_count = 0

    for idx, msg_data in enumerate(messages_to_send, start=1):
        name = msg_data['name']
        profile_url = msg_data['profile_url']
        score = msg_data['score']
        message = msg_data['message']

        print(f"[{idx}/{len(messages_to_send)}] 📤 {name} (スコア: {score}点) へ送信中...")

        result, error, details = send_message(driver, profile_url, name, message)

        log_message(name, profile_url, result, error, details)

        if result == "success":
            success_count += 1
            print(f"   ✅ 送信成功\n")
        else:
            error_count += 1
            print(f"   ❌ 送信失敗: {error}\n")

        # 遅延
        if idx < len(messages_to_send):
            delay = random.uniform(3, 6)
            time.sleep(delay)

    # サマリー
    print(f"{'='*70}")
    print(f"🎯 完了サマリー")
    print(f"{'='*70}")
    print(f"✅ 送信成功: {success_count} 件")
    print(f"❌ 送信失敗: {error_count} 件")
    print(f"📝 ログ: {MESSAGE_LOG_FILE}")
    print(f"{'='*70}\n")

# ==============================
# メイン処理
# ==============================
def main(min_score, max_messages):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn スコアリング・メッセージ送信")
    print(f"{'='*70}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # プロフィールCSVを読み込む
    if not os.path.exists(PROFILES_FILE):
        print(f"❌ エラー: {PROFILES_FILE} が見つかりません")
        print("先にプロフィール情報を取得してください。\n")
        exit(1)

    print(f"📂 プロフィール情報を読み込み中: {PROFILES_FILE}\n")

    profiles = []
    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profiles.append(row)

    print(f"✅ {len(profiles)} 件のプロフィールを読み込みました\n")

    # ログイン
    driver = login()

    try:
        # Step 4: AIスコアリング
        send_targets = score_all_candidates(profiles, min_score)

        if not send_targets:
            print("⚠️ 送信対象が0件です。処理を終了します。\n")
            return

        # Step 5-6: メッセージ生成・送信
        send_all_messages(driver, send_targets, max_messages)

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 処理完了")
        print(f"{'='*70}")
        print(f"終了日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

        input("\nEnterキーを押してブラウザを閉じます...")
        driver.quit()

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn スコアリング・メッセージ送信")
    print(f"{'='*70}\n")

    # 最低スコア
    print("【最低スコア】")
    while True:
        min_score_input = input("最低スコアを入力 (Enter=デフォルト「60」): ").strip()
        if not min_score_input:
            min_score = 60
            break
        try:
            min_score = int(min_score_input)
            if min_score >= 0:
                break
            else:
                print("⚠️ 0以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 最大メッセージ送信数
    print("\n【最大メッセージ送信数】")
    while True:
        max_messages_input = input("最大メッセージ送信数を入力 (Enter=デフォルト「50」): ").strip()
        if not max_messages_input:
            max_messages = 50
            break
        try:
            max_messages = int(max_messages_input)
            if max_messages > 0:
                break
            else:
                print("⚠️ 1以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 設定内容を確認
    print(f"\n{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"最低スコア: {min_score}点")
    print(f"最大メッセージ送信数: {max_messages}件")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(min_score, max_messages)
