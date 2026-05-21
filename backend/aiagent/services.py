from dataclasses import dataclass
import re
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction

from executions.models import TestExecution
from executions.serializers import TestExecutionSerializer
from executions.services import initialize_execution
from executions.tasks import dispatch_test_execution
from projects.models import Project
from testcases.models import TestCase
from testcases.serializers import TestCaseSerializer


AUTO_RUN_KEYWORDS = ('run', 'execute', 'start', 'auto run', 'run them', 'run it')
NO_RUN_KEYWORDS = ('do not run', "don't run", 'only generate', 'generate only', 'create only')


@dataclass
class AgentResult:
    reply: str
    needs_project_confirmation: bool
    matched_project: Project | None
    project_candidates: list[Project]
    generated_testcases: list[TestCase]
    executions: list[TestExecution]
    auto_run: bool


def visible_projects_for_user(user):
    role = getattr(getattr(user, 'profile', None), 'role', None)
    if user.is_superuser or role == 'admin':
        return Project.objects.all()
    return Project.objects.filter(owner=user)


def run_mock_agent(*, session, user, message: str) -> AgentResult:
    raw_message = (message or '').strip()
    pending_request = (session.context or {}).get('pending_request', '')
    visible_projects = list(visible_projects_for_user(user))
    matched_project = _match_project(raw_message, visible_projects)
    requirement = raw_message

    if pending_request and matched_project:
        requirement = pending_request

    if not matched_project:
        session.context = {
            **(session.context or {}),
            'pending_request': pending_request or raw_message,
        }
        session.save(update_fields=['context', 'updated_at'])
        candidates = visible_projects[:5]
        if candidates:
            names = ', '.join(project.name for project in candidates)
            reply = f'Which project should I generate these test cases for? I can match these projects: {names}.'
        else:
            reply = 'You do not have any available projects yet. Create a project first, then I can generate automated test cases.'
        return AgentResult(reply, True, None, candidates, [], [], False)

    auto_run = _should_auto_run(requirement)
    generated_testcases = _generate_testcases(project=matched_project, user=user, requirement=requirement)
    executions = []

    with transaction.atomic():
        for testcase in generated_testcases:
            testcase.save()
            if auto_run:
                execution = TestExecution.objects.create(
                    project=matched_project,
                    testcase=testcase,
                    triggered_by=user,
                    status=TestExecution.Status.PENDING,
                )
                initialize_execution(execution=execution)
                executions.append(execution)

        if auto_run:
            transaction.on_commit(lambda: [_dispatch_execution(execution.id) for execution in executions])

        session.project = matched_project
        session.context = {
            **(session.context or {}),
            'pending_request': '',
            'last_project_id': matched_project.id,
            'last_auto_run': auto_run,
            'last_testcase_ids': [testcase.id for testcase in generated_testcases],
            'last_execution_ids': [execution.id for execution in executions],
        }
        if not session.title:
            session.title = requirement[:80]
        session.save(update_fields=['project', 'context', 'title', 'updated_at'])

    action_text = 'and started execution' if auto_run else 'and saved them for manual execution from Executions'
    reply = f'I generated {len(generated_testcases)} automated test cases for {matched_project.name} {action_text}.'
    return AgentResult(reply, False, matched_project, [], generated_testcases, executions, auto_run)


def serialize_agent_result(result: AgentResult):
    return {
        'reply': result.reply,
        'needs_project_confirmation': result.needs_project_confirmation,
        'matched_project': _project_to_dict(result.matched_project),
        'project_candidates': [_project_to_dict(project) for project in result.project_candidates],
        'generated_testcases': TestCaseSerializer(result.generated_testcases, many=True).data,
        'executions': TestExecutionSerializer(result.executions, many=True).data,
        'auto_run': result.auto_run,
    }


def _match_project(message: str, projects: list[Project]) -> Project | None:
    normalized = message.casefold()
    if not normalized:
        return None

    exact_matches = [project for project in projects if project.name.casefold() in normalized]
    if exact_matches:
        return sorted(exact_matches, key=lambda project: len(project.name), reverse=True)[0]

    compact_message = ''.join(ch for ch in normalized if ch.isalnum())
    for project in projects:
        compact_name = ''.join(ch for ch in project.name.casefold() if ch.isalnum())
        if compact_name and compact_name in compact_message:
            return project

    return None


def _should_auto_run(message: str) -> bool:
    normalized = message.casefold()
    if any(keyword in normalized for keyword in NO_RUN_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in AUTO_RUN_KEYWORDS)


def _feature_from_requirement(requirement: str) -> tuple[str, str]:
    normalized = requirement.casefold()
    if 'search' in normalized:
        return 'Search', 'Search flow'
    if any(keyword in normalized for keyword in ('login', 'signin', 'sign in')):
        return 'Authentication', 'Login'
    if any(keyword in normalized for keyword in ('register', 'sign up', 'signup')):
        return 'Authentication', 'Registration'
    if 'project' in normalized:
        return 'Projects', 'Project management'
    return 'AI Generated', 'Requested workflow'


def _generate_testcases(*, project: Project, user, requirement: str) -> list[TestCase]:
    module, scenario = _feature_from_requirement(requirement)
    lower_requirement = requirement.casefold()
    target_base_url = _target_base_url_from_requirement(requirement=requirement, scenario=scenario)

    if scenario == 'Login':
        specs = [
            ('Successful login', 'Verify a valid user can sign in and reach the dashboard.', 'valid_user@example.com', 'pass123456', 'Dashboard'),
            ('Invalid password login', 'Verify an invalid password does not sign the user in.', 'valid_user@example.com', 'wrong-password', 'Invalid credentials'),
            ('Empty username login', 'Verify username validation appears before submitting credentials.', '', 'pass123456', 'Username'),
        ]
    elif scenario == 'Registration':
        specs = [
            ('Successful registration', 'Verify a new user can register with valid account details.', 'new_user@example.com', 'pass123456', 'Dashboard'),
            ('Weak password registration', 'Verify weak passwords are rejected.', 'weak_user@example.com', '123', 'password'),
            ('Duplicate email registration', 'Verify duplicate account data is rejected.', 'existing@example.com', 'pass123456', 'already'),
        ]
    elif scenario == 'Search flow':
        specs = [
            ('Search returns results', 'Verify a normal query produces visible results.', 'OpenAI', '', 'results'),
            ('Empty search validation', 'Verify empty search input is handled.', '', '', 'required'),
            ('No-result search', 'Verify no-result messaging appears for an unlikely query.', 'zz-no-results-zz', '', 'No results'),
        ]
    else:
        concise = requirement[:80] or 'requested workflow'
        specs = [
            ('Happy path', f'Verify the main path for {concise}.', 'sample input', '', 'success'),
            ('Required field validation', f'Verify required validation for {concise}.', '', '', 'required'),
            ('Error handling', f'Verify graceful error handling for {concise}.', 'invalid input', '', 'error'),
        ]

    if 'boundary' in lower_requirement:
        specs.append(('Boundary input', 'Verify boundary-sized input is handled correctly.', 'x' * 32, '', 'success'))

    return [
        TestCase(
            project=project,
            title=f'AI - {scenario} - {name}',
            description=description,
            module=module,
            scenario=f'{scenario}: {name}',
            category='ai-generated',
            tags=['ai-generated', module.casefold().replace(' ', '-')],
            priority='medium',
            status='ready',
            created_by=user,
            steps_json=_steps_for_spec(
                scenario=scenario,
                name=name,
                value=value,
                password=password,
                expected=expected,
                target_base_url=target_base_url,
            ),
        )
        for name, description, value, password, expected in specs
    ]


def _target_base_url_from_requirement(*, requirement: str, scenario: str) -> str:
    explicit_url = _extract_url(requirement)
    if explicit_url:
        return explicit_url

    normalized = requirement.casefold()
    if scenario == 'Search flow':
        if 'google' in normalized:
            return 'https://www.google.com'
        if 'bing' in normalized:
            return 'https://www.bing.com'

    return settings.AI_AGENT_TARGET_BASE_URL


def _extract_url(text: str) -> str:
    match = re.search(r'https?://[^\s,，。)]+', text or '', flags=re.IGNORECASE)
    if match:
        return _normalize_url(match.group(0))

    domain_match = re.search(r'\b(?:www\.)[a-z0-9.-]+\.[a-z]{2,}(?:/[^\s,，。)]*)?', text or '', flags=re.IGNORECASE)
    if domain_match:
        return _normalize_url(f'https://{domain_match.group(0)}')

    return ''


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ''
    return f'{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip("/")}'


def _steps_for_spec(*, scenario: str, name: str, value: str, password: str, expected: str, target_base_url: str | None = None):
    path = '/login' if scenario == 'Login' else '/register' if scenario == 'Registration' else '/'
    base_url = (target_base_url or settings.AI_AGENT_TARGET_BASE_URL).rstrip('/')
    steps = [
        _step(1, 'Launch browser', 'launch_browser', value='chromium'),
        _step(2, f'Open {scenario.lower()} page', 'open_page', target=f'{scenario} page', value=f'{base_url}{path}'),
    ]

    if scenario == 'Login':
        steps.extend(
            [
                _step(3, 'Enter username', 'input_text', target='Username field', selector='input:not([type])', value=value),
                _step(4, 'Enter password', 'input_text', target='Password field', selector="input[type='password']", value=password),
                _step(5, 'Submit form', 'click_button', target='Submit button', selector="button[type='submit']"),
                _step(6, f'Verify {expected}', 'verify_element', target=expected, selector='body'),
            ]
        )
    elif scenario == 'Registration':
        steps.extend(
            [
                _step(3, 'Enter username', 'input_text', target='Username field', selector='input:not([type])', value=value.split('@')[0] or 'ai_user'),
                _step(4, 'Enter email', 'input_text', target='Email field', selector="input[type='email']", value=value or 'ai_user@example.com'),
                _step(5, 'Enter password', 'input_text', target='Password field', selector="input[type='password']", value=password),
                _step(6, 'Submit form', 'click_button', target='Submit button', selector="button[type='submit']"),
                _step(7, f'Verify {expected}', 'verify_element', target=expected, selector='body'),
            ]
        )
    elif scenario == 'Search flow':
        steps.extend(
            [
                _step(3, 'Enter search query', 'input_text', target='Search input', selector="input[type='search'], input[name='q']", value=value),
                _step(4, 'Submit search', 'press_key', target='Search input', value='Enter'),
                _step(5, f'Verify {expected}', 'verify_element', target=expected, selector='body'),
            ]
        )
    else:
        steps.extend(
            [
                _step(3, f'Exercise {name.lower()}', 'input_text', target='Primary input', selector='input, textarea', value=value),
                _step(4, 'Submit workflow', 'click_button', target='Primary action', selector="button[type='submit'], button"),
                _step(5, f'Verify {expected}', 'verify_element', target=expected, selector='body'),
            ]
        )

    return steps


def _step(step_no, title, action, *, target='', selector='', value=''):
    return {
        'step_no': step_no,
        'step_title': title,
        'description': '',
        'action': action,
        'target': target,
        'locator_type': 'css',
        'selector': selector,
        'value': value,
        'note': '',
    }


def _project_to_dict(project: Project | None):
    if not project:
        return None
    return {
        'id': project.id,
        'name': project.name,
        'description': project.description,
    }


def _dispatch_execution(execution_id: int):
    dispatch_test_execution(execution_id)
