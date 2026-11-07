#!/usr/bin/env python3
"""Build the SpaceXTV Kodi repository and the release zips.

    python3 tools/build_repo.py OUT

OUT/site/  -> GitHub Pages = the Kodi repository (addons.xml, md5, zips, icons, index.html)
OUT/dist/  -> files attached to the GitHub release
OUT/VERSION, OUT/NOTES.md -> SpaceXTV version and release notes

Only the standard library - runs the same on a Mac and on GitHub Actions.
"""
import hashlib
import html
import os
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = 'plugin.program.spacextv'
REPO = 'repository.spacextv'
URL = 'https://beboss.github.io/spacextv/'
GITHUB = 'https://github.com/beBoss/spacextv'


def junk(name):
    return (name.startswith('._') or name in ('.DS_Store', 'Thumbs.db', '__pycache__')
            or name.endswith(('.pyc', '.pyo')) or name.startswith('.git'))


def read_addon(addon_id):
    path = os.path.join(ROOT, addon_id, 'addon.xml')
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    root = ET.fromstring(raw.encode('utf-8'))
    if root.tag != 'addon' or root.get('id') != addon_id:
        sys.exit('%s: wrong add-on id %r' % (path, root.get('id')))
    version = root.get('version') or ''
    if not re.match(r'^\d{4}\.\d{2}\.\d{2}\.\d{4}\.7$', version):
        sys.exit('%s: version %r must look like YYYY.MM.DD.HHMM.7' % (path, version))
    body = re.sub(r'^\s*<\?xml[^>]*\?>\s*', '', raw).strip()
    assets = []
    for tag in ('icon', 'fanart', 'banner', 'clearlogo', 'screenshot'):
        for e in root.iter(tag):
            if e.text and e.text.strip():
                assets.append(e.text.strip())
    news = (root.findtext('.//news') or '').strip()
    return version, body, assets, news


def _dir_entry(name):
    zi = zipfile.ZipInfo(name)
    zi.external_attr = (0o40755 << 16) | 0x10      # a normal folder on every system
    return zi


def make_zip(addon_id, dest):
    """<addon_id>/... inside the zip, without macOS / Python junk."""
    base = os.path.join(ROOT, addon_id)
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(_dir_entry(addon_id + '/'), '')
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if not junk(d))
            rel_dir = os.path.relpath(dirpath, base).replace(os.sep, '/')
            for d in dirnames:
                rel = d if rel_dir == '.' else rel_dir + '/' + d
                z.writestr(_dir_entry(addon_id + '/' + rel + '/'), '')
            for fn in sorted(filenames):
                if junk(fn):
                    continue
                rel = fn if rel_dir == '.' else rel_dir + '/' + fn
                z.write(os.path.join(dirpath, fn), addon_id + '/' + rel)
    with zipfile.ZipFile(dest) as z:
        bad = z.testzip()
        if bad:
            sys.exit('broken zip entry %s in %s' % (bad, dest))


def index_html(repo_zip, version):
    # Kodi reads this page as a folder: it lists <a href="X">X</a> links (text = link).
    e = html.escape
    return '''<!DOCTYPE html>
<html lang="bg">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpaceXTV Repository</title>
<style>
body{font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;margin:0 auto;padding:24px 16px;background:#fff;color:#1d1d1f}
code{background:#f2f2f4;padding:2px 6px;border-radius:4px;word-break:break-all}
a{color:#0a58ca}
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}code{background:#222}a{color:#7ab7ff}}
</style>
</head>
<body>
<h1>SpaceXTV Repository</h1>
<p>Bulsat телевизия на живо и ТВ програма за Kodi.<br>Bulsat live TV and TV guide for Kodi.</p>
<ul>
<li><a href="%(zip)s">%(zip)s</a> - Kodi repository / хранилище</li>
</ul>
<p>Kodi: <b>File manager &rarr; Add source</b> &rarr; <code>%(url)s</code><br>
then <b>Install from zip file</b> &rarr; <code>%(zip)s</code></p>
<p>SpaceXTV %(ver)s &middot; <a href="%(gh)s">GitHub</a> &middot; GPL-3.0</p>
</body>
</html>
''' % {'zip': e(repo_zip), 'url': e(URL), 'ver': e(version), 'gh': e(GITHUB)}


def main(out):
    site, dist = os.path.join(out, 'site'), os.path.join(out, 'dist')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(site)
    os.makedirs(dist)

    bodies, versions, news = [], {}, ''
    for addon_id in (PLUGIN, REPO):
        version, body, assets, n = read_addon(addon_id)
        versions[addon_id] = version
        bodies.append(body)
        if addon_id == PLUGIN:
            news = n
        folder = os.path.join(site, addon_id)
        os.makedirs(folder)
        # Kodi's updater: <datadir>/<id>/<id>-<version>.zip, artwork next to it
        zpath = os.path.join(folder, '%s-%s.zip' % (addon_id, version))
        make_zip(addon_id, zpath)
        for a in assets:
            src = os.path.join(ROOT, addon_id, a)
            if not os.path.isfile(src):
                sys.exit('%s: missing asset %s' % (addon_id, a))
            dst = os.path.join(folder, a)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)

    addons = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'
              + '\n'.join(bodies) + '\n</addons>\n').encode('utf-8')
    ET.fromstring(addons)       # must be valid XML
    with open(os.path.join(site, 'addons.xml'), 'wb') as f:
        f.write(addons)
    with open(os.path.join(site, 'addons.xml.md5'), 'w') as f:
        f.write(hashlib.md5(addons).hexdigest())

    # fixed names for links that never change
    repo_zip = REPO + '.zip'
    shutil.copy2(os.path.join(site, REPO, '%s-%s.zip' % (REPO, versions[REPO])),
                 os.path.join(site, repo_zip))
    with open(os.path.join(site, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html(repo_zip, versions[PLUGIN]))
    open(os.path.join(site, '.nojekyll'), 'w').close()

    shutil.copy2(os.path.join(site, PLUGIN, '%s-%s.zip' % (PLUGIN, versions[PLUGIN])), dist)
    shutil.copy2(os.path.join(site, repo_zip), dist)

    with open(os.path.join(out, 'VERSION'), 'w') as f:
        f.write(versions[PLUGIN])
    latest = news.split('[CR]')[0].strip()
    latest = re.sub(r'^\S+\s+-\s+', '', latest)
    with open(os.path.join(out, 'NOTES.md'), 'w', encoding='utf-8') as f:
        f.write('%s\n\n'
                '**Install with automatic updates / Инсталиране с автоматично обновяване:** '
                'Kodi → File manager → Add source → `%s` → Install from zip file → `%s`\n\n'
                '**Only the add-on / Само адона:** `%s-%s.zip` below (no automatic updates).\n\n'
                'Instructions / Инструкции: %s#readme\n'
                % (latest, URL, repo_zip, PLUGIN, versions[PLUGIN], GITHUB))
    print('SpaceXTV %s, repository %s -> %s' % (versions[PLUGIN], versions[REPO], out))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(os.path.abspath(sys.argv[1]))
