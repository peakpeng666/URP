import itertools
import numpy as np


class CapSet:

    def __init__(self):
        pass

    @staticmethod
    def cap_set_evaluate(self, priority, n: int) -> int:
        """Returns the size of an `n`-dimensional cap set."""
        capset = self._solve(priority, n)
        return len(capset)

    @staticmethod
    def _solve(self, priority, n: int) -> np.ndarray:
        """Returns a large cap set in `n` dimensions."""
        all_vectors = np.array(list(itertools.product((0, 1, 2), repeat=n)), dtype=np.int32)

        # Powers in decreasing order for compatibility with `itertools.product`, so
        # that the relationship `i = all_vectors[i] @ powers` holds for all `i`.
        powers = 3 ** np.arange(n - 1, -1, -1)

        # Precompute all priorities.
        priorities = np.array([priority.select_next_element(tuple(vector), n) for vector in all_vectors])

        # Build `capset` greedily, using priorities for prioritization.
        capset = np.empty(shape=(0, n), dtype=np.int32)
        while np.any(priorities != -np.inf):
            # Add a vector with maximum priority to `capset`, and set priorities of
            # invalidated vectors to `-inf`, so that they never get selected.
            max_index = np.argmax(priorities)
            vector = all_vectors[None, max_index]  # [1, n]
            blocking = np.einsum('cn,n->c', (- capset - vector) % 3, powers)  # [C]
            priorities[blocking] = -np.inf
            priorities[max_index] = -np.inf
            capset = np.concatenate([capset, vector], axis=0)

        return capset