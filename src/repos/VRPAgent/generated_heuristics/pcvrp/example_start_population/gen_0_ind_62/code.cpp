#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_REMOVE_COUNT = 10;
    const int MAX_REMOVE_COUNT = 20;
    const int NUM_INITIAL_SEEDS_MIN = 2;
    const int NUM_INITIAL_SEEDS_MAX = 4;
    const int NEIGHBOR_CONSIDERATION_LIMIT = 15;

    int numCustomersToRemove = getRandomNumber(MIN_REMOVE_COUNT, MAX_REMOVE_COUNT);
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerPool;
    std::unordered_set<int> customerPoolSet;

    std::vector<int> visited_customer_ids;
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        if (sol.customerToTourMap[i] != -1) {
            visited_customer_ids.push_back(i);
        }
    }

    if (visited_customer_ids.empty()) {
        for (int i = 1; i <= sol.instance.numCustomers; ++i) {
            visited_customer_ids.push_back(i);
        }
        if (visited_customer_ids.empty()) return {};
    }

    int numInitialSeeds = getRandomNumber(NUM_INITIAL_SEEDS_MIN, NUM_INITIAL_SEEDS_MAX);
    numInitialSeeds = std::min(numInitialSeeds, (int)visited_customer_ids.size());

    static thread_local std::mt19937 gen(std::random_device{}());
    std::shuffle(visited_customer_ids.begin(), visited_customer_ids.end(), gen);

    for (int i = 0; i < numInitialSeeds && selectedCustomers.size() < numCustomersToRemove; ++i) {
        int seed_customer = visited_customer_ids[i];
        if (selectedCustomers.insert(seed_customer).second) {
            for (int j = 0; j < std::min((int)sol.instance.adj[seed_customer].size(), NEIGHBOR_CONSIDERATION_LIMIT); ++j) {
                int neighbor_node = sol.instance.adj[seed_customer][j];
                if (neighbor_node > 0 && neighbor_node <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighbor_node) == selectedCustomers.end() &&
                    customerPoolSet.find(neighbor_node) == customerPoolSet.end())
                {
                    customerPool.push_back(neighbor_node);
                    customerPoolSet.insert(neighbor_node);
                }
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove && !customerPool.empty()) {
        int rand_idx = getRandomNumber(0, (int)customerPool.size() - 1);
        int current_customer = customerPool[rand_idx];

        std::swap(customerPool[rand_idx], customerPool.back());
        customerPool.pop_back();
        customerPoolSet.erase(current_customer);

        if (selectedCustomers.insert(current_customer).second) {
            if (selectedCustomers.size() == numCustomersToRemove) {
                break;
            }
            for (int j = 0; j < std::min((int)sol.instance.adj[current_customer].size(), NEIGHBOR_CONSIDERATION_LIMIT); ++j) {
                int neighbor_node = sol.instance.adj[current_customer][j];
                if (neighbor_node > 0 && neighbor_node <= sol.instance.numCustomers &&
                    selectedCustomers.find(neighbor_node) == selectedCustomers.end() &&
                    customerPoolSet.find(neighbor_node) == customerPoolSet.end())
                {
                    customerPool.push_back(neighbor_node);
                    customerPoolSet.insert(neighbor_node);
                }
            }
        }
    }
    
    if (selectedCustomers.size() < numCustomersToRemove) {
        std::vector<int> remaining_customers;
        for (int customer_id : visited_customer_ids) {
            if (selectedCustomers.find(customer_id) == selectedCustomers.end()) {
                remaining_customers.push_back(customer_id);
            }
        }
        std::shuffle(remaining_customers.begin(), remaining_customers.end(), gen);
        for (int customer_id : remaining_customers) {
            if (selectedCustomers.size() < numCustomersToRemove) {
                selectedCustomers.insert(customer_id);
            } else {
                break;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    std::vector<int> sorted_customers;
    sorted_customers.reserve(customers.size());
    std::unordered_set<int> added_to_sorted;

    int first_idx = getRandomNumber(0, (int)customers.size() - 1);
    int current_customer = customers[first_idx];

    sorted_customers.push_back(current_customer);
    added_to_sorted.insert(current_customer);

    for (size_t i = 1; i < customers.size(); ++i) {
        float min_dist = std::numeric_limits<float>::max();
        int next_customer = -1;

        for (int c : customers) {
            if (added_to_sorted.find(c) == added_to_sorted.end()) {
                float dist = instance.distanceMatrix[current_customer][c];
                if (dist < min_dist) {
                    min_dist = dist;
                    next_customer = c;
                }
            }
        }

        if (next_customer != -1) {
            sorted_customers.push_back(next_customer);
            added_to_sorted.insert(next_customer);
            current_customer = next_customer;
        } else {
            for(int c : customers) {
                if(added_to_sorted.find(c) == added_to_sorted.end()) {
                    sorted_customers.push_back(c);
                    added_to_sorted.insert(c);
                }
            }
            break; 
        }
    }

    customers = sorted_customers;
}