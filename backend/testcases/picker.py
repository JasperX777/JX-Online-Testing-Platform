from __future__ import annotations

import base64
import threading
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from executions.automation import _get_browser_launcher

_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


def _normalize_url(url: str) -> str:
    normalized = (url or '').strip()
    if not normalized:
        return normalized

    parsed = urlparse(normalized)
    if parsed.scheme:
        return normalized

    return f'https://{normalized}'


def _snapshot(session: dict[str, Any]) -> dict[str, Any]:
    return {
        'session_id': session['session_id'],
        'url': session['url'],
        'status': session['status'],
        'browser_name': session['browser_name'],
        'target': session.get('target', ''),
        'selector': session.get('selector', ''),
        'error': session.get('error', ''),
        'created_at': session['created_at'],
        'picked_at': session.get('picked_at'),
        'stop_requested': session.get('stop_requested', False),
        'screenshot_picker': session.get('screenshot_picker', False),
        'screenshot_data': session.get('screenshot_data', ''),
        'elements': session.get('elements', []),
        'viewport': session.get('viewport', {'width': 1440, 'height': 900}),
    }


def _update_session(session_id: str, **changes: Any) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        session.update(changes)
        return dict(session)


def start_picker_session(*, url: str, browser_name: str = 'chromium') -> dict[str, Any]:
    normalized_url = _normalize_url(url)
    session_id = uuid.uuid4().hex
    session = {
        'session_id': session_id,
        'url': normalized_url,
        'status': 'starting',
        'browser_name': browser_name,
        'target': '',
        'selector': '',
        'error': '',
        'created_at': time.time(),
        'picked_at': None,
        'stop_requested': False,
        'screenshot_picker': True,
        'screenshot_data': '',
        'elements': [],
        'viewport': {'width': 1440, 'height': 900},
    }
    with _lock:
        _sessions[session_id] = session

    thread = threading.Thread(
        target=_run_picker_session,
        kwargs={'session_id': session_id},
        daemon=True,
        name=f'picker-session-{session_id}',
    )
    thread.start()
    return _snapshot(session)


def get_picker_session(session_id: str) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)
        return _snapshot(session) if session else None


def stop_picker_session(session_id: str) -> dict[str, Any] | None:
    session = _update_session(session_id, stop_requested=True)
    return _snapshot(session) if session else None


def _run_picker_session(*, session_id: str) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        _update_session(
            session_id,
            status='error',
            error='Playwright is not available. Install the package and browser binaries before using the picker.',
        )
        return

    try:
        with sync_playwright() as playwright:
            session = get_picker_session(session_id)
            if session is None:
                return

            launcher, _ = _get_browser_launcher(playwright, session['browser_name'])
            browser = launcher.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            page.goto(session['url'], wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(750)
            elements = page.evaluate(
                r"""
                () => {
                  function escapeCssValue(value) {
                    if (window.CSS && typeof window.CSS.escape === 'function') {
                      return window.CSS.escape(value)
                    }
                    return String(value).replace(/["\\]/g, '\\$&')
                  }

                  function buildFriendlyLabel(element) {
                    const ariaLabel = element.getAttribute('aria-label')
                    const placeholder = element.getAttribute('placeholder')
                    const name = element.getAttribute('name')
                    const id = element.getAttribute('id')
                    const text = (element.textContent || '').trim()

                    return (
                      ariaLabel ||
                      placeholder ||
                      name ||
                      id ||
                      text.slice(0, 40) ||
                      `${element.tagName.toLowerCase()} element`
                    )
                  }

                  function buildSelector(element) {
                    const name = element.getAttribute('name')
                    const dataTestId = element.getAttribute('data-testid')
                    const ariaLabel = element.getAttribute('aria-label')
                    const placeholder = element.getAttribute('placeholder')
                    const id = element.getAttribute('id')
                    const classes = [...element.classList].filter(Boolean)
                    const tagName = element.tagName.toLowerCase()

                    const candidates = [
                      dataTestId ? `${tagName}[data-testid="${escapeCssValue(dataTestId)}"]` : '',
                      name ? `${tagName}[name="${escapeCssValue(name)}"]` : '',
                      ariaLabel ? `${tagName}[aria-label="${escapeCssValue(ariaLabel)}"]` : '',
                      placeholder ? `${tagName}[placeholder="${escapeCssValue(placeholder)}"]` : '',
                      id ? `#${escapeCssValue(id)}` : '',
                      classes.length > 0 ? `${tagName}.${classes.slice(0, 2).map(escapeCssValue).join('.')}` : '',
                      tagName,
                    ].filter(Boolean)

                    for (const candidate of candidates) {
                      try {
                        if (document.querySelectorAll(candidate).length === 1) return candidate
                      } catch {
                        // Try the next selector candidate.
                      }
                    }

                    return candidates[0] || tagName
                  }

                  const candidates = [
                    'input',
                    'textarea',
                    'select',
                    'button',
                    'a[href]',
                    '[role="button"]',
                    '[role="textbox"]',
                    '[contenteditable="true"]',
                    '[tabindex]:not([tabindex="-1"])',
                  ].join(',')

                  return [...document.querySelectorAll(candidates)]
                    .map((element, index) => {
                      const rect = element.getBoundingClientRect()
                      const style = window.getComputedStyle(element)
                      return {
                        index,
                        target: buildFriendlyLabel(element),
                        selector: buildSelector(element),
                        tag: element.tagName.toLowerCase(),
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height,
                        visible:
                          rect.width > 0 &&
                          rect.height > 0 &&
                          style.visibility !== 'hidden' &&
                          style.display !== 'none' &&
                          rect.bottom >= 0 &&
                          rect.right >= 0 &&
                          rect.top <= window.innerHeight &&
                          rect.left <= window.innerWidth,
                      }
                    })
                    .filter((element) => element.visible)
                    .slice(0, 250)
                }
                """
            )
            screenshot = page.screenshot(full_page=False)
            _update_session(
                session_id,
                status='ready',
                screenshot_data=f'data:image/png;base64,{base64.b64encode(screenshot).decode("ascii")}',
                elements=elements,
            )

            context.close()
            browser.close()
    except Exception as exc:
        _update_session(session_id, status='error', error=str(exc))
