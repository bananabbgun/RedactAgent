"""Record verification commands in a real JupyterLab terminal on the B70 host (headless Chromium, Playwright).

Shows the hardware (2x Arc Pro B70 via xpu-smi), the two vLLM servers, and a live end-to-end evaluation on the
held-out corpus. Produces terminal_raw.webm + terminal_marks.json for scripts/make_video.py.

    python scripts/record_terminal.py --lab https://127.0.0.1:8888/9/lab --out ~/ra_video
"""

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

STEPS = [  # (mark, command, seconds to wait after the prompt returns / max seconds)
    ("hw", "hostname; lscpu | grep -E 'Model name|^CPU\\(s\\)'; free -g | head -n 2", 4),
    ("gpus", "xpu-smi discovery | grep -E 'Device ID|Device Name|Memory Physical Size|PCI BDF'", 6),
    ("servers", "docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}'; curl -s 127.0.0.1:8000/v1/models | "
                "python3 -c \"import json,sys; print('card 0 serves:', json.load(sys.stdin)['data'][0]['root'])\"; "
                "curl -s 127.0.0.1:8001/v1/models | python3 -c \"import json,sys; print('card 1 serves:', "
                "json.load(sys.stdin)['data'][0]['root'])\"", 5),
    ("eval", "cd ~/RedactAgent && source deploy/b70/env.sh && rm -rf /tmp/v3_live && "
             "python eval/evaluate.py --workers 8 --data data/synthetic_v3 --out /tmp/v3_live --label '2x Arc Pro B70'", 6),
    ("power", "xpu-smi stats -d 0 | grep -E 'Power|Memory Used|Temperature' | head -n 6; "
              "xpu-smi stats -d 1 | grep -E 'Power|Memory Used|Temperature' | head -n 6", 6),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", default="https://127.0.0.1:8888/9/lab")
    ap.add_argument("--out", default=str(Path.home() / "ra_video"))
    ap.add_argument("--font", type=int, default=17)
    ap.add_argument("--steps", default=",".join(s[0] for s in STEPS), help="subset of steps, e.g. hw,gpus")
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    W, H = 1600, 900
    base = a.lab.rsplit("/lab", 1)[0]
    marks, t0 = [], None
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, ignore_https_errors=True,
                            record_video_dir=str(out / "_term"), record_video_size={"width": W, "height": H})
        page = ctx.new_page()
        # larger terminal font for a readable video (JupyterLab settings API)
        page.request.put(f"{base}/lab/api/settings/@jupyterlab/terminal-extension:plugin",
                         data=json.dumps({"raw": json.dumps({"fontSize": a.font, "theme": "light"})}),
                         headers={"Content-Type": "application/json"})
        # a separate, reset workspace so the user's own JupyterLab layout is untouched and the launcher is shown
        page.goto(f"{base}/lab/workspaces/ra-rec?reset", wait_until="domcontentloaded")
        try:
            page.wait_for_selector(".jp-LauncherCard", timeout=120000)
        except Exception:
            page.screenshot(path=str(out / "debug_launcher.png"))
            raise
        page.locator(".jp-LauncherCard[data-category='Other'][title*='erminal'], .jp-LauncherCard:has-text('Terminal')").first.click()
        page.wait_for_selector(".jp-Terminal .xterm-screen", timeout=60000)
        # collapse the file browser so the terminal fills the frame
        page.keyboard.press("Control+b")
        page.wait_for_timeout(1500)
        page.locator(".jp-Terminal").first.click()
        t0 = time.perf_counter()

        def mark(label):
            marks.append({"label": label, "t": round(time.perf_counter() - t0, 2)})
            print(f"{marks[-1]['t']:7.2f}s  {label}", flush=True)

        # The terminal is drawn on a canvas, so completion is detected from the host side: the shell rewrites a
        # small file every time its prompt returns (set up before the first `clear`, so it is not in the video).
        flag = Path(f"/tmp/ra_prompt_{int(time.time())}")
        page.keyboard.type(f"PROMPT_COMMAND='date +%s.%N > {flag}'", delay=5); page.keyboard.press("Enter")
        page.wait_for_timeout(800)
        page.keyboard.type("clear", delay=20); page.keyboard.press("Enter")
        page.wait_for_timeout(1200)

        def wait_prompt(since: float, limit: float):
            deadline = time.time() + limit
            while time.time() < deadline:
                if flag.exists() and float(flag.read_text().strip() or 0) > since:
                    return True
                page.wait_for_timeout(300)
            return False

        for label, cmd, after in [s for s in STEPS if s[0] in a.steps.split(",")]:
            mark(label)
            page.keyboard.type(cmd, delay=18)
            sent = time.time()
            page.keyboard.press("Enter")
            if not wait_prompt(sent, 900 if label == "eval" else 90):
                print(f"warning: no prompt after {label}", flush=True)
            mark(label + "_done")
            page.wait_for_timeout(after * 1000)
            if label in ("servers", "eval"):
                page.keyboard.type("clear", delay=20); page.keyboard.press("Enter")
                page.wait_for_timeout(600)
        page.screenshot(path=str(out / "terminal_last.png"))
        mark("end")
        video = page.video
        ctx.close()
        b.close()
        dst = out / "terminal_raw.webm"
        Path(video.path()).replace(dst)
    (out / "terminal_marks.json").write_text(json.dumps(marks, indent=1))
    print("saved", dst)


if __name__ == "__main__":
    main()
