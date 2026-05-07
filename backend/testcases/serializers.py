from rest_framework import serializers

from .constants import STEP_ACTION_VALUES
from .models import TestCase


def _default_step_description(*, action: str, target: str, value: str) -> str:
    if action == 'launch_browser':
        return f'Launch the {value or "chromium"} browser.'
    if action == 'open_page':
        return f'Open {value or target or "the target page"} in the browser.'
    if action == 'input_text':
        return f'Type {value or "the value"} into {target or "the selected field"}.'
    if action == 'click_button':
        return f'Click {target or "the selected button"}.'
    if action == 'press_key':
        return f'Press the {value or "configured"} key.'
    if action == 'verify_element':
        return f'Verify that {target or "the selected element"} is visible.'
    return target or value or 'Execute the configured step.'


SUPPORTED_BROWSER_VALUES = {'chromium', 'chrome', 'firefox', 'webkit', 'safari'}


class TestCaseSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestCase
        fields = (
            'id',
            'project',
            'title',
            'description',
            'module',
            'scenario',
            'steps_json',
            'category',
            'tags',
            'priority',
            'status',
            'created_by',
            'created_by_username',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_by', 'created_by_username', 'created_at', 'updated_at')
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True},
            'module': {'required': False, 'allow_blank': True},
            'scenario': {'required': False, 'allow_blank': True},
        }

    def validate_project(self, project):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        role = getattr(getattr(user, 'profile', None), 'role', None)

        if not user or not user.is_authenticated:
            return project

        if user.is_superuser or role == 'admin':
            return project

        if role == 'user' and project.owner_id == user.id:
            return project

        raise serializers.ValidationError('You do not have permission to write test cases in this project.')

    def validate_steps_json(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('Steps must be a list.')
        if not value:
            raise serializers.ValidationError('At least one step is required.')

        for index, step in enumerate(value, start=1):
            if not isinstance(step, dict):
                raise serializers.ValidationError(f'Step {index} must be an object.')

            step_no = step.get('step_no')
            step_title = step.get('step_title', '')
            description = step.get('description', '')
            action = step.get('action')
            target = step.get('target')
            selector = step.get('selector', '')
            locator_type = step.get('locator_type', 'css')
            raw_value = step.get('value', '')

            if step_no != index:
                raise serializers.ValidationError('Step numbers must start at 1 and be sequential.')
            if action not in STEP_ACTION_VALUES:
                raise serializers.ValidationError(f'Step {index} has an invalid action.')
            if not isinstance(step_title, str):
                raise serializers.ValidationError(f'Step {index} title must be a string.')
            if not isinstance(description, str):
                raise serializers.ValidationError(f'Step {index} description must be a string.')
            if not isinstance(selector, str):
                raise serializers.ValidationError(f'Step {index} selector must be a string.')
            if not isinstance(locator_type, str):
                raise serializers.ValidationError(f'Step {index} locator type must be a string.')
            if locator_type not in {'css'}:
                raise serializers.ValidationError(f'Step {index} locator type is invalid.')
            if action not in {'open_page', 'launch_browser', 'press_key'} and not selector.strip():
                raise serializers.ValidationError(f'Step {index} selector is required for {action}.')
            if 'value' in step and not isinstance(raw_value, str):
                raise serializers.ValidationError(f'Step {index} value must be a string.')
            if 'note' in step and not isinstance(step.get('note'), str):
                raise serializers.ValidationError(f'Step {index} note must be a string.')
            if action in {'launch_browser', 'open_page', 'input_text', 'press_key'} and not str(raw_value or '').strip():
                raise serializers.ValidationError(f'Step {index} value is required for {action}.')
            if not str(step_title or '').strip():
                raise serializers.ValidationError(f'Step {index} title is required.')
            if action == 'launch_browser' and str(raw_value or '').strip() not in SUPPORTED_BROWSER_VALUES:
                raise serializers.ValidationError(
                    f'Step {index} browser value must be one of: {", ".join(sorted(SUPPORTED_BROWSER_VALUES))}.'
                )

        return [
            {
                'step_no': step['step_no'],
                'step_title': step.get('step_title', '').strip(),
                'description': step.get('description', '').strip() or _default_step_description(
                    action=step['action'],
                    target=(step.get('target', '') or step.get('step_title', '')).strip(),
                    value=(step.get('value', '') or '').strip(),
                ),
                'action': step['action'],
                'target': (step.get('target', '') or step.get('step_title', '')).strip(),
                'locator_type': step.get('locator_type', 'css').strip() or 'css',
                'selector': step.get('selector', '').strip(),
                'value': step.get('value', '') or '',
                'note': step.get('note', '') or '',
            }
            for step in value
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        title = attrs.get('title')
        module = attrs.get('module')
        scenario = attrs.get('scenario')

        if not str(title or '').strip():
            if module and scenario:
                attrs['title'] = f'{module} - {scenario}'
            elif scenario:
                attrs['title'] = scenario
            else:
                attrs['title'] = 'Untitled Test Case'

        return attrs
