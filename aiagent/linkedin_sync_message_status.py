# aiagent/linkedin_sync_message_status.py
# LinkedInメッセージ履歴から送信済みステータスを同期

import os
import time
import csv
import pickle
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# アカウント名の定義
AVAILABLE_ACCOUNTS = ["依田", "桜井", "田中"]

def select_account():
    """アカウントを選択"""
    print(f"\n{'='*70}")
    print(f"📋 使用するLinkedInアカウントを選択")
    print(f"{'='*70}")
    for idx, account in enumerate(AVAILABLE_ACCOUNTS, start=1):
        print(f"{idx}. {account}")
    print(f"{'='*70}\n")

    while True:
        choice = input(f"アカウント番号を入力 (1-{len(AVAILABLE_ACCOUNTS)}): ").strip()
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(AVAILABLE_ACCOUNTS):
                selected = AVAILABLE_ACCOUNTS[choice_num - 1]
                print(f"\n✅ 選択: {selected}\n")
                return selected
            else:
                print(f"⚠️ 1-{len(AVAILABLE_ACCOUNTS)}の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

def get_account_paths(account_name):
    """アカウント毎のディレクトリとファイルパスを取得"""
    account_dir = os.path.join(BASE_DIR, "data", account_name)
    os.makedirs(account_dir, exist_ok=True)

    return {
        'account_dir': account_dir,
        'cookie_file': os.path.join(account_dir, "linkedin_cookies.pkl"),
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv")
    }

# ==============================
# profiles_master.csv 管理
# ==============================
def load_profiles_master(profiles_master_file):
    """profiles_master.csv を読み込む"""
    profiles_master = {}

    if os.path.exists(profiles_master_file):
        try:
            with open(profiles_master_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    profile_url = row.get('profile_url', '')
                    # profile_urlが空欄の場合は、UUIDをkeyにする
                    if profile_url:
                        key = profile_url
                    else:
                        # profile_urlが空欄（メッセージ同期から追加されたレコード）
                        import uuid
                        key = f"empty_{uuid.uuid4()}"
                    profiles_master[key] = row
        except Exception as e:
            print(f"⚠️ profiles_master.csv 読み込みエラー: {e}\n")

    return profiles_master

def save_profiles_master(profiles_master, profiles_master_file):
    """profiles_master.csv を保存"""
    fieldnames = [
        "profile_url", "name", "connected_date",
        "profile_fetched", "profile_fetched_at",
        "total_score", "scoring_decision", "exclusion_reason",
        "message_generated", "message_generated_at",
        "message_sent_status", "message_sent_at", "last_send_error",
        "duplicate_name_flag"
    ]

    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # profile_url でソート
        sorted_profiles = sorted(profiles_master.values(), key=lambda x: x.get('profile_url', ''))
        writer.writerows(sorted_profiles)

# ==============================
# ログイン
# ==============================
def login(account_name, cookie_file):
    """LinkedInにログイン（Cookie保存で2回目以降は自動）"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("detach", True)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Cookie自動ログイン
    if os.path.exists(cookie_file):
        print(f"🔑 保存されたCookieを使用して自動ログイン中（アカウント: {account_name}）...")
        driver.get("https://www.linkedin.com")
        time.sleep(2)

        try:
            with open(cookie_file, "rb") as f:
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
                os.remove(cookie_file)
        except Exception as e:
            print(f"⚠️ Cookie読み込みエラー: {e}")
            if os.path.exists(cookie_file):
                os.remove(cookie_file)

    # 手動ログイン
    print(f"🔑 LinkedIn 手動ログインモード開始（アカウント: {account_name}）...")
    print(f"⚠️  必ず '{account_name}' アカウントでログインしてください！")
    driver.get("https://www.linkedin.com/login")
    print("🌐 ご自身でLinkedInにログインしてください...")

    while ("feed" not in driver.current_url) and ("home" not in driver.current_url):
        time.sleep(1.5)

    print("✅ ログイン完了\n")

    # Cookieを保存
    try:
        cookies = driver.get_cookies()
        with open(cookie_file, "wb") as f:
            pickle.dump(cookies, f)
        print(f"💾 Cookieを保存しました（{account_name}用）\n")
    except Exception as e:
        print(f"⚠️ Cookie保存エラー: {e}\n")

    return driver

# ==============================
# メッセージ履歴から名前を取得
# ==============================
def get_message_names(driver, scroll_count):
    """メッセージ一覧から送信済みの相手の名前を取得"""

    print(f"{'='*70}")
    print(f"📧 メッセージ履歴の取得")
    print(f"{'='*70}")
    print(f"スクロール回数: {scroll_count}")
    print(f"{'='*70}\n")

    # メッセージページへ移動
    messaging_url = "https://www.linkedin.com/messaging/"
    driver.get(messaging_url)
    time.sleep(5)

    # スクロール実行
    print("📜 左側メッセージ一覧をスクロール中...")

    # 左側メッセージ一覧のコンテナを特定（複数の方法を試す）
    detect_script = """
    let container = null;
    let detectionMethod = '';

    // 方法1: 最も具体的なclass名（左側メッセージ一覧）
    container = document.querySelector('.msg-conversations-container__convo-list');
    if (container) {
        detectionMethod = '.msg-conversations-container__convo-list';
    }

    // 方法2: 代替class名
    if (!container) {
        container = document.querySelector('.msg-conversations-container .scrollable');
        if (container) {
            detectionMethod = '.msg-conversations-container .scrollable';
        }
    }

    // 方法3: msg-conversations-list
    if (!container) {
        container = document.querySelector('.msg-conversations-list');
        if (container) {
            detectionMethod = '.msg-conversations-list';
        }
    }

    // 方法4: 親要素の2番目の子要素（構造による指定）
    if (!container) {
        const parent = document.querySelector('.msg-conversations-container');
        if (parent) {
            container = parent.querySelector('div:nth-child(2)');
            if (container && container.scrollHeight > container.clientHeight) {
                detectionMethod = '.msg-conversations-container > div:nth-child(2)';
            } else {
                container = null;
            }
        }
    }

    // 方法5: 左側領域のスクロール可能要素を位置で判定
    if (!container) {
        const scrollables = document.querySelectorAll('[class*="msg-conversations"]');
        for (const el of scrollables) {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            // 左側（x座標が小さい）かつスクロール可能
            if (rect.x < 500 && rect.width > 300 && rect.width < 500 &&
                (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                el.scrollHeight > el.clientHeight) {
                container = el;
                detectionMethod = '位置判定 (x < 500, width 300-500)';
                break;
            }
        }
    }

    return {
        found: !!container,
        method: detectionMethod,
        scrollHeight: container ? container.scrollHeight : 0,
        clientHeight: container ? container.clientHeight : 0
    };
    """

    detection_result = driver.execute_script(detect_script)

    if detection_result['found']:
        print(f"✅ 左側メッセージ一覧コンテナを検出")
        print(f"   検出方法: {detection_result['method']}")
        print(f"   スクロール可能高さ: {detection_result['scrollHeight']}px")
        print(f"   表示領域高さ: {detection_result['clientHeight']}px\n")

        # スクロール実行
        for i in range(scroll_count):
            scroll_amount = random.randint(400, 600)

            scroll_result = driver.execute_script(f"""
                let container = document.querySelector('.msg-conversations-container__convo-list') ||
                               document.querySelector('.msg-conversations-container .scrollable') ||
                               document.querySelector('.msg-conversations-list');

                // フォールバック: 位置判定
                if (!container) {{
                    const scrollables = document.querySelectorAll('[class*="msg-conversations"]');
                    for (const el of scrollables) {{
                        const rect = el.getBoundingClientRect();
                        const style = window.getComputedStyle(el);
                        if (rect.x < 500 && rect.width > 300 && rect.width < 500 &&
                            (style.overflowY === 'auto' || style.overflowY === 'scroll')) {{
                            container = el;
                            break;
                        }}
                    }}
                }}

                if (container) {{
                    const beforeScroll = container.scrollTop;
                    container.scrollBy(0, {scroll_amount});
                    const afterScroll = container.scrollTop;
                    return {{
                        success: true,
                        scrolled: afterScroll - beforeScroll,
                        currentPosition: afterScroll,
                        totalHeight: container.scrollHeight
                    }};
                }}
                return {{ success: false }};
            """)

            if scroll_result['success']:
                wait_time = random.uniform(2, 4)
                time.sleep(wait_time)
                print(f"   スクロール {i+1}/{scroll_count} 完了 (位置: {scroll_result['currentPosition']}px / {scroll_result['totalHeight']}px)")
            else:
                print(f"   ⚠️ スクロール {i+1}/{scroll_count} 失敗")
                break

        print("\n✅ スクロール完了\n")
    else:
        print("⚠️ 左側メッセージ一覧コンテナが見つかりません")
        print("   手動でメッセージ一覧を下にスクロールしてから Enter を押してください...\n")
        input()

    time.sleep(3)

    # 名前を抽出
    print("🔍 メッセージ一覧から名前を抽出中...\n")

    extract_script = """
    const names = [];

    // 方法1: メッセージアイテムから名前を抽出
    const messageItems = document.querySelectorAll('li.msg-conversation-listitem, li[class*="conversation"]');

    messageItems.forEach(item => {
        let name = null;

        // パターン1: participant-names クラス
        const participantEl = item.querySelector('.msg-conversation-listitem__participant-names, [class*="participant-names"]');
        if (participantEl) {
            name = participantEl.textContent.trim();
        }

        // パターン2: 太字のspan要素
        if (!name) {
            const boldSpans = item.querySelectorAll('span[dir="ltr"]');
            for (const span of boldSpans) {
                const text = span.textContent.trim();
                // 時刻や日付ではない、実際の名前らしいテキスト
                if (text && text.length > 2 && text.length < 50 &&
                    !text.match(/\\d{1,2}:\\d{2}/) && !text.match(/\\d{1,2}月\\d{1,2}日/)) {
                    name = text;
                    break;
                }
            }
        }

        // パターン3: aria-label から抽出
        if (!name) {
            const ariaLabel = item.getAttribute('aria-label') || '';
            const match = ariaLabel.match(/(.+?)さんとの会話/);
            if (match) {
                name = match[1].trim();
            }
        }

        // パターン4: 最初の太字要素
        if (!name) {
            const boldEl = item.querySelector('strong, b, [class*="bold"]');
            if (boldEl) {
                name = boldEl.textContent.trim();
            }
        }

        // パターン5: 最初のリンク要素のテキスト
        if (!name) {
            const linkEl = item.querySelector('a[href*="/in/"]');
            if (linkEl) {
                const text = linkEl.textContent.trim();
                const lines = text.split('\\n');
                if (lines[0] && lines[0].length > 2 && lines[0].length < 50) {
                    name = lines[0];
                }
            }
        }

        if (name) {
            // クリーンアップ：余分な空白や改行を削除
            name = name.replace(/\\s+/g, ' ').trim();

            // 除外パターン
            const excludePatterns = [
                'メッセージ', 'あなた:', 'さん:',
                '日前', '週間前', '分前', '時間前',
                '新しいメッセージ', 'New message'
            ];

            const shouldExclude = excludePatterns.some(pattern => name.includes(pattern));

            if (!shouldExclude && name.length >= 2 && name.length <= 50) {
                names.push(name);
            }
        }
    });

    // 重複を削除
    return [...new Set(names)];
    """

    try:
        message_names = driver.execute_script(extract_script)
        print(f"✅ 抽出された名前: {len(message_names)}件\n")

        # デバッグ: 最初の10件を表示
        if message_names:
            print("🔍 最初の10件:")
            for i, name in enumerate(message_names[:10], 1):
                print(f"   {i}. {name}")
            print()

        return message_names

    except Exception as e:
        print(f"❌ 名前抽出エラー: {e}\n")
        return []

# ==============================
# メイン処理
# ==============================
def main(account_name, paths, scroll_count):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🔄 LinkedIn メッセージ送信ステータス同期")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    # ログイン
    driver = login(account_name, paths['cookie_file'])

    try:
        # profiles_master.csv 読み込み
        print(f"{'='*70}")
        print(f"📂 profiles_master.csv 読み込み")
        print(f"{'='*70}\n")

        profiles_master = load_profiles_master(paths['profiles_master_file'])
        print(f"✅ 既存レコード: {len(profiles_master)} 件\n")

        # メッセージ履歴から名前を取得
        message_names = get_message_names(driver, scroll_count)

        if not message_names:
            print("⚠️ メッセージ履歴から名前を取得できませんでした。\n")
            driver.quit()
            return

        # profiles_master と照合
        print(f"{'='*70}")
        print(f"🔍 profiles_master.csv との照合")
        print(f"{'='*70}\n")

        # 名前でインデックスを作成（重複チェック用）
        name_to_profiles = {}
        for url, profile in profiles_master.items():
            name = profile.get('name', '')
            if name:
                if name not in name_to_profiles:
                    name_to_profiles[name] = []
                name_to_profiles[name].append(profile)

        # 照合結果
        updated_list = []
        new_added_list = []
        duplicate_list = []

        for message_name in message_names:
            if message_name in name_to_profiles:
                profiles = name_to_profiles[message_name]

                if len(profiles) == 1:
                    # 1件のみ: 更新
                    profile = profiles[0]
                    profile['message_sent_status'] = '送信済'
                    profile['profile_fetched'] = '送信済のため不要'
                    profile['scoring_decision'] = '送信済のため不要'
                    profile['exclusion_reason'] = 'メッセージ送信済のため対象外'
                    updated_list.append(message_name)
                else:
                    # 複数件: 同姓同名 - 何も更新しない
                    duplicate_list.append(message_name)
                    # 同姓同名フラグを全ての該当レコードに設定
                    for profile in profiles:
                        profile['duplicate_name_flag'] = '同姓同名あり'
            else:
                # profiles_master.csvに存在しない → 新規登録
                import uuid
                temp_key = f"message_only_{uuid.uuid4()}"

                new_profile = {
                    "profile_url": "",  # 空欄
                    "name": message_name,
                    "connected_date": "",
                    "profile_fetched": "送信済のため不要",
                    "profile_fetched_at": "",
                    "total_score": "",
                    "scoring_decision": "送信済のため不要",
                    "exclusion_reason": "メッセージ送信済のため対象外",
                    "message_generated": "no",
                    "message_generated_at": "",
                    "message_sent_status": "送信済",
                    "message_sent_at": "",
                    "last_send_error": "",
                    "duplicate_name_flag": ""
                }

                profiles_master[temp_key] = new_profile
                new_added_list.append(message_name)

        # 同姓同名チェック（全体で実施）
        name_counts = {}
        for profile in profiles_master.values():
            name = profile.get('name', '')
            if name:
                name_counts[name] = name_counts.get(name, 0) + 1

        # 同姓同名フラグを設定
        for profile in profiles_master.values():
            name = profile.get('name', '')
            if name and name_counts.get(name, 0) > 1:
                profile['duplicate_name_flag'] = '同姓同名あり'
            elif 'duplicate_name_flag' not in profile:
                profile['duplicate_name_flag'] = ''

        # profiles_master.csv 保存
        if updated_list or new_added_list or duplicate_list:
            save_profiles_master(profiles_master, paths['profiles_master_file'])
            print(f"💾 profiles_master.csv 更新完了\n")

        # 結果サマリー
        print(f"{'='*70}")
        print(f"📊 処理結果サマリー")
        print(f"{'='*70}")
        print(f"✅ 既存更新: {len(updated_list)} 件")
        print(f"🆕 新規登録: {len(new_added_list)} 件")
        print(f"❌ 同姓同名エラー: {len(duplicate_list)} 件")
        print(f"{'='*70}\n")

        # 詳細リスト表示
        if updated_list:
            print(f"{'='*70}")
            print(f"✅ 既存更新された名前リスト ({len(updated_list)}件)")
            print(f"{'='*70}")
            for i, name in enumerate(updated_list, 1):
                print(f"  {i}. {name}")
            print()

        if new_added_list:
            print(f"{'='*70}")
            print(f"🆕 新規登録された名前リスト ({len(new_added_list)}件)")
            print(f"{'='*70}")
            for i, name in enumerate(new_added_list, 1):
                print(f"  {i}. {name}")
            print()

        if duplicate_list:
            print(f"{'='*70}")
            print(f"❌ 同姓同名エラーリスト ({len(duplicate_list)}件)")
            print(f"{'='*70}")
            for i, name in enumerate(duplicate_list, 1):
                print(f"  {i}. {name}")
            print()

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 メッセージ送信ステータス同期完了")
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
    print(f"🔄 LinkedIn メッセージ送信ステータス同期")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

    # スクロール回数
    print("【メッセージリストのスクロール回数】")
    while True:
        scroll_input = input("スクロール回数を入力 (Enter=デフォルト「5」): ").strip()
        if not scroll_input:
            scroll_count = 5
            break
        try:
            scroll_count = int(scroll_input)
            if scroll_count > 0:
                break
            else:
                print("⚠️ 1以上の数値を入力してください")
        except ValueError:
            print("⚠️ 数値を入力してください")

    # 設定内容を確認
    print(f"\n{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"スクロール回数: {scroll_count}")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths, scroll_count)
