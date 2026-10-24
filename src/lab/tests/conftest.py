"""Keep evolve offline contracts independent of any real field cache on the host."""
from functools import lru_cache

import pytest


@pytest.fixture(autouse=True)
def isolated_evolve_field_cache(request, tmp_path, monkeypatch):
    if not request.node.path.name.startswith('test_evolve_'):
        return
    from urp_lab.library import fields

    isolated = tmp_path / 'isolated-fields2benchmark'
    isolated.mkdir()
    monkeypatch.setattr(fields, 'DIR', isolated)
    monkeypatch.setattr(fields, 'INDEX', isolated / 'index.json')
    # Replace memoization wrappers, rather than clearing or reading host cache entries.
    monkeypatch.setattr(fields, '_index', lru_cache(maxsize=1)(fields._index.__wrapped__))
    monkeypatch.setattr(fields, '_scenario', lru_cache(maxsize=64)(fields._scenario.__wrapped__))

    def blocked_download(*args, **kwargs):
        raise AssertionError('Evolve offline contracts must not download field data')

    monkeypatch.setattr(fields, '_download', blocked_download)
