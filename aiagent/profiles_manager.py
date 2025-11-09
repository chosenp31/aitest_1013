# aiagent/profiles_manager.py
# LinkedIn メッセージ送信管理画面（Streamlit）

import os
import csv
import streamlit as st
import pandas as pd
from datetime import datetime

# ==============================
# 設定
# ==============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVAILABLE_ACCOUNTS = ["依田", "桜井", "田中"]

def get_account_paths(account_name):
    """アカウント毎のディレクトリとファイルパスを取得"""
    account_dir = os.path.join(BASE_DIR, "data", account_name)
    os.makedirs(account_dir, exist_ok=True)

    return {
        'account_dir': account_dir,
        'profiles_master_file': os.path.join(account_dir, "profiles_master.csv"),
        'generated_messages_file': os.path.join(account_dir, "generated_messages.csv")
    }

# ==============================
# データ読み込み・保存
# ==============================
def load_profiles_master(profiles_master_file):
    """profiles_master.csv を読み込む"""
    if not os.path.exists(profiles_master_file):
        return pd.DataFrame(columns=[
            "profile_url", "name", "connected_date",
            "profile_fetched", "profile_fetched_at",
            "total_score", "scoring_decision", "exclusion_reason",
            "message_generated", "message_generated_at",
            "message_sent_status", "message_sent_at", "last_send_error"
        ])

    df = pd.read_csv(profiles_master_file)

    # スコア表示の調整：skipの場合は"-"で表示
    if 'total_score' in df.columns and 'scoring_decision' in df.columns:
        df['total_score_display'] = df.apply(
            lambda row: '-' if row.get('scoring_decision') == 'skip' else row.get('total_score', ''),
            axis=1
        )

    # 送信対象の表示：○/✖️/判定前
    if 'scoring_decision' in df.columns:
        def get_target_display(decision):
            if pd.isna(decision) or decision == '':
                return '判定前'
            elif decision == 'send':
                return '○'
            elif decision == 'skip':
                return '✖️'
            else:
                return '判定前'

        df['送信対象_display'] = df['scoring_decision'].apply(get_target_display)

    # 送信ステータスの表示
    if 'scoring_decision' in df.columns and 'message_sent_status' in df.columns and 'message_generated' in df.columns:
        def get_status_display(row):
            decision = row.get('scoring_decision', '')
            status = row.get('message_sent_status', '')
            message_generated = row.get('message_generated', '')

            # エッジケース: skipなのにsuccess → 送信済を優先
            if status == 'success':
                return '送信済'

            # 判定前
            if pd.isna(decision) or decision == '':
                return '判定前'

            # skip → 送信対象外
            if decision == 'skip':
                return '送信対象外'

            # send の場合
            if decision == 'send':
                if status == 'pending':
                    # メッセージ生成済みかどうかで分岐
                    if message_generated == 'yes':
                        return '送信待'
                    else:
                        return 'メッセージ未生成'
                elif status == 'error':
                    return '送信エラー'

            return '判定前'

        df['送信ステータス_display'] = df.apply(get_status_display, axis=1)

    return df

def save_profiles_master(df, profiles_master_file):
    """profiles_master.csv を保存"""
    # 表示用の列は保存しない
    save_df = df.copy()
    display_columns = ['total_score_display', '送信対象_display', '送信ステータス_display']
    for col in display_columns:
        if col in save_df.columns:
            save_df = save_df.drop(columns=[col])

    save_df.to_csv(profiles_master_file, index=False, encoding='utf-8')

def load_messages(generated_messages_file):
    """generated_messages.csv を読み込む"""
    if not os.path.exists(generated_messages_file):
        return {}

    messages_map = {}
    with open(generated_messages_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            messages_map[row['profile_url']] = row['message']

    return messages_map

# ==============================
# 統計情報
# ==============================
def get_statistics(df):
    """統計情報を取得"""
    total = len(df)

    # 送信ステータス_display列を使用して集計
    if '送信ステータス_display' in df.columns:
        sent = len(df[df['送信ステータス_display'] == '送信済'])
        waiting = len(df[df['送信ステータス_display'] == '送信待'])
        message_not_generated = len(df[df['送信ステータス_display'] == 'メッセージ未生成'])
        excluded = len(df[df['送信ステータス_display'] == '送信対象外'])
        error = len(df[df['送信ステータス_display'] == '送信エラー'])
        pending_judge = len(df[df['送信ステータス_display'] == '判定前'])
    else:
        sent = 0
        waiting = 0
        message_not_generated = 0
        excluded = 0
        error = 0
        pending_judge = 0

    return {
        'total': total,
        'sent': sent,
        'waiting': waiting,
        'message_not_generated': message_not_generated,
        'excluded': excluded,
        'error': error,
        'pending_judge': pending_judge
    }

# ==============================
# Streamlit UI
# ==============================
def main():
    st.set_page_config(page_title="LinkedIn メッセージ送信管理", layout="wide")

    st.title("📊 LinkedIn メッセージ送信管理画面")
    st.markdown("---")

    # アカウント選択
    col1, col2 = st.columns([1, 3])
    with col1:
        account_name = st.selectbox("🔹 アカウント選択", AVAILABLE_ACCOUNTS)

    paths = get_account_paths(account_name)

    # データ読み込み
    df = load_profiles_master(paths['profiles_master_file'])
    messages_map = load_messages(paths['generated_messages_file'])

    if df.empty:
        st.warning(f"⚠️ {account_name} アカウントのデータがありません")
        return

    # 統計情報
    stats = get_statistics(df)

    st.markdown("### 📈 統計情報")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("全件", stats['total'])
    with col2:
        st.metric("✅ 送信済", stats['sent'])
    with col3:
        st.metric("⏳ 送信待", stats['waiting'])
    with col4:
        st.metric("📝 未生成", stats['message_not_generated'])
    with col5:
        st.metric("⊘ 対象外", stats['excluded'])
    with col6:
        st.metric("❌ エラー", stats['error'])

    st.markdown("---")

    # フィルター・検索
    st.markdown("### 🔍 フィルター・検索")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        status_filter = st.selectbox(
            "送信ステータス",
            ["全て", "送信済", "送信待", "メッセージ未生成", "送信対象外", "送信エラー", "判定前"]
        )

    with col2:
        decision_filter = st.selectbox(
            "送信対象",
            ["全て", "○", "✖️", "判定前"]
        )

    with col3:
        name_search = st.text_input("名前検索", "")

    # フィルタリング処理
    filtered_df = df.copy()

    # 送信ステータスでフィルタリング（送信ステータス_display列を使用）
    if status_filter != "全て" and '送信ステータス_display' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['送信ステータス_display'] == status_filter]

    # 送信対象でフィルタリング（送信対象_display列を使用）
    if decision_filter != "全て" and '送信対象_display' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['送信対象_display'] == decision_filter]

    if name_search:
        filtered_df = filtered_df[filtered_df['name'].str.contains(name_search, na=False)]

    st.markdown(f"**検索結果: {len(filtered_df)} 件**")

    st.markdown("---")

    # 一覧表示
    st.markdown("### 📋 プロフィール一覧")

    if filtered_df.empty:
        st.info("該当するデータがありません")
        return

    # 表示用のデータフレーム作成
    display_df = filtered_df.copy()

    # 表示列を選択
    display_columns = ['name', 'total_score_display', '送信対象_display', 'exclusion_reason', '送信ステータス_display', 'message_sent_at', 'last_send_error']
    display_df_filtered = display_df[display_columns].copy()
    display_df_filtered.columns = ['名前', 'スコア', '送信対象', '除外理由', '送信ステータス', '送信日時', 'エラー内容']

    # スタイリング関数
    def style_row(row):
        """行ごとのスタイルを設定"""
        # 送信対象が✖️の場合、グレーアウト
        if row['送信対象'] == '✖️':
            return ['background-color: #f0f0f0; color: #888888'] * len(row)
        # 送信ステータスが「送信待」の場合、薄い黄色
        elif row['送信ステータス'] == '送信待':
            return ['background-color: #fffbea'] * len(row)
        # 送信ステータスが「メッセージ未生成」の場合、薄いオレンジ
        elif row['送信ステータス'] == 'メッセージ未生成':
            return ['background-color: #fff3e0'] * len(row)
        else:
            return [''] * len(row)

    # スタイルを適用
    styled_df = display_df_filtered.style.apply(style_row, axis=1)

    # データエディタで表示
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )

    st.markdown("---")

    # 詳細表示・編集
    st.markdown("### 🔧 詳細表示・ステータス変更")

    # 行選択（名前で選択）
    selected_name = st.selectbox(
        "編集する人を選択",
        ["（選択してください）"] + filtered_df['name'].tolist()
    )

    if selected_name != "（選択してください）":
        selected_row = filtered_df[filtered_df['name'] == selected_name].iloc[0]
        profile_url = selected_row['profile_url']

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📄 基本情報")
            st.text(f"名前: {selected_row['name']}")
            st.text(f"つながり日: {selected_row['connected_date']}")
            score_display = selected_row.get('total_score_display', selected_row.get('total_score', '-'))
            st.text(f"スコア: {score_display}")
            target_display = selected_row.get('送信対象_display', '判定前')
            st.text(f"送信対象: {target_display}")
            if selected_row.get('exclusion_reason'):
                st.text(f"除外理由: {selected_row['exclusion_reason']}")
            st.text(f"プロフィールURL: {profile_url}")

        with col2:
            st.markdown("#### 📨 送信情報")
            status_display = selected_row.get('送信ステータス_display', '判定前')
            st.text(f"送信ステータス: {status_display}")
            st.text(f"送信日時: {selected_row['message_sent_at']}")
            if selected_row['last_send_error']:
                st.error(f"エラー内容: {selected_row['last_send_error']}")

        # メッセージ表示
        if profile_url in messages_map:
            st.markdown("#### 💬 生成されたメッセージ")
            st.text_area("", messages_map[profile_url], height=200, disabled=True)

        st.markdown("---")

        # ステータス変更
        st.markdown("#### ✏️ ステータス変更")

        col1, col2 = st.columns([3, 1])

        with col1:
            new_status = st.selectbox(
                "新しい送信ステータス",
                ["pending", "success", "error"],
                index=["pending", "success", "error"].index(selected_row['message_sent_status'])
            )

        with col2:
            st.write("")  # スペース
            st.write("")  # スペース
            if st.button("💾 保存", type="primary"):
                # ステータス更新
                df.loc[df['profile_url'] == profile_url, 'message_sent_status'] = new_status

                # タイムスタンプ更新
                if new_status == 'success':
                    df.loc[df['profile_url'] == profile_url, 'message_sent_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    df.loc[df['profile_url'] == profile_url, 'last_send_error'] = ''
                elif new_status == 'pending':
                    df.loc[df['profile_url'] == profile_url, 'message_sent_at'] = ''
                    df.loc[df['profile_url'] == profile_url, 'last_send_error'] = ''

                # 保存
                save_profiles_master(df, paths['profiles_master_file'])
                st.success("✅ 保存しました！")
                st.rerun()

    st.markdown("---")

    # 一括操作
    st.markdown("### 🛠️ 一括操作")
    st.warning("⚠️ 一括操作は慎重に行ってください")

    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        bulk_filter = st.selectbox(
            "対象を選択",
            ["全ての送信待ち (pending)", "全てのエラー (error)", "全ての送信成功 (success)", "全ての判定前（未判定）"]
        )

    with col2:
        bulk_new_status = st.selectbox(
            "変更後のステータス",
            ["pending", "success", "error", "送信対象外 (skip)"]
        )

    with col3:
        st.write("")  # スペース
        st.write("")  # スペース
        if st.button("🔄 一括変更", type="secondary"):
            count = 0

            if bulk_filter == "全ての判定前（未判定）":
                # 判定前の人を対象に
                mask = (df['scoring_decision'].isna()) | (df['scoring_decision'] == '')
                count = mask.sum()

                if count > 0 and bulk_new_status == "送信対象外 (skip)":
                    df.loc[mask, 'scoring_decision'] = 'skip'
                    df.loc[mask, 'exclusion_reason'] = '手動で対象外に設定'
                    df.loc[mask, 'total_score'] = '-'

                    # 保存
                    save_profiles_master(df, paths['profiles_master_file'])
                    st.success(f"✅ {count}件を送信対象外に変更しました！")
                    st.rerun()
                else:
                    st.error("判定前の一括変更は「送信対象外 (skip)」のみ選択可能です")
            else:
                # 既存の一括操作
                if bulk_filter == "全ての送信待ち (pending)":
                    target_status = 'pending'
                elif bulk_filter == "全てのエラー (error)":
                    target_status = 'error'
                elif bulk_filter == "全ての送信成功 (success)":
                    target_status = 'success'

                # message_sent_statusの変更のみ許可
                if bulk_new_status in ["pending", "success", "error"]:
                    # 対象行を更新
                    mask = df['message_sent_status'] == target_status
                    count = mask.sum()

                    if count > 0:
                        df.loc[mask, 'message_sent_status'] = bulk_new_status

                        # タイムスタンプ更新
                        if bulk_new_status == 'success':
                            df.loc[mask, 'message_sent_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            df.loc[mask, 'last_send_error'] = ''
                        elif bulk_new_status == 'pending':
                            df.loc[mask, 'message_sent_at'] = ''
                            df.loc[mask, 'last_send_error'] = ''

                        # 保存
                        save_profiles_master(df, paths['profiles_master_file'])
                        st.success(f"✅ {count}件のステータスを {bulk_new_status} に変更しました！")
                        st.rerun()
                    else:
                        st.info("対象データがありません")
                else:
                    st.error("このフィルターでは「送信対象外 (skip)」は選択できません")

if __name__ == "__main__":
    main()
