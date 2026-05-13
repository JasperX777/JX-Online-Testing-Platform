from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from django.conf import settings


class AutomationDependencyError(RuntimeError):
    pass


class UnsupportedAutomationActionError(ValueError):
    pass


@dataclass
class AutomationStepFailure(Exception):
    step_no: int
    reason: str
    screenshot_path: str = ''


def _build_screenshot_path(*, execution_id: int, step_no: int) -> Path:
    directory = Path(settings.EXECUTION_SCREENSHOT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f'execution_{execution_id}_step_{step_no}.png'


def _build_video_dir(*, execution_id: int) -> Path:
    directory = Path(settings.EXECUTION_VIDEO_DIR) / f'execution_{execution_id}'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _capture_failure_screenshot(page, *, execution_id: int, step_no: int) -> str:
    screenshot_path = _build_screenshot_path(execution_id=execution_id, step_no=step_no)
    page.screenshot(path=str(screenshot_path), full_page=True)
    return str(screenshot_path)


def _get_browser_launcher(playwright, browser_name: str):
    browser_name = (browser_name or 'chromium').strip().lower()
    browser_aliases = {
        'chrome': 'chromium',
        'safari': 'webkit',
    }
    resolved_browser_name = browser_aliases.get(browser_name, browser_name)
    launcher = getattr(playwright, resolved_browser_name, None)
    if launcher is None:
        raise UnsupportedAutomationActionError(f'Browser "{browser_name}" is not supported.')
    return launcher, resolved_browser_name


def _ensure_browser_session(*, playwright, browser_name: str, execution_id: int, browser, context, page):
    if browser is not None and page is not None:
        return browser, context, page

    launcher, resolved_browser_name = _get_browser_launcher(playwright, browser_name)
    browser = launcher.launch(headless=True)
    context = browser.new_context(
        record_video_dir=str(_build_video_dir(execution_id=execution_id)),
        viewport={'width': 1440, 'height': 900},
    )
    page = context.new_page()
    return browser, context, page


def _run_step(page, step_result):
    action = step_result.action
    selector = step_result.selector
    value = step_result.value

    if action == 'launch_browser':
        return
    if action == 'open_page':
        page.goto(value, wait_until='domcontentloaded')
        return
    if action == 'input_text':
        locator = page.locator(selector)
        locator.click()
        locator.fill('')
        try:
            locator.press_sequentially(value, delay=45)
        except AttributeError:
            page.keyboard.type(value, delay=45)
        return
    if action == 'click_button':
        page.locator(selector).click()
        return
    if action == 'press_key':
        page.keyboard.press(value)
        return
    if action == 'verify_element':
        page.locator(selector).wait_for(state='visible')
        return

    raise UnsupportedAutomationActionError(f'Action "{action}" is not supported for automated execution.')


def _pause_for_recording(page, *, milliseconds: int = 600) -> None:
    if page is not None:
        page.wait_for_timeout(milliseconds)


def _collect_video_path(page, *, execution_id: int) -> str:
    video_dir = _build_video_dir(execution_id=execution_id)
    if page is None or page.video is None:
        videos = sorted(video_dir.glob('*.webm'), key=lambda item: item.stat().st_mtime, reverse=True)
        return str(videos[0]) if videos else ''
    try:
        video_path = page.video.path()
        if video_path:
            return video_path
    except Exception:
        pass

    videos = sorted(video_dir.glob('*.webm'), key=lambda item: item.stat().st_mtime, reverse=True)
    return str(videos[0]) if videos else ''


def execute_steps(*, execution, step_results) -> dict:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # pragma: no cover - environment dependent
        raise AutomationDependencyError(
            'Playwright is not available. Install the Python package and browser binaries before running automated executions.'
        ) from exc

    with sync_playwright() as playwright:
        browser = None
        context = None
        page = None
        selected_browser = 'chromium'
        outcomes = []
        video_path = ''
        try:
            for step_result in step_results:
                try:
                    if step_result.action == 'launch_browser':
                        selected_browser = step_result.value.strip().lower() or 'chromium'
                        browser, context, page = _ensure_browser_session(
                            playwright=playwright,
                            browser_name=selected_browser,
                            execution_id=execution.id,
                            browser=browser,
                            context=context,
                            page=page,
                        )
                    else:
                        browser, context, page = _ensure_browser_session(
                            playwright=playwright,
                            browser_name=selected_browser,
                            execution_id=execution.id,
                            browser=browser,
                            context=context,
                            page=page,
                    )
                    _run_step(page, step_result)
                    _pause_for_recording(page)
                except (PlaywrightTimeoutError, PlaywrightError, UnsupportedAutomationActionError) as exc:
                    outcomes.append(
                        {
                            'step_no': step_result.step_no,
                            'status': 'failed',
                            'error_message': str(exc),
                            'screenshot_path': '',
                        }
                    )
                    break

                outcomes.append(
                    {
                        'step_no': step_result.step_no,
                        'status': 'passed',
                        'error_message': '',
                        'screenshot_path': '',
                    }
                )
            _pause_for_recording(page, milliseconds=1000)
        finally:
            if context is not None:
                context.close()
                video_path = _collect_video_path(page, execution_id=execution.id)
            if browser is not None:
                browser.close()

    return {
        'outcomes': outcomes,
        'video_path': video_path,
    }
