#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <limits>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> potentialExpansionPoints;

    int numCustomersToRemove = getRandomNumber(10, 25); 

    if (sol.instance.numCustomers == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) { 
        numCustomersToRemove = 1; 
    }

    int initialCustomer = getRandomNumber(1, sol.instance.numCustomers); 
    selectedCustomersSet.insert(initialCustomer);
    potentialExpansionPoints.push_back(initialCustomer);

    const float P_ADD_NEIGHBOR = 0.8f; 
    const int MAX_NEIGHBORS_TO_CONSIDER = 15; 

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (potentialExpansionPoints.empty()) {
            int newStartCustomer = -1;
            int attempts = 0;
            const int MAX_RANDOM_ATTEMPTS = 100; 
            do {
                if (selectedCustomersSet.size() == sol.instance.numCustomers) break;
                newStartCustomer = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            } while (selectedCustomersSet.count(newStartCustomer) > 0 && attempts < MAX_RANDOM_ATTEMPTS);

            if (selectedCustomersSet.count(newStartCustomer) == 0 && newStartCustomer != -1) { 
                selectedCustomersSet.insert(newStartCustomer);
                potentialExpansionPoints.push_back(newStartCustomer);
            } else if (selectedCustomersSet.size() == sol.instance.numCustomers) {
                break; 
            } else { 
                while(selectedCustomersSet.size() < numCustomersToRemove && selectedCustomersSet.size() < sol.instance.numCustomers){
                    int randCust = getRandomNumber(1, sol.instance.numCustomers);
                    selectedCustomersSet.insert(randCust);
                }
                break;
            }
        }

        int seedCustomerIdx = getRandomNumber(0, potentialExpansionPoints.size() - 1);
        int currentSeed = potentialExpansionPoints[seedCustomerIdx];

        int neighborsConsidered = 0;
        for (int neighbor : sol.instance.adj[currentSeed]) {
            if (neighbor == 0) continue; 
            if (selectedCustomersSet.count(neighbor) == 0) { 
                if (getRandomFraction() < P_ADD_NEIGHBOR) {
                    selectedCustomersSet.insert(neighbor);
                    potentialExpansionPoints.push_back(neighbor); 
                    if (selectedCustomersSet.size() == numCustomersToRemove) {
                        break; 
                    }
                }
            }
            neighborsConsidered++;
            if (neighborsConsidered >= MAX_NEIGHBORS_TO_CONSIDER) {
                break; 
            }
        }
        if (selectedCustomersSet.size() == numCustomersToRemove) { 
            break;
        }
    }
    
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float TIME_WINDOW_WEIGHT = 500.0f; 
    const float DEMAND_WEIGHT = 1.0f;        
    const float SERVICE_TIME_WEIGHT = 5.0f;  
    const float DISTANCE_WEIGHT = 0.1f;      
    const float RANDOM_NOISE_WEIGHT = 0.1f;  

    const float EPSILON = 0.001f; 

    for (int customerId : customers) {
        float score = 0.0f;

        float tw_width = instance.endTW[customerId] - instance.startTW[customerId];
        if (tw_width < EPSILON) { 
            score += TIME_WINDOW_WEIGHT * 1000.0f; 
        } else {
            score += TIME_WINDOW_WEIGHT / tw_width;
        }

        score += DEMAND_WEIGHT * instance.demand[customerId];

        score += SERVICE_TIME_WEIGHT * instance.serviceTime[customerId];

        score += DISTANCE_WEIGHT * instance.distanceMatrix[0][customerId];

        score += RANDOM_NOISE_WEIGHT * getRandomFraction(); 

        customerScores.push_back({score, customerId});
    }

    std::sort(customerScores.begin(), customerScores.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; 
              });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }
}