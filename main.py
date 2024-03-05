import time
from string import Template
import json

import httpx
from pynput import keyboard
from pynput.keyboard import Key, Controller
import pyperclip

controller = Controller()


def fix_text(text):
    prompt = PROMPT_TEMPLATE.substitute(text=text)
    response = httpx.post(
        OLLAMA_ENDPOINT,
        json={"prompt": prompt, **OLLAMA_CONFIG},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )

    if response.status_code != 200:
        print("Error", response.status_code)
        return None

    content_type = response.headers.get("Content-Type", "")

    # Process application/json response
    if content_type.startswith("application/json"):
        print("JSON response")
        try:
            response_data = response.json()
            return response_data.get("response", "").strip()
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None

    # Process application/x-ndjson response
    elif content_type.startswith("application/x-ndjson"):
        print("NDJSON response")
        try:
            fixed_text = []
            for line in response.text.splitlines():
                line_data = json.loads(line)
                fixed_line = line_data.get("response", "").strip()
                fixed_text.append(fixed_line)
            return "\n".join(fixed_text)
        except json.JSONDecodeError as e:
            print(f"NDJSON decode error: {e}")
            return None

    else:
        print(f"Unsupported content type: {content_type}")
        return None


def fix_current_line():
    # macOS short cut to select current line: Cmd+Shift+Left
    controller.press(Key.cmd)
    controller.press(Key.shift)
    controller.press(Key.left)

    controller.release(Key.cmd)
    controller.release(Key.shift)
    controller.release(Key.left)

    fix_selection()


def fix_selection():
    # 1. Copy selection to clipboard
    with controller.pressed(Key.cmd):
        controller.tap("c")

    # 2. Get the clipboard string
    time.sleep(0.1)
    text = pyperclip.paste()

    # 3. Fix string
    if not text:
        return
    fixed_text = fix_text(text)
    if not fixed_text:
        return

    # 4. Paste the fixed string to the clipboard
    pyperclip.copy(fixed_text)
    time.sleep(0.1)

    # 5. Paste the clipboard and replace the selected text
    with controller.pressed(Key.cmd):
        controller.tap("v")


def on_f9():
    fix_current_line()


def on_f10():
    fix_selection()


with open("config.json", "r") as f:
    config = json.load(f)
    OLLAMA_ENDPOINT = config["ollama_endpoint"]
    OLLAMA_CONFIG = config["ollama_config"]
    if isinstance(config["prompt_template"], list):
        prompt_template_str = "\n".join(config["prompt_template"])
    else:
        prompt_template_str = config["prompt_template"]
    PROMPT_TEMPLATE = Template(prompt_template_str)

# OLLAMA_CONFIG = {
#    "model": "mistral",
#    "keep_alive": "5m",
#    "stream": False,
# }

'''
PROMPT_TEMPLATE = Template(
    """Fix all typos and casing and punctuation in this text, while preserving all new line characters:

$text

Return only the final corrected text. don't include the original text or any preamble.
"""
)
'''

print("Press F9 to fix the current line, F10 to fix the selected text.")
print(f"Using Ollama endpoint: {OLLAMA_ENDPOINT}")
print(f"Using Ollama config: {OLLAMA_CONFIG}")
print(f"Using Ollama endpoint: {PROMPT_TEMPLATE}")

with keyboard.GlobalHotKeys({"<101>": on_f9, "<109>": on_f10}) as h:
    h.join()
