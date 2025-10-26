# LinkedIn 自動化AIシステム

KPMG Consultingのリファラル採用を効率化するための、**完全自動化**LinkedInリクルートシステムです。

## 🎯 機能概要

### ✅ 実装済み機能

**新しいワークフロー（2025-10-26実装）**

1. **候補者自動検索 + 一括つながり申請**
   - キーワード、地域を柔軟に設定
   - 検索結果から全員に自動でつながり申請（最大50件、テスト時5件）
   - プロフィール遷移なしで高速処理

2. **つながりリスト取得**
   - 日付でフィルタリング（例：2025-10-24以降）
   - 新規つながりのみを抽出

3. **プロフィール詳細取得**
   - 各つながりのプロフィールページから詳細情報を取得
   - 職歴（会社名、役職、期間）
   - 学歴（卒業年）
   - スキル

4. **AIスコアリング（OpenAI API）**
   - 年齢評価：25-30歳（25点）、31-35歳（20点）、36-40歳（15点）、41歳以上除外
   - IT業界経験：0-40点（SIer、エンジニア、コンサル等）
   - ポジション評価：-30〜+20点
   - 除外条件：経営層（社長、CEO、取締役等）、HR職種（リクルーター、採用担当等）
   - 60点以上を送信対象に抽出（最大50件、テスト時2件）

5. **AI自動メッセージ生成 + 送信**
   - OpenAI APIでメッセージを生成（軽微なバリエーション）
   - LinkedInメッセージ機能で自動送信
   - 送信結果をCSVに記録

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

### 🎯 新しいワークフロー（推奨）

**ステップ1: 候補者検索 + つながり申請**

```bash
source venv/bin/activate
python3 aiagent/linkedin_send_connections.py
```

検索キーワード、地域を指定し、検索結果の全員につながり申請を送信します。
- **テスト時**: 1ページ、最大5件
- **本番時**: 5ページ、最大50件（コード内のMAX_PAGES, MAX_REQUESTSを変更）

**出力:** `data/connection_logs.csv`

---

**ステップ2: つながりリスト取得**

```bash
python3 aiagent/linkedin_get_connections.py
```

対話式で日付を入力し、その日以降の新規つながりを取得します。

**出力:** `data/new_connections.csv`

---

**ステップ3: プロフィール詳細取得**

```bash
python3 aiagent/linkedin_get_profiles.py
```

新規つながりのプロフィールページから詳細情報（職歴、学歴、スキル）を取得します。

**出力:** `data/profile_details.csv`

---

**ステップ4: AIスコアリング**

```bash
python3 aiagent/linkedin_scorer_v2.py
```

**評価基準:**
- ✅ 年齢: 25-30歳（25点）、31-35歳（20点）、36-40歳（15点）
- ✅ IT業界経験: 0-40点（SIer、エンジニア、コンサル等）
- ✅ ポジション: -30〜+20点
- ❌ 41歳以上除外
- ❌ 経営層除外（社長、CEO、CIO、執行役員、取締役）
- ❌ HR職種除外（リクルーター、採用担当、ヘッドハンター等）

**出力:**
- `data/candidates_scored_v2.csv` - 全候補者のスコア
- `data/messages_v2.csv` - 送信対象（60点以上、最大50件）

---

**ステップ5: メッセージ生成 + 送信**

```bash
python3 aiagent/linkedin_send_messages.py
```

高スコア候補者にAI生成メッセージを送信します。
- **テスト時**: 最大2件
- **本番時**: 最大50件（コード内のMAX_MESSAGESを変更）

**出力:** `data/message_logs.csv`

---

## 📁 ディレクトリ構成

```
aitest_1013/
├── aiagent/
│   ├── linkedin_send_connections.py    # Step 1: つながり申請送信
│   ├── linkedin_get_connections.py     # Step 2: つながりリスト取得
│   ├── linkedin_get_profiles.py        # Step 3: プロフィール詳細取得
│   ├── linkedin_scorer_v2.py           # Step 4: AIスコアリング（詳細版）
│   ├── linkedin_send_messages.py       # Step 5-6: メッセージ生成+送信
│   ├── linkedin_search.py              # （旧）候補者検索
│   ├── linkedin_scorer.py              # （旧）AIスコアリング
│   └── linkedin_pipeline_improved.py   # （旧）接続リクエスト送信
├── data/
│   ├── connection_logs.csv             # つながり申請履歴
│   ├── new_connections.csv             # 新規つながりリスト
│   ├── profile_details.csv             # プロフィール詳細
│   ├── candidates_scored_v2.csv        # AIスコアリング結果
│   ├── messages_v2.csv                 # メッセージ送信対象リスト
│   ├── message_logs.csv                # メッセージ送信履歴
│   └── cookies.pkl                     # ログインCookie（自動生成）
├── debug_output/                       # デバッグファイル保存先
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

### 2025-10-26（新ワークフロー実装）
- ✅ **ワークフロー大幅変更**: 全員つながり申請 → プロフィール詳細取得 → AIスコアリング → メッセージ送信
- ✅ 新スクリプト作成
  - `linkedin_send_connections.py`: 検索結果から一括つながり申請
  - `linkedin_get_connections.py`: つながりリスト取得（日付フィルタ）
  - `linkedin_get_profiles.py`: プロフィール詳細取得（職歴・学歴・スキル）
  - `linkedin_scorer_v2.py`: 詳細プロフィール版AIスコアリング
  - `linkedin_send_messages.py`: AI自動メッセージ生成+送信
- ✅ スコアリング基準の更新
  - 年齢評価を細分化（25-30歳: 25点、31-35歳: 20点、36-40歳: 15点）
  - 41歳以上を厳格に除外
  - HR・人材関係職種を除外（リクルーター、採用担当等）
  - 経営層除外を強化
- ✅ テスト用制限を追加（つながり申請5件、メッセージ送信2件）

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
