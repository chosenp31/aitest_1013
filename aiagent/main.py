# aiagent/main.py
import streamlit as st
import sys
import os
from datetime import datetime

# =====================================
# パス設定（aiagent をモジュールとして認識させる）
# =====================================
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =====================================
# モジュール読み込み
# =====================================
from aiagent.linkedin_scraper import scrape_candidates
from aiagent.analyzer import analyze_candidates
from aiagent.linkedin_sender import send_connection_requests
from dotenv import load_dotenv

# =====================================
# 環境変数の読み込み
# =====================================
load_dotenv()

# =====================================
# Streamlit ページ設定
# =====================================
st.set_page_config(page_title="LinkedIn Auto Agent", layout="wide")

# =====================================
# セッションステート初期化
# =====================================
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "AI提案条件"
if "log_messages" not in st.session_state:
    st.session_state.log_messages = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None

# =====================================
# データパス定義
# =====================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
SENT_LOG_PATH = os.path.join(DATA_DIR, "sent_log.csv")
SCORED_PATH = os.path.join(DATA_DIR, "candidates_scored.csv")
RAW_PATH = os.path.join(DATA_DIR, "candidates_raw.csv")

# =====================================
# ログ関数
# =====================================
def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    st.session_state.log_messages.append(msg)
    print(msg)

# =====================================
# タブ構成
# =====================================
tabs = ["AI提案条件", "ダッシュボード", "返信フォロー", "設定・ログ"]
selected_tab = st.sidebar.radio("メニューを選択してください", tabs, index=tabs.index(st.session_state.active_tab))
st.session_state.active_tab = selected_tab

# =====================================
# タブ①：AI提案条件
# =====================================
if selected_tab == "AI提案条件":
    st.title("🤖 AI提案条件")
    st.write("候補者検索 → AIスコアリング → 自動送信 を実行します。")

    with st.form("ai_conditions_form"):
        col1, col2 = st.columns(2)
        with col1:
            target_region = st.text_input("地域条件（例：Tokyo, Japan）", "Japan")
        with col2:
            max_pages = st.number_input("検索ページ数（1〜10）", min_value=1, max_value=10, value=2, step=1)
        job_keywords = st.text_area("職種キーワード（カンマ区切り）", "ITコンサル, SIer, システムエンジニア")

        run_all = st.form_submit_button("🔎 検索 → 🧠 スコア → ✉️ 送信（ワンボタン実行）")

    if run_all:
        with st.spinner("LinkedIn 検索を実行中..."):
            kw = ",".join([k.strip() for k in job_keywords.split(",") if k.strip()])
            count = scrape_candidates(keywords=kw, location=target_region, max_pages=int(max_pages))
            log(f"検索完了：{count}件 抽出 → {RAW_PATH}")

        with st.spinner("AIスコアリングを実行中..."):
            send_targets = analyze_candidates(input_csv=RAW_PATH, output_csv=SCORED_PATH)
            log(f"AIスコアリング完了：送信対象 {len(send_targets)} 件 → {SCORED_PATH}")

        with st.spinner("LinkedIn に接続リクエストを送信中..."):
            send_connection_requests()
            log("接続リクエスト送信フローを完了")

        st.success("✅ ワンボタン実行が完了しました。")
        st.session_state.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =====================================
# タブ②：ダッシュボード
# =====================================
elif selected_tab == "ダッシュボード":
    st.title("📊 ダッシュボード")
    st.write("送信数や返信率などを実データで可視化します。")

    import pandas as pd
    if os.path.exists(SENT_LOG_PATH):
        df = pd.read_csv(SENT_LOG_PATH)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df["day"] = df["date"].dt.date

            st.subheader("日別 送信数")
            day_counts = df.groupby("day")["profile_url"].count().reset_index(name="送信数")
            st.dataframe(day_counts, use_container_width=True)

            st.subheader("直近の送信履歴（最新50件）")
            st.dataframe(df.sort_values("date", ascending=False).head(50), use_container_width=True)
        else:
            st.info("送信ログがまだありません。AI提案条件タブから実行してください。")
    else:
        st.info("送信ログがまだありません。AI提案条件タブから実行してください。")

# =====================================
# タブ③：返信フォロー（ダミー）
# =====================================
elif selected_tab == "返信フォロー":
    st.title("📬 返信フォロー")
    st.write("返信検出モジュールの統合は次フェーズで行います。")

# =====================================
# タブ④：設定・ログ
# =====================================
elif selected_tab == "設定・ログ":
    st.title("⚙️ 設定・ログ")
    st.write("APIキーや送信制御設定、ログの確認を行います。")

    st.subheader("実行ログ")
    for msg in st.session_state.log_messages[-200:]:
        st.text(msg)
    st.caption("（最新200件を表示）")

    st.divider()
    st.write(f"最終実行: {st.session_state.last_run or '未実行'}")
