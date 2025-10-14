import streamlit as st
import sys
import os
from datetime import datetime

# カレントディレクトリを aiagent 配下に固定
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# ページ設定
st.set_page_config(page_title="LinkedIn Auto Agent", layout="wide")

# Session State 初期化
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "AI提案条件"
if "log_messages" not in st.session_state:
    st.session_state.log_messages = []

# 共通ログ関数
def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    st.session_state.log_messages.append(msg)
    print(msg)

# -------------------------
# メインタブ構成
# -------------------------
tabs = ["AI提案条件", "ダッシュボード", "返信フォロー", "設定・ログ"]
selected_tab = st.sidebar.radio("メニューを選択してください", tabs, index=tabs.index(st.session_state.active_tab))
st.session_state.active_tab = selected_tab

# -------------------------
# タブ①：AI提案条件
# -------------------------
if selected_tab == "AI提案条件":
    st.title("🤖 AI提案条件")
    st.write("ここでは候補者検索条件やAIスコアリング条件を設定します。")

    # 仮のフォーム（後で analyzer.py と連携）
    with st.form("ai_conditions_form"):
        age_limit = st.number_input("年齢上限", min_value=20, max_value=60, value=40)
        target_region = st.text_input("地域条件（例：Tokyo, Japan）", "Japan")
        job_keywords = st.text_area("職種キーワード（カンマ区切り）", "ITコンサル, SIer, システムエンジニア")
        submitted = st.form_submit_button("AI提案を実行")

        if submitted:
            log(f"AI提案条件を実行：年齢≤{age_limit}, 地域={target_region}, 職種={job_keywords}")
            st.success("AI提案条件を送信しました。（ダミー動作）")

# -------------------------
# タブ②：ダッシュボード
# -------------------------
elif selected_tab == "ダッシュボード":
    st.title("📊 ダッシュボード")
    st.write("送信数や返信率などを可視化します。")

    # 仮のデータフレーム表示
    import pandas as pd
    dummy_data = pd.DataFrame({
        "日付": ["2025-10-11", "2025-10-12", "2025-10-13"],
        "送信数": [20, 25, 30],
        "返信数": [3, 4, 5]
    })
    st.dataframe(dummy_data, use_container_width=True)

# -------------------------
# タブ③：返信フォロー
# -------------------------
elif selected_tab == "返信フォロー":
    st.title("📬 返信フォロー")
    st.write("返信のあった候補者にフォロー文を生成します。")

    # 仮データ
    candidates = ["山田太郎", "佐藤花子", "鈴木一郎"]
    selected_name = st.selectbox("候補者を選択", candidates)
    date1 = st.date_input("候補日①")
    date2 = st.date_input("候補日②")
    date3 = st.date_input("候補日③")

    if st.button("フォローメッセージを生成（ダミー）"):
        follow_message = f"{selected_name}様、以下の日程はいかがでしょうか？\n・{date1}\n・{date2}\n・{date3}"
        st.text_area("生成結果", follow_message, height=150)
        log(f"フォローメッセージ生成：{selected_name}")

# -------------------------
# タブ④：設定・ログ
# -------------------------
elif selected_tab == "設定・ログ":
    st.title("⚙️ 設定・ログ")
    st.write("APIキーや送信制御設定、ログの確認を行います。")

    st.subheader("ログ出力")
    for msg in st.session_state.log_messages[-20:]:
        st.text(msg)

    st.caption("（最新20件を表示）")
