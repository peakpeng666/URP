#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <limits>
#include "Utils.h"

static thread_local std::mt19937 gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(10, 25);
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    if (sol.instance.numCustomers == 0 || num_to_remove == 0) {
        return {};
    }

    int initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_seed_customer);
    selected_customers_vec.push_back(initial_seed_customer);

    while (selected_customers_set.size() < num_to_remove) {
        int seed_idx = getRandomNumber(0, (int)selected_customers_vec.size() - 1);
        int seed_customer = selected_customers_vec[seed_idx];

        const auto& neighbors = sol.instance.adj[seed_customer];

        if (neighbors.empty()) {
            continue;
        }

        int max_neighbors_to_consider = std::min((int)neighbors.size(), 10);

        int neighbor_idx = getRandomNumber(0, max_neighbors_to_consider - 1);
        int candidate_customer = neighbors[neighbor_idx];

        if (selected_customers_set.find(candidate_customer) == selected_customers_set.end() &&
            candidate_customer >= 1 && candidate_customer <= sol.instance.numCustomers) {
            selected_customers_set.insert(candidate_customer);
            selected_customers_vec.push_back(candidate_customer);
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    int sort_type = getRandomNumber(0, 4);

    switch (sort_type) {
        case 0: {
            std::shuffle(customers.begin(), customers.end(), gen);
            break;
        }
        case 1: {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.prizes[c1] > instance.prizes[c2];
            });
            break;
        }
        case 2: {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                float ratio1 = (instance.demand[c1] > 0) ? instance.prizes[c1] / instance.demand[c1] : std::numeric_limits<float>::max();
                float ratio2 = (instance.demand[c2] > 0) ? instance.prizes[c2] / instance.demand[c2] : std::numeric_limits<float>::max();
                return ratio1 > ratio2;
            });
            break;
        }
        case 3: {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.demand[c1] < instance.demand[c2];
            });
            break;
        }
        case 4: {
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.distanceMatrix[0][c1] < instance.distanceMatrix[0][c2];
            });
            break;
        }
    }
}