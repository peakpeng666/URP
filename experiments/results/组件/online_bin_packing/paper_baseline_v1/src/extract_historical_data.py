"""Data-only recognizer for the three frozen 2024 EoH numeric pickle files.

This is NOT a pickle virtual machine. A fixed, observed grammar is matched token
by token. NumPy globals, REDUCE and BUILD are inert syntax; no payload callable
is resolved/invoked and no NumPy import occurs. Only four-byte little-endian
signed integer payloads become exact Python ints. Unknown variants fail closed.
"""
import collections
import hashlib
import json
import pathlib
import pickletools

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAX_BYTES = 800_000
MAX_OPS = 500_000
COMMIT = 'e4b5ddba03b2b88025747e11c6049f8b529a4368'
ANY = object()


class NumericGrammarError(ValueError):
    pass


class Tokens:
    def __init__(self, raw):
        if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
            raise NumericGrammarError('byte bound/type')
        self.raw = raw
        self.it = iter(pickletools.genops(raw))
        self.counts = collections.Counter()
        self.frames = []
        self.total = 0
        self.memo = 0

    def next(self):
        while True:
            try:
                op, arg, pos = next(self.it)
            except (StopIteration, ValueError, OverflowError) as e:
                raise NumericGrammarError('invalid or incomplete opcode stream') from e
            self.total += 1
            if self.total > MAX_OPS:
                raise NumericGrammarError('opcode bound')
            name = op.name
            self.counts[name] += 1
            if name == 'FRAME':
                if type(arg) is not int or arg <= 0 or pos + 9 + arg > len(self.raw):
                    raise NumericGrammarError('invalid frame length')
                if (not self.frames and pos != 2) or (self.frames and self.frames[-1][1] != pos):
                    raise NumericGrammarError('noncontiguous frame')
                self.frames.append((pos + 9, pos + 9 + arg))
                continue
            if pos != 0 and (not self.frames or not self.frames[-1][0] <= pos < self.frames[-1][1]):
                raise NumericGrammarError('unframed token')
            if name == 'MEMOIZE':
                self.memo += 1
                if self.memo > 150_018:
                    raise NumericGrammarError('memo bound')
            return name, arg, pos

    def expect(self, name, arg=ANY):
        actual, value, pos = self.next()
        if actual != name or (arg is not ANY and (type(value) is not type(arg) or value != arg)):
            raise NumericGrammarError(f'expected {name} at {pos}; got {actual}')
        return value

    def sequence(self, expected):
        for name, arg in expected:
            self.expect(name, arg)

    def finish(self):
        name, _, pos = self.next()
        if name != 'STOP' or pos != len(self.raw) - 1:
            raise NumericGrammarError('missing STOP or trailing bytes')
        if not self.frames or self.frames[-1][1] != len(self.raw):
            raise NumericGrammarError('incomplete frame coverage')
        try:
            next(self.it)
        except StopIteration:
            return
        raise NumericGrammarError('unexpected token after STOP')


PREAMBLE = [
    ('SHORT_BINUNICODE', 'numpy.core.multiarray'), ('MEMOIZE', None),
    ('SHORT_BINUNICODE', 'scalar'), ('MEMOIZE', None),
    ('STACK_GLOBAL', None), ('MEMOIZE', None),
    ('SHORT_BINUNICODE', 'numpy'), ('MEMOIZE', None),
    ('SHORT_BINUNICODE', 'dtype'), ('MEMOIZE', None),
    ('STACK_GLOBAL', None), ('MEMOIZE', None),
    ('SHORT_BINUNICODE', 'i4'), ('MEMOIZE', None),
    ('NEWFALSE', None), ('NEWTRUE', None), ('TUPLE3', None),
    ('MEMOIZE', None), ('REDUCE', None), ('MEMOIZE', None),
    ('MARK', None), ('BININT1', 3), ('SHORT_BINUNICODE', '<'),
    ('MEMOIZE', None), ('NONE', None), ('NONE', None), ('NONE', None),
    ('BININT', -1), ('BININT', -1), ('BININT1', 0),
    ('TUPLE', None), ('MEMOIZE', None), ('BUILD', None),
]
SCALAR_END = [('MEMOIZE', None), ('TUPLE2', None), ('MEMOIZE', None),
              ('REDUCE', None), ('MEMOIZE', None)]


def decode_numeric_pickle_with_audit(raw):
    """Return primitive data and opcode audit; recognize only frozen <i4 format."""
    t = Tokens(raw)
    t.expect('PROTO', 4)
    t.expect('EMPTY_DICT', None)
    t.expect('MEMOIZE', None)
    n = t.expect('BININT2')
    if type(n) is not int or n not in (1000, 5000, 10000):
        raise NumericGrammarError('unsupported item count')
    t.sequence([('EMPTY_LIST', None), ('MEMOIZE', None), ('MARK', None)])
    instances = []
    first = True
    for _ in range(5):
        t.sequence([('EMPTY_LIST', None), ('MEMOIZE', None)])
        items = []
        for _ in range(n // 1000):
            t.expect('MARK', None)
            for _ in range(1000):
                if first:
                    t.sequence(PREAMBLE)
                    first = False
                else:
                    t.sequence([('BINGET', 5), ('BINGET', 11)])
                payload = t.expect('SHORT_BINBYTES')
                if type(payload) is not bytes or len(payload) != 4:
                    raise NumericGrammarError('non-i4 scalar payload')
                value = int.from_bytes(payload, byteorder='little', signed=True)
                if not 1 <= value <= 100:
                    raise NumericGrammarError('item outside [1,100]')
                items.append(value)
                t.sequence(SCALAR_END)
            t.expect('APPENDS', None)
        instances.append(items)
    t.sequence([('APPENDS', None), ('SETITEM', None)])
    t.finish()
    if t.memo != 15 * n + 18:
        raise NumericGrammarError('unexpected memo count')
    audit = {'opcodes': dict(t.counts), 'opcode_count': t.total,
             'frames': t.frames, 'original_item_dtype': '<i4',
             'original_scalar_type': 'numpy.int32', 'decoded_item_type': 'exact Python int',
             'payload_globals_resolved': 0, 'payload_reducers_invoked': 0,
             'n': n, 'instances': 5}
    return {n: instances}, audit


def decode_numeric_pickle(raw):
    return decode_numeric_pickle_with_audit(raw)[0]


def hash_json(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


def prepare():
    # These are our own data-only helpers, not modules from the upstream tree.
    from extract_data import embedded_data, validate_lists, decode_numeric_pickle as decode_current
    historical = ROOT / 'upstream' / 'historical'
    provenance = json.loads((historical / 'provenance.json').read_text())
    if provenance['commit'] != COMMIT:
        raise NumericGrammarError('unexpected historical commit')
    verified = {r['path']: r for r in provenance['files']}

    def read(path):
        raw = (historical / path).read_bytes()
        record = verified[path]
        if (len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']
                or hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest() != record['git_blob_sha1']):
            raise NumericGrammarError('historical source integrity mismatch')
        return raw

    sets, reports, records = {}, {}, []
    for suffix, n in [('1k', 1000), ('5k', 5000), ('10k', 10000)]:
        name = f'test_dataset_{suffix}'
        path = f'examples/bp_online/evaluation/testingdata/{name}.pkl'
        data, audit = decode_numeric_pickle_with_audit(read(path))
        lists = validate_lists(data, n)
        sets[name] = lists
        reports[name] = dict(audit, source_path=path, source_sha256=verified[path]['sha256'],
                            numeric_sha256=hash_json(data), ordered_lists_sha256=hash_json(lists),
                            sums=[sum(x) for x in lists], minima=[min(x) for x in lists],
                            maxima=[max(x) for x in lists], instance_item_hashes=[hash_json(x) for x in lists])
        for i, items in enumerate(lists):
            records.append({'id': f'{name}_{i}', 'source_set': name, 'source_index': i,
                            'n': n, 'items': items, 'items_sha256': hash_json(items),
                            'source_dtype': '<i4'})

    for name, path in [
        ('historical_design_5k', 'eoh/src/eoh/problems/optimization/bp_online/get_instance.py'),
        ('historical_eval_embedded_5k', 'examples/bp_online/evaluation/get_instance.py')]:
        embedded = embedded_data(read(path))
        if list(embedded) != [f'test_{i}' for i in range(5)]:
            raise NumericGrammarError('embedded keys')
        lists = [v['items'] for v in embedded.values()]
        validate_lists({5000: lists}, 5000)
        if any(v['num_items'] != 5000 for v in embedded.values()):
            raise NumericGrammarError('embedded count')
        sets[name] = lists
        reports[name] = {'source_path': path, 'ordered_lists_sha256': hash_json(lists),
                         'literal_capacities': [v['capacity'] for v in embedded.values()],
                         'source_dtype': 'Python int literal', 'instance_item_hashes': [hash_json(x) for x in lists]}

    current_prov = json.loads((ROOT / 'upstream' / 'provenance.json').read_text())
    current_verified = {v['path']: v for v in current_prov['files']}
    current_sets = {}
    for name in ('test_dataset_1k', 'test_dataset_5k', 'test_dataset_10k', 'training_dataset_5k'):
        path = f'examples/bp_online/testingdata/{name}.pkl'
        raw = (ROOT / 'upstream' / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != current_verified[path]['sha256']:
            raise NumericGrammarError('current source integrity mismatch')
        data, _ = decode_current(raw)
        n = next(iter(data))
        current_sets['current_' + name] = validate_lists(data, n)
    path = 'examples/bp_online/get_instance.py'
    raw = (ROOT / 'upstream' / path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != current_verified[path]['sha256']:
        raise NumericGrammarError('current embedded integrity mismatch')
    current_sets['current_embedded_design_5k'] = [v['items'] for v in embedded_data(raw).values()]

    combined = dict(sets, **current_sets)
    comparisons = []
    for i, left in enumerate(combined):
        for right in list(combined)[i + 1:]:
            a, b = combined[left], combined[right]
            exact = [{'left': j, 'right': k} for j, x in enumerate(a) for k, y in enumerate(b) if x == y]
            prefixes = [{'left': j, 'right': k, 'length': min(len(x), len(y))}
                        for j, x in enumerate(a) for k, y in enumerate(b)
                        if len(x) != len(y) and x[:min(len(x), len(y))] == y[:min(len(x), len(y))]]
            comparisons.append({'left': left, 'right': right, 'ordered_equal': a == b,
                                'exact_matches': exact, 'full_shorter_prefix_matches': prefixes})

    output = {'schema_version': 1, 'source_commit': COMMIT,
              'source_commit_date': provenance['commit_date'], 'sets': sets,
              'instances': records,
              'scope': 'Historical 2024 official item sequences; capacity is assigned by the corrected host'}
    audit = {'source_commit': COMMIT, 'source_commit_date': provenance['commit_date'],
             'current_comparison_commit': current_prov['commit'], 'sets': reports,
             'current_comparison_hashes': {k: hash_json(v) for k, v in current_sets.items()},
             'comparisons': comparisons,
             'historical_training_named_pickle': 'absent from the complete pinned 2024 repository tree',
             'data_source_note': 'Training/design uses embedded historical_design_5k; no absent historical training pickle is fabricated.',
             'statistical_note': 'No exact/prefix overlap does not establish statistical independence or unseen generalization.',
             'safety': {'upstream_modules_imported': 0, 'pickle_load_calls': 0,
                        'payload_globals_resolved': 0, 'payload_reducers_invoked': 0, 'solver_calls': 0}}
    (ROOT / 'data').mkdir(exist_ok=True)
    for name, value in [('historical_numeric.json', output), ('historical_data_audit.json', audit)]:
        with (ROOT / 'data' / name).open('x') as f:
            json.dump(value, f, indent=2)
            f.write('\n')
    print(json.dumps({'sets': reports, 'overlapping_pairs': [v for v in comparisons if v['exact_matches']]}, indent=2))


if __name__ == '__main__':
    prepare()
