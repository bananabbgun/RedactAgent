"""Drive the running web app with Playwright (system Chrome) and save a screenshot for the deck.

    python -m redactagent.server &      # then:
    python scripts/capture_ui.py --sample 01_discharge_summary_EN.jpg --policy research
"""

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8080/")
    ap.add_argument("--sample", default="01_discharge_summary_EN.jpg")
    ap.add_argument("--policy", default="research")
    ap.add_argument("--out", default=str(ROOT / "deck" / "assets" / "ui.png"))
    a = ap.parse_args()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1600, "height": 940}, device_scale_factor=2)
        pg.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_selector("#sample option", state="attached", timeout=60000)
        pg.select_option("#sample", a.sample)
        pg.select_option("#policy", a.policy)
        pg.click("#run")
        pg.wait_for_selector("#stats:not(.hidden)", timeout=600000)
        pg.wait_for_timeout(2500)
        pg.click("#export")
        pg.wait_for_selector("#downloads:not(.hidden)", timeout=60000)
        pg.wait_for_timeout(1500)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=a.out)
        print("saved", a.out)
        b.close()


if __name__ == "__main__":
    main()
