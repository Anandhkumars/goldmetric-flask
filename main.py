import webview
import threading
import time
import requests
from app import app

def run_flask():
    app.run(host="127.0.0.1", port=5000, debug=False)

def wait_for_flask():
    while True:
        try:
            requests.get("http://127.0.0.1:5000/")
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    wait_for_flask()
    webview.create_window("GoldMetric - Desktop App", "http://127.0.0.1:5000/")
    webview.start()
