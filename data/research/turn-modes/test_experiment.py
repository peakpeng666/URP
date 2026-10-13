import copy,json,unittest
from pathlib import Path
import checker,solver,oracle,evaluate_candidate
from generate_data import fixtures,grid
class Tests(unittest.TestCase):
    def test_known_counterexample_and_infeasible(self):
        dead,cycle,free=fixtures()
        for inst,expected in ((dead,None),(cycle,3)):
            m,t=solver.solve(inst,'mode');r,_=solver.solve(inst,'reset');o=oracle.solve(inst)
            self.assertEqual(m['cost'],expected);self.assertEqual(m['cost'],o['cost'])
            self.assertEqual(r['cost'],2);self.assertFalse(checker.check(inst,r)['valid'])
        a,_=solver.solve(free,'mode');b,_=solver.solve(free,'reset');self.assertEqual(a['cost'],b['cost']);self.assertTrue(checker.check(free,b)['valid'])
    def test_mutation_rejections(self):
        inst=fixtures()[1];good,_=solver.solve(inst,'mode');self.assertTrue(checker.check(inst,good)['valid'])
        mutations={}
        v=copy.deepcopy(good);v['routes'][0]['services']=[];mutations['missing']=v
        v=copy.deepcopy(good);v['routes'][0]['services']*=2;mutations['duplicate']=v
        v=copy.deepcopy(good);v['routes'][0]['nodes']=[0,1,0];v['routes'][0]['cost']=2;v['cost']=2;mutations['forbidden_turn']=v
        v=copy.deepcopy(good);v['routes'][0]['nodes'][1]=999;mutations['broken_arc']=v
        v=copy.deepcopy(good);v['routes'][0]['services'][0]['position']=0;mutations['wrong_service_location']=v
        v=copy.deepcopy(good);v['cost']-=1;mutations['forged_total']=v
        v=copy.deepcopy(good);v['routes'][0]['cost']-=1;mutations['forged_route_cost']=v
        for label,value in mutations.items():
            with self.subTest(label=label):self.assertFalse(checker.check(inst,value)['valid'])
        limited=copy.deepcopy(inst);limited['capacity']=0;self.assertIn('route0:capacity',checker.check(limited,good)['errors'])
    def test_raw_oracle_matches_mode_smoke(self):
        for seed in range(8000,8006):
            inst=grid(3,3,5,seed,['uturn','left_cost','left_ban'][seed%3]);a,tab=solver.solve(inst,'mode');b=oracle.solve(inst)
            self.assertEqual(a['cost'],b['cost']);self.assertTrue(checker.check(inst,a)['valid']);self.assertTrue(checker.check(inst,b)['valid'])
            for seq in ([0],[0,1],[2,1,3],[4,3,2,1]):
                d=solver.fixed_sequence(inst,tab,seq);cost,_=solver.brute_modes(tab,seq);self.assertEqual(d['cost'],cost)
    def test_candidate_adapter(self):
        dead,cycle,_=fixtures()
        r=evaluate_candidate.evaluate(cycle,{'service_sequences':[[0]]});self.assertTrue(r['accepted']);self.assertEqual(r['solution']['cost'],3)
        self.assertFalse(evaluate_candidate.evaluate(dead,{'service_sequences':[[0]]})['accepted'])
        self.assertFalse(evaluate_candidate.evaluate(cycle,{'service_sequences':[[0,0]]})['accepted'])
        self.assertFalse(evaluate_candidate.evaluate(cycle,{'service_sequences':[[99]]})['accepted'])
        self.assertFalse(evaluate_candidate.evaluate(cycle,{'service_sequences':[['0']]})['accepted'])
    def test_service_does_not_reset_heading(self):
        # With U-turn prohibited, the only legal return takes the third node.
        inst=fixtures()[1];good,_=solver.solve(inst,'mode');self.assertEqual(good['routes'][0]['nodes'],[0,1,2,0])
    def test_pass_through_does_not_service(self):
        inst=fixtures()[1];inst['customers'].append({'id':1,'node':2,'demand':1});inst['capacity']=2
        route={'status':'optimal','cost':3,'routes':[{'nodes':[0,1,2,0],'cost':3,'services':[{'customer':0,'position':1}]}]}
        self.assertIn('exact_once_service',checker.check(inst,route)['errors'])
if __name__=='__main__':unittest.main(verbosity=2)
