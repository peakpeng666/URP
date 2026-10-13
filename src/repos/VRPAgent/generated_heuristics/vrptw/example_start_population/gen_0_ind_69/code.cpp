#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::sort
#include <utility>   // For std::pair
#include "Utils.h"

// Constants for select_by_llm_1
static const int MIN_REMOVE_CUSTOMERS = 10;
static const int MAX_REMOVE_CUSTOMERS = 20;
static const float EXPANSION_PROBABILITY = 0.85f; // Probability of expanding from an already selected customer
static const int NUM_NEIGHBORS_TO_CONSIDER = 5;  // When expanding, consider top N closest neighbors

// Helper struct for sorting in sort_by_llm_1
struct CustomerSortInfo {
    int id;
    float start_tw;
    float tw_width;
    float random_noise; // For stochasticity in tie-breaking
};

// Custom comparison function for sorting CustomerSortInfo
bool compareCustomers(const CustomerSortInfo& a, const CustomerSortInfo& b) {
    // Primary sort: earliest start time window
    if (a.start_tw != b.start_tw) {
        return a.start_tw < b.start_tw;
    }
    // Secondary sort: narrowest time window width
    if (a.tw_width != b.tw_width) {
        return a.tw_width < b.tw_width;
    }
    // Tertiary: random noise for stochastic tie-breaking
    return a.random_noise < b.random_noise;
}

// Step 1: Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selected_customers_vec;
    std::unordered_set<int> selected_customers_set;

    int numCustomersToRemove = getRandomNumber(MIN_REMOVE_CUSTOMERS, MAX_REMOVE_CUSTOMERS);

    // Ensure at least one customer is picked initially
    if (sol.instance.numCustomers == 0) {
        return selected_customers_vec;
    }

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_vec.push_back(seed_customer);
    selected_customers_set.insert(seed_customer);

    while (selected_customers_vec.size() < numCustomersToRemove) {
        int candidate_customer_id = -1;
        bool chosen_globally = getRandomFractionFast() < (1.0f - EXPANSION_PROBABILITY);

        if (chosen_globally) {
            // Attempt to find a completely random unselected customer (global exploration)
            int attempts = 0;
            while (attempts < 100) { // Limit attempts to prevent infinite loop on small instances
                int rand_c = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(rand_c) == selected_customers_set.end()) {
                    candidate_customer_id = rand_c;
                    break;
                }
                attempts++;
            }
        }

        if (candidate_customer_id == -1) { // If global choice failed or not chosen
            // Expand from an already selected customer (local exploration)
            if (selected_customers_vec.empty()) { // Should not happen after initial seed
                 break;
            }
            int source_customer_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
            int source_customer = selected_customers_vec[source_customer_idx];

            std::vector<int> neighbor_candidates;
            // Iterate through `adj` list for closest neighbors
            for (int neighbor_id : sol.instance.adj[source_customer]) {
                // Ensure neighbor_id is a customer (1 to numCustomers) and not depot (0)
                // and not already selected
                if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers &&
                    selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                    neighbor_candidates.push_back(neighbor_id);
                    if (neighbor_candidates.size() >= NUM_NEIGHBORS_TO_CONSIDER) {
                        break; // Limit the number of neighbors considered for speed
                    }
                }
            }

            if (!neighbor_candidates.empty()) {
                candidate_customer_id = neighbor_candidates[getRandomNumber(0, neighbor_candidates.size() - 1)];
            } else {
                // Fallback: if no suitable neighbors found, try a random customer globally
                int attempts = 0;
                while (attempts < 100) {
                    int rand_c = getRandomNumber(1, sol.instance.numCustomers);
                    if (selected_customers_set.find(rand_c) == selected_customers_set.end()) {
                        candidate_customer_id = rand_c;
                        break;
                    }
                    attempts++;
                }
            }
        }

        if (candidate_customer_id != -1) {
            selected_customers_vec.push_back(candidate_customer_id);
            selected_customers_set.insert(candidate_customer_id);
        } else {
            // If no customer could be added after all attempts (e.g., all customers selected, or very small instance)
            break;
        }
    }

    return selected_customers_vec;
}

// Step 3: Ordering of the removed customers heuristic
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<CustomerSortInfo> sort_info_list;
    sort_info_list.reserve(customers.size());

    for (int customer_id : customers) {
        CustomerSortInfo info;
        info.id = customer_id;
        info.start_tw = instance.startTW[customer_id];
        info.tw_width = instance.TW_Width[customer_id];
        info.random_noise = getRandomFractionFast(); // [0, 1] for tie-breaking
        sort_info_list.push_back(info);
    }

    std::sort(sort_info_list.begin(), sort_info_list.end(), compareCustomers);

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_info_list[i].id;
    }
}