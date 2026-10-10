"""Record a scripted screen capture of the web app for the demo video.

Writes a .webm plus a JSON list of (label, seconds-from-start) marks that make_video.py
uses to cut out model waiting time and to place narration.

    python scripts/record_demo.py --out-dir ../deliverables/video_work
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
    + 'background:rgba(59,91,219,.35);border:2px solid #1f3a8a;transform:translate(-50%,-50%);left:-50px;top:-50px;transition:width .1s,height .1s';
  document.addEventListener('DOMContentLoaded', () => document.body.appendChild(c));
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', () => { c.style.width = '14px'; c.style.height = '14px'; }, true);
  document.addEventListener('mouseup', () => { c.style.width = '22px'; c.style.height = '22px'; }, true);
})();
"""


class Rec:
    def __init__(self, page):
        self.page, self.t0, self.marks = page, time.perf_counter(), []

    def mark(self, label):
        self.marks.append({"label": label, "t": round(time.perf_counter() - self.t0, 2)})
        print(f"{self.marks[-1]['t']:7.2f}s  {label}", flush=True)

    def move(self, selector, steps=25):
        box = self.page.locator(selector).first.bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=steps)
        return box

    def click(self, selector, pause=500):
        self.move(selector)
        self.page.wait_for_timeout(250)
        self.page.locator(selector).first.click()
        self.page.wait_for_timeout(pause)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/")
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    W, H = 1600, 900
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=str(out), record_video_size={"width": W, "height": H})
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        r = Rec(page)
        page.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#sample option", state="attached", timeout=60000)
        page.mouse.move(W / 2, H / 2)
        r.wait(1500)
        r.mark("start")

        # --- document 1: English discharge summary, research policy
        r.move("#sample"); page.select_option("#sample", "01_discharge_summary_EN.jpg"); r.wait(1200)
        r.move("#policy"); page.select_option("#policy", "research"); page.dispatch_event("#policy", "change"); r.wait(1800)
        r.mark("policy_research")
        r.click("#run", 800)
        r.mark("detect_start")
        page.wait_for_selector("#stats:not(.hidden)", timeout=900000)
        r.mark("detect_done")
        r.wait(2500)
        # hover a few findings in the list to show highlights + reasons
        items = page.locator("#list .item")
        for i in range(min(4, items.count())):
            box = items.nth(i).bounding_box()
            page.mouse.move(box["x"] + 60, box["y"] + box["height"] / 2, steps=20)
            r.wait(1300)
        # hover a box on the page to show its tooltip
        rects = page.locator("#overlay rect")
        if rects.count():
            box = rects.nth(min(2, rects.count() - 1)).bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
            r.wait(2600)
        r.mark("reviewed")
        # reject one finding (human in the loop) and re-accept it
        first = page.locator("#list .item input").first
        bb = first.bounding_box()
        page.mouse.move(bb["x"] + 6, bb["y"] + 6, steps=20); r.wait(300)
        r.mark("reject_click")
        first.click(); r.wait(2400)
        r.mark("rejected_one")
        page.locator("#list .item input").first.click(); r.wait(2200)
        # switch policies: same detections, different lawful output
        for pid in ("litigation", "public_release", "research"):
            r.move("#policy")
            r.mark(f"select_{pid}")
            page.select_option("#policy", pid); page.dispatch_event("#policy", "change")
            r.wait(4300)
            r.mark(f"policy_{pid}")
        # export + audit
        r.mark("export_click")
        r.click("#export", 600)
        page.wait_for_selector("#downloads:not(.hidden)", timeout=60000)
        r.wait(800)
        r.move("#downloads"); r.wait(2600)
        r.move("#audit"); r.wait(3000)
        r.mark("exported")

        # --- document 2: Chinese medical certificate with seals, strict policy
        r.move("#sample"); page.select_option("#sample", "02_medical_certificate_ZH.jpg"); page.dispatch_event("#sample", "change"); r.wait(1000)
        r.move("#policy"); page.select_option("#policy", "strict"); page.dispatch_event("#policy", "change"); r.wait(1000)
        r.click("#run", 800)
        r.mark("detect2_start")
        page.wait_for_selector("#stats:not(.hidden)", timeout=900000)
        r.mark("detect2_done")
        r.wait(2500)
        rects = page.locator("#overlay rect")
        for i in range(rects.count()):
            box = rects.nth(i).bounding_box()
            if box and box["width"] > 60 and box["height"] > 60:  # a seal
                page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
                r.wait(2200)
                break
        r.wait(2500)
        r.mark("end")
        video = page.video
        ctx.close()
        b.close()
        src = Path(video.path())
        dst = out / "demo_raw.webm"
        src.replace(dst)
    (out / "marks.json").write_text(json.dumps(r.marks, indent=1))
    print("saved", dst)


if __name__ == "__main__":
    main()
