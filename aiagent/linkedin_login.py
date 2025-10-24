# aiagent/linkedin_login.py
# ✅ 完全手動ログイン専用版（CookieもChatGPTも一切使用しない）

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


def linkedin_login():
    """
    手動ログイン専用。Chromeを開いてLinkedInにアクセスするだけ。
    Cookieも保存・読み込みしない。
    """
    print("🔑 LinkedIn手動ログインモード開始...")
    print("🌐 ブラウザが開いたら、自分でLinkedInにログインしてください。")
    print("✅ ログイン後、このウィンドウはそのまま開いたままでOKです。")

    # Chrome起動設定
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("detach", True)  # ブラウザを閉じない

    # ChromeDriver起動
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # ログインページを開く
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)

    print("👋 ログインが完了したら、そのまま別モジュール（例: linkedin_sender.py）を実行してください。")
    return driver


if __name__ == "__main__":
    linkedin_login()
