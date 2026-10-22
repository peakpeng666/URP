#!/usr/bin/env python3
"""Read official registry metadata; refuse mirror byte-identity mismatch before npm runs."""
import json, pathlib, sys, urllib.parse, urllib.request
root = pathlib.Path(sys.argv[1])
lock = json.loads((root / 'src/frontend/package-lock.json').read_text())
count = 0
for key, pkg in lock['packages'].items():
    url = pkg.get('resolved')
    if not url:
        continue
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in {'registry.npmjs.org', 'registry.npmmirror.com'}:
        raise RuntimeError('non_allowlisted_npm_source')
    if parsed.hostname != 'registry.npmmirror.com':
        continue
    name = key.rsplit('node_modules/', 1)[-1]
    request = 'https://registry.npmjs.org/' + urllib.parse.quote(name, safe='') + '/' + urllib.parse.quote(pkg['version'], safe='')
    with urllib.request.urlopen(request, timeout=45) as response:
        metadata = json.load(response)
    integrity = metadata.get('dist', {}).get('integrity')
    if not integrity or integrity != pkg.get('integrity'):
        raise RuntimeError('npm_mirror_identity_mismatch')
    count += 1
print(json.dumps({'mirror_identities_verified': count}))
