#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomersToRemove = getRandomNumber(10, 30);

    int pivotCustomerId = getRandomNumber(1, sol.instance.numCustomers);

    std::unordered_set<int> selectedCustomersSet;
    selectedCustomersSet.insert(pivotCustomerId);

    std::vector<int> candidatePool;
    candidatePool.push_back(pivotCustomerId);

    int desiredPoolSize = numCustomersToRemove * 2 + 1;

    for (int neighborId : sol.instance.adj[pivotCustomerId]) {
        if (neighborId > 0 && neighborId <= sol.instance.numCustomers) {
            candidatePool.push_back(neighborId);
            if (candidatePool.size() >= desiredPoolSize) {
                break;
            }
        }
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    std::shuffle(candidatePool.begin(), candidatePool.end(), gen);

    for (int customerId : candidatePool) {
        if (selectedCustomersSet.size() < numCustomersToRemove) {
            selectedCustomersSet.insert(customerId);
        } else {
            break;
        }
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

struct CustomerReinsertionSortCriterion {
    const Instance& instance;
    std::mt19937& gen;

    CustomerReinsertionSortCriterion(const Instance& inst, std::mt19937& g) : instance(inst), gen(g) {}

    bool operator()(int c1_id, int c2_id) const {
        float prize1 = instance.prizes[c1_id];
        float prize2 = instance.prizes[c2_id];

        float dist1 = instance.distanceMatrix[0][c1_id];
        float dist2 = instance.distanceMatrix[0][c2_id];

        float epsilon = 0.001f;
        std::uniform_real_distribution<float> dist_uniform(0.0f, epsilon);
        prize1 += dist_uniform(gen);
        prize2 += dist_uniform(gen);

        if (prize1 != prize2) {
            return prize1 > prize2;
        } else {
            return dist1 < dist2;
        }
    }
};

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    static thread_local std::mt19937 gen(std::random_device{}());

    std::sort(customers.begin(), customers.end(), CustomerReinsertionSortCriterion(instance, gen));
}