# aiagent/message_generator.py
import os
from openai import OpenAI

# OpenAI APIクライアント初期化
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_message(name: str, role: str = "", company: str = "", custom_context: str = "") -> str:
    """
    ChatGPTを使って50文字以内のフォーマルなLinkedIn初回メッセージを生成する。
    - name: 相手の名前（必須）
    - role: 職種や肩書き（任意）
    - company: 所属企業名（任意）
    - custom_context: 特別な文脈がある場合（任意）
    """

    # メッセージテンプレートをChatGPTに指示
    prompt = f"""
    以下の条件に沿って日本語のLinkedIn初回メッセージを1文生成してください。

    条件:
    - 50文字以内
    - フォーマルで丁寧な印象
    - 「はじめまして。」で始める
    - コンサルティング業界の経験・関心を伝える
    - 相手の名前({name})を自然に含める
    - 不要な挨拶や署名は省く
    - トーンは柔らかく、勧誘色を出さない

    参考情報:
    - 職種: {role if role else '不明'}
    - 会社: {company if company else '不明'}
    - 補足: {custom_context if custom_context else '特になし'}

    出力は本文のみで返してください。
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        message = response.choices[0].message.content.strip()

        # 50文字超過時の安全対策（ChatGPTが稀に超えるため）
        if len(message) > 50:
            message = message[:49] + "。"

        print(f"✨ 生成メッセージ: {message}")
        return message

    except Exception as e:
        print(f"❌ メッセージ生成エラー: {e}")
        return "メッセージ生成に失敗しました。"


# --- スクリプトとして直接実行された場合 ---
if __name__ == "__main__":
    # テスト用呼び出し
    msg = generate_message(
        name="田中太郎",
        role="ITコンサルタント",
        company="KPMGコンサルティング",
        custom_context="デジタル戦略案件のご経験に興味があります。"
    )
    print("\n出力メッセージ:", msg)
