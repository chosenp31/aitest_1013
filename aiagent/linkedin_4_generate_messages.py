# aiagent/linkedin_4_generate_messages.py
# メッセージ生成のみ（固定テンプレート使用）
# profiles_master.csv で統合管理

import os
import csv
from datetime import datetime

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
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv")
    }

# メッセージテンプレート（アカウント別）
MESSAGE_TEMPLATES = {
    "依田": """{name}さん

突然のご連絡失礼します。
KPMGコンサルティングの依田と申します！

お互いのキャリアや業界の話をざっくばらんにお話しできればと思いご連絡させていただきました。

私からは以下のようなトピックをお話しできるかと思います。
・KPMG/フューチャーアーキテクトでのプロジェクト経験
デジタル戦略におけるロードマップ策定、AX人材確保計画策定、IoTシステム導入計画策定・実行支援、基幹システム刷新におけるPMOなど
・転職時に検討したBIG4、アクセンチュアの比較や選考情報

30分程度オンラインでMTGさせていただくと嬉しいです！
よろしくお願いいたします。""",

    "桜井": """{name}さん

桜井と申します。

よろしくお願いいたします。""",

    "田中": """{name}さん

田中と申します。

よろしくお願いいたします。"""
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
                    if profile_url:
                        profiles_master[profile_url] = row
        except Exception as e:
            print(f"⚠️ profiles_master.csv 読み込みエラー: {e}\n")

    return profiles_master

def save_profiles_master(profiles_master, profiles_master_file):
    """profiles_master.csv を保存"""
    fieldnames = [
        "profile_url", "name", "connected_date",
        "profile_fetched", "profile_fetched_at",
        "total_score", "scoring_decision",
        "message_generated", "message_generated_at",
        "message_sent_status", "message_sent_at", "last_send_error"
    ]

    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # profile_url でソート
        sorted_profiles = sorted(profiles_master.values(), key=lambda x: x.get('profile_url', ''))
        writer.writerows(sorted_profiles)

def update_profile_master(profiles_master, profile_url, updates):
    """profiles_master の特定エントリを更新"""
    if profile_url not in profiles_master:
        profiles_master[profile_url] = {
            "profile_url": profile_url,
            "name": "",
            "connected_date": "",
            "profile_fetched": "no",
            "profile_fetched_at": "",
            "total_score": "",
            "scoring_decision": "",
            "message_generated": "no",
            "message_generated_at": "",
            "message_sent_status": "pending",
            "message_sent_at": "",
            "last_send_error": ""
        }

    profiles_master[profile_url].update(updates)

# ==============================
# メッセージ生成
# ==============================
def generate_message(name, account_name):
    """メッセージを生成（アカウント別・固定テンプレート）"""
    # アカウント別のテンプレートを取得
    template = MESSAGE_TEMPLATES.get(account_name, MESSAGE_TEMPLATES["依田"])
    message = template.format(name=name)
    return message

# ==============================
# メイン処理
# ==============================
def main(account_name, paths):
    """メイン処理"""

    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ生成")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"開始日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    try:
        # profiles_master.csv 読み込み
        print(f"{'='*70}")
        print(f"📂 profiles_master.csv 読み込み")
        print(f"{'='*70}\n")

        profiles_master = load_profiles_master(paths['profiles_master_file'])
        print(f"✅ 既存レコード: {len(profiles_master)} 件\n")

        # 送信対象抽出（scoring_decision=send かつ message_sent_status≠success）
        send_targets = []
        for profile_url, profile in profiles_master.items():
            if (profile.get('scoring_decision') == 'send' and
                profile.get('message_sent_status') != 'success'):
                send_targets.append(profile)

        if not send_targets:
            print("⚠️ 送信対象が0件です。処理を終了します。\n")
            return

        print(f"{'='*70}")
        print(f"📋 送信対象")
        print(f"{'='*70}")
        print(f"対象者数: {len(send_targets)} 件")
        print(f"{'='*70}\n")

        # メッセージ生成（message_generated=no のみ）
        messages_to_generate = [p for p in send_targets if p.get('message_generated') != 'yes']

        if messages_to_generate:
            print(f"{'='*70}")
            print(f"💬 メッセージ生成")
            print(f"{'='*70}")
            print(f"対象者数: {len(messages_to_generate)} 件")
            print(f"{'='*70}\n")

            # generated_messages.csv に保存
            messages_data = []

            for idx, profile in enumerate(messages_to_generate, start=1):
                name = profile['name']
                profile_url = profile['profile_url']
                score = profile.get('total_score', '0')

                print(f"[{idx}/{len(messages_to_generate)}] 💬 {name} (スコア: {score}点) のメッセージを生成中...")
                message = generate_message(name, account_name)
                print(f"   ✅ 生成完了\n")

                messages_data.append({
                    'profile_url': profile_url,
                    'name': name,
                    'total_score': score,
                    'message': message,
                    'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                # profiles_master 更新
                update_profile_master(profiles_master, profile_url, {
                    'message_generated': 'yes',
                    'message_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

            # generated_messages.csv に追記
            file_exists = os.path.exists(paths['generated_messages_file'])
            with open(paths['generated_messages_file'], "a", newline="", encoding="utf-8") as f:
                fieldnames = ["profile_url", "name", "total_score", "message", "generated_at"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(messages_data)

            save_profiles_master(profiles_master, paths['profiles_master_file'])
            print(f"💾 メッセージ保存完了: {paths['generated_messages_file']}\n")
        else:
            print("✅ すべてメッセージ生成済みです\n")

        # 生成済みメッセージを一覧表示
        print(f"{'='*70}")
        print(f"📋 生成済みメッセージ一覧")
        print(f"{'='*70}\n")

        # generated_messages.csv から送信対象のメッセージを読み込み
        messages_map = {}
        if os.path.exists(paths['generated_messages_file']):
            with open(paths['generated_messages_file'], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    messages_map[row['profile_url']] = row

        for idx, profile in enumerate(send_targets, start=1):
            profile_url = profile['profile_url']
            if profile_url in messages_map:
                msg = messages_map[profile_url]
                print(f"--- [{idx}/{len(send_targets)}] {msg['name']} (スコア: {msg['total_score']}点) ---")
                print(f"{msg['message']}")
                print()

    except KeyboardInterrupt:
        print("\n\n⚠️ ユーザーによって処理が中断されました\n")
    except Exception as e:
        print(f"\n\n❌ エラーが発生しました: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n{'='*70}")
        print(f"🏁 メッセージ生成完了")
        print(f"{'='*70}")
        print(f"終了日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

# ==============================
# エントリポイント
# ==============================
if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🚀 LinkedIn メッセージ生成")
    print(f"{'='*70}\n")

    # Step 1: アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    print(f"📁 データ保存先: {paths['account_dir']}\n")

    # 設定内容を確認
    print(f"{'='*70}")
    print(f"📋 設定内容")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"{'='*70}\n")

    confirm = input("この設定で実行しますか？ (Enter=実行 / no=キャンセル): ").strip().lower()
    if confirm == 'no':
        print("\n❌ 処理をキャンセルしました\n")
        exit(0)

    main(account_name, paths)
