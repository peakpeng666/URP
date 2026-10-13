"""No-model prototype: typed JSON tree -> unchanged validated math-dag-v1.
Never evaluates source text. Finite depth grammar; no model/backend imports.
"""
import json
import pathlib
import sys
ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'math_dag_v1' / 'src'))
from schema import StructureError, strict_json, validate_program

COEFFICIENTS = [-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 4.0, 10.0, 100.0, 500.0]
BINARY = ('add', 'sub', 'mul', 'div')
UNARY = ('exp', 'sqrt')
MAX_DEPTH = 2

def generation_schema():
    defs = {}
    def ref(t, d): return {'$ref': f'#/$defs/{t}{d}'}
    def seq(op, args):
        return {'type': 'array', 'prefixItems': [{'const': op}] + args,
                'minItems': len(args)+1, 'maxItems': len(args)+1}
    for d in range(MAX_DEPTH+1):
        s = [{'const': 'item'}, {'type': 'number', 'enum': COEFFICIENTS}]
        v = [{'const': 'bins'}]
        b = []
        if d:
            sr, vr = ref('s', d-1), ref('v', d-1)
            pairs = [(vr, vr), (vr, sr), (sr, vr)]
            s += [seq(op, [sr, sr]) for op in BINARY] + [seq(op, [sr]) for op in UNARY]
            v += [seq(op, list(p)) for op in BINARY for p in pairs] + [seq(op, [vr]) for op in UNARY]
            b += [seq('gt', list(p)) for p in pairs]
            if d >= 2:
                v += [seq('where', [ref('b', d-1), x, y]) for x in (sr, vr) for y in (sr, vr)]
        defs[f's{d}'] = {'anyOf': s}
        defs[f'v{d}'] = {'anyOf': v}
        if b: defs[f'b{d}'] = {'anyOf': b}
    return {'$schema': 'https://json-schema.org/draft/2020-12/schema',
            'type': 'object', 'properties': {'schema': {'const': 'typed-tree-v1'}, 'score': ref('v', MAX_DEPTH)},
            'required': ['schema', 'score'], 'additionalProperties': False, '$defs': defs}

def compile_tree(raw):
    if type(raw) is not bytes or len(raw) > 8192:
        raise StructureError('tree byte limit/type')
    try: obj = strict_json(raw.decode('utf-8'))
    except UnicodeError as exc: raise StructureError('UTF8 required') from exc
    if type(obj) is not dict or set(obj) != {'schema', 'score'} or obj['schema'] != 'typed-tree-v1':
        raise StructureError('tree top-level schema')
    constants, nodes, constant_ids, node_ids = [], [], {}, {}
    def constant(x):
        value = float(x)
        key = value.hex()
        if key not in constant_ids:
            constant_ids[key] = 'c'+str(len(constants))
            constants.append({'type': 'f64', 'value': value})
        return constant_ids[key]
    def node(op, args):
        key = (op, *args)
        if key not in node_ids:
            node_ids[key] = len(nodes)
            nodes.append(list(key))
        return node_ids[key]
    def walk(x, depth):
        if depth < 0: raise StructureError('tree depth')
        if type(x) in (int, float) and x in COEFFICIENTS:
            return constant(x), 's'
        if type(x) is str and x in ('item', 'bins'):
            return node('mul', [x, constant(1.0)]), 's' if x == 'item' else 'v'
        if type(x) is not list or not x or type(x[0]) is not str:
            raise StructureError('tree term')
        op = x[0]
        arity = 2 if op in BINARY or op == 'gt' else 1 if op in UNARY else 3 if op == 'where' else -1
        if len(x) != arity+1 or not depth: raise StructureError('tree operation/arity/depth')
        children = [walk(y, depth-1) for y in x[1:]]
        args, types = zip(*children)
        if op == 'where':
            if types[0] != 'b' or any(t not in ('s', 'v') for t in types[1:]):
                raise StructureError('tree where types')
            out = 'v'
        else:
            if any(t not in ('s', 'v') for t in types): raise StructureError('tree numeric types')
            if op == 'gt':
                if 'v' not in types: raise StructureError('tree gt requires vector')
                out = 'b'
            else: out = 'v' if 'v' in types else 's'
        return node(op, args), out
    result, tag = walk(obj['score'], MAX_DEPTH)
    if tag != 'v': raise StructureError('tree root must be numeric vector')
    # Depth 2 has <=4 authored operators, plus <=2 input casts; CSE only reduces this.
    if len(nodes) > 6: raise StructureError('compiled node bound')
    dag = {'schema': 'math-dag-v1', 'description': 'Compiled typed tree v1',
           'constants': constants, 'nodes': nodes, 'return_node': result}
    encoded = json.dumps(dag, separators=(',', ':'), allow_nan=False).encode()
    return validate_program(encoded), dag

if __name__ == '__main__':
    (ROOT/'generation_schema.json').write_text(json.dumps(generation_schema(), indent=2)+'\n')
