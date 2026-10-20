"""Screenshot the web app at an exact viewport through Edge/Chrome's DevTools protocol.

Headless --screenshot can't emulate phones (Edge's window is never narrower than ~500 px) and
doesn't wait for data. This drives the browser directly: exact device metrics, light/dark,
and it waits until a CSS selector exists.

    uv run --with websocket-client --no-project python scripts/capture.py \
        --url http://localhost:5173/ --out .impeccable/review/mobile.png --width 375 --height 812 \
        --scale 2 --mobile --wait-for .stats
"""

import argparse
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--scale", type=float, default=1)
    p.add_argument("--mobile", action="store_true")
    p.add_argument("--scheme", choices=["light", "dark"])
    p.add_argument("--wait-for", default="body", help="CSS selector that must exist first")
    p.add_argument("--settle", type=float, default=1.5, help="seconds after the selector appears")
    p.add_argument("--browser", default=EDGE)
    a = p.parse_args()

    profile = Path(tempfile.mkdtemp(prefix="cartograph-capture-"))
    # Port 0: the browser picks a free port and writes it to DevToolsActivePort in the profile.
    proc = subprocess.Popen([a.browser, "--headless=new", "--remote-debugging-port=0",
                             f"--user-data-dir={profile}", "--hide-scrollbars", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):  # wait for the DevTools endpoint
            try:
                port = (profile / "DevToolsActivePort").read_text().split()[0]
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                page = next(t for t in tabs if t["type"] == "page")
                break
            except (OSError, StopIteration, IndexError):
                time.sleep(0.2)
        else:
            raise SystemExit("browser did not start")
        # No Origin header: the browser rejects origins it wasn't told to trust.
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60,
                                         suppress_origin=True)
        ids = iter(range(1, 10_000))

        def send(method: str, **params):
            mid = next(ids)
            ws.send(json.dumps({"id": mid, "method": method, "params": params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == mid:
                    if "error" in msg:
                        raise RuntimeError(f"{method}: {msg['error']}")
                    return msg.get("result", {})

        send("Emulation.setDeviceMetricsOverride", width=a.width, height=a.height,
             deviceScaleFactor=a.scale, mobile=a.mobile)
        if a.scheme:
            send("Emulation.setEmulatedMedia",
                 features=[{"name": "prefers-color-scheme", "value": a.scheme}])
        send("Page.enable")
        send("Page.navigate", url=a.url)
        deadline = time.time() + 60
        while time.time() < deadline:
            found = send("Runtime.evaluate", expression=f"!!document.querySelector({a.wait_for!r})",
                         returnByValue=True)["result"].get("value")
            if found:
                break
            time.sleep(0.25)
        else:
            raise SystemExit(f"{a.wait_for} never appeared at {a.url}")
        time.sleep(a.settle)  # let the map lay out and the camera finish moving
        shot = send("Page.captureScreenshot", format="png")
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_bytes(base64.b64decode(shot["data"]))
        print(f"{a.out} ({a.width}x{a.height} @{a.scale}x)")
        ws.close()
    finally:
        # The browser spawns helper processes; end the whole tree so the next run starts clean.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, check=False)


if __name__ == "__main__":
    main()
