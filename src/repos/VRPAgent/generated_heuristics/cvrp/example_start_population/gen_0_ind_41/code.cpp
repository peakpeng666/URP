#include "AgentDesigned.h"
#include <vector>
#include <unordered_set>
#include <algorithm>
#include <limits>
#include <utility>
#include "Utils.h"

std::vector<int> select_by_llm_1(const Solution& sol) {
    int numCustomers = sol.instance.numCustomers;
    int minCustomersToRemove = std::max(2, (int)(numCustomers * 0.01));
    int maxCustomersToRemove = std::min(15, (int)(numCustomers * 0.05));
    if (maxCustomersToRemove < minCustomersToRemove) {
        maxCustomersToRemove = minCustomersToRemove;
    }
    int numToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    std::unordered_set<int> selectedCustomersSet;
    std::vector<bool> isSelected(numCustomers + 1, false);

    int seedCustomer = getRandomNumber(1, numCustomers);
    selectedCustomersSet.insert(seedCustomer);
    isSelected[seedCustomer] = true;

    int maxConsideredCandidates = std::min(50, numCustomers - 1);

    while (selectedCustomersSet.size() < numToRemove) {
        std::vector<std::pair<float, int>> distances_to_selected;
        distances_to_selected.reserve(numCustomers - selectedCustomersSet.size());

        for (int cust_id = 1; cust_id <= numCustomers; ++cust_id) {
            if (!isSelected[cust_id]) {
                float min_dist = std::numeric_limits<float>::max();
                for (int sel_cust_id : selectedCustomersSet) {
                    min_dist = std::min(min_dist, sol.instance.distanceMatrix[cust_id][sel_cust_id]);
                }
                distances_to_selected.push_back({min_dist, cust_id});
            }
        }

        if (distances_to_selected.empty()) {
             break;
        }

        std::sort(distances_to_selected.begin(), distances_to_selected.end());

        int numAvailableCandidates = std::min((int)distances_to_selected.size(), maxConsideredCandidates);
        int selected_idx_in_top_k = getRandomNumber(0, numAvailableCandidates - 1);
        int nextCustomer = distances_to_selected[selected_idx_in_top_k].second;

        selectedCustomersSet.insert(nextCustomer);
        isSelected[nextCustomer] = true;
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> scoredCustomers;
    scoredCustomers.reserve(customers.size());

    float max_dist_to_depot = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        max_dist_to_depot = std::max(max_dist_to_depot, instance.distanceMatrix[i][0]);
    }
    float noise_magnitude = 0.05f * max_dist_to_depot;
    if (noise_magnitude < 0.001f) noise_magnitude = 0.001f;

    for (int customer_id : customers) {
        float score = instance.distanceMatrix[customer_id][0] + getRandomFractionFast() * noise_magnitude;
        scoredCustomers.push_back({score, customer_id});
    }

    std::sort(scoredCustomers.begin(), scoredCustomers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scoredCustomers[i].second;
    }
}