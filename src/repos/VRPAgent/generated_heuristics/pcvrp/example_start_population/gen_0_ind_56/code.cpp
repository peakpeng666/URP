#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> current_expansion_queue; 

    int num_customers_to_remove = getRandomNumber(10, 20);
    if (num_customers_to_remove > sol.instance.numCustomers) {
        num_customers_to_remove = sol.instance.numCustomers;
    }

    int num_customers = sol.instance.numCustomers;

    int seed_id;
    int max_seed_attempts = 100;
    bool found_visited_seed = false;

    for (int i = 0; i < max_seed_attempts; ++i) {
        int potential_seed = getRandomNumber(1, num_customers);
        if (sol.customerToTourMap[potential_seed] != -1) {
            seed_id = potential_seed;
            found_visited_seed = true;
            break;
        }
    }
    if (!found_visited_seed) {
        seed_id = getRandomNumber(1, num_customers);
    }
    
    selected_customers_set.insert(seed_id);
    current_expansion_queue.push_back(seed_id);

    size_t head = 0;
    while (selected_customers_set.size() < num_customers_to_remove) {
        if (head >= current_expansion_queue.size()) {
            int new_seed_fallback = -1;
            int fallback_attempts = 0;
            const int MAX_FALLBACK_ATTEMPTS = 500; 

            while (fallback_attempts < MAX_FALLBACK_ATTEMPTS) {
                int potential_fallback_customer = getRandomNumber(1, num_customers);
                if (selected_customers_set.find(potential_fallback_customer) == selected_customers_set.end()) {
                    new_seed_fallback = potential_fallback_customer;
                    break;
                }
                fallback_attempts++;
            }

            if (new_seed_fallback != -1) {
                selected_customers_set.insert(new_seed_fallback);
                current_expansion_queue.push_back(new_seed_fallback);
                head = current_expansion_queue.size() - 1;
            } else { 
                break;
            }
        }

        int focus_customer_id = current_expansion_queue[head++];

        for (int neighbor_id : sol.instance.adj[focus_customer_id]) {
            if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                if (getRandomFractionFast() < 0.75f) {
                    selected_customers_set.insert(neighbor_id);
                    current_expansion_queue.push_back(neighbor_id);
                    if (selected_customers_set.size() == num_customers_to_remove) {
                        goto end_selection_loop;
                    }
                }
            }
        }
    }
end_selection_loop:;

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    struct CustomerScore {
        int id;
        float score;
    };

    std::vector<CustomerScore> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id];
        
        score -= (float)instance.demand[customer_id] * 0.1f;

        if (instance.numCustomers > 0 && instance.total_prizes > 0) {
            score += getRandomFractionFast() * 0.5f * (instance.total_prizes / instance.numCustomers);
        } else {
            score += getRandomFractionFast();
        }

        customer_scores.push_back({customer_id, score});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [](const CustomerScore& a, const CustomerScore& b) {
        return a.score > b.score;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].id;
    }
}