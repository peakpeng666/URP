import math
import random
import unittest
from sphere_ga import Config, CountedSphere, Individual, make_toolbox, evaluate_invalid, vary, replace, run

class TeachingTests(unittest.TestCase):
    def setUp(self):
        self.c = Config(dimension=2, population=4, generations=2)
        self.o = CountedSphere(self.c)
        self.t = make_toolbox(self.c, self.o)

    def test_hand_sphere_and_min_direction(self):
        a, b = Individual([3., 4.]), Individual([1., 2.])
        evaluate_invalid([a,b], self.t)
        self.assertEqual(a.fitness.values, (25.,))
        self.assertEqual(b.fitness.values, (5.,))
        self.assertEqual(self.t.survivors([a,b], 1), [b])
        self.assertGreater(b.fitness, a.fitness)  # weighted comparison

    def test_clone_invalidation_no_shared_inputs(self):
        p = Individual([1., 2.]); evaluate_invalid([p], self.t)
        original = list(p)
        children = vary([p]*4, self.t, self.c)
        self.assertEqual(p, original)
        self.assertTrue(p.fitness.valid)
        self.assertTrue(all(not c.fitness.valid for c in children))
        self.assertEqual(len(set(map(id, children))), 4)
        self.assertTrue(all(c is not p and c.fitness is not p.fitness for c in children))
        children[0][0] = 0.0
        self.assertEqual(p, original)
        self.assertEqual(self.o.ledger[0]['x'], original)

    def test_selection_rejects_unevaluated(self):
        p, c = Individual([1., 2.]), Individual([0., 0.])
        evaluate_invalid([p], self.t)
        with self.assertRaises(ValueError): replace([p], [c], self.t, 1)
        evaluate_invalid([c], self.t)
        self.assertEqual(replace([p], [c], self.t, 1)[0].fitness.values, (0.,))

    def test_every_clone_charged_and_budget_guard(self):
        c = Config(dimension=2, population=4, generations=2, cxpb=0, mutpb=0)
        result = run(c)
        self.assertEqual(result['evaluations'], 12)
        self.assertEqual([h['evaluations'] for h in result['history']], [4,8,12])
        objective = CountedSphere(Config(dimension=2, population=2, generations=0))
        objective([0.,0.]); objective([0.,0.])
        with self.assertRaises(RuntimeError): objective([0.,0.])

    def test_reproducible_and_rng_restored(self):
        old = random.getstate()
        self.assertEqual(run(self.c), run(self.c))
        self.assertEqual(random.getstate(), old)

    def test_raw_ledger_and_bounds(self):
        result = run(self.c)
        for row in result['ledger']:
            self.assertEqual(math.fsum(v*v for v in row['x']), row['value'])
            self.assertTrue(all(self.c.lower <= v <= self.c.upper for v in row['x']))
        best = [h['best'] for h in result['history']]
        self.assertTrue(all(b <= a for a,b in zip(best,best[1:])))

    def test_invalid_input_and_config(self):
        for x in ([float('nan'),0.], [9.,0.], [0.]):
            with self.assertRaises(ValueError): self.o(x)
        self.assertEqual(len(self.o.ledger), 0)
        with self.assertRaises(ValueError): run(Config(population=1))

    def test_odd_population_and_zero_generations(self):
        self.assertEqual(run(Config(population=3, generations=1))['evaluations'], 6)
        self.assertEqual(run(Config(population=3, generations=0))['evaluations'], 3)

if __name__ == '__main__': unittest.main()
