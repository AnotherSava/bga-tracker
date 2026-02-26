"""
BGA Browser Helper - Opens a browser for you to interact with.
Commands are read from 'cmd.txt' and results written to 'result.txt'.
All activity is logged to 'browse.log'.
"""

import os
import sys
import time
import traceback

from playwright.sync_api import sync_playwright
from playwright._impl._errors import TargetClosedError

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(_MODULE_DIR))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
CMD_FILE = os.path.join(PROJECT_ROOT, "scripts", "cmd.txt")
RESULT_FILE = os.path.join(OUTPUT_DIR, "result.txt")
LOG_FILE = os.path.join(OUTPUT_DIR, "browse.log")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_result(lines):
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    start_url = sys.argv[1] if len(sys.argv) > 1 else "https://boardgamearena.com"

    # Clean up
    for f in [CMD_FILE, RESULT_FILE, LOG_FILE]:
        if os.path.exists(f):
            os.remove(f)

    log("Starting browser...")

    with sync_playwright() as p:
        # Use real Chrome with persistent profile (like makerworld.py)
        # This keeps the browser alive and preserves login sessions
        chrome_profile = os.path.join(PROJECT_ROOT, ".chrome_bga_profile")
        context = p.chromium.launch_persistent_context(
            chrome_profile,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--hide-crash-restore-bubble",
                "--disable-session-crashed-bubble",
                "--no-restore-session-state",
            ],
            viewport={"width": 1920, "height": 1080},
        )
        def page_alive(p):
            """Check if page renderer is actually alive (not just cached url)."""
            try:
                p.evaluate("1")
                return True
            except Exception:
                return False

        def ensure_page():
            """Return a live page, reopening if the renderer crashed."""
            nonlocal page
            if page_alive(page):
                return page
            log("Page renderer dead, reopening...")
            try:
                page.close()
            except Exception:
                pass
            page = context.new_page()
            page.goto(start_url, wait_until="domcontentloaded")
            log(f"Reopened: {page.url}")
            return page

        # Close any extra restored tabs from a previous session, keep one
        pages = context.pages
        if len(pages) > 1:
            for old_page in pages[1:]:
                try:
                    old_page.close()
                except Exception:
                    pass
        page = pages[0] if pages else context.new_page()

        log(f"Navigating to {start_url}")
        page.goto(start_url, wait_until="domcontentloaded")
        log(f"Page loaded: {page.url}")
        log(f"Watching for commands in {CMD_FILE}")

        tick = 0
        while True:
            if not os.path.exists(CMD_FILE):
                time.sleep(0.5)
                tick += 1
                if tick % 10 == 0:
                    ensure_page()
                continue

            try:
                with open(CMD_FILE, "r") as f:
                    line = f.read().strip()
            except Exception:
                time.sleep(0.3)
                continue

            if not line:
                time.sleep(0.3)
                continue

            os.remove(CMD_FILE)
            log(f"Got command: {line}")

            parts = line.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None
            output = []

            try:
                ensure_page()

                if cmd == "quit" or cmd == "exit":
                    output.append("Closing browser...")
                    write_result(output)
                    break

                elif cmd == "screenshot":
                    fname = arg or "screenshot.png"
                    if not fname.endswith(".png"):
                        fname += ".png"
                    if not os.path.isabs(fname):
                        fname = os.path.join(PROJECT_ROOT, fname)
                    page.screenshot(path=fname, full_page=False)
                    output.append(f"Screenshot saved: {fname}")

                elif cmd == "fullscreenshot":
                    fname = arg or "screenshot_full.png"
                    if not fname.endswith(".png"):
                        fname += ".png"
                    if not os.path.isabs(fname):
                        fname = os.path.join(PROJECT_ROOT, fname)
                    page.screenshot(path=fname, full_page=True)
                    output.append(f"Full page screenshot saved: {fname}")

                elif cmd == "html":
                    selector = arg or "body"
                    el = page.query_selector(selector)
                    if el:
                        html = el.evaluate("e => e.outerHTML")
                        output.append(html[:10000])
                        if len(html) > 10000:
                            output.append(f"... (truncated, total {len(html)} chars)")
                    else:
                        output.append(f"No element found for selector: {selector}")

                elif cmd == "classes":
                    selector = arg or "body"
                    els = page.query_selector_all(selector)
                    for el in els[:30]:
                        tag = el.evaluate("e => e.tagName.toLowerCase()")
                        cls = el.get_attribute("class") or ""
                        eid = el.get_attribute("id") or ""
                        desc = f"<{tag}"
                        if eid:
                            desc += f' id="{eid}"'
                        if cls:
                            desc += f' class="{cls}"'
                        desc += ">"
                        output.append(desc)

                elif cmd == "children":
                    selector = arg or "body"
                    el = page.query_selector(selector)
                    if el:
                        children = el.evaluate("""e => {
                            return Array.from(e.children).map(c => {
                                let desc = '<' + c.tagName.toLowerCase();
                                if (c.id) desc += ' id="' + c.id + '"';
                                if (c.className && typeof c.className === 'string') desc += ' class="' + c.className + '"';
                                desc += '>';
                                return desc;
                            });
                        }""")
                        for c in children:
                            output.append(c)
                    else:
                        output.append(f"No element found for selector: {selector}")

                elif cmd == "url":
                    # Use evaluate to get the real URL (page.url can be cached)
                    try:
                        real_url = page.evaluate("window.location.href")
                        output.append(real_url)
                    except Exception:
                        output.append(page.url + " (cached, renderer may be dead)")

                elif cmd == "goto":
                    if arg:
                        page.goto(arg, wait_until="domcontentloaded")
                        # Verify renderer survived navigation
                        if page_alive(page):
                            output.append(f"Navigated to: {page.url}")
                        else:
                            url = page.url
                            log(f"Renderer crashed after navigating to {url}")
                            page = ensure_page()
                            output.append(f"Error: page renderer crashed after navigating to {url}")
                    else:
                        output.append("Usage: goto <url>")

                elif cmd == "inject":
                    if arg:
                        page.add_style_tag(content=arg)
                        output.append("CSS injected.")
                    else:
                        output.append("Usage: inject <css>")

                elif cmd == "injectfile":
                    if arg and os.path.exists(arg):
                        with open(arg, "r") as f:
                            css = f.read()
                        page.add_style_tag(content=css)
                        output.append(f"CSS injected from {arg}")
                    else:
                        output.append(f"File not found: {arg}")

                elif cmd == "styles":
                    selector = arg or "body"
                    el = page.query_selector(selector)
                    if el:
                        styles = el.evaluate("""e => {
                            const cs = window.getComputedStyle(e);
                            const props = ['color','background-color','font-size','font-family',
                                'padding','margin','border','display','position','width','height',
                                'overflow','z-index','opacity','box-shadow'];
                            const result = {};
                            for (const p of props) result[p] = cs.getPropertyValue(p);
                            return result;
                        }""")
                        for k, v in styles.items():
                            output.append(f"  {k}: {v}")
                    else:
                        output.append(f"No element found for selector: {selector}")

                elif cmd == "fill":
                    # fill <selector> ||| <text>
                    if arg and "|||" in arg:
                        sel, text = arg.split("|||", 1)
                        page.fill(sel.strip(), text.strip())
                        output.append(f"Filled {sel.strip()}")
                    else:
                        output.append("Usage: fill <selector> ||| <text>")

                elif cmd == "fillfile":
                    # fillfile <selector> ||| <filepath>
                    if arg and "|||" in arg:
                        sel, fpath = arg.split("|||", 1)
                        fpath = fpath.strip()
                        if os.path.exists(fpath):
                            with open(fpath, "r", encoding="utf-8") as f:
                                text = f.read()
                            page.fill(sel.strip(), text)
                            output.append(f"Filled {sel.strip()} from {fpath} ({len(text)} chars)")
                        else:
                            output.append(f"File not found: {fpath}")
                    else:
                        output.append("Usage: fillfile <selector> ||| <filepath>")

                elif cmd == "click":
                    if arg:
                        page.click(arg)
                        output.append(f"Clicked: {arg}")
                    else:
                        output.append("Usage: click <selector>")

                elif cmd == "eval":
                    if arg:
                        # If arg is a file path, read and execute it
                        # Resolve relative paths from project root
                        eval_path = arg
                        if not os.path.isabs(eval_path):
                            eval_path = os.path.join(PROJECT_ROOT, eval_path)
                        if os.path.exists(eval_path):
                            with open(eval_path, "r", encoding="utf-8") as f:
                                js = f.read()
                            result = page.evaluate(js)
                        else:
                            result = page.evaluate(arg)
                        output.append(str(result))
                    else:
                        output.append("Usage: eval <js expression or file path>")

                elif cmd == "wait":
                    secs = float(arg) if arg else 2
                    page.wait_for_timeout(int(secs * 1000))
                    output.append(f"Waited {secs}s")

                else:
                    output.append(f"Unknown command: {cmd}")

            except TargetClosedError as e:
                output.append(f"Error: {e}")
                log(f"TargetClosedError, recovering: {e}")
                page = ensure_page()
            except Exception as e:
                output.append(f"Error: {e}")
                log(f"Error: {traceback.format_exc()}")

            write_result(output)
            log(f"Executed: {cmd} -> {output[0] if output else '(no output)'}")

        context.close()
        log("Browser closed.")


if __name__ == "__main__":
    main()
