#include <vector>
#include <unordered_set>
#include <algorithm> // For std::min, std::sort, std::swap
// Assuming Solution.h, Instance.h, Tour.h are available via AgentDesigned.h or directly
// Including them explicitly for clarity on dependencies.
#include "Solution.h"
#include "Instance.h"
#include "Utils.h" // For getRandomNumber, getRandomFractionFast

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int min_removals = 10;
    int max_removals = 20;
    int numCustomersToRemove = getRandomNumber(min_removals, std::min(max_removals, sol.instance.numCustomers));

    const int neighborhood_search_limit = 5;

    int initial_seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_list.push_back(initial_seed_customer_id);
    selected_customers_set.insert(initial_seed_customer_id);

    while (selected_customers_list.size() < numCustomersToRemove) {
        int source_idx = getRandomNumber(0, selected_customers_list.size() - 1);
        int source_customer_id = selected_customers_list[source_idx];

        std::vector<int> potential_neighbors_to_add;

        for (int i = 0; i < std::min((int)sol.instance.adj[source_customer_id].size(), neighborhood_search_limit); ++i) {
            int neighbor_id = sol.instance.adj[source_customer_id][i];
            if (neighbor_id != 0 && selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                potential_neighbors_to_add.push_back(neighbor_id);
            }
        }

        if (!potential_neighbors_to_add.empty()) {
            int new_customer = potential_neighbors_to_add[getRandomNumber(0, potential_neighbors_to_add.size() - 1)];
            selected_customers_list.push_back(new_customer);
            selected_customers_set.insert(new_customer);
        } else {
            int fallback_customer_id;
            bool found_fallback = false;
            for (int k = 0; k < 100 && selected_customers_list.size() < sol.instance.numCustomers; ++k) {
                fallback_customer_id = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(fallback_customer_id) == selected_customers_set.end()) {
                    selected_customers_list.push_back(fallback_customer_id);
                    selected_customers_set.insert(fallback_customer_id);
                    found_fallback = true;
                    break;
                }
            }
            if (!found_fallback && selected_customers_list.size() < numCustomersToRemove) {
                break;
            }
        }
    }
    return selected_customers_list;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        return instance.prizes[c1] > instance.prizes[c2];
    });

    const float P_swap = 0.15;

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < P_swap) {
            std::swap(customers[i], customers[i+1]);
        }
    }
}