#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <queue>
#include <utility>

// Assuming Utils.h provides:
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0);
// float getRandomFractionFast(); // Fast random float [0, 1]

std::vector<int> select_by_llm_1(const Solution& sol) {
    int num_to_remove = getRandomNumber(10, 20);
    std::unordered_set<int> selected_customers;
    std::priority_queue<std::pair<float, int>, std::vector<std::pair<float, int>>, std::greater<std::pair<float, int>>> pq;

    while (selected_customers.size() < num_to_remove) {
        if (pq.empty()) {
            int start_customer = getRandomNumber(1, sol.instance.numCustomers);
            pq.push({0.0f, start_customer});
        }

        std::pair<float, int> current_pair = pq.top();
        pq.pop();
        int current_customer = current_pair.second;

        if (selected_customers.count(current_customer)) {
            continue;
        }

        selected_customers.insert(current_customer);

        if (selected_customers.size() >= num_to_remove) {
            break;
        }

        size_t num_neighbors_to_consider = std::min((size_t)10, sol.instance.adj[current_customer].size());
        for (size_t i = 0; i < num_neighbors_to_consider; ++i) {
            int neighbor = sol.instance.adj[current_customer][i];
            if (!selected_customers.count(neighbor)) {
                float dist = sol.instance.distanceMatrix[current_customer][neighbor];
                float perturbed_dist = dist * (1.0f + getRandomFractionFast() * 0.5f);
                pq.push({perturbed_dist, neighbor});
            }
        }
    }

    return std::vector<int>(selected_customers.begin(), selected_customers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    for (int customer_id : customers) {
        float base_score = 0.0f;

        base_score += instance.prizes[customer_id];

        base_score -= static_cast<float>(instance.demand[customer_id]) * 0.1f;

        if (!instance.adj[customer_id].empty()) {
            float dist_to_closest = instance.distanceMatrix[customer_id][instance.adj[customer_id][0]];
            base_score -= dist_to_closest * 0.5f;
        } else {
            base_score -= 1000.0f;
        }

        float random_noise_magnitude = (instance.total_prizes / static_cast<float>(instance.numCustomers + 1)) * 0.5f; // Add 1 to numCustomers to prevent division by zero if there are no customers
        float final_score = base_score + (getRandomFractionFast() - 0.5f) * random_noise_magnitude;

        scored_customers.push_back({final_score, customer_id});
    }

    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}