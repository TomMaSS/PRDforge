#!/usr/bin/env python3
"""Record a ~45s demo video of PRDforge Web UI.

Prerequisites:
    docker compose up -d
    pip install -r scripts/requirements.txt
    playwright install chromium

Usage:
    python scripts/record_demo.py

    # With custom credentials
    DEMO_EMAIL=admin@example.com DEMO_PASSWORD=secret python scripts/record_demo.py

Output:
    demo.webm in the project root.

Convert to GIF (requires ffmpeg):
    ffmpeg -i demo.webm -vf \
      "fps=12,scale=960:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" \
      demo.gif
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("DEMO_BASE_URL", "http://localhost:3000")
DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@prdforge.local")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "prdforge-demo")
DEMO_NAME = "Demo User"
DEMO_PROJECT_SLUG = "prdforge-demo"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "demo.webm"
WIDTH, HEIGHT = 1440, 900


def bootstrap_user(page):
    """Ensure demo user exists via /api/auth/setup (idempotent)."""
    result = page.evaluate(f"""
        fetch('/api/auth/setup', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                name: '{DEMO_NAME}',
                email: '{DEMO_EMAIL}',
                password: '{DEMO_PASSWORD}'
            }})
        }}).then(r => ({{ status: r.status, ok: r.ok }}))
    """)
    status = result.get("status", 0)
    if status not in (200, 409):
        print(f"ERROR: /api/auth/setup returned {status}. Stack may not be running.")
        sys.exit(1)
    print(f"Bootstrap: status={status} ({'created' if status == 200 else 'already exists'})")


def sign_in(page):
    """Sign in via the UI form."""
    page.goto(f"{BASE_URL}/signin")
    page.fill("#email", DEMO_EMAIL)
    page.fill("#password", DEMO_PASSWORD)
    page.click('button[type="submit"]')

    # Wait for redirect to /projects
    page.wait_for_url("**/projects", timeout=10_000)
    print("Signed in successfully")


def ensure_demo_project(page):
    """Create demo project with saas-mvp template (ignore if slug exists)."""
    result = page.evaluate(f"""
        fetch('/api/projects', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{
                name: 'PRDforge Demo',
                slug: '{DEMO_PROJECT_SLUG}',
                description: 'Demo SaaS MVP project',
                template_id: 'saas-mvp'
            }})
        }}).then(r => ({{ status: r.status, ok: r.ok }}))
    """)
    status = result.get("status", 0)
    if status in (200, 201, 409):
        print(f"Demo project: status={status}")
    else:
        print(f"WARNING: create project returned {status}")


def main():
    video_dir = tempfile.mkdtemp(prefix="prdforge-demo-")
    demo_comment_id = None

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=video_dir,
            record_video_size={"width": WIDTH, "height": HEIGHT},
        )
        page = context.new_page()

        # ── Setup ──────────────────────────────────────────────────
        page.goto(BASE_URL)
        page.wait_for_timeout(1000)
        bootstrap_user(page)

        # ── Scene 1: Sign in (0-4s) ───────────────────────────────
        sign_in(page)
        page.wait_for_timeout(1500)

        ensure_demo_project(page)
        page.wait_for_timeout(500)

        # ── Scene 2: Projects list → click demo project (4-7s) ───
        page.reload()
        page.wait_for_timeout(1500)

        # Click the demo project card
        card = page.locator("text=PRDforge Demo").first
        if card.is_visible():
            card.click()
        else:
            page.goto(f"{BASE_URL}/projects/{DEMO_PROJECT_SLUG}")
        page.wait_for_timeout(2000)

        # ── Scene 3: Browse sections (7-16s) ──────────────────────
        sidebar_buttons = page.locator("nav button")

        # Click through sidebar sections
        for section_text in ["Tech Stack", "Data Model", "API Design"]:
            btn = sidebar_buttons.filter(has_text=section_text).first
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(2000)

        # ── Scene 4: Select text → comment form (16-22s) ──────────
        # Create a comment via API for demo purposes
        demo_comment_id = page.evaluate(f"""
            fetch('/api/projects/{DEMO_PROJECT_SLUG}/sections/api-design/comments', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    anchor_text: 'POST /api/auth/login',
                    anchor_prefix: '### `',
                    anchor_suffix: '`',
                    body: 'Should we add rate limiting to the login endpoint?'
                }})
            }}).then(r => r.json()).then(d => d.id || null).catch(() => null)
        """)
        page.wait_for_timeout(500)

        # Reload section to show comment
        btn = sidebar_buttons.filter(has_text="API Design").first
        if btn.is_visible():
            btn.click()
        page.wait_for_timeout(2500)

        # ── Scene 5: Dependencies tab (22-28s) ────────────────────
        deps_tab = page.locator('[value="deps"]').first
        if deps_tab.is_visible():
            deps_tab.click()
            page.wait_for_timeout(4000)

        # ── Scene 6: Stats tab (28-33s) ───────────────────────────
        stats_tab = page.locator('[value="stats"]').first
        if stats_tab.is_visible():
            stats_tab.click()
            page.wait_for_timeout(3000)

        # Back to sections
        sections_tab = page.locator('[value="sections"]').first
        if sections_tab.is_visible():
            sections_tab.click()
        page.wait_for_timeout(1000)

        # ── Scene 7: Chat panel (33-39s) ──────────────────────────
        chat_tab = page.locator('[value="chat"]').first
        if chat_tab.is_visible():
            chat_tab.click()
            page.wait_for_timeout(1500)

            # Type a message (don't send — just show the composer)
            chat_input = page.locator('textarea[placeholder]').first
            if chat_input.is_visible():
                chat_input.fill("What sections need the most attention?")
                page.wait_for_timeout(2000)
                chat_input.fill("")

            # Back to sections
            if sections_tab.is_visible():
                sections_tab.click()
            page.wait_for_timeout(1000)

        # ── Scene 8: Theme toggle (39-43s) ────────────────────────
        theme_btn = page.locator('button[aria-label="Toggle theme"]').first
        if theme_btn.is_visible():
            theme_btn.click()
            page.wait_for_timeout(2000)
            theme_btn.click()
            page.wait_for_timeout(1500)

        # ── Scene 9: Final hold (43-46s) ──────────────────────────
        page.wait_for_timeout(2000)

        # ── Cleanup: delete demo comment ───────────────────────────
        if demo_comment_id:
            page.evaluate(f"""
                fetch('/api/projects/{DEMO_PROJECT_SLUG}/sections/api-design/comments/{demo_comment_id}', {{
                    method: 'DELETE'
                }})
            """)

        # Finalize video
        video_path = page.video.path()
        context.close()
        browser.close()

    # Copy video to project root
    shutil.copy2(video_path, OUTPUT)
    shutil.rmtree(video_dir, ignore_errors=True)

    print(f"\nDemo video saved to: {OUTPUT}")
    print()
    print("Convert to GIF with:")
    print(
        '  ffmpeg -i demo.webm -vf "fps=12,scale=960:-1:flags=lanczos,'
        'split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" demo.gif'
    )


if __name__ == "__main__":
    main()
