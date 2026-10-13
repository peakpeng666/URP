#include "AgentDesigned.h"
#include <vector>
#include <algorithm> // For std::sort
#include <unordered_set>
#include <random> // For std::mt19937, std::random_device (though getRandomNumber is used)
#include "Utils.h"

void add_neighbors_to_candidates(int customer_id, const Instance& instance,
                                 std::vector<int>& candidateCustomersList,
                                 std::unordered_set<int>& inCandidateCustomersSet,
                                 const std::unordered_set<int>& selectedCustomers) {
    int num_neighbors_to_consider = getRandomNumber(3, 8); 

    int actual_neighbors = std::min((int)instance.adj[customer_id].size(), num_neighbors_to_consider);

    for (int i = 0; i < actual_neighbors; ++i) {
        int neighbor_id = instance.adj[customer_id][i];
        if (neighbor_id != 0 &&
            selectedCustomers.find(neighbor_id) == selectedCustomers.end() &&
            inCandidateCustomersSet.find(neighbor_id) == inCandidateCustomersSet.end()) {
            
            candidateCustomersList.push_back(neighbor_id);
            inCandidateCustomersSet.insert(neighbor_id);
        }
    }
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> candidateCustomersList;
    std::unordered_set<int> inCandidateCustomersSet;

    int numCustomersToRemove = getRandomNumber(15, 25); 

    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers.insert(seed_customer);

    add_neighbors_to_candidates(seed_customer, sol.instance, candidateCustomersList, inCandidateCustomersSet, selectedCustomers);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (candidateCustomersList.empty()) {
            int new_seed_customer;
            do {
                new_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomers.count(new_seed_customer));
            
            selectedCustomers.insert(new_seed_customer);
            add_neighbors_to_candidates(new_seed_customer, sol.instance, candidateCustomersList, inCandidateCustomersSet, selectedCustomers);

            if (selectedCustomers.size() >= numCustomersToRemove || candidateCustomersList.empty()) {
                break;
            }
        }
        
        int rand_idx = getRandomNumber(0, (int)candidateCustomersList.size() - 1);
        int current_customer = candidateCustomersList[rand_idx];

        candidateCustomersList[rand_idx] = candidateCustomersList.back();
        candidateCustomersList.pop_back();
        inCandidateCustomersSet.erase(current_customer);

        if (selectedCustomers.find(current_customer) == selectedCustomers.end()) {
            selectedCustomers.insert(current_customer);
            add_neighbors_to_candidates(current_customer, sol.instance, candidateCustomersList, inCandidateCustomersSet, selectedCustomers);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    for (int customer_id : customers) {
        float score = instance.prizes[customer_id] 
                      - instance.distanceMatrix[0][customer_id] 
                      - (getRandomFraction(0.0f, 0.05f) * instance.demand[customer_id]); 

        score += getRandomFraction(-5.0f, 5.0f); 

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