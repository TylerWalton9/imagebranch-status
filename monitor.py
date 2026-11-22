"""Check ImageBranch from a GitHub-hosted runner and notify Feishu on transitions."""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

TARGETS = {
    "Website": "https://imagebranch.com/",
    "API": "https://api.imagebranch.com/readyz",
}
STATE_FILE = Path("state.json")


def check(url):
    detail = "unavailable"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ImageBranch-Uptime/1.0"})
            with urllib.request.urlopen(req, timeout=20) as response:
                if not 200 <= response.status < 300:
                    detail = "HTTP " + str(response.status)
                elif url.endswith("/readyz") and json.load(response).get("status") != "ready":
                    detail = "readiness check failed"
                else:
                    return True, "HTTP " + str(response.status)
        except urllib.error.HTTPError as error:
            detail = "HTTP " + str(error.code)
        except (OSError, ValueError):
            detail = "network or response error"
        if attempt < 2:
            time.sleep(5)
    return False, detail


def notify(title, color, text):
    url = os.environ.get("FEISHU_ALERT_WEBHOOK", "")
    if not url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        raise RuntimeError("Feishu secret is missing or invalid")
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"template": color, "title": {"tag": "plain_text", "content": "ImageBranch · " + title}},
            "elements": [{"tag": "div", "text": {"tag": "plain_text", "content": text}}],
        },
    }
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.load(response)
            if not 200 <= response.status < 300 or data.get("code", data.get("errcode", 0)) != 0:
                raise RuntimeError("Feishu rejected the notification")
    except (OSError, ValueError):
        raise RuntimeError("Feishu delivery failed") from None


def run(test_notification=False):
    now = datetime.datetime.now(datetime.timezone.utc)
    stamp = now.isoformat()
    if test_notification:
        notify("外部监控测试", "blue", "GitHub Actions 外部监控平台测试通知。首页和 API 配置为每 5 分钟检查。")
        print("External platform test notification delivered")
        return
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    old = state.get("monitors", {})
    next_monitors = {}
    for name, url in TARGETS.items():
        up, detail = check(url)
        previous = old.get(name, {})
        last_notice = previous.get("notified_at", "")
        reminder = not up and (not last_notice or (now - datetime.datetime.fromisoformat(last_notice)).total_seconds() >= 3600)
        changed = previous.get("up") is not None and previous["up"] != up
        if changed or reminder:
            title = "外部监控已恢复" if up else "外部监控异常"
            notify(title, "green" if up else "red", f"{name}\n{url}\n{detail}\n检查时间 {stamp}")
            last_notice = stamp
        next_monitors[name] = {
            "up": up,
            "detail": detail,
            "changed_at": stamp if not previous or changed else previous["changed_at"],
            "notified_at": last_notice,
        }
        print(f"{name}: {'UP' if up else 'DOWN'} ({detail})")
    if not state:
        notify("外部监控已启用", "green", "已启用首页与 API 的独立外部监控。每 5 分钟检查，异常和恢复时通知。")
    # Hourly check-ins keep the repository active without a commit every five minutes.
    result = {"last_checked_hour_utc": now.strftime("%Y-%m-%dT%H:00:00Z"), "monitors": next_monitors}
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(STATE_FILE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-notification", action="store_true")
    args = parser.parse_args()
    try:
        run(args.test_notification)
    except Exception as error:
        # Never log exception text containing request credentials.
        print("Monitor failed: " + type(error).__name__, file=sys.stderr)
        sys.exit(1)
