#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    int numCustomersToRemove = getRandomNumber(10, 25);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(initial_customer_id);
    selected_customers_vec.push_back(initial_customer_id);

    const int K_NEIGHBORS_TO_CONSIDER = 15;
    const int MAX_ANCHOR_RETRIES = 5;

    while (selected_customers_vec.size() < numCustomersToRemove) {
        int current_retries = 0;
        bool added_customer_in_iteration = false;

        while (!added_customer_in_iteration && current_retries < MAX_ANCHOR_RETRIES) {
            int anchor_idx_in_vec = getRandomNumber(0, static_cast<int>(selected_customers_vec.size()) - 1);
            int anchor_customer_id = selected_customers_vec[anchor_idx_in_vec];

            std::vector<int> candidate_neighbors;
            for (int neighbor_id : sol.instance.adj[anchor_customer_id]) {
                if (selected_customers_set.count(neighbor_id) == 0) {
                    candidate_neighbors.push_back(neighbor_id);
                    if (candidate_neighbors.size() >= K_NEIGHBORS_TO_CONSIDER) {
                        break;
                    }
                }
            }

            if (!candidate_neighbors.empty()) {
                int selected_neighbor_idx = getRandomNumber(0, static_cast<int>(candidate_neighbors.size()) - 1);
                int new_customer_id = candidate_neighbors[selected_neighbor_idx];

                selected_customers_set.insert(new_customer_id);
                selected_customers_vec.push_back(new_customer_id);
                added_customer_in_iteration = true;
            } else {
                current_retries++;
            }
        }

        if (!added_customer_in_iteration) {
            int random_customer_id;
            do {
                random_customer_id = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_customers_set.count(random_customer_id) > 0 && selected_customers_set.size() < sol.instance.numCustomers);

            if (selected_customers_set.count(random_customer_id) > 0 && selected_customers_set.size() == sol.instance.numCustomers) {
                break; 
            }

            selected_customers_set.insert(random_customer_id);
            selected_customers_vec.push_back(random_customer_id);
        }
    }
    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    int strategy_choice = getRandomNumber(0, 3); 

    if (strategy_choice == 0) {
        std::shuffle(customers.begin(), customers.end(), gen);
    } else if (strategy_choice == 1) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.demand[c1] > instance.demand[c2];
        });
    } else if (strategy_choice == 2) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
        });
    } else if (strategy_choice == 3) {
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            float min_dist_c1 = std::numeric_limits<float>::max();
            float min_dist_c2 = std::numeric_limits<float>::max();

            for (int other_c : customers) {
                if (c1 != other_c) {
                    min_dist_c1 = std::min(min_dist_c1, instance.distanceMatrix[c1][other_c]);
                }
            }

            for (int other_c : customers) {
                if (c2 != other_c) {
                    min_dist_c2 = std::min(min_dist_c2, instance.distanceMatrix[c2][other_c]);
                }
            }
            return min_dist_c1 > min_dist_c2;
        });
    }
}