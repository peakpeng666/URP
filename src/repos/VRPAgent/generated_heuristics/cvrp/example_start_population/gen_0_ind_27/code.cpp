#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::shuffle
#include <numeric>   // For std::iota
#include <tuple>     // For std::tuple

// Headers from Utils.h (assuming these are available)
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0);
// float getRandomFractionFast(); // Function to generate a random fraction (float) in the range [0, 1] using a fast method
// std::vector<int> argsort(const std::vector<float>& values); // Function to perform argsort on a vector of float values


// Customer selection heuristic for LNS (Step 1)
// Selects a subset of customers to remove, ensuring they are somewhat spatially related
// and incorporating stochastic behavior.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec;

    int minCustomersToRemove = 10;
    int maxCustomersToRemove = 20;
    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    if (numCustomersToRemove >= sol.instance.numCustomers) {
        std::vector<int> allCustomers(sol.instance.numCustomers);
        std::iota(allCustomers.begin(), allCustomers.end(), 1);
        return allCustomers;
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(initialCustomer);
    selectedCustomersVec.push_back(initialCustomer);

    const int NEIGHBORHOOD_POOL_SIZE = 10;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int rand_selected_idx = getRandomNumber(0, selectedCustomersVec.size() - 1);
        int current_center_customer = selectedCustomersVec[rand_selected_idx];

        const auto& neighbors_of_center = sol.instance.adj[current_center_customer];
        std::vector<int> candidate_neighbors;

        for (int neighbor_node : neighbors_of_center) {
            if (neighbor_node == 0) {
                continue;
            }
            if (selectedCustomersSet.find(neighbor_node) == selectedCustomersSet.end()) {
                candidate_neighbors.push_back(neighbor_node);
            }
            if (candidate_neighbors.size() >= NEIGHBORHOOD_POOL_SIZE) {
                break;
            }
        }

        if (!candidate_neighbors.empty()) {
            int rand_neighbor_idx = getRandomNumber(0, candidate_neighbors.size() - 1);
            int customer_to_add = candidate_neighbors[rand_neighbor_idx];

            selectedCustomersSet.insert(customer_to_add);
            selectedCustomersVec.push_back(customer_to_add);
        } else {
            int new_seed_customer;
            do {
                new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.find(new_seed_customer) != selectedCustomersSet.end());

            selectedCustomersSet.insert(new_seed_customer);
            selectedCustomersVec.push_back(new_seed_customer);
        }
    }
    return selectedCustomersVec;
}

// Customer ordering heuristic for LNS (Step 3)
// Sorts the removed customers for greedy reinsertion, prioritizing critical customers
// and incorporating stochastic behavior for diversity.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<std::tuple<float, float, int>> customer_criteria;
    customer_criteria.reserve(customers.size());

    const float PERTURBATION_EPSILON = 1e-4;

    for (int customer_id : customers) {
        float demand_score = static_cast<float>(instance.demand[customer_id]);
        float dist_to_depot_score = instance.distanceMatrix[customer_id][0];

        float random_perturbation = (getRandomFractionFast() - 0.5) * PERTURBATION_EPSILON;

        customer_criteria.emplace_back(demand_score + random_perturbation, dist_to_depot_score + random_perturbation, customer_id);
    }

    std::sort(customer_criteria.begin(), customer_criteria.end(),
              [](const std::tuple<float, float, int>& a, const std::tuple<float, float, int>& b) {
                  if (std::get<0>(a) != std::get<0>(b)) {
                      return std::get<0>(a) > std::get<0>(b);
                  }
                  return std::get<1>(a) > std::get<1>(b);
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = std::get<2>(customer_criteria[i]);
    }
}