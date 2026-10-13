#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::shuffle
#include <vector>
#include <cmath>     // For std::min
#include "Utils.h"   // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    int num_to_remove = getRandomNumber(10, 25);

    std::vector<int> candidate_queue;

    // Seed selection: Pick a random customer to start the cluster
    int initial_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer);
    selected_customers_vec.push_back(initial_customer);
    candidate_queue.push_back(initial_customer);

    // Expand selection using a biased BFS-like approach to find close customers
    while (selected_customers_set.size() < num_to_remove && !candidate_queue.empty()) {
        int current_customer_idx = getRandomNumber(0, candidate_queue.size() - 1);
        int current_customer = candidate_queue[current_customer_idx];

        // Fast removal from vector (swap with last and pop_back)
        candidate_queue[current_customer_idx] = candidate_queue.back();
        candidate_queue.pop_back();

        const auto& neighbors = sol.instance.adj[current_customer];
        // Explore a random subset of the closest neighbors
        int num_neighbors_to_check = std::min((int)neighbors.size(), getRandomNumber(1, 8));

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor = neighbors[i];
            if (neighbor == 0) continue; // Skip depot

            if (selected_customers_set.find(neighbor) == selected_customers_set.end()) {
                // Probabilistically add the neighbor, favoring addition if more customers are needed
                float prob_add = 0.7f + (float)(num_to_remove - selected_customers_set.size()) / num_to_remove * 0.2f;
                if (getRandomFractionFast() < prob_add) {
                    selected_customers_set.insert(neighbor);
                    selected_customers_vec.push_back(neighbor);
                    candidate_queue.push_back(neighbor);

                    if (selected_customers_set.size() >= num_to_remove) {
                        break;
                    }
                }
            }
        }
    }

    // Fallback: If not enough customers were gathered by proximity, add random ones
    while (selected_customers_set.size() < num_to_remove) {
        int random_customer = getRandomNumber(1, sol.instance.numCustomers);
        if (selected_customers_set.find(random_customer) == selected_customers_set.end()) {
            selected_customers_set.insert(random_customer);
            selected_customers_vec.push_back(random_customer);
        }
    }

    return selected_customers_vec;
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Determine sorting strategy stochastically for diversity
    int strategy = getRandomNumber(0, 3); // 0: Prize/Demand, 1: Prize, 2: Distance to Depot, 3: Random

    switch (strategy) {
        case 0: { // Sort by Prize / Demand (descending)
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                float ratio1 = (instance.demand[c1] > 0) ? (float)instance.prizes[c1] / instance.demand[c1] : instance.prizes[c1];
                float ratio2 = (instance.demand[c2] > 0) ? (float)instance.prizes[c2] / instance.demand[c2] : instance.prizes[c2];
                return ratio1 > ratio2;
            });
            break;
        }
        case 1: { // Sort by Prize (descending)
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.prizes[c1] > instance.prizes[c2];
            });
            break;
        }
        case 2: { // Sort by Distance to Depot (ascending)
            std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
                return instance.distanceMatrix[0][c1] < instance.distanceMatrix[0][c2];
            });
            break;
        }
        case 3: { // Random sort
            static thread_local std::mt19937 random_engine(std::random_device{}()); // Use a separate engine for shuffle
            std::shuffle(customers.begin(), customers.end(), random_engine);
            break;
        }
    }
}