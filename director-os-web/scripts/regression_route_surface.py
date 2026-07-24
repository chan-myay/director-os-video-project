from __future__ import annotations

import json
import re
import shutil
import shlex
import socket
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.request import Request, urlopen


BASE_URL = "http://127.0.0.1:8787"
PROJECT_ID = "burmese-music-video"


REQUIRED_ROUTES = [
    "/",
    "/studio",
    f"/studio/projects/{PROJECT_ID}",
    f"/studio/projects/{PROJECT_ID}/result",
    f"/studio/projects/{PROJECT_ID}/storyboard",
    f"/studio/projects/{PROJECT_ID}/audio-truth",
    "/studio-loop",
    "/studio-loop/1",
    "/studio-loop/2",
    "/animatic",
    "/music-analysis",
    "/music-analysis/brain",
    "/burmese-language/font-check",
    "/burmese-language/listening-sync",
    "/burmese-language/sync-calibration",
    "/lipsync/brain-readiness",
    "/command-center",
]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        for key in ("href", "src"):
            value = values.get(key)
            if value:
                self.urls.append((tag, value))


def fetch(path_or_url: str, range_request: bool = False) -> tuple[int, str, str, bytes]:
    url = urljoin(BASE_URL, path_or_url)
    headers = {"User-Agent": "director-regression-route-surface/1.0"}
    if range_request:
        headers["Range"] = "bytes=0-1023"
    request = Request(url, method="GET", headers=headers)
    try:
        with urlopen(request, timeout=15) as response:
            return response.status, response.geturl(), response.headers.get("content-type", ""), response.read(500_000)
    except HTTPError as exc:
        return exc.code, exc.geturl(), exc.headers.get("content-type", ""), exc.read(200_000)
    except (URLError, socket.timeout, TimeoutError) as exc:
        raise AssertionError(f"GET {url} failed: {exc}") from exc


def visible_urls(html: bytes, page_url: str) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(html.decode("utf-8", errors="ignore"))
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for tag, raw_url in parser.urls:
        if raw_url.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urldefrag(urljoin(page_url, raw_url))[0]
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != "127.0.0.1:8787":
            continue
        if url not in seen:
            found.append((tag, url))
            seen.add(url)
    return found


def assert_route_ok(route: str) -> None:
    status, final_url, content_type, body = fetch(route)
    assert status != 500, f"{route} returned HTTP 500"
    assert status in {200, 303, 307, 404, 410}, f"{route} returned unexpected HTTP {status}"
    if "text/html" in content_type and status in {200, 303, 307}:
        assert b"Internal Server Error" not in body, f"{route} rendered an internal error page"
    if status in {404, 410}:
        text = body.decode("utf-8", errors="ignore")
        assert any(label in text for label in ("Not available yet", "Superseded", "Blocked", "Needs approval", "unavailable", "not found")), (
            f"{route} returned {status} without a useful empty-state message"
        )
    if final_url.endswith(".json") or "application/json" in content_type:
        json.loads(body.decode("utf-8"))


def chrome_main_page_check() -> None:
    chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    if not chrome.exists():
        print("SKIP chrome_main_page_check: Chrome is not installed")
        return
    profile = tempfile.mkdtemp(prefix="director-route-surface-chrome-")
    command = " ".join(
        shlex.quote(part)
        for part in [
            str(chrome),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            f"--user-data-dir={profile}",
            "--dump-dom",
            f"{BASE_URL}/studio/projects/{PROJECT_ID}",
        ]
    )
    stdout_path = Path(tempfile.mktemp(prefix="director-chrome-dom-", suffix=".html"))
    stderr_path = Path(tempfile.mktemp(prefix="director-chrome-dom-", suffix=".log"))
    deadline = time.time() + 45
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open("w", encoding="utf-8") as stderr_file:
            process = subprocess.Popen(
                ["/bin/zsh", "-lc", command],
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
            )
        while time.time() < deadline:
            stdout = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
            if "</html>" in stdout:
                process.terminate()
                break
            if process.poll() is not None:
                break
        else:
            process.terminate()
            raise AssertionError("Chrome timed out before rendering the Studio DOM")
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    stdout = stdout_path.read_text(encoding="utf-8", errors="ignore") if stdout_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8", errors="ignore") if stderr_path.exists() else ""
    if stdout_path.exists():
        stdout_path.unlink()
    if stderr_path.exists():
        stderr_path.unlink()
    assert "<html" in stdout and "</html>" in stdout, stderr[-2000:]
    assert "Internal Server Error" not in stdout
    browser_error_patterns = (r"Uncaught ", r"ReferenceError", r"TypeError", r"SyntaxError")
    combined = stdout + "\n" + stderr
    assert not any(re.search(pattern, combined) for pattern in browser_error_patterns), combined[-4000:]


def main() -> int:
    failures: list[str] = []
    for route in REQUIRED_ROUTES:
        try:
            assert_route_ok(route)
        except AssertionError as exc:
            failures.append(str(exc))

    status, final_url, _, body = fetch("/studio")
    assert status == 200, "/studio must render for visible link crawl"
    for tag, url in visible_urls(body, final_url):
        try:
            is_media = urlparse(url).path.lower().endswith(".mp4")
            status, _, content_type, response_body = fetch(url, range_request=is_media)
            if is_media:
                assert status in {200, 206}, f"{url} returned HTTP {status}, expected 200/206"
            else:
                assert status != 500, f"{url} returned HTTP 500"
            if urlparse(url).path.lower().endswith(".json") or "application/json" in content_type:
                json.loads(response_body.decode("utf-8"))
        except AssertionError as exc:
            failures.append(f"{tag} {url}: {exc}")

    try:
        chrome_main_page_check()
    except AssertionError as exc:
        failures.append(f"Chrome main page check: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS route surface: no HTTP 500s, visible media OK, main Studio page browser-rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
