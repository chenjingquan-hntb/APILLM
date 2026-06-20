"""Verify frontend-backend integration."""
from playwright.sync_api import sync_playwright
import json, sys

API_KEY = "sk-relay-d0f56f1221c906cce79d4688a6e5e26a452df6b1621348ce"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda err: errors.append(err.message))

    page.goto('http://127.0.0.1:8000/', wait_until='networkidle')

    # 1. Input API Key
    page.fill('#api-key-input', API_KEY)
    page.click('#api-key-apply')
    page.wait_for_timeout(1500)

    # 2. Key status
    key_status = page.locator('#key-status').text_content()

    # 3. Load models
    page.click('#model-load')
    page.wait_for_timeout(4000)
    model_status = page.locator('#model-status').text_content()
    model_count = page.locator('#model-count').text_content()

    # 4. Health status
    health = page.locator('#health-status').text_content()

    results = {
        'key_status': key_status,
        'model_status': model_status,
        'model_count': model_count,
        'health': health,
        'js_errors': len(errors),
    }

    page.screenshot(path='D:/workspace/LLMAPI/app/Web/screenshot_after.png', full_page=True)

    with open('D:/workspace/LLMAPI/app/Web/test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print('Test completed. Results saved to test_results.json')
    browser.close()
