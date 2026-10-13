#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

static thread_local std::mt19937 gen_select(std::random_device{}());
static thread_local std::mt19937 gen_sort(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    if (sol.instance.numCustomers == 0) {
        return {};
    }

    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_list;

    int num_to_remove = getRandomNumber(10, 30);
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1;
    }
    if (num_to_remove == 0) { // If numCustomers was 0, or it somehow became 0
        return {};
    }

    int start_customer_idx;
    bool found_valid_start = false;
    for (int i = 0; i < 10; ++i) { // Try a few times to get a visited customer, or any random if none visited
        start_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
        if (sol.customerToTourMap[start_customer_idx] != -1) {
            found_valid_start = true;
            break;
        }
    }
    if (!found_valid_start) { // Fallback if no visited customer found, or all customers are unvisited
         start_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    }
    
    selected_customers_set.insert(start_customer_idx);
    selected_customers_list.push_back(start_customer_idx);

    const int K_NEIGHBORS_TO_CONSIDER = 7; 
    int seed_customer_list_idx = 0; 

    while (selected_customers_set.size() < num_to_remove) {
        if (selected_customers_list.empty()) { 
            int new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            if (selected_customers_set.find(new_random_customer) == selected_customers_set.end()) {
                selected_customers_set.insert(new_random_customer);
                selected_customers_list.push_back(new_random_customer);
            }
            continue;
        }

        int seed_customer = selected_customers_list[seed_customer_list_idx % selected_customers_list.size()];
        seed_customer_list_idx++;

        const std::vector<int>& neighbors = sol.instance.adj[seed_customer];
        
        bool added_new = false;
        // Collect potential candidates from neighbors, applying stochasticity
        std::vector<int> candidates;
        for (size_t i = 0; i < neighbors.size() && i < K_NEIGHBORS_TO_CONSIDER; ++i) {
            int candidate_customer = neighbors[i];
            float selection_prob = 1.0f - (static_cast<float>(i) / K_NEIGHBORS_TO_CONSIDER) * 0.4f; 
            if (getRandomFractionFast() < selection_prob) {
                if (selected_customers_set.find(candidate_customer) == selected_customers_set.end()) {
                    candidates.push_back(candidate_customer);
                }
            }
        }

        if (!candidates.empty()) {
            std::shuffle(candidates.begin(), candidates.end(), gen_select); // Randomize candidate order
            selected_customers_set.insert(candidates[0]);
            selected_customers_list.push_back(candidates[0]);
            added_new = true;
        }

        if (!added_new && selected_customers_set.size() < num_to_remove) {
            // If no new customer was added from current seed, and we've exhausted trying neighbors,
            // pick a new random customer to ensure progress and diversity.
            int new_random_customer = getRandomNumber(1, sol.instance.numCustomers);
            if (selected_customers_set.find(new_random_customer) == selected_customers_set.end()) {
                selected_customers_set.insert(new_random_customer);
                selected_customers_list.push_back(new_random_customer);
            }
        }
    }
    
    if (selected_customers_list.size() > num_to_remove) {
        selected_customers_list.resize(num_to_remove);
    }

    std::shuffle(selected_customers_list.begin(), selected_customers_list.end(), gen_select);

    return selected_customers_list;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customer_prizes_pairs;
    customer_prizes_pairs.reserve(customers.size());

    for (int customer_id : customers) {
        if (customer_id >= 0 && customer_id < instance.prizes.size()) { // Basic bounds check
            customer_prizes_pairs.push_back({instance.prizes[customer_id], customer_id});
        }
    }

    std::sort(customer_prizes_pairs.begin(), customer_prizes_pairs.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first; 
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_prizes_pairs[i].second;
    }

    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFractionFast() < 0.15f) { 
            std::swap(customers[i], customers[i+1]);
        }
    }
}