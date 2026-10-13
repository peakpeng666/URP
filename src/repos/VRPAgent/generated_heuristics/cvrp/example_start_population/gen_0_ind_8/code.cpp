#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include "Utils.h"

template<typename T>
T pop_random_element(std::vector<T>& vec) {
    if (vec.empty()) {
        return T();
    }
    int idx = getRandomNumber(0, vec.size() - 1);
    T element = vec[idx];
    vec[idx] = vec.back();
    vec.pop_back();
    return element;
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    const Instance& instance = sol.instance;

    int num_to_remove = getRandomNumber(15, 30);
    if (instance.numCustomers < 500) {
        num_to_remove = std::max(5, std::min(num_to_remove, instance.numCustomers / 5));
    }

    int initial_customer = getRandomNumber(1, instance.numCustomers);
    selected_customers_set.insert(initial_customer);
    selected_customers_vec.push_back(initial_customer);

    std::vector<int> candidate_neighbors;
    std::unordered_set<int> candidate_neighbors_set;

    int num_initial_neighbors_to_add = std::min((int)instance.adj[initial_customer].size(), 10);
    for (int i = 0; i < num_initial_neighbors_to_add; ++i) {
        int neighbor_id = instance.adj[initial_customer][i];
        if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
            candidate_neighbors_set.find(neighbor_id) == candidate_neighbors_set.end()) {
            candidate_neighbors.push_back(neighbor_id);
            candidate_neighbors_set.insert(neighbor_id);
        }
    }

    while (selected_customers_vec.size() < num_to_remove) {
        if (candidate_neighbors.empty()) {
            int fallback_customer = -1;
            std::vector<int> all_customers_shuffled(instance.numCustomers);
            for(int i = 0; i < instance.numCustomers; ++i) all_customers_shuffled[i] = i + 1;
            static thread_local std::mt19937 gen_local(std::random_device{}());
            std::shuffle(all_customers_shuffled.begin(), all_customers_shuffled.end(), gen_local);

            for (int cust_id : all_customers_shuffled) {
                if (selected_customers_set.find(cust_id) == selected_customers_set.end()) {
                    fallback_customer = cust_id;
                    break;
                }
            }
            if (fallback_customer == -1) {
                break;
            }

            selected_customers_set.insert(fallback_customer);
            selected_customers_vec.push_back(fallback_customer);

            num_initial_neighbors_to_add = std::min((int)instance.adj[fallback_customer].size(), 10);
            for (int i = 0; i < num_initial_neighbors_to_add; ++i) {
                int neighbor_id = instance.adj[fallback_customer][i];
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    candidate_neighbors_set.find(neighbor_id) == candidate_neighbors_set.end()) {
                    candidate_neighbors.push_back(neighbor_id);
                    candidate_neighbors_set.insert(neighbor_id);
                }
            }
            continue;
        }

        int next_customer_to_add = pop_random_element(candidate_neighbors);
        candidate_neighbors_set.erase(next_customer_to_add);

        if (selected_customers_set.find(next_customer_to_add) == selected_customers_set.end()) {
            selected_customers_set.insert(next_customer_to_add);
            selected_customers_vec.push_back(next_customer_to_add);

            int num_neighbors_to_add_per_step = std::min((int)instance.adj[next_customer_to_add].size(), 5);
            for (int i = 0; i < num_neighbors_to_add_per_step; ++i) {
                int neighbor_id = instance.adj[next_customer_to_add][i];
                if (selected_customers_set.find(neighbor_id) == selected_customers_set.end() &&
                    candidate_neighbors_set.find(neighbor_id) == candidate_neighbors_set.end()) {
                    candidate_neighbors.push_back(neighbor_id);
                    candidate_neighbors_set.insert(neighbor_id);
                }
            }
        }
    }

    return selected_customers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    int strategy_choice = getRandomNumber(0, 2);

    if (strategy_choice == 0) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.distanceMatrix[0][a] < instance.distanceMatrix[0][b];
        });
    } else if (strategy_choice == 1) {
        std::sort(customers.begin(), customers.end(), [&](int a, int b) {
            return instance.demand[a] > instance.demand[b];
        });
    } else {
        std::shuffle(customers.begin(), customers.end(), gen);
    }
}