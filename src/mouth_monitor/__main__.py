from __future__ import annotations

import os
import threading
import time
import webbrowser

import uvicorn


def _open_browser(url: str) -> None:
    time.sleep(1.0)
    webbrowser.open(url)


def main() -> None:
    host = "127.0.0.1"
    port = int(os.environ.get("MOUTH_MONITOR_PORT", "8765"))
    url = f"http://{host}:{port}"
    if os.environ.get("MOUTH_MONITOR_NO_BROWSER") != "1":
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    uvicorn.run("mouth_monitor.app:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
