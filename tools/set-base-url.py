#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point every absolute URL in the site at a new base.

The canonical link, the Open Graph and Twitter tags, every @id and url in the
JSON-LD, sitemap.xml, robots.txt and the base recorded in sync-jsonld.py all
have to agree, or search engines index one address and are told another.

    python3 tools/set-base-url.py https://gary2686.github.io/

Run it right after renaming the repository, then commit and push.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ['index.html', 'sitemap.xml', 'robots.txt', os.path.join('tools', 'sync-jsonld.py')]


def current_base():
    src = io.open(os.path.join(ROOT, 'tools', 'sync-jsonld.py'), encoding='utf-8').read()
    m = re.search(r'^BASE = "([^"]+)"', src, re.M)
    if not m:
        sys.exit('could not read the current base from tools/sync-jsonld.py')
    return m.group(1)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    new = sys.argv[1]
    if not new.startswith(('http://', 'https://')):
        sys.exit('the new base must start with http:// or https://')
    if not new.endswith('/'):
        new += '/'

    old = current_base()
    if old == new:
        print('already set to ' + new)
        return

    total = 0
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        src = io.open(path, encoding='utf-8').read()
        n = src.count(old)
        if not n:
            continue
        io.open(path, 'w', encoding='utf-8').write(src.replace(old, new))
        total += n
        print('%-24s %3d' % (rel, n))

    leftover = 0
    for rel in FILES:
        leftover += io.open(os.path.join(ROOT, rel), encoding='utf-8').read().count(old)
    if leftover:
        sys.exit('%d references to the old base survived' % leftover)

    print('\n%s\n  -> %s\n%d references rewritten.' % (old, new, total))
    print('Next: python3 tools/sync-jsonld.py, then commit and push.')


if __name__ == '__main__':
    main()
