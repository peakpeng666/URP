"""Tiny synthetic tests only: no historical input loads or grid evaluation."""
import pathlib
import sys
import unittest
import warnings
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from control import GRID, ORDER, ORIGINAL, score, pack, select_winner, fitness
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from published_eoh_formula_v1.src.formula import score as trusted
from paper_baseline_v1.src.checker import check_assignment

class Tiny(unittest.TestCase):
    def test_grid(self):
        self.assertEqual(len(set(GRID)), 27)
        self.assertEqual(ORDER[0], ORIGINAL)

    def test_original_bitwise_and_immutable(self):
        for i, values in [(1,[1,2,4,5,100]), (25,[25,99,100]),
                          (20,[100,80,20,80]), (100,[100,500,500])]:
            b=np.array(values,dtype=np.int64); before=b.tobytes()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                actual=score(np.int64(i),b); expected=trusted(np.int32(i),b)
            self.assertEqual(actual.tobytes(),expected.tobytes())
            self.assertEqual(b.tobytes(),before)
            self.assertEqual(int(np.argmax(actual)),int(np.argmax(expected)))

    def test_c100_all_feasible_pairs_bitwise(self):
        pairs=0
        for i in range(1,101):
            b=np.arange(i,101,dtype=np.int64)
            for layout in (b,b[::-1]):
                actual=score(np.int64(i),layout)
                expected=trusted(np.int32(i),layout)
                self.assertEqual(actual.tobytes(),expected.tobytes())
                self.assertEqual(int(np.argmax(actual)),int(np.argmax(expected)))
            pairs+=len(b)
        self.assertEqual(pairs,5050)

    def test_first_argmax_and_packing(self):
        self.assertEqual(int(np.argmax(score(np.int64(10),np.array([50,50],dtype=np.int64)))),0)
        items=[40,60,20,80]; r=pack(items,100)
        check_assignment(items,100,r['assignment'],r['used_bins'],r['residuals'])
        self.assertEqual(r['assignment'],[0,0,1,1])

    def test_grid_endpoints_finite(self):
        for p in (GRID[0],GRID[-1]):
            self.assertTrue(np.all(np.isfinite(score(np.int64(20),np.array([20,60,100],dtype=np.int64),p))))

    def test_tie_prefers_original_and_incomplete_rejected(self):
        values={p:[11]*5 for p in GRID}
        self.assertEqual(select_winner([10]*5,values),ORIGINAL)
        values[GRID[0]]=[10]*5
        self.assertEqual(select_winner([10]*5,values),GRID[0])
        del values[GRID[1]]
        with self.assertRaises(ValueError):select_winner([10]*5,values)

    def test_mean_ratio_not_ratio_of_sums(self):
        self.assertEqual(str(fitness([1,2,1,1,1],[1,3,1,1,1])),'14/15')

    def test_dtype_rejected(self):
        with self.assertRaises(ValueError):score(np.int32(10),np.array([20],dtype=np.int64))

if __name__=='__main__':unittest.main()
