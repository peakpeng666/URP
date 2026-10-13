#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort, std::min
#include <utility>   // For std::pair

#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToSelect = getRandomNumber(10, 20); // Small number of customers
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> resultCustomers;

    // Start with a random seed customer
    int current_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(current_customer);
    resultCustomers.push_back(current_customer);

    int max_adj_neighbors_to_check = 15; // Number of closest neighbors to consider for selection
    int fallback_counter = 0;
    const int MAX_FALLBACK_ATTEMPTS = numCustomersToSelect * 10; // Max attempts before forcing a random pick

    while (selectedCustomersSet.size() < numCustomersToSelect) {
        bool added_new_customer = false;

        if (!resultCustomers.empty()) {
            // Pick a random customer from the already selected ones
            int source_idx = getRandomNumber(0, resultCustomers.size() - 1);
            int source_customer = resultCustomers[source_idx];

            int num_neighbors = sol.instance.adj[source_customer].size();
            int effective_num_neighbors = std::min(num_neighbors, max_adj_neighbors_to_check);

            if (effective_num_neighbors > 0) {
                // Attempt to pick a neighbor randomly from the closest ones
                int attempts_per_source = 0;
                const int MAX_ATTEMPTS_PER_SOURCE = 5; // Limit attempts from one source

                while (attempts_per_source < MAX_ATTEMPTS_PER_SOURCE) {
                    int neighbor_idx = getRandomNumber(0, effective_num_neighbors - 1);
                    int candidate_neighbor = sol.instance.adj[source_customer][neighbor_idx];

                    // Check if candidate is not the depot (0) and not already selected
                    if (candidate_neighbor != 0 && !selectedCustomersSet.count(candidate_neighbor)) {
                        selectedCustomersSet.insert(candidate_neighbor);
                        resultCustomers.push_back(candidate_neighbor);
                        added_new_customer = true;
                        fallback_counter = 0; // Reset fallback counter on success
                        break;
                    }
                    attempts_per_source++;
                }
            }
        }

        if (!added_new_customer) {
            fallback_counter++;
            // If unable to find a connected customer after many attempts or if progress is slow,
            // pick a truly random unselected customer as a fallback to ensure completion and diversity.
            if (fallback_counter > MAX_FALLBACK_ATTEMPTS ||
                (selectedCustomersSet.size() < (numCustomersToSelect / 2) && fallback_counter > MAX_FALLBACK_ATTEMPTS / 2)) {
                int random_customer_fallback;
                do {
                    random_customer_fallback = getRandomNumber(1, sol.instance.numCustomers);
                } while (selectedCustomersSet.count(random_customer_fallback)); // Ensure it's not already selected

                selectedCustomersSet.insert(random_customer_fallback);
                resultCustomers.push_back(random_customer_fallback);
                fallback_counter = 0; // Reset fallback counter after fallback
            }
        }
    }

    return resultCustomers;
}


// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_scores; // Pair of (score, customer_id)
    std::unordered_set<int> removed_customers_set(customers.begin(), customers.end()); // For O(1) lookup

    const int MAX_ADJ_NEIGHBORS_FOR_SCORE = 20; // Number of closest neighbors to check for connectivity score

    for (int cust_id : customers) {
        float connectivity_score = 0.0;
        int num_neighbors_to_check = std::min((int)instance.adj[cust_id].size(), MAX_ADJ_NEIGHBORS_FOR_SCORE);

        for (int i = 0; i < num_neighbors_to_check; ++i) {
            int neighbor_id = instance.adj[cust_id][i];
            if (removed_customers_set.count(neighbor_id)) { // Check if neighbor is also in the removed set
                connectivity_score += 1.0;
            }
        }

        // Combine connectivity and demand into a single score.
        // Connectivity is prioritized (multiplied by a large factor) as it relates to forming clusters,
        // then demand is considered (higher demand customers are generally harder to place).
        float combined_score = connectivity_score * 1000.0f + instance.demand[cust_id];
        customer_scores.push_back({combined_score, cust_id});
    }

    // Sort in descending order of combined_score (higher score first)
    std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the new sorted order
    for (size_t i = 0; i < customer_scores.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}