#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include "Utils.h"

template <typename T>
T getRandomElement(const std::vector<T>& vec) {
    return vec[getRandomNumber(0, vec.size() - 1)];
}

bool isValidCustomer(int customerId, const Instance& instance) {
    return customerId > 0 && customerId <= instance.numCustomers;
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    static thread_local std::mt19937 shuffle_gen(std::random_device{}());

    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> selectedCustomersList;

    int numCustomersToRemove = getRandomNumber(15, 40);

    float randomSeedProb = 0.2f;
    float addNeighborProb = 0.7f;

    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int currentCustomerToAdd = -1;

        if (selectedCustomersSet.empty() || getRandomFraction() < randomSeedProb) {
            do {
                currentCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
            } while (selectedCustomersSet.count(currentCustomerToAdd));
        } else {
            int anchorCustomer = getRandomElement(selectedCustomersList);
            
            bool foundNeighbor = false;
            int maxNeighborsToConsider = std::min((int)sol.instance.adj[anchorCustomer].size(), 10);
            
            std::vector<int> candidateNeighbors;
            for (int i = 0; i < maxNeighborsToConsider; ++i) {
                int neighbor = sol.instance.adj[anchorCustomer][i];
                if (isValidCustomer(neighbor, sol.instance) && !selectedCustomersSet.count(neighbor)) {
                    candidateNeighbors.push_back(neighbor);
                }
            }

            if (!candidateNeighbors.empty()) {
                std::shuffle(candidateNeighbors.begin(), candidateNeighbors.end(), shuffle_gen);
                for (int neighbor : candidateNeighbors) {
                    if (getRandomFraction() < addNeighborProb) {
                        currentCustomerToAdd = neighbor;
                        foundNeighbor = true;
                        break;
                    }
                }
            }

            if (!foundNeighbor) {
                do {
                    currentCustomerToAdd = getRandomNumber(1, sol.instance.numCustomers);
                } while (selectedCustomersSet.count(currentCustomerToAdd));
            }
        }
        
        if (currentCustomerToAdd != -1) {
            selectedCustomersSet.insert(currentCustomerToAdd);
            selectedCustomersList.push_back(currentCustomerToAdd);
        }
    }

    return selectedCustomersList;
}

struct CustomerSortInfo {
    int customerId;
    float score;
};

bool compareCustomerSortInfo(const CustomerSortInfo& a, const CustomerSortInfo& b) {
    return a.score < b.score;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<CustomerSortInfo> sortInfos;
    sortInfos.reserve(customers.size());

    float min_tw_width = instance.TW_Width[customers[0]];
    float max_tw_width = instance.TW_Width[customers[0]];
    for (int cust_id : customers) {
        if (instance.TW_Width[cust_id] < min_tw_width) min_tw_width = instance.TW_Width[cust_id];
        if (instance.TW_Width[cust_id] > max_tw_width) max_tw_width = instance.TW_Width[cust_id];
    }
    float tw_width_range = max_tw_width - min_tw_width;
    if (tw_width_range == 0.0f) tw_width_range = 1.0f;

    float stochastic_noise_magnitude = tw_width_range * 0.08f;

    for (int customerId : customers) {
        float score = instance.TW_Width[customerId];
        score += getRandomFraction() * stochastic_noise_magnitude;
        sortInfos.push_back({customerId, score});
    }

    std::sort(sortInfos.begin(), sortInfos.end(), compareCustomerSortInfo);

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sortInfos[i].customerId;
    }
}