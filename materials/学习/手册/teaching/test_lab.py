import numpy as np
import pytest
from lab import minimize_ga, tour_cost, exact_tsp, greedy_tsp, pack, validate_packing, reproduce_unscored_population_bug

SQUARE = np.linalg.norm(np.array([[0,0],[1,0],[1,1],[0,1]])[:,None]-np.array([[0,0],[1,0],[1,1],[0,1]])[None,:], axis=-1)

def test_original_order_bug():
    assert reproduce_unscored_population_bug() == 'TypeError'

def test_ga_scores_and_accounting():
    f = lambda x: float(x@x)
    r = minimize_ga(f, generations=7, population=10)
    assert r.evaluations == 80
    assert r.best_loss == pytest.approx(f(np.array(r.best_genome)))
    assert len(r.history) == 8
    assert all(a >= b for a,b in zip(r.history,r.history[1:]))

def test_ga_seed_replay():
    f = lambda x: float(x@x)
    assert minimize_ga(f, seed=6) == minimize_ga(f, seed=6)

def test_ga_dimension_one():
    assert np.isfinite(minimize_ga(lambda x: float(x@x), dim=1).best_loss)

def test_ga_zero_generations():
    assert minimize_ga(lambda x: float(x@x), generations=0).evaluations == 24

@pytest.mark.parametrize('loss', [lambda x: float('nan'),lambda x: float('inf')])
def test_ga_nonfinite(loss):
    with pytest.raises(ValueError): minimize_ga(loss)

@pytest.mark.parametrize('kwargs',[{'dim':0},{'population':1},{'generations':-1},{'mutation_rate':2},{'sigma':-1}])
def test_ga_bad_inputs(kwargs):
    with pytest.raises(ValueError): minimize_ga(lambda x: float(x@x),**kwargs)

def test_square_oracle():
    assert exact_tsp(SQUARE)[1] == pytest.approx(4)
    assert tour_cost([0,2,1,3],SQUARE) == pytest.approx(2+2*np.sqrt(2))
    assert greedy_tsp(SQUARE)[1] == pytest.approx(4)

@pytest.mark.parametrize('tour', [[0,1,1,3],[0,1,2],[0,1,2,4],[False,1,2,3]])
def test_tour_rejects(tour):
    with pytest.raises(ValueError): tour_cost(tour,SQUARE)

def test_asymmetric_oracle():
    d=np.array([[0,1,9],[9,0,1],[1,9,0]],dtype=float)
    assert exact_tsp(d)[1] == 3
    assert tour_cost([0,2,1],d)==27

def test_scale_and_relabel():
    assert exact_tsp(7*SQUARE)[1] == pytest.approx(28)
    p=[2,0,3,1]
    assert exact_tsp(SQUARE[np.ix_(p,p)])[1] == pytest.approx(4)

def test_matrix_rejection():
    with pytest.raises(ValueError): exact_tsp(np.zeros((3,2)))
    with pytest.raises(ValueError): exact_tsp(np.zeros((10,10)))

@pytest.mark.parametrize('rule,count',[('first_fit',2),('best_fit',2),('next_fit',3)])
def test_bin_counterexample(rule,count):
    a,loads=pack([.6,.6,.4,.4],rule=rule)
    assert len(loads)==count
    assert validate_packing([.6,.6,.4,.4],a)==count

def test_overload_and_missing():
    with pytest.raises(ValueError): validate_packing([.6,.6],[0,0])
    with pytest.raises(ValueError): validate_packing([.6,.6],[0])

def test_empty_packing():
    assert pack([])==([],[])
    assert validate_packing([],[])==0

@pytest.mark.parametrize('x',[-.1,0,1.1,float('nan')])
def test_invalid_item(x):
    with pytest.raises(ValueError): pack([x])
