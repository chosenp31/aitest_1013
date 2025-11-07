#!/usr/bin/env python3
# aiagent/reset_messages.py
# メッセージ関連のステータスをリセット（メッセージを再生成するため）

import os
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# アカウント名の定義
AVAILABLE_ACCOUNTS = ["依田", "桜井", "田中"]

def select_account():
    """アカウントを選択"""
    print(f"\n{'='*70}")
    print(f"📋 リセットするアカウントを選択")
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

    return {
        'account_dir': account_dir,
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv")
    }

def reset_messages(account_name, paths):
    """メッセージ関連のステータスをリセット"""

    print(f"\n{'='*70}")
    print(f"🔄 メッセージリセット")
    print(f"{'='*70}")
    print(f"アカウント: {account_name}")
    print(f"{'='*70}\n")

    # profiles_master.csv を読み込み
    profiles_master_file = paths['profiles_master_file']

    if not os.path.exists(profiles_master_file):
        print(f"❌ エラー: {profiles_master_file} が見つかりません\n")
        return

    profiles_master = {}

    with open(profiles_master_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            profile_url = row.get('profile_url', '')
            if profile_url:
                profiles_master[profile_url] = row

    print(f"📊 現在のステータス:")

    # メッセージ生成済みの件数を確認
    generated_count = sum(1 for p in profiles_master.values() if p.get('message_generated') == 'yes')
    print(f"  メッセージ生成済み: {generated_count} 件\n")

    if generated_count == 0:
        print("⚠️ メッセージが生成されていないため、リセットの必要はありません\n")
        return

    # 確認
    print("【実行内容】")
    print("1. profiles_master.csv のメッセージ生成ステータスをリセット")
    print("   - message_generated を 'no' に変更")
    print("   - message_generated_at を空に変更")
    print("2. generated_messages.csv を削除")
    print()

    confirm = input("この内容でリセットしますか？ (Enter=実行 / no=キャンセル): ").strip().lower()

    if confirm == 'no':
        print("\n❌ リセットをキャンセルしました\n")
        return

    # profiles_master.csv を更新
    reset_count = 0

    for profile_url, profile in profiles_master.items():
        if profile.get('message_generated') == 'yes':
            profile['message_generated'] = 'no'
            profile['message_generated_at'] = ''
            reset_count += 1

    # profiles_master.csv を保存
    fieldnames = [
        "profile_url", "name", "connected_date",
        "profile_fetched", "profile_fetched_at",
        "total_score", "scoring_decision", "exclusion_reason",
        "message_generated", "message_generated_at",
        "message_sent_status", "message_sent_at", "last_send_error"
    ]

    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        sorted_profiles = sorted(profiles_master.values(), key=lambda x: x.get('profile_url', ''))
        writer.writerows(sorted_profiles)

    print(f"✅ profiles_master.csv を更新しました（{reset_count}件をリセット）")

    # generated_messages.csv を削除
    generated_messages_file = paths['generated_messages_file']

    if os.path.exists(generated_messages_file):
        os.remove(generated_messages_file)
        print(f"✅ generated_messages.csv を削除しました")
    else:
        print(f"⚠️ generated_messages.csv は存在しませんでした")

    print()
    print(f"{'='*70}")
    print(f"🎉 リセット完了")
    print(f"{'='*70}")
    print(f"次のステップ:")
    print(f"  python linkedin_4_generate_messages.py")
    print(f"  でメッセージを再生成してください")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🔄 メッセージリセットツール")
    print(f"{'='*70}\n")

    # アカウント選択
    account_name = select_account()
    paths = get_account_paths(account_name)

    # リセット実行
    reset_messages(account_name, paths)
