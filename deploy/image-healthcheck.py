#!/usr/bin/env python3
"""Fail Docker health checks on HTTP errors or a non-healthy JSON response."""
import json
import os
import urllib.request


def check(url=None):
    port = int(os.environ.get('URP_PORT', '4100'))
    target = url or f'http://127.0.0.1:{port}/lab/api/health'
    with urllib.request.urlopen(target, timeout=3) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or payload.get('status') != 'ok':
        raise RuntimeError(f'Gateway is not healthy: {payload!r}')


if __name__ == '__main__':
    check()
