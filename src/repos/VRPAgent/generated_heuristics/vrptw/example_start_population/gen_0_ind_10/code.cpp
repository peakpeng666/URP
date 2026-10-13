#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort
#include <vector> // For std::vector
#include <utility> // For std::pair
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    int numCustomersToRemove = getRandomNumber(10, 30); // Number of customers to remove

    if (sol.tours.empty() || sol.instance.numCustomers == 0) {
        return {};
    }

    // Attempt to seed the selection with a customer from a random tour
    int initialCustomer = -1;
    if (sol.tours.size() > 0) {
        int randomTourIdx = getRandomNumber(0, sol.tours.size() - 1);
        const Tour& selectedTour = sol.tours[randomTourIdx];
        if (!selectedTour.customers.empty()) {
            int initialCustomerIdxInTour = getRandomNumber(0, selectedTour.customers.size() - 1);
            initialCustomer = selectedTour.customers[initialCustomerIdxInTour];
        }
    }
    
    // Fallback if no initial customer could be picked from tours (e.g., all tours empty)
    if (initialCustomer == -1 && sol.instance.numCustomers > 0) {
        initialCustomer = getRandomNumber(1, sol.instance.numCustomers);
    }

    if (initialCustomer != -1) {
        selectedCustomers.insert(initialCustomer);
    }

    // Expand the selection based on proximity within tours or randomly
    while (selectedCustomers.size() < numCustomersToRemove) {
        if (!selectedCustomers.empty() && getRandomFraction() < 0.8) { // High probability to expand from existing
            int customerToExpandFrom = *std::next(selectedCustomers.begin(), getRandomNumber(0, selectedCustomers.size() - 1));
            
            // Check if customerToExpandFrom has a valid tour mapping
            if (customerToExpandFrom >= 0 && customerToExpandFrom < sol.customerToTourMap.size()) {
                int tourIdx = sol.customerToTourMap[customerToExpandFrom];
                if (tourIdx >= 0 && tourIdx < sol.tours.size()) {
                    const Tour& currentTour = sol.tours[tourIdx];
                    
                    int idxInTour = -1;
                    for (size_t i = 0; i < currentTour.customers.size(); ++i) {
                        if (currentTour.customers[i] == customerToExpandFrom) {
                            idxInTour = i;
                            break;
                        }
                    }

                    if (idxInTour != -1) {
                        int nextCustomerToAdd = -1;
                        // Try successor
                        if (idxInTour + 1 < currentTour.customers.size()) {
                            if (selectedCustomers.find(currentTour.customers[idxInTour + 1]) == selectedCustomers.end()) {
                                nextCustomerToAdd = currentTour.customers[idxInTour + 1];
                            }
                        }
                        // If successor is already selected or not available, try predecessor
                        if (nextCustomerToAdd == -1 && idxInTour - 1 >= 0) {
                            if (selectedCustomers.find(currentTour.customers[idxInTour - 1]) == selectedCustomers.end()) {
                                nextCustomerToAdd = currentTour.customers[idxInTour - 1];
                            }
                        }
                        
                        if (nextCustomerToAdd != -1) {
                            selectedCustomers.insert(nextCustomerToAdd);
                            continue; // Successfully added, continue to next iteration
                        }
                    }
                }
            }
        }
        
        // Fallback: Add a completely random customer if expansion failed or by chance
        int randomCustomer = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomers.find(randomCustomer) == selectedCustomers.end()) {
            selectedCustomers.insert(randomCustomer);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> customerTWs;
    customerTWs.reserve(customers.size());

    for (int customer_id : customers) {
        if (customer_id >= 0 && customer_id < instance.TW_Width.size()) {
            customerTWs.push_back({instance.TW_Width[customer_id], customer_id});
        }
    }

    std::sort(customerTWs.begin(), customerTWs.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customerTWs.size(); ++i) {
        customers[i] = customerTWs[i].second;
    }
}