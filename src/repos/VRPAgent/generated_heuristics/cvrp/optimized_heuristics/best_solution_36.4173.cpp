#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <cmath>
#include <limits>
#include <numeric>

#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    static thread_local std::mt19937 gen(std::random_device{}());

    int numCustomersToRemove = getRandomNumber(10, 25);
    if (sol.instance.numCustomers == 0 || numCustomersToRemove <= 0) {
        return {};
    }
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    
    std::vector<bool> isSelected(sol.instance.numCustomers + 1, false);
    std::vector<int> selectedCustomersList; 
    selectedCustomersList.reserve(numCustomersToRemove);

    std::vector<int> customersToExpand; 
    customersToExpand.reserve(numCustomersToRemove * 2);

    if (!sol.tours.empty()) {
        int tourIdx = getRandomNumber(0, sol.tours.size() - 1);
        const Tour& initialTour = sol.tours[tourIdx];

        if (!initialTour.customers.empty()) {
            int numToSelectFromTour = getRandomNumber(1, std::min(numCustomersToRemove, (int)initialTour.customers.size()));
            int startPos = getRandomNumber(0, initialTour.customers.size() - 1);

            for (int i = 0; i < numToSelectFromTour; ++i) {
                int customerId = initialTour.customers[(startPos + i) % initialTour.customers.size()];
                if (customerId > 0 && customerId <= sol.instance.numCustomers && !isSelected[customerId]) {
                    isSelected[customerId] = true;
                    selectedCustomersList.push_back(customerId);
                    customersToExpand.push_back(customerId);
                    if (selectedCustomersList.size() == numCustomersToRemove) return selectedCustomersList;
                }
            }
        }
    }

    if (selectedCustomersList.empty() && sol.instance.numCustomers > 0) {
        int initialSeed = getRandomNumber(1, sol.instance.numCustomers);
        if (!isSelected[initialSeed]) {
            isSelected[initialSeed] = true;
            selectedCustomersList.push_back(initialSeed);
            customersToExpand.push_back(initialSeed);
        }
    }
    
    int head = 0;
    std::vector<int> candidatesBuffer; 
    candidatesBuffer.reserve(30); 

    while (selectedCustomersList.size() < numCustomersToRemove) {
        int currentCustomer = -1;
        
        if (!customersToExpand.empty() && head < customersToExpand.size()) {
            if (getRandomFractionFast() < 0.75) { 
                currentCustomer = customersToExpand[head++];
            } else { 
                currentCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];
            }
        } else if (!selectedCustomersList.empty()) {
            currentCustomer = selectedCustomersList[getRandomNumber(0, selectedCustomersList.size() - 1)];
        } else {
            break; 
        }

        candidatesBuffer.clear();
        
        int maxNeighborsFromAdj = std::min((int)sol.instance.adj[currentCustomer].size(), getRandomNumber(5, 15)); 
        for (int i = 0; i < maxNeighborsFromAdj; ++i) {
            int neighborId = sol.instance.adj[currentCustomer][i];
            if (neighborId > 0 && neighborId <= sol.instance.numCustomers && 
                !isSelected[neighborId]) {
                candidatesBuffer.push_back(neighborId);
            }
        }

        int tourIdx = sol.customerToTourMap[currentCustomer];
        if (tourIdx >= 0 && tourIdx < sol.tours.size()) {
            const Tour& currentTour = sol.tours[tourIdx];
            if (!currentTour.customers.empty()) {
                auto it = std::find(currentTour.customers.begin(), currentTour.customers.end(), currentCustomer);
                if (it != currentTour.customers.end()) {
                    int customerPosInTour = std::distance(currentTour.customers.begin(), it);

                    if (customerPosInTour > 0) {
                        int predCustomer = currentTour.customers[customerPosInTour - 1];
                        if (predCustomer > 0 && predCustomer <= sol.instance.numCustomers && !isSelected[predCustomer]) {
                            candidatesBuffer.push_back(predCustomer);
                        }
                    }
                    if (customerPosInTour < static_cast<int>(currentTour.customers.size()) - 1) {
                        int succCustomer = currentTour.customers[customerPosInTour + 1];
                        if (succCustomer > 0 && succCustomer <= sol.instance.numCustomers && !isSelected[succCustomer]) {
                            candidatesBuffer.push_back(succCustomer);
                        }
                    }
                }
                
                int numToSampleFromTour = getRandomNumber(1, std::min((int)currentTour.customers.size(), 3)); 
                for (int i = 0; i < numToSampleFromTour; ++i) {
                    int randCustomerInTour = currentTour.customers[getRandomNumber(0, currentTour.customers.size() - 1)];
                    if (randCustomerInTour > 0 && randCustomerInTour <= sol.instance.numCustomers && 
                        !isSelected[randCustomerInTour]) {
                        candidatesBuffer.push_back(randCustomerInTour);
                    }
                }
            }
        }
        
        std::shuffle(candidatesBuffer.begin(), candidatesBuffer.end(), gen);

        for (int candidateId : candidatesBuffer) {
            if (getRandomFractionFast() < 0.80) { 
                if (!isSelected[candidateId]) {
                    isSelected[candidateId] = true;
                    selectedCustomersList.push_back(candidateId);
                    customersToExpand.push_back(candidateId);
                    if (selectedCustomersList.size() == numCustomersToRemove) {
                        break;
                    }
                }
            }
        }

        if (selectedCustomersList.size() < numCustomersToRemove && head >= customersToExpand.size()) {
            int newSeed = -1;
            int attempts = 0;
            const int MAX_SEED_ATTEMPTS = 50; 
            do {
                newSeed = getRandomNumber(1, sol.instance.numCustomers);
                attempts++;
            } while (isSelected[newSeed] && attempts < MAX_SEED_ATTEMPTS);
            
            if (!isSelected[newSeed]) {
                isSelected[newSeed] = true;
                selectedCustomersList.push_back(newSeed);
                customersToExpand.push_back(newSeed);
            } else {
                break;
            }
        }
    }

    return selectedCustomersList;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());
    
    const float DISTANCE_EPSILON = 0.001f; 

    int choice = getRandomNumber(0, 99); 
    bool ascending = getRandomNumber(0, 1) == 0;

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    if (choice < 15) { 
        for (int custId : customers) {
            scoredCustomers.push_back({instance.distanceMatrix[0][custId], custId});
        }
    } else if (choice < 30) { 
        for (int custId : customers) {
            scoredCustomers.push_back({(float)instance.demand[custId], custId});
        }
    } else if (choice < 45) { 
        for (int custId : customers) {
            float score = 0.0f;
            if (instance.distanceMatrix[0][custId] > DISTANCE_EPSILON) { 
                score = (float)instance.demand[custId] / instance.distanceMatrix[0][custId];
            } else { 
                score = (float)instance.demand[custId] / DISTANCE_EPSILON;
            }
            scoredCustomers.push_back({score, custId});
        }
    } else if (choice < 55) { 
        int pivotId;
        if (getRandomFractionFast() < 0.50) { 
            pivotId = getRandomNumber(1, instance.numCustomers); 
        } else {
            pivotId = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)]; 
        }
        for (int custId : customers) {
            scoredCustomers.push_back({instance.distanceMatrix[pivotId][custId], custId});
        }
    } else if (choice < 65) { 
        float centroidX = 0.0;
        float centroidY = 0.0;
        if (!customers.empty()) {
            for (int custId : customers) {
                centroidX += instance.nodePositions[custId][0];
                centroidY += instance.nodePositions[custId][1];
            }
            centroidX /= static_cast<float>(customers.size());
            centroidY /= static_cast<float>(customers.size());
        }

        for (int custId : customers) {
            float dist_x = instance.nodePositions[custId][0] - centroidX;
            float dist_y = instance.nodePositions[custId][1] - centroidY;
            scoredCustomers.push_back({std::sqrt(dist_x * dist_x + dist_y * dist_y), custId});
        }
    } else if (choice < 73) { 
        for (size_t i = 0; i < customers.size(); ++i) {
            float currentScore = 0.0f;
            for (size_t j = 0; j < customers.size(); ++j) {
                if (i == j) continue;
                currentScore += instance.distanceMatrix[customers[i]][customers[j]];
            }
            scoredCustomers.push_back({currentScore, customers[i]});
        }
    } else if (choice < 78) { 
        bool sortByX = getRandomNumber(0, 1) == 0;
        for (int custId : customers) {
            float score = sortByX ? instance.nodePositions[custId][0] : instance.nodePositions[custId][1];
            scoredCustomers.push_back({score, custId});
        }
    } else if (choice < 83) { 
        float depotX = instance.nodePositions[0][0];
        float depotY = instance.nodePositions[0][1];
        for (int custId : customers) {
            scoredCustomers.push_back({std::atan2(instance.nodePositions[custId][1] - depotY, instance.nodePositions[custId][0] - depotX), custId});
        }
    } else if (choice < 88) { 
        float maxDemandInSubset = 0.0f;
        float maxDistDepotInSubset = 0.0f;
        int pivotCustomerId = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)]; 
        float maxDistPivotInSubset = 0.0f;

        for (int custId : customers) {
            maxDemandInSubset = std::max(maxDemandInSubset, static_cast<float>(instance.demand[custId]));
            maxDistDepotInSubset = std::max(maxDistDepotInSubset, instance.distanceMatrix[0][custId]);
            maxDistPivotInSubset = std::max(maxDistPivotInSubset, instance.distanceMatrix[pivotCustomerId][custId]);
        }
        
        if (maxDemandInSubset < DISTANCE_EPSILON) maxDemandInSubset = DISTANCE_EPSILON;
        if (maxDistDepotInSubset < DISTANCE_EPSILON) maxDistDepotInSubset = DISTANCE_EPSILON;
        if (maxDistPivotInSubset < DISTANCE_EPSILON) maxDistPivotInSubset = DISTANCE_EPSILON;

        for (int custId : customers) {
            float demandNormalized = static_cast<float>(instance.demand[custId]) / maxDemandInSubset;
            float distFromDepotNormalized = instance.distanceMatrix[0][custId] / maxDistDepotInSubset;
            float distToPivotNormalized = instance.distanceMatrix[pivotCustomerId][custId] / maxDistPivotInSubset;

            float score = 0.40f * demandNormalized + 
                          0.30f * (1.0f - distFromDepotNormalized) + 
                          0.20f * (1.0f - distToPivotNormalized) +
                          0.10f * getRandomFractionFast(); 
            scoredCustomers.push_back({score, custId});
        }
    } else if (choice < 95) { 
        std::vector<int> sortedCustomers;
        sortedCustomers.reserve(customers.size());
        std::vector<bool> isRemainingInSubset(instance.numCustomers + 1, false); 
        for(int cust : customers) isRemainingInSubset[cust] = true;

        int currentCustomer = customers[getRandomNumber(0, static_cast<int>(customers.size()) - 1)]; 
        sortedCustomers.push_back(currentCustomer);
        isRemainingInSubset[currentCustomer] = false;

        while (static_cast<int>(sortedCustomers.size()) < static_cast<int>(customers.size())) {
            float minDistance = std::numeric_limits<float>::max();
            int nextCustomer = -1;
            
            for (int custId : customers) { 
                if (isRemainingInSubset[custId]) {
                    if (instance.distanceMatrix[currentCustomer][custId] < minDistance) {
                        minDistance = instance.distanceMatrix[currentCustomer][custId];
                        nextCustomer = custId;
                    }
                }
            }
            
            if (nextCustomer != -1) {
                sortedCustomers.push_back(nextCustomer);
                isRemainingInSubset[nextCustomer] = false;
                currentCustomer = nextCustomer;
            } else {
                for (int custId : customers) {
                    if (isRemainingInSubset[custId]) {
                        sortedCustomers.push_back(custId);
                        isRemainingInSubset[custId] = false;
                        currentCustomer = custId;
                        break;
                    }
                }
            }
        }
        customers = sortedCustomers;
        if (!ascending) { 
            std::reverse(customers.begin(), customers.end());
        }
        return; 
    } else { 
        std::shuffle(customers.begin(), customers.end(), gen);
        return; 
    }

    if (!scoredCustomers.empty()) {
        if (ascending) {
            std::sort(scoredCustomers.begin(), scoredCustomers.end());
        } else {
            std::sort(scoredCustomers.begin(), scoredCustomers.end(), std::greater<std::pair<float, int>>());
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = scoredCustomers[i].second;
        }
    }

    int numPerturbSwaps = getRandomNumber(0, std::min((int)customers.size() / 2, 3)); 
    for (int i = 0; i < numPerturbSwaps; ++i) {
        if (customers.size() < 2) break;
        int idx1 = getRandomNumber(0, customers.size() - 1);
        int idx2 = getRandomNumber(0, customers.size() - 1);
        std::swap(customers[idx1], customers[idx2]);
    }
}