# aiagent/cleanup_unknown_names.py
# 「名前不明」のレコードをprofiles_master.csvから削除

import os
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNTS = ["依田", "桜井", "田中"]

def cleanup_unknown_names(account_name):
    """名前不明のレコードを削除"""
    account_dir = os.path.join(BASE_DIR, "data", account_name)
    profiles_master_file = os.path.join(account_dir, "profiles_master.csv")

    if not os.path.exists(profiles_master_file):
        print(f"⚠️ {account_name}: profiles_master.csv が見つかりません")
        return

    # CSVを読み込み
    profiles = []
    with open(profiles_master_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            profiles.append(row)

    # 名前不明を除外
    original_count = len(profiles)
    filtered_profiles = [p for p in profiles if p.get('name') != '名前不明']
    removed_count = original_count - len(filtered_profiles)

    # 保存
    with open(profiles_master_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_profiles)

    print(f"✅ {account_name}: {removed_count}件削除 (残り: {len(filtered_profiles)}件)")

if __name__ == "__main__":
    print(f"\n{'='*70}")
    print(f"🗑️  「名前不明」レコード削除")
    print(f"{'='*70}\n")

    for account in ACCOUNTS:
        cleanup_unknown_names(account)

    print(f"\n{'='*70}")
    print(f"✅ 完了")
    print(f"{'='*70}\n")
