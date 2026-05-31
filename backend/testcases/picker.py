from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
from typing import Any
from urllib.parse import urlparse

from executions.automation import _get_browser_launcher

_PICKER_SCRIPT = r"""
(() => {
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
    const id = element.getAttribute('id')
    if (id) return `#${escapeCssValue(id)}`

    const name = element.getAttribute('name')
    if (name) return `${element.tagName.toLowerCase()}[name="${escapeCssValue(name)}"]`

    const dataTestId = element.getAttribute('data-testid')
    if (dataTestId) return `${element.tagName.toLowerCase()}[data-testid="${escapeCssValue(dataTestId)}"]`

    const classes = [...element.classList].filter(Boolean)
    if (classes.length > 0) {
      return `${element.tagName.toLowerCase()}.${classes.slice(0, 2).map(escapeCssValue).join('.')}`
    }

    return element.tagName.toLowerCase()
  }

  function cleanupPrevious() {
    if (window.__codexPickerCleanup) {
      window.__codexPickerCleanup()
      window.__codexPickerCleanup = null
    }
  }

  function installPicker() {
    cleanupPrevious()

    let activeElement = null
    let previousOutline = ''

    const handleMouseOver = (event) => {
      const element = event.target
      if (!(element instanceof HTMLElement)) return
      if (activeElement && activeElement !== element) {
        activeElement.style.outline = previousOutline
      }
      activeElement = element
      previousOutline = element.style.outline
      element.style.outline = '2px solid #5be4d0'
    }

    const handleMouseOut = (event) => {
      const element = event.target
      if (!(element instanceof HTMLElement)) return
      element.style.outline = previousOutline
    }

    const handleClick = async (event) => {
      event.preventDefault()
      event.stopPropagation()
      const element = event.target
      if (!(element instanceof HTMLElement)) return
      const payload = {
        target: buildFriendlyLabel(element),
        selector: buildSelector(element),
      }
      if (window.__codexPickerPick) {
        await window.__codexPickerPick(payload)
      }
    }

    document.addEventListener('mouseover', handleMouseOver, true)
    document.addEventListener('mouseout', handleMouseOut, true)
    document.addEventListener('click', handleClick, true)

    window.__codexPickerCleanup = () => {
      document.removeEventListener('mouseover', handleMouseOver, true)
      document.removeEventListener('mouseout', handleMouseOut, true)
      document.removeEventListener('click', handleClick, true)
      if (activeElement) {
        activeElement.style.outline = previousOutline
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', installPicker, { once: true })
  } else {
    installPicker()
  }

  window.__codexInstallPicker = installPicker
})()
"""

_sessions: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()
_display_lock = threading.Lock()


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
    }


def _update_session(session_id: str, **changes: Any) -> dict[str, Any] | None:
    with _lock:
        session = _sessions.get(session_id)
        if session is None:
            return None
        session.update(changes)
        return dict(session)


def _start_virtual_display() -> tuple[subprocess.Popen[bytes] | None, dict[str, str]]:
    env = os.environ.copy()
    if env.get('DISPLAY'):
        return None, env

    xvfb_path = shutil.which('Xvfb')
    if not xvfb_path:
        raise RuntimeError(
            'The picker needs a graphical display. Install Xvfb in the backend container '
            'or run the picker on a machine with a desktop session.'
        )

    with _display_lock:
        for display_number in range(90, 130):
            display = f':{display_number}'
            process = subprocess.Popen(
                [
                    xvfb_path,
                    display,
                    '-screen',
                    '0',
                    '1440x900x24',
                    '-nolisten',
                    'tcp',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.2)
            if process.poll() is None:
                env['DISPLAY'] = display
                return process, env
            process.wait(timeout=1)

    raise RuntimeError('Unable to start a virtual display for the picker.')


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

    stop_event = threading.Event()

    def handle_pick(_, payload: dict[str, Any]) -> None:
        _update_session(
            session_id,
            status='picked',
            target=(payload or {}).get('target', ''),
            selector=(payload or {}).get('selector', ''),
            picked_at=time.time(),
        )
        stop_event.set()

    try:
        virtual_display = None
        with sync_playwright() as playwright:
            session = get_picker_session(session_id)
            if session is None:
                return

            launcher, _ = _get_browser_launcher(playwright, session['browser_name'])
            virtual_display, browser_env = _start_virtual_display()
            browser = launcher.launch(headless=False, env=browser_env)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            context.expose_binding('__codexPickerPick', handle_pick)
            context.add_init_script(_PICKER_SCRIPT)
            page = context.new_page()
            page.goto(session['url'], wait_until='domcontentloaded', timeout=60000)
            page.evaluate("window.__codexInstallPicker && window.__codexInstallPicker()")
            _update_session(session_id, status='ready')

            while not stop_event.wait(0.25):
                latest = get_picker_session(session_id)
                if latest is None:
                    break
                if latest['status'] == 'picked':
                    break
                if latest['stop_requested']:
                    _update_session(session_id, status='stopped')
                    break
                if page.is_closed():
                    _update_session(session_id, status='stopped')
                    break

            context.close()
            browser.close()
    except Exception as exc:
        _update_session(session_id, status='error', error=str(exc))
    finally:
        if virtual_display is not None and virtual_display.poll() is None:
            virtual_display.terminate()
            try:
                virtual_display.wait(timeout=3)
            except subprocess.TimeoutExpired:
                virtual_display.kill()
