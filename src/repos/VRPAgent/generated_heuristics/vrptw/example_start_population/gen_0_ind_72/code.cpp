#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> expansionCandidates;

    int numCustomersToRemove = getRandomNumber(10, 20); 
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(initialSeedCustomer);
    expansionCandidates.push_back(initialSeedCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (expansionCandidates.empty()) {
            int newSeed = -1;
            for (int i = 1; i <= sol.instance.numCustomers; ++i) {
                if (selectedCustomers.find(i) == selectedCustomers.end()) {
                    newSeed = i;
                    break;
                }
            }
            if (newSeed != -1) {
                selectedCustomers.insert(newSeed);
                expansionCandidates.push_back(newSeed);
            } else {
                break;
            }
        }

        int currentSeedIndex = getRandomNumber(0, (int)expansionCandidates.size() - 1);
        int currentSeedCustomer = expansionCandidates[currentSeedIndex];

        expansionCandidates[currentSeedIndex] = expansionCandidates.back();
        expansionCandidates.pop_back();

        int neighborsConsidered = 0;
        int maxNeighborsToConsider = getRandomNumber(2, 6);
        
        for (int neighbor_id : sol.instance.adj[currentSeedCustomer]) {
            if (neighborsConsidered >= maxNeighborsToConsider) {
                break;
            }
            if (neighbor_id == 0) {
                continue;
            }
            if (selectedCustomers.find(neighbor_id) != selectedCustomers.end()) {
                continue;
            }

            if (getRandomFraction() < 0.2f) {
                 continue;
            }

            selectedCustomers.insert(neighbor_id);
            expansionCandidates.push_back(neighbor_id);

            neighborsConsidered++;

            if (selectedCustomers.size() >= numCustomersToRemove) {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<int, std::pair<float, float>>> customer_metrics;
    customer_metrics.reserve(customers.size());

    for (int customer_id : customers) {
        customer_metrics.push_back({customer_id, {instance.startTW[customer_id], instance.TW_Width[customer_id]}});
    }

    std::sort(customer_metrics.begin(), customer_metrics.end(),
              [](const std::pair<int, std::pair<float, float>>& a,
                 const std::pair<int, std::pair<float, float>>& b) {
                  if (a.second.first != b.second.first) {
                      return a.second.first < b.second.first;
                  }
                  return a.second.second < b.second.second;
              });

    static thread_local std::mt19937 gen(std::random_device{}());
    
    int shuffle_block_size = getRandomNumber(2, 5);

    for (size_t i = 0; i < customer_metrics.size(); i += shuffle_block_size) {
        size_t end_idx = std::min(i + shuffle_block_size, customer_metrics.size());
        std::shuffle(customer_metrics.begin() + i, customer_metrics.begin() + end_idx, gen);
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_metrics[i].first;
    }
}