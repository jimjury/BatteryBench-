"""Check that JSON source files and committed browser wrappers match exactly."""
import json
import re
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.scripts=[]
    def handle_starttag(self, tag, attrs):
        options=dict(attrs)
        if 'id' in options:
            self.ids.append(options['id'])
        if tag=='script' and 'src' in options:
            self.scripts.append(options['src'])


def main():
    for key, filename, dest in [
        ('CELLSCOPE_CATALOG','catalog.json','catalog.generated.js'),
        ('CELLSCOPE_DEMO_RUN','demo_run.json','demo.generated.js')]:
        data=json.loads((ROOT/'web/data'/filename).read_text(encoding='utf-8'))
        text=(ROOT/'web/assets'/dest).read_text(encoding='utf-8')
        match=re.search(rf'window\.{key} = (.+);\s*$',text,re.DOTALL)
        assert match, f'{dest} is missing or malformed'
        assert json.loads(match.group(1))==data, f'{dest} is stale: run scripts/sync_assets.py'
    page=PageParser()
    page.feed((ROOT/'web/index.html').read_text(encoding='utf-8'))
    assert len(page.ids)==len(set(page.ids)), 'Repeated HTML IDs'
    assert len(page.ids)>=70
    for relative in page.scripts:
        assert (ROOT/'web'/relative).is_file(), f'Broken script reference: {relative}'
    print(f'PASS assets, {len(page.ids)} unique IDs, {len(page.scripts)} local script refs')


if __name__=='__main__':
    main()
