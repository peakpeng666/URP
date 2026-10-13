#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int min_remove_customers = 10;
    int max_remove_customers = 20;
    int num_to_remove = getRandomNumber(min_remove_customers, max_remove_customers);

    std::unordered_set<int> selected_customers_set;
    std::vector<int> potential_sources; 

    int first_seed = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(first_seed);
    potential_sources.push_back(first_seed);

    int max_neighbors_to_check_per_source = 5;

    while (selected_customers_set.size() < num_to_remove && !potential_sources.empty()) {
        int source_idx_in_vec = getRandomNumber(0, potential_sources.size() - 1);
        int source_customer = potential_sources[source_idx_in_vec];

        const std::vector<int>& neighbors = sol.instance.adj[source_customer];
        int neighbors_explored_from_current_source = 0;

        for (int neighbor_id : neighbors) {
            if (selected_customers_set.size() == num_to_remove) break;

            if (neighbor_id == 0 || neighbor_id > sol.instance.numCustomers) {
                continue;
            }

            if (selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                float prob_add = 0.6;
                if (getRandomFraction() < prob_add) {
                    selected_customers_set.insert(neighbor_id);
                    potential_sources.push_back(neighbor_id);
                }
            }
            neighbors_explored_from_current_source++;
            if (neighbors_explored_from_current_source >= max_neighbors_to_check_per_source) {
                break;
            }
        }
        
        if (selected_customers_set.size() < num_to_remove && getRandomFraction() < 0.15) {
            int new_seed = getRandomNumber(1, sol.instance.numCustomers);
            if (selected_customers_set.find(new_seed) == selected_customers_set.end()) {
                selected_customers_set.insert(new_seed);
                potential_sources.push_back(new_seed);
            }
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    float rand_choice = getRandomFraction();

    if (rand_choice < 0.7) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float tw1 = instance.TW_Width[c1];
            float tw2 = instance.TW_Width[c2];
            if (tw1 != tw2) return tw1 < tw2;

            float dist1 = instance.distanceMatrix[0][c1];
            float dist2 = instance.distanceMatrix[0][c2];
            if (dist1 != dist2) return dist1 > dist2;
            
            return c1 < c2;
        });
    } else if (rand_choice < 0.9) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            int demand1 = instance.demand[c1];
            int demand2 = instance.demand[c2];
            if (demand1 != demand2) return demand1 > demand2;

            float tw1 = instance.TW_Width[c1];
            float tw2 = instance.TW_Width[c2];
            if (tw1 != tw2) return tw1 < tw2;
            
            return c1 < c2;
        });
    } else {
        static thread_local std::mt19937 gen(std::random_device{}());
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}