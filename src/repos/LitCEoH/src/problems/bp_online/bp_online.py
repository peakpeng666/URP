from .get_instance import GetData
import numpy as np


class BPonline():
    def __init__(self):
        getdata = GetData()
        self.instances, self.lb = getdata.get_instances()

    def get_valid_bin_indices(self, item: float, bins: np.ndarray) -> np.ndarray:
        """Returns indices of bins in which item can fit."""
        return np.nonzero((bins - item) >= 0)[0]

    def online_binpack(self, items: tuple, bins: np.ndarray, alg):
        """Performs online binpacking of `items` into `bins`."""
        # Track which items are added to each bin.
        packing = [[] for _ in bins]
        # Add items to bins.
        n = 1
        for item in items:
            # Extract bins that have sufficient space to fit item.
            valid_bin_indices = self.get_valid_bin_indices(item, bins)
            # Score each bin based on heuristic.
            priorities = alg.score(item, bins[valid_bin_indices])
            # Add item to bin with highest priority.
            best_bin = valid_bin_indices[np.argmax(priorities)]
            bins[best_bin] -= item
            packing[best_bin].append(item)
            n = n + 1

        # Remove unused bins from packing.
        packing = [bin_items for bin_items in packing if bin_items]
        return packing, bins

    def evaluateGreedy(self, alg) -> float:
        for name, dataset in self.instances.items():
            num_bins_list = []
            for _, instance in dataset.items():
                capacity = instance['capacity']
                items = np.array(instance['items'])

                # Create num_items bins so there will always be space for all items,
                # regardless of packing order. Array has shape (num_items,).
                bins = np.array([capacity for _ in range(instance['num_items'])])
                # Pack items into bins and return remaining capacity in bins_packed, which
                # has shape (num_items,).
                _, bins_packed = self.online_binpack(items, bins, alg)
                # If remaining capacity in a bin is equal to initial capacity, then it is
                # unused. Count number of used bins.
                num_bins = (bins_packed != capacity).sum()

                num_bins_list.append(-num_bins)

            # avg_num_bins = -self.evaluateGreedy(dataset, algorithm)
            avg_num_bins = -np.mean(np.array(num_bins_list))
            fitness = (avg_num_bins - self.lb[name]) / self.lb[name]

        return fitness
