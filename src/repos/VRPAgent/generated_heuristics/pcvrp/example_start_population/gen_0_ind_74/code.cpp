#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <numeric>
#include "Utils.h"
#include <queue>


struct CustomerScore {
    int id;
    float score;

    bool operator>(const CustomerScore& other) const {
        return score > other.score;
    }
};

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(10, 20);

    if (numCustomersToRemove == 0) {
        return {};
    }

    int initialSeedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    
    std::vector<int> candidates; 
    candidates.push_back(initialSeedCustomer);
    selectedCustomersSet.insert(initialSeedCustomer);
    selectedCustomersList.push_back(initialSeedCustomer);

    std::unordered_set<int> visitedCandidates;
    visitedCandidates.insert(initialSeedCustomer);

    float diversification_prob = 0.15f;
    int max_neighbors_to_consider = 3;

    int currentCandidateIdx = 0;

    while (selectedCustomersList.size() < numCustomersToRemove) {
        int currentCustomer;

        if (getRandomFraction() < diversification_prob || currentCandidateIdx >= candidates.size()) {
            currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.count(currentCustomer)) {
                continue;
            }
            if (visitedCandidates.find(currentCustomer) == visitedCandidates.end()) {
                candidates.push_back(currentCustomer);
                visitedCandidates.insert(currentCustomer);
            }
            // If we've just diversified by adding a new random customer, try to process it
            // if we are out of other candidates, or randomly pick it.
            // For simplicity, just let the next iteration pick it if it's the only un-processed candidate.
            // Or ensure we pick from candidates that haven't been processed yet.
            // A simple `currentCandidateIdx = candidates.size() -1;` here would prioritize it.
            // Let's refine this to ensure we always try to process an available candidate efficiently.
            // If currentCandidateIdx is exhausted, a new random one will replenish and we will try process it next.
        }
        
        if (currentCandidateIdx < candidates.size()) {
            currentCustomer = candidates[currentCandidateIdx];
            currentCandidateIdx++;
        } else {
            // This happens if candidates became empty and diversification_prob didn't yield a new one yet.
            // Or if all candidates have been selected.
            // We need to ensure we get a new random customer if we're out of options.
            currentCustomer = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.count(currentCustomer)) {
                continue;
            }
            if (visitedCandidates.find(currentCustomer) == visitedCandidates.end()) {
                candidates.push_back(currentCustomer);
                visitedCandidates.insert(currentCustomer);
                currentCandidateIdx = candidates.size() - 1; // Prioritize this new one
                currentCustomer = candidates[currentCandidateIdx]; // Set currentCustomer to the newly added one
                currentCandidateIdx++;
            } else {
                continue; // Already processed/selected, try again.
            }
        }

        if (selectedCustomersSet.find(currentCustomer) == selectedCustomersSet.end()) {
            selectedCustomersSet.insert(currentCustomer);
            selectedCustomersList.push_back(currentCustomer);
        }
        if (selectedCustomersList.size() >= numCustomersToRemove) {
            break; 
        }

        for (int i = 0; i < std::min((int)sol.instance.adj[currentCustomer].size(), max_neighbors_to_consider); ++i) {
            int neighbor = sol.instance.adj[currentCustomer][i];
            if (neighbor != 0 && selectedCustomersSet.find(neighbor) == selectedCustomersSet.end() && visitedCandidates.find(neighbor) == visitedCandidates.end()) {
                if (getRandomFraction() < 0.8f) {
                    candidates.push_back(neighbor);
                    visitedCandidates.insert(neighbor);
                }
            }
        }
    }
    
    if (selectedCustomersList.size() > numCustomersToRemove) {
        selectedCustomersList.resize(numCustomersToRemove);
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<CustomerScore> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float epsilon_noise_factor = 0.05f;
    float min_demand_epsilon = 1e-6f;

    for (int customerId : customers) {
        float score = instance.prizes[customerId] / (instance.demand[customerId] + min_demand_epsilon);
        
        score += getRandomFraction(-epsilon_noise_factor, epsilon_noise_factor) * score;
        
        scoredCustomers.push_back({customerId, score});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const CustomerScore& a, const CustomerScore& b) {
        return a.score > b.score;
    });

    for (size_t i = 0; i < scoredCustomers.size(); ++i) {
        customers[i] = scoredCustomers[i].id;
    }
}