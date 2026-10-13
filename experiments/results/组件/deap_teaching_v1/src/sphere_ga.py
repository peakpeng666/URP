"""Small DEAP minimization lesson; not an eaSimple or legacy-GA reproduction."""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import random
from dataclasses import asdict, dataclass
from deap import base, creator, tools

if not hasattr(creator, 'TeachingFitnessMinV1'):
    creator.create('TeachingFitnessMinV1', base.Fitness, weights=(-1.0,))
    creator.create('TeachingIndividualV1', list, fitness=creator.TeachingFitnessMinV1)
Individual = creator.TeachingIndividualV1

@dataclass(frozen=True)
class Config:
    seed: int = 20261005
    dimension: int = 5
    population: int = 20
    generations: int = 20
    lower: float = -5.12
    upper: float = 5.12
    cxpb: float = 0.8
    mutpb: float = 0.3
    eta_c: float = 15.0
    eta_m: float = 20.0
    tournament: int = 3

    @property
    def budget(self):
        return self.population * (self.generations + 1)

    def validate(self):
        if self.dimension < 1 or self.population < 2 or self.generations < 0:
            raise ValueError('invalid population, dimension or generations')
        if not (math.isfinite(self.lower) and math.isfinite(self.upper) and self.lower < self.upper):
            raise ValueError('invalid bounds')
        if not (0 <= self.cxpb <= 1 and 0 <= self.mutpb <= 1):
            raise ValueError('invalid probability')
        if self.eta_c <= 0 or self.eta_m <= 0 or self.tournament < 1:
            raise ValueError('invalid operator parameters')

class CountedSphere:
    def __init__(self, config):
        self.config, self.ledger = config, []

    def __call__(self, individual):
        c = self.config
        if len(self.ledger) >= c.budget:
            raise RuntimeError('evaluation budget exhausted')
        x = list(individual)
        if len(x) != c.dimension or any(not math.isfinite(v) or not c.lower <= v <= c.upper for v in x):
            raise ValueError('invalid genome')
        value = math.fsum(v * v for v in x)
        self.ledger.append({'evaluation': len(self.ledger) + 1, 'x': x, 'value': value})
        return (value,)

def make_toolbox(c, objective):
    t = base.Toolbox()  # clone is deepcopy by default
    t.register('coordinate', random.uniform, c.lower, c.upper)
    t.register('individual', tools.initRepeat, Individual, t.coordinate, c.dimension)
    t.register('population', tools.initRepeat, list, t.individual)
    t.register('evaluate', objective)
    t.register('parents', tools.selTournament, tournsize=c.tournament)
    t.register('mate', tools.cxSimulatedBinaryBounded, eta=c.eta_c, low=c.lower, up=c.upper)
    t.register('mutate', tools.mutPolynomialBounded, eta=c.eta_m, low=c.lower, up=c.upper, indpb=1/c.dimension)
    t.register('survivors', tools.selBest)
    return t

def evaluate_invalid(population, toolbox):
    for individual in population:
        if not individual.fitness.valid:
            individual.fitness.values = toolbox.evaluate(individual)

def vary(population, toolbox, c):
    if not all(p.fitness.valid for p in population):
        raise ValueError('parents must be evaluated')
    children = [toolbox.clone(p) for p in toolbox.parents(population, c.population)]
    for left, right in zip(children[::2], children[1::2]):
        if random.random() < c.cxpb:
            toolbox.mate(left, right)
    for child in children:
        if random.random() < c.mutpb:
            toolbox.mutate(child)
        # Deliberately reevaluate EVERY child, even unchanged clones. This gives
        # exactly N*(G+1) charged objective calls, unlike eaSimple's cache policy.
        del child.fitness.values
    return children

def replace(population, children, toolbox, n):
    if not all(p.fitness.valid for p in population + children):
        raise ValueError('evaluate all candidates BEFORE survival selection')
    return [toolbox.clone(p) for p in toolbox.survivors(population + children, n)]

def run(c=Config()):
    c.validate()
    previous = random.getstate()
    random.seed(c.seed)
    try:
        objective = CountedSphere(c)
        toolbox = make_toolbox(c, objective)
        population = toolbox.population(c.population)
        evaluate_invalid(population, toolbox)
        history = []
        for generation in range(c.generations + 1):
            best = tools.selBest(population, 1)[0]
            history.append({'generation': generation, 'evaluations': len(objective.ledger),
                            'best': best.fitness.values[0], 'x': list(best)})
            if generation == c.generations:
                break
            children = vary(population, toolbox, c)
            evaluate_invalid(children, toolbox)
            population = replace(population, children, toolbox, c.population)
        assert len(objective.ledger) == c.budget
        assert all(b['best'] <= a['best'] for a, b in zip(history, history[1:]))
        return {'config': asdict(c), 'budget': c.budget, 'evaluations': len(objective.ledger),
                'history': history, 'ledger': objective.ledger,
                'final_population': [{'x': list(p), 'value': p.fitness.values[0]} for p in population]}
    finally:
        random.setstate(previous)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('refusing to overwrite an existing result')
    result = run()
    result['environment'] = {'python': platform.python_version(),
                             'deap': importlib.metadata.version('deap'),
                             'numpy': importlib.metadata.version('numpy')}
    result['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'evaluations': result['evaluations'], 'initial': result['history'][0]['best'],
                      'final': result['history'][-1]['best']}))

if __name__ == '__main__':
    main()
