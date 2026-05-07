STEP_ACTION_CHOICES = [
    ('launch_browser', 'Launch Browser'),
    ('open_page', 'Open Page'),
    ('click_button', 'Click Button'),
    ('input_text', 'Input Text'),
    ('press_key', 'Press Key'),
    ('verify_element', 'Verify Element'),
]

STEP_ACTION_VALUES = {value for value, _label in STEP_ACTION_CHOICES}
