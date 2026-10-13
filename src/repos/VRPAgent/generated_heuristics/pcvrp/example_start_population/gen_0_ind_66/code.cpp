#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // Required for std::sort
#include <vector>    // Required for std::vector
#include "Utils.h"   // Required for getRandomNumber, getRandomFractionFast

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersVec; 
    std::vector<int> expansionFrontier; 

    // Determine a stochastic number of customers to remove
    int numCustomersToRemove = getRandomNumber(5, 25); 

    if (sol.instance.numCustomers == 0) {
        return {};
    }

    // Start by selecting a random seed customer
    int seedCustomer = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    selectedCustomersVec.push_back(seedCustomer);
    expansionFrontier.push_back(seedCustomer);

    // Expand the selection from the frontier until enough customers are chosen
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        // If the current expansion frontier is exhausted, start a new cluster from a random unselected customer
        if (expansionFrontier.empty()) {
            int newSeed = getRandomNumber(1, sol.instance.numCustomers);
            if (selectedCustomersSet.insert(newSeed).second) { // Attempt to insert; .second is true if successful (wasn't already there)
                selectedCustomersVec.push_back(newSeed);
                expansionFrontier.push_back(newSeed);
            }
            continue; 
        }

        // Randomly pick a customer from the current frontier to expand from
        int frontierIdx = getRandomNumber(0, expansionFrontier.size() - 1);
        int currentCustomer = expansionFrontier[frontierIdx];
        // Remove the chosen customer from the frontier to avoid immediate re-processing from it
        expansionFrontier.erase(expansionFrontier.begin() + frontierIdx); 

        int neighborsChecked = 0;
        const int maxNeighborsToCheck = 10; // Limit the number of closest neighbors to check for speed and locality
        const float probAddNeighbor = 0.85f; // Probability to consider adding an encountered neighbor

        // Iterate through the closest neighbors (adj list is sorted by distance)
        for (int neighbor : sol.instance.adj[currentCustomer]) {
            if (selectedCustomersSet.size() == numCustomersToRemove) {
                break; 
            }
            if (neighborsChecked >= maxNeighborsToCheck) {
                break; 
            }
            
            // Stochastic decision to consider adding this neighbor
            if (getRandomFractionFast() < probAddNeighbor) {
                // If the neighbor is not already selected, add it to the set and frontier
                if (selectedCustomersSet.insert(neighbor).second) {
                    selectedCustomersVec.push_back(neighbor);
                    expansionFrontier.push_back(neighbor); 
                }
            }
            neighborsChecked++;
        }
    }
    return selectedCustomersVec;
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Store pairs of (score, customerId) for sorting
    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    // Calculate a score for each customer based on prize/demand, with stochastic perturbation
    for (int customerId : customers) {
        float prize = instance.prizes[customerId];
        float demand = instance.demand[customerId];
        
        float score;
        if (demand > 0) {
            score = prize / demand;
        } else {
            // Customers with 0 demand: If they have a prize, they are extremely valuable (infinite prize/demand).
            // If they also have 0 prize, they are not valuable.
            score = prize > 0 ? 1e9f : -1e9f; 
        }
        
        // Add a small stochastic component to break ties and introduce diversity
        score += getRandomFractionFast() * 0.001f; 
        scoredCustomers.push_back({score, customerId});
    }

    // Sort customers in descending order based on their calculated score
    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}