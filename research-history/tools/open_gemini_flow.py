from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / ".browser-profiles" / "gemini-flow"
FLOW_URL = "https://labs.google/fx/tools/flow"


def main() -> None:
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(PROFILE),
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=False,
            viewport={"width": 1440, "height": 960},
            args=["--no-first-run"],
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=120000)
        print("Gemini Flow window is open. Sign in if requested.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            context.close()


if __name__ == "__main__":
    main()
