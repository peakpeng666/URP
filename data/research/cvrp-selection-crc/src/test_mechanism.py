import unittest, copy
from experiment import crc, route, fit, predict, ALGOS
class MechanismTests(unittest.TestCase):
    def record(self,score,harm=True):return {'score':score,'harm':harm,'chosen':'a','sbs':'b'}
    def test_sample_floor_forces_safety(self):
        g=crc([self.record(.1,False) for _ in range(6)],.1)
        self.assertTrue(g['safe_endpoint']);self.assertAlmostEqual(g['finite_sample_floor'],1/7)
    def test_nine_safe_cal_points_allow_finite_threshold(self):
        g=crc([self.record(.1,False) for _ in range(9)],.1)
        self.assertFalse(g['safe_endpoint']);self.assertEqual(g['threshold'],0)
    def test_small_sample_sensitive_alpha_is_distinct(self):
        g=crc([self.record(.1,False) for _ in range(6)],.2)
        self.assertEqual(g['threshold'],0)
    def test_strict_threshold_and_monotonicity(self):
        cal=[self.record(.2),self.record(.4)]+[self.record(.1,False) for _ in range(4)]
        g=crc(cal,.2);self.assertEqual(g['threshold'],.4)
        self.assertFalse(route(self.record(.4),g)[1]);self.assertTrue(route(self.record(.5),g)[1])
        losses=[sum(x['harm'] and x['score']>t for x in cal) for t in [0,.1,.2,.3,.4,1]]
        self.assertEqual(losses,sorted(losses,reverse=True))
    def test_all_fallback_never_has_harm(self):
        g={'safe_endpoint':True,'threshold':None}
        self.assertEqual(route(self.record(10000),g),('b',False))
    def test_no_misnamed_probability(self):
        # Ranking margins are only scores and can never certify class confidence.
        self.assertNotIn('probability',crc([self.record(.5,False)]*6,.2))
    def test_empty_calibration_safe_fallback(self):self.assertTrue(crc([],.1)['safe_endpoint'])
    def test_inference_does_not_accept_any_performance_labels(self):
        feat={str(i):{'values':[i,1]} for i in range(4)}
        mat={str(i):{a:{'normalized_cost':1+i*.1+k} for k,a in enumerate(ALGOS)} for i in range(3)}
        model=fit(['0','1','2'],feat,mat);result=predict(model,'3',feat)
        self.assertEqual(result['chosen'],ALGOS[0]);self.assertNotIn('3',model['targets'])
if __name__=='__main__':unittest.main(verbosity=2)
