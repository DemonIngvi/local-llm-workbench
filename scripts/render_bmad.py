#!/usr/bin/env python3
"""Render BMAD Markdown sources as a standalone, offline HTML document."""
import html
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
PLANNING = ROOT / '_bmad-output' / 'planning-artifacts'
IMPLEMENTATION = ROOT / '_bmad-output' / 'implementation-artifacts'
OUTPUT = ROOT / 'docs' / 'bmad.html'
ORDER = ['product-brief.md', 'prd.md', 'architecture.md', 'harness-research.md',
         'epics.md', 'implementation-readiness.md', 'sprint-status.md']


def inline(text):
    text = html.escape(text, quote=True)
    # Allow only web URLs. Escaped text remains escaped in labels and attributes.
    text = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r'<a href="\2" rel="noopener noreferrer">\1</a>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def markdown(text):
    result = []
    paragraph = []
    in_list = False
    in_code = False

    def flush():
        if paragraph:
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            result.append('</ul>')
            in_list = False

    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            close_list()
            result.append('</code></pre>' if in_code else '<pre><code>')
            in_code = not in_code
            continue
        if in_code:
            result.append(html.escape(line) + '\n')
            continue
        heading = re.match(r'^(#{1,6})\s+(.+)$', line)
        item = re.match(r'^\s*[-*]\s+(.+)$', line)
        if heading:
            flush()
            close_list()
            level = min(len(heading.group(1)) + 1, 6)
            result.append(f'<h{level}>' + inline(heading.group(2)) + f'</h{level}>')
        elif item:
            flush()
            if not in_list:
                result.append('<ul>')
                in_list = True
            result.append('<li>' + inline(item.group(1)) + '</li>')
        elif not line.strip():
            flush()
            close_list()
        else:
            close_list()
            paragraph.append(line.strip())
    flush()
    close_list()
    if in_code:
        result.append('</code></pre>')
    return '\n'.join(result)


def source_files():
    files = [p for folder in (PLANNING, IMPLEMENTATION) for p in folder.glob('*.md')]
    ranks = {name: index for index, name in enumerate(ORDER)}
    return sorted(files, key=lambda p: (ranks.get(p.name, len(ranks)), p.name))


def render(files):
    menu = []
    sections = []
    for index, path in enumerate(files, 1):
        content = path.read_text(encoding='utf-8')
        title = next((line[2:].strip() for line in content.splitlines() if line.startswith('# ')), path.stem)
        anchor = 'document-' + str(index)
        menu.append(f'<li><a href="#{anchor}">{html.escape(title)}</a></li>')
        source = path.relative_to(ROOT).as_posix()
        sections.append(f'<section id="{anchor}" class="document"><div class="source">Источник: {html.escape(source)}</div>{markdown(content)}</section>')
    return '''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local LLM Workbench — план и документация</title>
<style>
:root{color-scheme:light;--ink:#182537;--muted:#53657b;--line:#dce4ed;--accent:#2859a5}
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}
header{background:#15283f;color:white;padding:2.2rem max(1.5rem,calc((100vw - 1200px)/2))}header h1{margin:0;font-size:clamp(1.6rem,3vw,2.4rem)}header p{margin:.5rem 0 0;color:#cfdef2}
.layout{max-width:1200px;margin:0 auto;padding:1.5rem;display:grid;grid-template-columns:260px minmax(0,1fr);gap:1.5rem;align-items:start}
nav{position:sticky;top:1rem;background:white;border:1px solid var(--line);border-radius:12px;padding:1rem}nav strong{display:block}nav ul{padding-left:1.2rem;margin:.5rem 0}nav li{margin:.4rem 0}a{color:var(--accent);overflow-wrap:anywhere}
.document{scroll-margin-top:1rem;background:white;border:1px solid var(--line);border-radius:12px;padding:1.5rem 2rem;margin-bottom:1.3rem;overflow-wrap:anywhere}
.document h2{line-height:1.25;margin:.45rem 0 1rem;font-size:1.6rem}.document h3{margin-top:1.6rem}.source{font-size:.75rem;color:var(--muted)}code{background:#eef2f7;border-radius:4px;padding:.12em .3em;font-size:.9em}pre{overflow:auto;background:#182537;color:#f4f8ff;padding:1rem;border-radius:8px}pre code{background:transparent;padding:0}li{margin:.25rem 0}
@media(max-width:760px){.layout{display:block}nav{position:static;margin-bottom:1rem}.document{padding:1.2rem}}@media print{body{background:white}nav{position:static}.layout{display:block}.document{break-inside:avoid;border:0;padding:0}}
</style></head><body><header><h1>Local LLM Workbench</h1><p>План проекта и документация · пользовательская HTML-версия</p></header>
<div class="layout"><nav aria-label="Содержание"><strong>Содержание</strong><ul>''' + '\n'.join(menu) + '''</ul><small>Сформировано из Markdown-файлов проекта. Откройте локально, без сервера.</small></nav><main>''' + '\n'.join(sections) + '''</main></div></body></html>\n'''


def main():
    files = source_files()
    if not files:
        raise SystemExit('No BMAD documents found')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(files), encoding='utf-8')
    print(f'Generated {OUTPUT} from {len(files)} Markdown documents')


if __name__ == '__main__':
    main()
