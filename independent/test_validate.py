import copy
from decimal import Decimal as D
import unittest
from validate import check, check_result, distance

class IndependentChecks(unittest.TestCase):
    def setUp(self):
        self.p={'coordinates':[(D(0),D(0)),(D(3),D(0)),(D(0),D(4))], 'demands':[0,2,2], 'capacity':4}
        self.routes=[[0,1,2,0]]
    def test_valid(self): self.assertTrue(check(self.p,self.routes,12,1)['valid'])
    def test_duplicate(self): self.assertFalse(check(self.p,[[0,1,1,0]],6,1)['valid'])
    def test_missing(self): self.assertFalse(check(self.p,[[0,1,0]],6,1)['valid'])
    def test_capacity(self):
        self.p['capacity']=3
        self.assertFalse(check(self.p,self.routes,12,1)['valid'])
    def test_fleet(self): self.assertFalse(check(self.p,[[0,1,0],[0,2,0]],14,1)['valid'])
    def test_depot(self): self.assertFalse(check(self.p,[[0,1,0,2,0]],14,1)['valid'])
    def test_wrong_cost(self): self.assertFalse(check(self.p,self.routes,11,1)['valid'])
    def test_bool_node(self): self.assertFalse(check(self.p,[[0,True,2,0]],12,1)['valid'])
    def test_float_cost(self): self.assertFalse(check(self.p,self.routes,12.0,1)['valid'])
    def test_empty_route(self): self.assertFalse(check(self.p,[[0,0]],0,1)['valid'])
    def test_round_half_up(self): self.assertEqual(distance((D(0),D(0)),(D('2.5'),D(0))),3)
    def test_below_half(self): self.assertEqual(distance((D(0),D(0)),(D('2.499999999999999999'),D(0))),2)
    def test_failure_kept(self):
        r=check_result(self.p,{'status':'TIMEOUT','feasible':False},1)
        self.assertTrue(r['count_in_denominator']); self.assertFalse(r['eligible'])
    def test_late_incumbent_rejected(self):
        r=check_result(self.p,{'status':'OK','feasible':True,'routes':self.routes,'cost':12,'start_monotonic_ns':1,'incumbent_emitted_ns':3,'incumbent_received_ns':5,'deadline_monotonic_ns':4,'budget_seconds':1},1)
        self.assertFalse(r['eligible'])

if __name__=='__main__': unittest.main()
