#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility> // For std::pair

// Helper function to get a random element from a vector and remove it
template<typename T>
T pop_random_element(std::vector<T>& vec) {
    if (vec.empty()) {
        throw std::out_of_range("Vector is empty.");
    }
    int idx = getRandomNumber(0, vec.size() - 1);
    T element = vec[idx];
    vec.erase(vec.begin() + idx);
    return element;
}

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    std::vector<int> customerQueue;
    std::unordered_set<int> visitedForSelection;

    int numCustomersToRemove = getRandomNumber(
        std::max(10, static_cast<int>(sol.instance.numCustomers * 0.02)),
        std::min(50, static_cast<int>(sol.instance.numCustomers * 0.08))
    );

    int startCustomer = getRandomNumber(1, sol.instance.numCustomers);
    customerQueue.push_back(startCustomer);
    visitedForSelection.insert(startCustomer);

    while (selectedCustomers.size() < numCustomersToRemove) {
        if (customerQueue.empty()) {
            int newStartCustomer;
            int attempts = 0;
            while (attempts < sol.instance.numCustomers * 2) {
                newStartCustomer = getRandomNumber(1, sol.instance.numCustomers);
                if (visitedForSelection.find(newStartCustomer) == visitedForSelection.end()) {
                    customerQueue.push_back(newStartCustomer);
                    visitedForSelection.insert(newStartCustomer);
                    break;
                }
                attempts++;
            }
            if (customerQueue.empty()) {
                break;
            }
        }

        int customerToSelect = pop_random_element(customerQueue);
        selectedCustomers.insert(customerToSelect);

        if (selectedCustomers.size() >= numCustomersToRemove) {
            break;
        }

        int neighborsToAddLimit = 5;
        int neighborsAddedCount = 0;

        for (int neighbor : sol.instance.adj[customerToSelect]) {
            if (neighborsAddedCount >= neighborsToAddLimit) {
                break;
            }
            if (visitedForSelection.find(neighbor) == visitedForSelection.end()) {
                customerQueue.push_back(neighbor);
                visitedForSelection.insert(neighbor);
                neighborsAddedCount++;
            }
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> customerScores;
    customerScores.reserve(customers.size());

    const float EPSILON = 0.001f;

    for (int customer_id : customers) {
        float distance_to_depot = instance.distanceMatrix[0][customer_id];
        float score = instance.prizes[customer_id] / (distance_to_depot + EPSILON);
        customerScores.push_back({score, customer_id});
    }

    std::sort(customerScores.begin(), customerScores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customerScores[i].second;
    }

    float swapProbability = 0.25f;
    for (size_t i = 0; i + 1 < customers.size(); ++i) {
        if (getRandomFraction() < swapProbability) {
            std::swap(customers[i], customers[i+1]);
        }
    }
}