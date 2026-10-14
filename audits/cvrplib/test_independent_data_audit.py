import unittest
from fractions import Fraction as F
from independent_data_audit import edge,parse
from pathlib import Path
from tempfile import TemporaryDirectory
class ExactEdges(unittest.TestCase):
 def test_half_up_not_bankers(self):self.assertEqual(edge((F(0),F(0)),(F('2.5'),F(0))),3)
 def test_euclidean_not_manhattan(self):self.assertEqual(edge((0,0),(3,4)),5)
 def test_below_half(self):self.assertEqual(edge((0,0),(F('2.499999999999999999999'),0)),2)
 def test_above_half(self):self.assertEqual(edge((0,0),(F('2.500000000000000000001'),0)),3)
 def test_large_integer(self):self.assertEqual(edge((0,0),(10**30,0)),10**30)
 def test_per_edge_not_total_rounding(self):self.assertEqual(2*edge((0,0),(1,1)),2)
 def test_symmetric_negative(self):self.assertEqual(edge((-3,-4),(0,0)),edge((0,0),(-3,-4)))
if __name__=='__main__':unittest.main()
