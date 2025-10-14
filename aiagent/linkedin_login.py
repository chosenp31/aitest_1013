# aiagent/linkedin_login.py

import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI

# ChatGPT API クライアント
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Cookie保存先
COOKIE_PATH = os.path.join(os.path.dirname(__file__), "../data/linkedin_cookies.json")

def analyze_login_page(html_source: str):
    """
    ChatGPTにHTML構造を渡し、
    手動ログインが必要か自動ログイン可能かを判定する
    """
    prompt = f"""
    次のHTMLはLinkedInのログインページのソースです。
    このページではユーザーの手動入力が必要ですか？
    それともCookieや自動ログインボタンで自動ログインが可能ですか？
    JSONで回答してください。
    {{ "manual_required": true or false }}
    HTML: {html_source[:8000]}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        answer = json.loads(response.choices[0].message.content)
        return answer.get("manual_required", True)
    except Exception as e:
        print("⚠️ ChatGPT解析失敗:", e)
        return True

def linkedin_login():
    """
    初回手動ログイン → Cookie保存
    2回目以降：Cookieによる自動ログイン
    """
    print("🔑 LinkedInログイン開始...")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    # Cookieが既にある場合、自動ログイン試行
    if os.path.exists(COOKIE_PATH):
        print("🍪 Cookieを読み込み中...")
        try:
            with open(COOKIE_PATH, "r") as f:
                cookies = json.load(f)
            for cookie in cookies:
                driver.add_cookie(cookie)
            driver.refresh()
            time.sleep(3)

            if "feed" in driver.current_url:
                print("✅ Cookieで自動ログイン成功")
                return driver
            else:
                print("⚠️ Cookieログイン失敗 → 手動ログインに切り替えます")
        except Exception as e:
            print("Cookie処理エラー:", e)

    # ページ解析（ChatGPTで自動/手動判定）
    html_source = driver.page_source
    manual_required = analyze_login_page(html_source)

    if manual_required:
        print("👋 手動ログインを待機中です。ブラウザで入力してください...")
        while "feed" not in driver.current_url:
            time.sleep(5)
        print("✅ 手動ログイン完了！Cookieを保存します。")
    else:
        print("🤖 ChatGPTが自動ログイン可能と判断 → 自動入力を試行")
        try:
            driver.find_element(By.ID, "username").send_keys(os.getenv("LINKEDIN_EMAIL"))
            driver.find_element(By.ID, "password").send_keys(os.getenv("LINKEDIN_PASSWORD"))
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(5)
        except Exception as e:
            print("自動ログインエラー:", e)

    # ログイン成功後Cookie保存
    if "feed" in driver.current_url:
        cookies = driver.get_cookies()
        os.makedirs(os.path.dirname(COOKIE_PATH), exist_ok=True)
        with open(COOKIE_PATH, "w") as f:
            json.dump(cookies, f, indent=2)
        print("💾 Cookieを保存しました。")
    else:
        print("❌ ログイン未完了：手動で確認してください。")

    return driver

# --- スクリプトとして直接実行された場合 ---
if __name__ == "__main__":
    linkedin_login()

