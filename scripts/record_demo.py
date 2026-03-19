#!/usr/bin/env python3
"""Record a ~30s demo video of PRDforge Web UI.

Prerequisites:
    docker compose up -d
    pip install -r scripts/requirements.txt
    playwright install chromium

Usage:
    python scripts/record_demo.py

Output:
    demo.webm in the project root.

Convert to GIF (requires ffmpeg):
    ffmpeg -y -i demo.webm -vf \
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


def api(page, method, path, body=None):
    """Browser-context fetch helper (inherits session cookie)."""
    js_body = f", body: '{body}'" if body else ""
    return page.evaluate(f"""
        fetch('{path}', {{
            method: '{method}',
            headers: {{'Content-Type': 'application/json'}}
            {js_body}
        }}).then(r => r.json().then(d => ({{status: r.status, ...d}})).catch(() => ({{status: r.status}})))
    """)


def bootstrap_user(page):
    r = api(page, "POST", "/api/auth/setup",
            f'{{"name":"{DEMO_NAME}","email":"{DEMO_EMAIL}","password":"{DEMO_PASSWORD}"}}')
    status = r.get("status", 0)
    if status not in (200, 409):
        print(f"ERROR: /api/auth/setup returned {status}. Stack may not be running.")
        sys.exit(1)
    print(f"Bootstrap: {'created' if status == 200 else 'exists'}")


def sign_in(page):
    page.goto(f"{BASE_URL}/signin")
    page.wait_for_timeout(400)
    page.fill("#email", DEMO_EMAIL, timeout=3000)
    page.fill("#password", DEMO_PASSWORD)
    page.wait_for_timeout(200)
    page.click('button[type="submit"]')
    page.wait_for_url("**/projects", timeout=10_000)
    print("Signed in")


def ensure_demo_project(page):
    r = api(page, "POST", "/api/projects",
            f'{{"name":"PRDforge Demo","slug":"{DEMO_PROJECT_SLUG}",'
            '"description":"SaaS MVP requirements — AI-assisted editing","template_id":"saas-mvp"}')
    print(f"Project: status={r.get('status')}")


def seed_comments(page):
    comments = [
        ("overview", "Describe the product vision",
         "product vision and the problem",
         "We should tighten the vision statement — needs a one-liner elevator pitch."),
        ("tech-stack", "Describe the high-level system",
         "high-level system architecture",
         "Should we commit to a monorepo or separate frontend/backend repos from day one?"),
        ("api-design", "POST /api/auth/login",
         "### Authentication",
         "Rate limiting on login? 5 attempts per minute per IP seems reasonable."),
    ]
    ids = []
    for slug, anchor, prefix, body in comments:
        r = api(page, "POST",
                f"/api/projects/{DEMO_PROJECT_SLUG}/sections/{slug}/comments",
                f'{{"anchor_text":"{anchor}","anchor_prefix":"{prefix}","body":"{body}"}}')
        cid = r.get("id")
        if cid:
            ids.append((slug, cid))
    print(f"Seeded {len(ids)} comments")
    return ids


def cleanup_comments(page, comment_ids):
    for slug, cid in comment_ids:
        api(page, "DELETE",
            f"/api/projects/{DEMO_PROJECT_SLUG}/sections/{slug}/comments/{cid}")


def click_sidebar(page, text):
    btn = page.locator("nav button").filter(has_text=text).first
    if btn.is_visible(timeout=2000):
        btn.click()
        return True
    return False


def click_tab(page, value):
    tab = page.locator(f'[value="{value}"]').first
    if tab.is_visible(timeout=2000):
        tab.click()
        return True
    return False


def main():
    video_dir = tempfile.mkdtemp(prefix="prdforge-demo-")
    comment_ids = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=video_dir,
            record_video_size={"width": WIDTH, "height": HEIGHT},
        )
        page = context.new_page()

        # ── Pre-recording setup ──────────────────────────────────────
        page.goto(BASE_URL)
        page.wait_for_timeout(500)
        bootstrap_user(page)

        # ── Sign in fast ─────────────────────────────────────────────
        sign_in(page)
        page.wait_for_timeout(300)

        # Create project after sign-in (needs auth cookie)
        ensure_demo_project(page)

        # ── Projects list (brief) ────────────────────────────────────
        page.goto(f"{BASE_URL}/projects")
        page.wait_for_timeout(1200)

        # Enter demo project
        card = page.locator("text=PRDforge Demo").first
        if card.is_visible(timeout=3000):
            card.click()
        else:
            page.goto(f"{BASE_URL}/projects/{DEMO_PROJECT_SLUG}")
        page.wait_for_timeout(1500)

        # Seed comments
        comment_ids = seed_comments(page)

        # ── Switch to light mode immediately ─────────────────────────
        theme_btn = page.locator('button[aria-label="Toggle theme"]').first
        if theme_btn.is_visible(timeout=1500):
            theme_btn.click()
        page.wait_for_timeout(800)

        # ── Browse a couple of sections ──────────────────────────────
        # Product Overview is auto-selected, pause briefly
        page.wait_for_timeout(1200)

        click_sidebar(page, "Tech Stack")
        page.wait_for_timeout(1500)

        click_sidebar(page, "Data Model")
        page.wait_for_timeout(1500)

        # ── Comments tab ─────────────────────────────────────────────
        click_tab(page, "comments")
        page.wait_for_timeout(2500)

        # ── Dependencies tab ─────────────────────────────────────────
        click_tab(page, "dependencies")
        page.wait_for_timeout(3000)

        # ── Changelog tab ────────────────────────────────────────────
        click_tab(page, "changelog")
        page.wait_for_timeout(2500)

        # ── Stats tab ────────────────────────────────────────────────
        click_tab(page, "stats")
        page.wait_for_timeout(2500)

        # ── Settings page ────────────────────────────────────────────
        settings_btn = page.locator("text=Settings").last
        if settings_btn.is_visible(timeout=1500):
            settings_btn.click()
        page.wait_for_timeout(2500)

        # ── Final hold ───────────────────────────────────────────────
        page.wait_for_timeout(800)

        # ── Cleanup ──────────────────────────────────────────────────
        cleanup_comments(page, comment_ids)

        video_path = page.video.path()
        context.close()
        browser.close()

    shutil.copy2(video_path, OUTPUT)
    shutil.rmtree(video_dir, ignore_errors=True)

    print(f"\nDemo video saved to: {OUTPUT}")
    print(
        '\nConvert to GIF:\n'
        '  ffmpeg -y -i demo.webm -vf "fps=12,scale=960:-1:flags=lanczos,'
        'split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" demo.gif'
    )


if __name__ == "__main__":
    main()
