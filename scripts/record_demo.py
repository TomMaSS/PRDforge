#!/usr/bin/env python3
"""Record a ~35s demo video of PRDforge Web UI.

Prerequisites:
    docker compose up -d
    pip install -r scripts/requirements.txt
    playwright install chromium

Usage:
    python scripts/record_demo.py

Output:
    demo.webm in the project root.

Convert to GIF (requires ffmpeg):
    ffmpeg -i demo.webm -vf \
      "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
      demo.gif
"""

import shutil
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8088"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "demo.webm"
WIDTH, HEIGHT = 1280, 720


def main():
    video_dir = tempfile.mkdtemp(prefix="prdforge-demo-")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=video_dir,
            record_video_size={"width": WIDTH, "height": HEIGHT},
        )
        page = context.new_page()

        # ── Scene 1: Landing (0-5s) ──────────────────────────────
        page.goto(BASE_URL)
        page.wait_for_selector("#sectionList .section-item", timeout=10_000)
        page.wait_for_timeout(2500)

        # ── Scene 2: Browse sections (5-12s) ─────────────────────
        page.locator(".section-item").filter(has_text="Overview").first.click()
        page.wait_for_selector(".section-title", timeout=5000)
        page.wait_for_timeout(2500)

        page.locator(".section-item").filter(has_text="Data Model").click()
        page.wait_for_selector(".section-title", timeout=5000)
        page.wait_for_timeout(2500)

        # ── Scene 3: Scroll content (12-16s) ─────────────────────
        page.evaluate(
            'document.querySelector(".main").scrollBy({top: 400, behavior: "smooth"})'
        )
        page.wait_for_timeout(1500)
        page.evaluate(
            'document.querySelector(".main").scrollBy({top: 300, behavior: "smooth"})'
        )
        page.wait_for_timeout(1500)

        # ── Scene 4: Dependency graph (16-23s) ───────────────────
        page.locator('.nav-icon[data-tab="deps"]').click()
        page.wait_for_timeout(4000)  # let force-directed graph settle
        # hover near center to trigger node highlight
        canvas = page.locator("canvas")
        if canvas.count():
            box = canvas.bounding_box()
            if box:
                page.mouse.move(
                    box["x"] + box["width"] * 0.45,
                    box["y"] + box["height"] * 0.4,
                )
        page.wait_for_timeout(2000)

        # ── Scene 5: Add a comment (23-30s) ──────────────────────
        page.locator('.nav-icon[data-tab="sections"]').click()
        page.wait_for_timeout(500)
        page.locator(".section-item").filter(has_text="API Specification").click()
        page.wait_for_selector(".section-title", timeout=5000)
        page.wait_for_timeout(1500)

        # Create comment via API (more reliable than simulating text selection)
        comment_resp = page.evaluate("""
            fetch('/api/projects/snaphabit/sections/api-spec/comments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    anchor_text: 'Rate limiting',
                    anchor_prefix: '**',
                    anchor_suffix: ':** 100 req/min',
                    body: 'Should we add per-endpoint rate limits?'
                })
            }).then(r => r.json())
        """)
        page.wait_for_timeout(800)
        # Reload section to show highlight + comment card
        page.evaluate("loadSection('api-spec')")
        page.wait_for_timeout(3000)

        # ── Scene 6: Theme toggle (30-34s) ───────────────────────
        page.locator("#themeBtn").click()
        page.wait_for_timeout(2000)
        page.locator("#themeBtn").click()
        page.wait_for_timeout(1500)

        # ── Scene 7: Final hold (34-36s) ─────────────────────────
        page.wait_for_timeout(1500)

        # ── Cleanup: delete the demo comment ─────────────────────
        if comment_resp and isinstance(comment_resp, dict) and "id" in comment_resp:
            cid = comment_resp["id"]
            page.evaluate(f"""
                fetch('/api/projects/snaphabit/sections/api-spec/comments/{cid}', {{
                    method: 'DELETE'
                }})
            """)

        # Finalize video
        video_path = page.video.path()
        context.close()
        browser.close()

    # Copy video to project root
    shutil.copy2(video_path, OUTPUT)
    # Clean up temp dir
    shutil.rmtree(video_dir, ignore_errors=True)

    print(f"Demo video saved to: {OUTPUT}")
    print()
    print("Convert to GIF with:")
    print(
        '  ffmpeg -i demo.webm -vf "fps=12,scale=960:-1:flags=lanczos,'
        'split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" demo.gif'
    )


if __name__ == "__main__":
    main()
