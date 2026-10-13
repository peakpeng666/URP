#include "AgentDesigned.h"
#include <unordered_set>
#include <queue>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 20;
const int MAX_NEIGHBORS_TO_CONSIDER_FOR_EXPANSION = 8;
const float PROB_ADD_NEIGHBOR = 0.8f;

const int SORT_PERTURBATION_SWAPS_FACTOR = 3;

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::queue<int> q;

    int numCustomersToTarget = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    int numInitialSeeds = getRandomNumber(1, 3);

    while (selectedCustomersSet.size() < numInitialSeeds) {
        int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomersSet.find(seed_customer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(seed_customer);
            q.push(seed_customer);
        }
    }

    while (selectedCustomersSet.size() < numCustomersToTarget) {
        if (q.empty()) {
            int current_size = selectedCustomersSet.size();
            for (int i = 0; i < (numCustomersToTarget - current_size); ++i) {
                int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
                selectedCustomersSet.insert(randomCustomer);
            }
            break;
        }
        
        int current_customer = q.front();
        q.pop();

        int neighbors_to_check = std::min((int)sol.instance.adj[current_customer].size(), MAX_NEIGHBORS_TO_CONSIDER_FOR_EXPANSION);
        for (int i = 0; i < neighbors_to_check; ++i) {
            int neighbor = sol.instance.adj[current_customer][i];
            if (selectedCustomersSet.find(neighbor) == selectedCustomersSet.end()) {
                if (getRandomFractionFast() < PROB_ADD_NEIGHBOR) {
                    selectedCustomersSet.insert(neighbor);
                    q.push(neighbor);
                    if (selectedCustomersSet.size() >= numCustomersToTarget) {
                        break;
                    }
                }
            }
        }
    }
    
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        customer_scores.push_back({instance.prizes[customer_id], customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first;
              });

    int num_swaps = customers.size() * SORT_PERTURBATION_SWAPS_FACTOR;
    for (int k = 0; k < num_swaps; ++k) {
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        if (idx1 != idx2) {
            std::swap(customer_scores[idx1], customer_scores[idx2]);
        }
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}