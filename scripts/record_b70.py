"""Record the final demo on the Arc Pro B70 host itself (headless Chromium via Playwright).

Produces one continuous .webm plus marks.json (label -> seconds) used by make_video to cut out
waiting and place narration. Run on the B70 host while `deploy/b70/up.sh` serves the app:

    python scripts/record_b70.py --url http://127.0.0.1:8080/ --out ~/ra_video
"""

import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CURSOR_JS = """
(() => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;z-index:99999;width:22px;height:22px;border-radius:50%;pointer-events:none;'
    + 'background:rgba(59,91,219,.35);border:2px solid #1f3a8a;transform:translate(-50%,-50%);left:-50px;top:-50px;';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(c));
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
})();
"""


class Rec:
    def __init__(self, page):
        self.page, self.t0, self.marks = page, time.perf_counter(), []

    def mark(self, label):
        self.marks.append({"label": label, "t": round(time.perf_counter() - self.t0, 2)})
        print(f"{self.marks[-1]['t']:7.2f}s  {label}", flush=True)

    def move(self, sel, steps=25):
        box = self.page.locator(sel).first.bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)

    def click(self, sel, pause=600):
        self.move(sel)
        self.page.wait_for_timeout(250)
        self.page.locator(sel).first.click()
        self.page.wait_for_timeout(pause)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/")
    ap.add_argument("--out", default=str(Path.home() / "ra_video"))
    ap.add_argument("--batch", type=int, default=36)
    a = ap.parse_args()
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    W, H = 1600, 900
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(out), record_video_size={"width": W, "height": H})
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        r = Rec(page)
        base = a.url.rstrip("/")

        # 1) environment proof
        page.goto(base + "/system", wait_until="domcontentloaded")
        page.wait_for_selector("#gpus:not(:empty)", timeout=60000)
        page.mouse.move(W / 2, H / 2)
        r.mark("system")
        r.wait(9000)

        # 2) single document, research policy
        page.goto(base + "/", wait_until="domcontentloaded")
        page.wait_for_selector("#sample option", state="attached", timeout=60000)
        r.mark("review")
        r.wait(1200)
        r.move("#sample"); page.select_option("#sample", "01_discharge_summary_EN.jpg"); page.dispatch_event("#sample", "change"); r.wait(1000)
        r.move("#policy"); page.select_option("#policy", "research"); page.dispatch_event("#policy", "change"); r.wait(1500)
        r.click("#run", 600)
        r.mark("detect_start")
        page.wait_for_selector("#stats:not(.hidden)", timeout=600000)
        r.mark("detect_done")
        r.wait(2000)
        items = page.locator("#list .item")
        for i in range(min(4, items.count())):
            bb = items.nth(i).bounding_box()
            page.mouse.move(bb["x"] + 60, bb["y"] + bb["height"] / 2, steps=20)
            r.wait(1100)
        r.move(".risk") if page.locator(".risk").count() else None
        r.mark("risk")
        r.wait(3500)
        for pid in ("litigation", "public_release", "research"):
            r.move("#policy")
            r.mark(f"select_{pid}")
            page.select_option("#policy", pid); page.dispatch_event("#policy", "change")
            r.wait(3800)
        r.mark("export_click")
        r.click("#export", 600)
        page.wait_for_selector("#downloads:not(.hidden)", timeout=60000)
        r.move("#audit"); r.wait(3000)
        r.mark("exported")

        # 3) Traditional Chinese document
        r.move("#sample"); page.select_option("#sample", "02_medical_certificate_ZH.jpg"); page.dispatch_event("#sample", "change"); r.wait(800)
        r.move("#policy"); page.select_option("#policy", "strict"); page.dispatch_event("#policy", "change"); r.wait(800)
        r.click("#run", 600)
        r.mark("detect2_start")
        page.wait_for_selector("#stats:not(.hidden)", timeout=600000)
        r.mark("detect2_done")
        r.wait(4500)

        # 4) batch
        page.goto(base + "/batch", wait_until="domcontentloaded")
        page.wait_for_selector("#policy option", state="attached", timeout=60000)
        r.mark("batch")
        r.wait(1500)
        page.select_option("#demo", str(a.batch))
        r.click("#go", 400)
        r.mark("batch_start")
        page.wait_for_selector("#dl:not(.hidden)", timeout=1800000)
        r.mark("batch_done")
        r.move("#dl"); r.wait(4000)
        r.mark("end")
        video = page.video
        ctx.close()
        b.close()
        dst = out / "demo_b70_raw.webm"
        Path(video.path()).replace(dst)
    (out / "marks.json").write_text(json.dumps(r.marks, indent=1))
    print("saved", dst)


if __name__ == "__main__":
    main()
