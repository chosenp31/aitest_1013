# run_pipeline.py
# LinkedInリクルート自動化パイプライン（ワンコマンド実行）

import sys
import os

# aiagentモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aiagent.linkedin_search import search_candidates
from aiagent.linkedin_scorer import score_all_candidates
from aiagent.linkedin_pipeline_improved import manual_login, send_requests

def main():
    """
    LinkedIn自動化パイプライン

    1. 候補者検索
    2. AIスコアリング
    3. 接続リクエスト送信
    """

    print("\n" + "="*70)
    print("🚀 LinkedIn自動化パイプライン")
    print("="*70 + "\n")

    # ==============================
    # ステップ1: 検索条件の入力
    # ==============================
    print("📝 検索条件を入力してください\n")

    keywords = input("検索キーワード（デフォルト: SIer OR エンジニア OR ITコンサル...）\n> ").strip()
    if not keywords:
        keywords = "SIer OR エンジニア OR ITコンサルタント OR ITエンジニア OR DXエンジニア"

    location = input("\n地域（デフォルト: Japan）\n> ").strip()
    if not location:
        location = "Japan"

    max_pages_input = input("\n検索ページ数（デフォルト: 3）\n> ").strip()
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else 3

    # ==============================
    # ステップ2: 候補者検索
    # ==============================
    print("\n" + "="*70)
    print("🔍 ステップ1: 候補者検索")
    print("="*70 + "\n")

    try:
        count = search_candidates(keywords, location, max_pages)
        if count == 0:
            print("❌ 候補者が見つかりませんでした。検索条件を変更してください。")
            return
    except Exception as e:
        print(f"❌ 検索中にエラーが発生: {e}")
        return

    # ==============================
    # ステップ3: AIスコアリング
    # ==============================
    print("\n" + "="*70)
    print("🧠 ステップ2: AIスコアリング")
    print("="*70 + "\n")

    confirm = input("AIスコアリングを実行しますか？（y/n）\n> ").strip().lower()
    if confirm != 'y':
        print("⚠️ スコアリングをスキップしました。")
        print("💡 手動で実行: python3 aiagent/linkedin_scorer.py")
        return

    try:
        send_count = score_all_candidates()
        if send_count == 0:
            print("❌ 送信対象が0件です。処理を終了します。")
            return
    except Exception as e:
        print(f"❌ スコアリング中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return

    # ==============================
    # ステップ4: 接続リクエスト送信
    # ==============================
    print("\n" + "="*70)
    print("📤 ステップ3: 接続リクエスト送信")
    print("="*70 + "\n")

    confirm = input(f"{send_count}件の候補者に接続リクエストを送信しますか？（y/n）\n> ").strip().lower()
    if confirm != 'y':
        print("⚠️ 送信をスキップしました。")
        print("💡 手動で実行: python3 aiagent/linkedin_pipeline_improved.py")
        return

    try:
        driver = manual_login()
        send_requests(driver)
    except Exception as e:
        print(f"❌ 送信中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return

    # ==============================
    # 完了
    # ==============================
    print("\n" + "="*70)
    print("🎉 パイプライン完了！")
    print("="*70 + "\n")
    print("📊 結果ファイル:")
    print("   - data/candidates_raw.csv     : 検索結果（全候補者）")
    print("   - data/candidates_scored.csv  : スコアリング結果")
    print("   - data/messages.csv           : 送信対象リスト")
    print("   - data/logs.csv               : 送信ログ")
    print()

if __name__ == "__main__":
    main()
