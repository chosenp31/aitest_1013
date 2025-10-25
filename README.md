# LinkedIn 自動化AIシステム

KPMG Consultingのリファラル採用を効率化するための、**完全自動化**LinkedInリクルートシステムです。

## 🎯 機能概要

### ✅ 実装済み機能

1. **候補者自動検索**
   - キーワード、地域を柔軟に設定
   - 複数ページの検索結果を自動抽出
   - 名前、職歴、会社、場所などを取得

2. **AIスコアリング（OpenAI API）**
   - 候補者の年齢を自動推定（職歴・卒業年から）
   - IT業界経験を自動判定
   - 経営層（社長、CEO、CIO等）を自動除外
   - 60点以上を送信対象に自動抽出（最大30件まで）

3. **接続リクエスト自動送信**
   - 「つながりを申請」ボタンの自動検出
   - 既接続・保留中を自動スキップ
   - 送信結果をCSVに記録

4. **ワンコマンド実行**
   - 検索 → スコアリング → 送信を一気に実行

---

## 📦 必要な環境

- **OS**: macOS / Linux
- **Python**: 3.12以上
- **ブラウザ**: Google Chrome（最新版）
- **その他**:
  - OpenAI APIキー（有料・従量課金）
  - ChromeDriverは自動インストール

---

## 🚀 セットアップ手順

### ステップ1: リポジトリのクローン

```bash
git clone <repository-url>
cd aitest_1013
```

### ステップ2: 仮想環境の作成と有効化

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
```

### ステップ3: 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### ステップ4: OpenAI APIキーの取得

1. https://platform.openai.com/ にアクセス
2. 「API keys」から新しいAPIキーを作成
3. 支払い方法を登録（使用量上限の設定を推奨）

### ステップ5: 環境変数の設定

```bash
# .envファイルを作成
cat > .env << 'EOF'
# OpenAI API設定
OPENAI_API_KEY=sk-proj-あなたのAPIキー
OPENAI_MODEL=gpt-4o-mini

# スコアリング基準
MAX_AGE=40
MIN_SCORE=60
MAX_SEND_COUNT=30
EOF
```

**重要**: `sk-proj-あなたのAPIキー` を実際のAPIキーに置き換えてください。

---

## 📋 使い方

### 🎯 方法1: ワンコマンド実行（推奨）

すべての工程を一度に実行：

```bash
source venv/bin/activate
python3 run_pipeline.py
```

**実行の流れ:**
1. 検索条件を入力（キーワード、地域、ページ数）
2. LinkedIn候補者検索
3. AIスコアリング
4. 接続リクエスト送信

**実行時間の目安:**
- 検索: 3ページで約5分
- スコアリング: 100人で約2分（OpenAI API）
- 送信: 10人で約2分

---

### 🔧 方法2: 個別実行（細かく制御したい場合）

#### ステップ1: 候補者検索

```bash
python3 aiagent/linkedin_search.py
```

**カスタマイズ例:**

```bash
# キーワード、地域、ページ数を指定
python3 aiagent/linkedin_search.py "SIer OR エンジニア" "Tokyo" 5
```

**出力:** `data/candidates_raw.csv`

---

#### ステップ2: AIスコアリング

```bash
python3 aiagent/linkedin_scorer.py
```

**評価基準:**
- ✅ 年齢40歳以下（職歴・卒業年から推定）
- ✅ IT業界経験あり（SIer、エンジニア、コンサル等）
- ❌ 学生、未経験、IT無関係の業界
- ❌ 経営層（社長、CEO、CIO、執行役員、取締役）

**出力:**
- `data/candidates_scored.csv` - 全候補者のスコア
- `data/messages.csv` - 送信対象（60点以上、最大30件）

---

#### ステップ3: 接続リクエスト送信

```bash
python3 aiagent/linkedin_pipeline_improved.py
```

**自動処理:**
- 既につながっている → スキップ
- 保留中（送信済み） → スキップ
- 未接続 → 送信

**出力:** `data/logs.csv`

---

## 📁 ディレクトリ構成

```
aitest_1013/
├── aiagent/
│   ├── linkedin_search.py              # 候補者検索
│   ├── linkedin_scorer.py              # AIスコアリング
│   ├── linkedin_pipeline_improved.py   # 接続リクエスト送信
│   └── main.py                         # Streamlit UI（開発中）
├── data/
│   ├── candidates_raw.csv              # 検索結果（全候補者）
│   ├── candidates_scored.csv           # スコアリング結果
│   ├── messages.csv                    # 送信対象リスト
│   └── logs.csv                        # 送信履歴
├── debug_output/                       # デバッグファイル保存先
├── run_pipeline.py                     # ワンコマンド実行
├── requirements.txt                    # 依存パッケージ
├── .env                                # 環境変数（APIキー等）
├── README.md                           # このファイル
└── TROUBLESHOOTING_GUIDE.md            # トラブルシューティング
```

---

## 💰 コスト（OpenAI API）

**使用モデル:** gpt-4o-mini（推奨）

**料金:**
- 候補者1人あたり: 約$0.0004（約0.06円）
- 100人スコアリング: 約$0.04（約6円）
- 1000人スコアリング: 約$0.40（約60円）

**結論:** 非常に安価です。月間1000人スコアリングしても100円以下。

---

## 📊 ログファイルの見方

### data/logs.csv（送信履歴）

```csv
date,name,url,result,error,details
2025-10-25 12:00:00,山田太郎,https://...,success,,sent_without_note
2025-10-25 12:01:00,佐藤花子,https://...,skip,既接続,already_connected
2025-10-25 12:02:00,鈴木一郎,https://...,error,ボタン未検出,
```

**result列:**
- `success`: 送信成功
- `skip`: スキップ（既接続、保留中、URLなし）
- `error`: エラー発生

### data/candidates_scored.csv（スコアリング結果）

```csv
name,url,headline,company,location,estimated_age,score,decision,reason
山田太郎,https://...,ITエンジニア,株式会社ABC,Tokyo,32,85,send,IT業界経験豊富
佐藤花子,https://...,学生,XYZ大学,Osaka,22,20,skip,学生のため除外
```

---

## ⚙️ カスタマイズ

### スコアリング基準の変更

`.env` ファイルを編集：

```env
# 年齢上限を変更
MAX_AGE=45

# 最低スコアを変更
MIN_SCORE=70

# 1回の送信数上限を変更
MAX_SEND_COUNT=20
```

### 検索キーワードの変更

`run_pipeline.py` 実行時に対話的に入力、または
`aiagent/linkedin_search.py` を直接実行：

```bash
python3 aiagent/linkedin_search.py "あなたのキーワード" "Japan" 5
```

---

## ⚠️ 重要な注意事項

### セキュリティ
- ✅ Cookie保存で自動ログイン（2回目以降）
- ✅ Cookieは `.gitignore` で除外（Git管理外）
- ✅ APIキーは `.env` ファイルで管理（Gitにコミットしない）
- ✅ `.gitignore` で機密情報を除外

### LinkedIn利用規約
- ⚠️ 送信件数は1日30件以内を推奨（MAX_SEND_COUNT=30）
- ⚠️ ランダム遅延を設定（人間らしい動作）
- ⚠️ 過度な自動化はアカウント制限の可能性あり

### 運用上の注意
- 📌 送信前にスコアリング結果を確認（手動チェックも併用推奨）
- 📌 接続申請時、メッセージは送信できません（LinkedIn仕様）
- 📌 返信率をモニタリング（低い場合はアプローチ見直し）

---

## 🐛 トラブルシューティング

詳細は [TROUBLESHOOTING_GUIDE.md](./TROUBLESHOOTING_GUIDE.md) を参照してください。

### よくある問題

#### 1. 「OPENAI_API_KEYが設定されていません」エラー

**原因:** `.env` ファイルがない、またはAPIキーが正しくない

**解決策:**
```bash
# .envファイルを確認
cat .env

# APIキーが正しいか確認（sk-proj-で始まる）
```

#### 2. 「つながりを申請」ボタンが検出できない

**原因:** LinkedInのUI変更、または既接続

**解決策:**
- `data/logs.csv` を確認して詳細を確認
- デバッグ用スクリーンショットを確認 (`debug_output/`)

#### 3. スコアリングが遅い

**原因:** OpenAI APIのレート制限

**解決策:**
- `gpt-4o-mini` を使用（より高速）
- 候補者数を減らす（検索ページ数を減らす）

---

## 📝 変更履歴

### 2025-10-26
- ✅ スコアリング基準の更新
  - 最低スコア: 70点 → 60点
  - 除外条件に経営層を追加（社長、CEO、CIO等）
  - 送信数上限を30件に設定（60点以上全員、最大30件）
- ✅ Cookie保存で自動ログイン機能を追加
- ✅ ページネーションボタン誤検出を修正（「1次」フィルター問題）
- ✅ 候補者抽出セレクターをLinkedIn新DOM構造に対応

### 2025-10-25
- ✅ 完全自動化システムを実装
  - 候補者検索スクリプト（柔軟な条件設定）
  - OpenAI APIによるAIスコアリング（年齢推定を含む）
  - ワンコマンド実行スクリプト
- ✅ 古い不要なファイルを削除
- ✅ 「つながりを申請」ボタン検出の誤検知を修正

### 2025-10-24
- ✅ 改善版スクリプト作成（複数検出戦略）
- ✅ デバッグツール作成
- ✅ トラブルシューティングガイド作成
- ✅ README.md・requirements.txt 整備

### 2025-10-14
- ✅ 自動ログイン廃止 → 手動ログイン化
- ✅ ボタン検出ロジック改善（Shadow DOM対応）
- ✅ Streamlit UI実装

### 2025-10-06
- ✅ 初期実装（候補者検索・スコアリング・送信）

---

## 🤝 コントリビューション

このプロジェクトは内部利用を想定していますが、改善提案は歓迎します。

---

## 📄 ライセンス

内部利用のため非公開

---

## 📞 サポート

問題が解決しない場合は、以下の情報を添えてご連絡ください:
- `debug_output/` フォルダ内のファイル
- `data/logs.csv` の内容
- エラーメッセージの全文
- 実行環境（OS、Pythonバージョン）
