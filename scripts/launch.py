"""Local launcher; uses only the bundled interpreter and standard library initially."""
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import threading
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
URL = "http://localhost:8001"


def running_app():
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                URL + "/api/v1/health", timeout=1) as response:
            return json.load(response).get("application") == "personal-chef"
    except (OSError, ValueError):
        return False


def port_available():
    try:
        with socket.socket() as probe:
            if os.name == "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            probe.bind(("127.0.0.1", 8001))
        return True
    except OSError:
        return False


def open_when_ready(stop):
    for _ in range(120):
        if stop.is_set():
            return
        if running_app():
            print(f"服务已就绪，正在打开 {URL}；关闭此窗口或按 Ctrl+C 停止。", flush=True)
            webbrowser.open(URL)
            return
        stop.wait(0.5)
    print(f"自动打开超时，请查看启动日志，或手动访问 {URL}。", flush=True)


def main():
    os.environ["PERSONAL_CHEF_HOME"] = str(ROOT)
    # The source checkout is app/ itself; the distribution contains an app/ child.
    sys.path.insert(0, str(ROOT if (ROOT / "app").is_dir() else ROOT.parent))
    if running_app():
        print(f"程序已经启动，打开 {URL}")
        webbrowser.open(URL)
        return 0
    if not port_available():
        print("端口 8001 已被其他程序占用。请先关闭该程序，再重新启动。")
        return 1
    env = ROOT / ".env"
    if not env.exists():
        shutil.copyfile(ROOT / ".env.example", env)
        print("已生成 .env，请用记事本打开，填写自己的密钥及模型名称后重新启动。")
    from app.common.config import missing_settings
    missing = missing_settings()
    if missing:
        print("配置尚未完成：" + "、".join(missing))
        print(f"请编辑 {env}；配置说明见 README.md。")
        return 1
    stop = threading.Event()
    try:
        import uvicorn
        from app.main import app
        threading.Thread(target=open_when_ready, args=(stop,), daemon=True).start()
        uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        import traceback
        print("启动失败。请检查配置，以下日志可用于排查（分享前请遮住密钥）。")
        traceback.print_exc()
        return 1
    finally:
        stop.set()


if __name__ == "__main__":
    sys.exit(main())
