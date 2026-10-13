#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort and std::shuffle
#include <vector>    // For std::vector
#include <utility>   // For std::pair

#include "Utils.h"

static std::mt19937& get_mt19937_generator() {
    static thread_local std::mt19937 gen(std::random_device{}());
    return gen;
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(8, 22);
    std::unordered_set<int> selectedCustomers;

    int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    int visited_seed_attempts = 5;
    while (sol.customerToTourMap[seed_customer_id] == -1 && visited_seed_attempts > 0) {
        seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        visited_seed_attempts--;
    }
    selectedCustomers.insert(seed_customer_id);

    while (selectedCustomers.size() < numCustomersToRemove) {
        bool customer_added_in_this_iteration = false;
        
        std::vector<int> current_selected_vector(selectedCustomers.begin(), selectedCustomers.end());
        
        std::shuffle(current_selected_vector.begin(), current_selected_vector.end(), get_mt19937_generator());

        for (int pivot_customer_id : current_selected_vector) {
            for (int neighbor_id : sol.instance.adj[pivot_customer_id]) {
                if (neighbor_id == 0) continue;
                if (selectedCustomers.find(neighbor_id) == selectedCustomers.end()) {
                    selectedCustomers.insert(neighbor_id);
                    customer_added_in_this_iteration = true;
                    break;
                }
            }
            if (customer_added_in_this_iteration) break;
        }

        if (!customer_added_in_this_iteration) {
            int random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
            int fallback_attempts = 0;
            while (selectedCustomers.find(random_unselected_customer) != selectedCustomers.end() && 
                   fallback_attempts < 100 &&
                   selectedCustomers.size() < sol.instance.numCustomers) {
                random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                fallback_attempts++;
            }
            
            if (selectedCustomers.find(random_unselected_customer) == selectedCustomers.end()) {
                selectedCustomers.insert(random_unselected_customer);
            } else {
                break; 
            }
        }
    }
    
    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    std::uniform_real_distribution<float> dist_noise(0.0f, 1.0f);

    float max_prize_in_customers = 0.0f;
    for (int customer_id : customers) {
        if (instance.prizes[customer_id] > max_prize_in_customers) {
            max_prize_in_customers = instance.prizes[customer_id];
        }
    }
    if (max_prize_in_customers < 1.0f) {
        max_prize_in_customers = 100.0f;
    }

    for (int customer_id : customers) {
        float stochastic_noise = dist_noise(get_mt19937_generator()) * (max_prize_in_customers * 0.005f);
        
        float score = instance.prizes[customer_id] - 
                      (static_cast<float>(instance.demand[customer_id]) * 0.01f) + 
                      stochastic_noise;
        
        customer_scores.push_back({score, customer_id});
    }

    std::sort(customer_scores.begin(), customer_scores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; 
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}