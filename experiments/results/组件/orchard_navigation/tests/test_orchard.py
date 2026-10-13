import unittest,sys,pathlib,copy,random,math
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from model import build_graph, check_query
from planners import plan
from validator import geometry_free, bfs_oracle, validate, segment_clear
from freeze import make_maps

def tiny(w,h,obstacles=(),rho=0):
    return {'width':w,'height':h,'resolution_m':1.,'robot_halfwidth_m':rho,'clearance_m':0.,'obstacles':list(obstacles)}
def q(s,g):return {'start':list(s),'goal':list(g)}

class OrchardTests(unittest.TestCase):
    def check_case(self,m,query,expected):
        self.assertEqual(bfs_oracle(m,query),expected)
        for alg in ('astar','dijkstra'):
            result=plan(m,query,alg)
            self.assertEqual(result['cost_steps'],expected)
            self.assertTrue(validate(m,query,result,expected)['valid'])
    def test_known_optima(self):
        self.check_case(tiny(3,3),q((0,0),(2,2)),4)
        self.check_case(tiny(3,3,[[1,0,1,1]]),q((0,0),(2,0)),6)
        self.check_case(tiny(3,3,[[1,0,1,2]]),q((0,0),(2,0)),None)
        self.check_case(tiny(1,1),q((0,0),(0,0)),0)
        self.check_case(tiny(5,1),q((0,0),(4,0)),4)
    def test_heading_wrap_and_turns(self):
        m=tiny(3,3); query=q((0,0),(2,2))
        out={'status':'ok','path':[[0,0],[1,0],[2,0],[2,1],[2,2]],'cost_steps':4,'cost_m':4}
        v=validate(m,query,out,4); self.assertTrue(v['valid']);self.assertEqual(v['turn_count'],1);self.assertAlmostEqual(v['heading_change_rad'],math.pi/2)
    def test_alternative_optimal_paths_accepted(self):
        m=tiny(3,3);query=q((0,0),(2,2))
        paths=[[[0,0],[1,0],[2,0],[2,1],[2,2]],[[0,0],[0,1],[1,1],[1,2],[2,2]]]
        for path in paths:self.assertTrue(validate(m,query,{'status':'ok','path':path,'cost_steps':4,'cost_m':4},4)['valid'])
    def test_rejections(self):
        m=tiny(3,3);query=q((0,0),(2,2));good=plan(m,query,'astar')
        mutations=[('wrong_start',{'path':[[1,0]]+good['path'][1:]}),('wrong_goal',{'path':good['path'][:-1]}),
          ('non_adjacent',{'path':[[0,0],[2,2]]}),('step_cost',{'cost_steps':999}),('meter_cost',{'cost_m':float('nan')}),
          ('coordinate_type',{'path':[[False,0]]+good['path'][1:]}),('out_of_bounds',{'path':[[0,0],[-1,0],[2,2]]}),
          ('false_unreachable',{'status':'unreachable','path':[],'cost_steps':None,'cost_m':None}),
          ('empty_ok_path',{'path':[]}),('status',{'status':'magic'}),('path_not_list',{'path':'path'}),
          ('step_cost',{'cost_steps':True}),('meter_cost',{'cost_m':True})]
        for expected,patch in mutations:
            with self.subTest(expected=expected):
                out=copy.deepcopy(good);out.update(patch);v=validate(m,query,out,4)
                self.assertFalse(v['valid']);self.assertIn(expected,v['errors'])
        blocked=tiny(3,3,[[1,0,1,0]])
        out={'status':'ok','path':[[0,0],[1,0],[2,0]],'cost_steps':2,'cost_m':2}
        self.assertIn('point_collision',validate(blocked,q((0,0),(2,0)),out,4)['errors'])
        self.assertFalse(segment_clear(blocked,[0,0],[2,0]))
        loop=copy.deepcopy(good);loop['path']=[good['path'][0],good['path'][1],good['path'][0]]+good['path'][1:];loop['cost_steps']=6;loop['cost_m']=6
        self.assertIn('not_optimal',validate(m,query,loop,4)['errors'])
        out={'status':'ok','path':[[0,0],[1,0],[2,0]],'cost_steps':2,'cost_m':2}
        self.assertIn('false_reachable',validate(tiny(3,1,[[1,0,1,0]]),q((0,0),(2,0)),out,None)['errors'])
    def test_invalid_inputs(self):
        for bad in ([True,0],[-1,0],[3,0],[1.5,0]):
            with self.assertRaises(ValueError):plan(tiny(3,3),{'start':bad,'goal':[2,2]},'astar')
        with self.assertRaises(ValueError):plan(tiny(3,3,[[0,0,0,0]]),q((0,0),(2,2)),'dijkstra')
        with self.assertRaises(ValueError):plan(tiny(3,3),q((0,0),(2,2)),'rrt')
    def test_geometry_matches_inflation(self):
        for rho in (0,.2,.49,.5,.7,1.,1.5):
            m=tiny(8,7,[[3,2,4,4]],rho)
            f=build_graph(m); independent=geometry_free(m)
            self.assertEqual({(i%8,i//8) for i,v in enumerate(f) if v},independent)
    def test_random_tiny_maps_all_endpoint_pairs(self):
        rng=random.Random(62239) # only fixture generation; not the experiment seeds
        pairs=0
        for _ in range(20):
            m=tiny(4,4,[[x,y,x,y] for y in range(4) for x in range(4) if rng.random()<.24])
            free=sorted(geometry_free(m))
            for s in free:
                for g in free:
                    self.check_case(m,q(s,g),bfs_oracle(m,q(s,g)));pairs+=1
        self.assertGreater(pairs,2000)
    def test_frozen_design_geometry_and_reachability(self):
        maps,queries=make_maps();self.assertEqual(len(maps),12);self.assertEqual(len(queries),96)
        self.assertEqual(sum(not x['expected_reachable'] for x in queries),12)
        for m in maps:
            free=build_graph(m); oracle_free=geometry_free(m)
            self.assertEqual({(i%m['width'],i//m['width']) for i,v in enumerate(free) if v},oracle_free)
            for query in (x for x in queries if x['map_id']==m['map_id']):check_query(m,query,free)

if __name__=='__main__':unittest.main(verbosity=2)
