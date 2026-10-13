import json
import random
import unittest
import warnings
import numpy as np
from jsonschema import Draft202012Validator, ValidationError
from typed_tree import compile_tree, generation_schema, COEFFICIENTS, StructureError
from interpreter import evaluate, pack, WorkBudget, NumericInvalid

SCHEMA = generation_schema()
VALIDATOR = Draft202012Validator(SCHEMA)
def obj(score): return {'schema': 'typed-tree-v1', 'score': score}
def compile(score): return compile_tree(json.dumps(obj(score)).encode())[0]
def scores(score, item=5, bins=(5,25,40)):
    return evaluate(compile(score), np.int32(item), np.array(bins,dtype=np.int64), WorkBudget())['scores']

class ContractTests(unittest.TestCase):
    def test_schema_is_valid(self): Draft202012Validator.check_schema(SCHEMA)
    def test_hand_calculations(self):
        cases = [
            ('bins', [5,25,40]),
            (['mul','bins',0.0], [0,0,0]),
            (['mul','bins',-1.0], [-5,-25,-40]),
            (['sub','bins','item'], [0,20,35]),
            (['div',['sub','bins','item'],'item'], [0,4,7]),
            (['where',['gt','bins',10.0],['sub',100.0,'bins'],0.0], [0,75,60]),
            (['where',['gt','bins',10.0],1.0,0.0], [0,1,1]),
            (['sqrt',['sub','bins','item']], [0,np.sqrt(20),np.sqrt(35)]),
        ]
        for tree,want in cases:
            with self.subTest(tree=tree):
                VALIDATOR.validate(obj(tree))
                np.testing.assert_allclose(scores(tree), want)
    def test_packing_direction_and_first_tie(self):
        items=[6,4,6,4]
        for tree in (['mul','bins',0.0], ['mul','bins',-1.0]):
            out=pack(compile(tree),items,10,WorkBudget())
            self.assertEqual(out['assignment'],[0,0,1,1])
        out=pack(compile('bins'),items,10,WorkBudget())
        self.assertEqual(out['used_bins'],4)
    def test_invalid_type_and_references(self):
        bad=['c0', 0, 'item', ['gt','bins',1.0], ['where','bins',1.0,0.0],
             ['where',['gt','item',1.0],1.0,0.0], ['add',['gt','bins',1.0], 'bins'],
             ['add','bins',True], ['add','bins',3.0], ['exec','bins'],
             ['add','bins'], ['add','bins',1.0,2.0],
             ['sqrt',['sqrt',['sqrt','bins']]]]
        for tree in bad:
            with self.subTest(tree=tree):
                with self.assertRaises(ValidationError): VALIDATOR.validate(obj(tree))
                with self.assertRaises(StructureError): compile(tree)
    def test_json_bounds_and_duplicate_keys(self):
        for raw in (b'{"schema":"typed-tree-v1","score":"bins","score":"item"}',
                    b'{"schema":"typed-tree-v1","score":NaN}',
                    b'{"schema":"typed-tree-v1","score":"bins","extra":1}',
                    b' '*8193, b'\xff'):
            with self.assertRaises(StructureError): compile_tree(raw)
    def test_no_numeric_safety_claim(self):
        for tree in (['div','bins',0.0], ['sqrt',['sub','item','bins']], ['exp',['mul','bins',500.0]]):
            VALIDATOR.validate(obj(tree))
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with self.assertRaises(NumericInvalid): scores(tree)
    def test_determinism_and_cse(self):
        tree=['sub',['mul','bins',2.0],['mul','bins',2.0]]
        a,dag=compile_tree(json.dumps(obj(tree)).encode())
        b,_=compile_tree(json.dumps(obj(tree)).encode())
        self.assertEqual(a,b)
        self.assertEqual(len(dag['nodes']),3)
        self.assertEqual(a.types, ('vf64','vf64','vf64'))
    def test_signed_zero_constants_are_not_merged(self):
        tree=['where',['gt','bins',0.0],-0.0,0.0]
        VALIDATOR.validate(obj(tree))
        program,dag=compile_tree(json.dumps(obj(tree)).encode())
        zero_hex=[float(c['value']).hex() for c in dag['constants'] if c['value']==0.0]
        self.assertEqual(sorted(zero_hex), ['-0x0.0p+0','0x0.0p+0'])
        self.assertTrue(np.all(np.signbit(scores(tree))))
        self.assertNotEqual(program.nodes[-1][2],program.nodes[-1][3])

    def test_1000_schema_constructed_trees(self):
        rng=random.Random(20261004)
        def sample(s):
            if '$ref' in s: return sample(SCHEMA['$defs'][s['$ref'].split('/')[-1]])
            if 'anyOf' in s: return sample(rng.choice(s['anyOf']))
            if 'const' in s: return s['const']
            if 'enum' in s: return rng.choice(s['enum'])
            if s.get('type')=='array': return [sample(x) for x in s['prefixItems']]
            raise AssertionError(s)
        seen=set()
        for _ in range(1000):
            tree=sample(SCHEMA['properties']['score'])
            VALIDATOR.validate(obj(tree))
            program,dag=compile_tree(json.dumps(obj(tree)).encode())
            self.assertEqual(program.types[program.return_node], 'vf64')
            self.assertLessEqual(len(dag['nodes']),6)
            for i,node in enumerate(dag['nodes']):
                self.assertTrue(all(type(x) is not int or x<i for x in node[1:]))
            seen.add(json.dumps(tree))
        self.assertGreater(len(seen),800)

if __name__ == '__main__': unittest.main(verbosity=2)
