"""Optional real Chromium interaction test: python tests/browser_smoke.py"""
from pathlib import Path
import json
from tempfile import TemporaryDirectory
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run():
    errors = []
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    url = f'http://127.0.0.1:{server.server_port}/web/index.html'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        desktop = browser.new_context(viewport={'width': 1440, 'height': 900}, device_scale_factor=1, accept_downloads=True)
        page = desktop.new_page()
        page.on('pageerror', lambda ex: errors.append(str(ex)))
        page.goto(url, wait_until='load')
        page.wait_for_selector('.dataset-card', timeout=15000)
        assert page.locator('.dataset-card').count() == 12
        assert 'CELL' in page.title()
        page.screenshot(path='/mnt/data/CellScope-Lab-preview-desktop.png',full_page=True)
        # Catalog search + modal
        page.locator('#dataset-search').fill('HUST')
        assert page.locator('.dataset-card').count() == 1
        page.locator('.dataset-card').click()
        assert page.locator('#dataset-modal').is_visible()
        assert page.locator('#modal-body a').count() == 1
        page.keyboard.press('Escape')
        assert not page.locator('#dataset-modal').is_visible()
        page.locator('#dataset-search').fill('')
        page.locator('[data-filter="multi-ion"]').click()
        assert page.locator('.dataset-card').count() == 1
        page.locator('[data-filter="all"]').click()
        # Signal processing controls
        page.locator('#pipe-step').fill('3')
        assert page.locator('#pipe-out').inner_text() == '80'
        page.locator('#pipe-window').fill('16')
        assert page.locator('#pipe-windows').inner_text() == '64'
        page.locator('#pipe-norm').select_option('minmax')
        # Split audit warning
        page.locator('#split-unit').select_option('cycle')
        assert '⚠' in page.locator('#split-note').inner_text()
        # Dynamic model explorer
        page.locator('[data-model="transformer"]').click()
        assert 'Transformer Encoder' in page.locator('#model-title').inner_text()
        page.locator('.flow-step').nth(2).click()
        assert 'LAYER 03' in page.locator('#inspector-number').inner_text()
        page.locator('#model-play').click()
        assert '暂停' in page.locator('#model-play').inner_text()
        page.locator('#model-play').click()
        # Run config, task restrictions, download
        page.locator('#exp-task').select_option('soh')
        assert page.locator('#exp-split').input_value() == 'battery'
        assert page.locator('#exp-window').input_value() == '6'
        with page.expect_download() as download_info:
            page.locator('#exp-download').click()
        assert download_info.value.suggested_filename.startswith('cellscope_soh_')
        # Results import
        sample = json.loads((ROOT / 'web/data/demo_run.json').read_text(encoding='utf-8'))
        sample['source']['synthetic'] = False  # only for UI import state; do not imply scientific validity
        with TemporaryDirectory() as temp:
            file = Path(temp) / 'imported_metrics.json'
            file.write_text(json.dumps(sample), encoding='utf-8')
            page.locator('#result-upload').set_input_files(str(file))
        assert 'IMPORTED EXPERIMENT' in page.locator('#result-source').inner_text()
        assert 'SOC' in page.locator('#result-source').inner_text()
        page.locator('#result-reset').click()
        assert 'SYNTHETIC DEMO' in page.locator('#result-source').inner_text()
        page.locator('#theme-toggle').click()
        assert 'light' in page.locator('body').get_attribute('class')
        page.locator('#theme-toggle').click()
        assert not errors, errors
        # Check desktop viewport overflow (side panels fit)
        width=page.evaluate('document.documentElement.scrollWidth')
        assert width <= 1445, f'overflow at desktop: {width}'
        # Mobile layouts
        mob=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=1)
        mp=mob.new_page();mp.on('pageerror',lambda ex:errors.append(str(ex)))
        mp.goto(url,wait_until='load')
        mp.wait_for_selector('.dataset-card')
        assert mp.locator('.dataset-card').count() == 12
        mp.locator('#nav-toggle').click()
        assert 'open' in mp.locator('#sidebar').get_attribute('class')
        mp.locator('[data-section="models"]').click()
        assert not mp.locator('#sidebar').get_attribute('class').endswith('open')
        mp.screenshot(path='/mnt/data/CellScope-Lab-preview-mobile.png',full_page=True)
        mobile_width=mp.evaluate('document.documentElement.scrollWidth')
        assert mobile_width <= 393, f'overflow at mobile: {mobile_width}'
        assert not errors, errors
        print('Browser QA PASS: 12 datasets, modal, search, filtering, pipeline, split audit, model animation, config download, JSON import, theme, mobile nav')
        print('Desktop overflow width:',width,'Mobile overflow width:',mobile_width)
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    run()
