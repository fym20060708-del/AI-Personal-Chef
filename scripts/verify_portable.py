"""Offline integration checks against the assembled portable interpreter."""
import json
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "dist" / "AI-私人厨师-Windows"
PYTHON = PACKAGE / "runtime" / "python.exe"


def main():
    assert PYTHON.is_file()
    assert not (PACKAGE / ".env").exists(), "Release must not contain credentials"
    assert not list((PACKAGE / "data").iterdir()), "Release must not contain chat data"
    spec = importlib.util.spec_from_file_location("portable_launcher", PACKAGE / "scripts" / "launch.py")
    launcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(launcher)
    with patch.object(launcher, "running_app", return_value=True), patch.object(launcher.webbrowser, "open") as browser:
        assert launcher.main() == 0
        browser.assert_called_once_with("http://localhost:8001")
    with patch.object(launcher, "running_app", return_value=False), patch.object(launcher, "port_available", return_value=False):
        assert launcher.main() == 1
    print("PASS: repeated launch and occupied-port handling")
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONHOME", "PYTHONPATH"}}
    # A fresh folder with spaces and Chinese characters tests location-independent launching.
    with tempfile.TemporaryDirectory(prefix="厨师 启动测试 ") as temporary:
        home = Path(temporary)
        (home / "scripts").mkdir()
        shutil.copy2(PACKAGE / "scripts" / "launch.py", home / "scripts" / "launch.py")
        shutil.copy2(PACKAGE / ".env.example", home / ".env.example")
        (home / "app" / "common").mkdir(parents=True)
        (home / "app" / "__init__.py").touch()
        (home / "app" / "common" / "__init__.py").touch()
        shutil.copy2(PACKAGE / "app" / "common" / "config.py", home / "app" / "common" / "config.py")
        result = subprocess.run([str(PYTHON), "-I", "-X", "utf8", str(home / "scripts" / "launch.py")],
                                cwd=temporary, env=env, capture_output=True, encoding="utf-8", timeout=30)
        assert result.returncode == 1, result.stdout + result.stderr
        assert "配置尚未完成" in result.stdout, result.stdout + result.stderr
        assert (home / ".env").exists()
        print("PASS: first-run configuration, Chinese/space path, isolated runtime")

        code = '''
import os, sys, socket
sys.path.insert(0, sys.argv[1])
os.environ['PERSONAL_CHEF_HOME'] = sys.argv[2]
for name in ['DASHSCOPE_API_KEY','TAVILY_API_KEY','OSS_ACCESS_KEY_ID','OSS_ACCESS_KEY_SECRET','OSS_BUCKET']:
    os.environ[name] = 'offline-test-placeholder'
os.environ['DASHSCOPE_BASE_URL'] = 'https://example.invalid/v1'
os.environ['DASHSCOPE_MODEL'] = 'offline-test-model'
os.environ['OSS_ENDPOINT'] = 'oss-cn-beijing.aliyuncs.com'
os.environ['OSS_REGION'] = 'cn-beijing'
# Remove the empty first-run file so the fake environment stays intact.
from pathlib import Path
Path(sys.argv[2], '.env').unlink()
import uvicorn
from app.main import app
sock = socket.socket()
sock.bind(('127.0.0.1', 0))
Path(sys.argv[2], 'port.txt').write_text(str(sock.getsockname()[1]))
uvicorn.Server(uvicorn.Config(app, log_level='info')).run(sockets=[sock])
'''
        with (home / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([str(PYTHON), "-I", "-X", "utf8", "-c", code,
                                        str(PACKAGE), temporary], cwd=temporary, env=env,
                                       stdout=log, stderr=log)
            try:
                last_error = "port file not created"
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                for _ in range(40):
                    if process.poll() is not None:
                        raise AssertionError((home / "server.log").read_text(encoding="utf-8"))
                    if (home / "port.txt").exists():
                        url = "http://127.0.0.1:" + (home / "port.txt").read_text()
                        try:
                            with opener.open(url + "/api/v1/health", timeout=1) as response:
                                assert json.load(response)["application"] == "personal-chef"
                            break
                        except OSError as error:
                            last_error = repr(error)
                    time.sleep(0.5)
                else:
                    raise AssertionError("Server startup timed out: " + last_error + "\n" + (home / "server.log").read_text(encoding="utf-8"))
                with opener.open(url + "/", timeout=3) as response:
                    assert "AI 私人厨师" in response.read().decode()
                with opener.open(url + "/api/v1/chat/messages?thread_id=offline-check", timeout=3) as response:
                    assert json.load(response) == {"messages": []}
                request = urllib.request.Request(url + "/api/v1/chat/messages?thread_id=offline-check", method="DELETE")
                with opener.open(request, timeout=3) as response:
                    assert json.load(response) == {"success": True}
                assert (home / "data" / "personal_chief.db").exists()
                print("PASS: portable backend, health, frontend, empty history, clear history, data path")
            finally:
                process.terminate()
                process.wait(timeout=10)
    print("No remote AI calls were made. Release remains free of user configuration and data.")


if __name__ == "__main__":
    main()
