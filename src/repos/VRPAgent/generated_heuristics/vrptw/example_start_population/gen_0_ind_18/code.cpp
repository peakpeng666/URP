#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <unordered_map>
#include <algorithm> // For std::sort
#include "Utils.h"

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    int min_remove = 15;
    int max_remove = 35;
    int num_to_remove = getRandomNumber(min_remove, max_remove);

    std::unordered_set<int> selected_set;
    std::vector<int> selected_vec;

    // Base scores for customers based on inherent properties
    // Higher score means higher likelihood of being chosen
    std::vector<float> base_scores(sol.instance.numCustomers + 1, 0.0f);
    for (int i = 1; i <= sol.instance.numCustomers; ++i) {
        float score = 1.0f; // Base score for stochasticity

        // Prioritize customers with tighter time windows (smaller width)
        if (sol.instance.endTW[i] - sol.instance.startTW[i] > 0.001f) {
            score += (1.0f - sol.instance.TW_Width[i] / (sol.instance.endTW[i] - sol.instance.startTW[i])) * 5.0f;
        } else {
            score += 5.0f; // Very tight or point-in-time window
        }

        // Prioritize customers with higher demand
        score += (float)sol.instance.demand[i] / sol.instance.vehicleCapacity * 3.0f;

        base_scores[i] = score;
    }

    // Pool of candidate customers for selection, and their current effective scores
    std::vector<int> candidate_pool_vec;
    std::unordered_map<int, float> candidate_pool_effective_scores;
    float current_pool_total_score = 0.0f;

    // Parameters for selection
    int max_adj_neighbors_to_add = 10; // How many closest neighbors to consider for adding to pool
    float exploration_prob = 0.15f;    // Probability of picking a completely random customer (for diversity)
    float proximity_bonus_weight = 100.0f; // How strongly proximity to existing selected customers influences score

    // Seed selection: Pick one random customer to start a "cluster"
    int first_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(first_customer);
    selected_vec.push_back(first_customer);

    // Populate initial candidate pool with neighbors of the first selected customer
    for (int neighbor_idx : sol.instance.adj[first_customer]) {
        if (selected_set.find(neighbor_idx) == selected_set.end()) {
            float effective_score = base_scores[neighbor_idx] + proximity_bonus_weight / (sol.instance.distanceMatrix[first_customer][neighbor_idx] + 0.001f);
            if (candidate_pool_effective_scores.find(neighbor_idx) == candidate_pool_effective_scores.end()) {
                candidate_pool_vec.push_back(neighbor_idx);
            }
            candidate_pool_effective_scores[neighbor_idx] = effective_score;
            current_pool_total_score += effective_score;
        }
        if (candidate_pool_vec.size() >= max_adj_neighbors_to_add * 2) { // Limit initial pool size based on neighbors
            break;
        }
    }


    // Main loop for selecting customers
    while (selected_vec.size() < num_to_remove) {
        int next_customer_to_add = -1;

        // Exploration/Diversification: With a small probability, pick a completely random customer
        // This ensures the selected customers do not form a single compact cluster
        if (getRandomFractionFast() < exploration_prob || candidate_pool_vec.empty() || current_pool_total_score < 0.001f) {
            int random_customer = getRandomNumber(1, sol.instance.numCustomers);
            while (selected_set.find(random_customer) != selected_set.end() && selected_set.size() < sol.instance.numCustomers) {
                random_customer = getRandomNumber(1, sol.instance.numCustomers);
            }
            if (selected_set.find(random_customer) == selected_set.end()) {
                next_customer_to_add = random_customer;
            }
        } else { // Exploitation: Pick from the candidate pool based on effective scores
            float r = getRandomFractionFast() * current_pool_total_score;
            float current_sum = 0.0f;
            int chosen_idx_in_pool = -1;

            // Roulette wheel selection from the candidate pool
            for (size_t i = 0; i < candidate_pool_vec.size(); ++i) {
                int c_id = candidate_pool_vec[i];
                if (selected_set.find(c_id) != selected_set.end()) { // Already selected, skip
                    continue;
                }

                float score = candidate_pool_effective_scores[c_id];
                current_sum += score;
                if (current_sum >= r) {
                    next_customer_to_add = c_id;
                    chosen_idx_in_pool = i;
                    break;
                }
            }

            // Remove selected customer from pool (vector and map)
            if (next_customer_to_add != -1 && chosen_idx_in_pool != -1) {
                current_pool_total_score -= candidate_pool_effective_scores[next_customer_to_add];
                candidate_pool_effective_scores.erase(next_customer_to_add);
                if (chosen_idx_in_pool != (int)candidate_pool_vec.size() - 1) {
                    candidate_pool_vec[chosen_idx_in_pool] = candidate_pool_vec.back();
                }
                candidate_pool_vec.pop_back();
            } else {
                // Fallback to random if selection from pool fails unexpectedly
                int random_customer = getRandomNumber(1, sol.instance.numCustomers);
                while (selected_set.find(random_customer) != selected_set.end() && selected_set.size() < sol.instance.numCustomers) {
                    random_customer = getRandomNumber(1, sol.instance.numCustomers);
                }
                if (selected_set.find(random_customer) == selected_set.end()) {
                    next_customer_to_add = random_customer;
                }
            }
        }

        // Add the chosen customer to the selected set and vector
        if (next_customer_to_add != -1) {
            selected_set.insert(next_customer_to_add);
            selected_vec.push_back(next_customer_to_add);

            // Expand candidate pool with neighbors of the newly selected customer
            for (int neighbor_idx : sol.instance.adj[next_customer_to_add]) {
                if (selected_set.find(neighbor_idx) == selected_set.end()) {
                    float new_effective_score = base_scores[neighbor_idx] + proximity_bonus_weight / (sol.instance.distanceMatrix[next_customer_to_add][neighbor_idx] + 0.001f);
                    
                    auto it = candidate_pool_effective_scores.find(neighbor_idx);
                    if (it == candidate_pool_effective_scores.end()) {
                        candidate_pool_vec.push_back(neighbor_idx);
                        candidate_pool_effective_scores[neighbor_idx] = new_effective_score;
                        current_pool_total_score += new_effective_score;
                    } else if (new_effective_score > it->second) {
                        current_pool_total_score += (new_effective_score - it->second);
                        it->second = new_effective_score;
                    }
                }
            }
        }
    }
    return selected_vec;
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a combination of time window tightness, demand, and service time,
    // with a stochastic component to ensure diversity.
    std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
        // Stochastic perturbation applied to TW_Width to randomize ordering for very similar customers
        float tw1_perturbed = instance.TW_Width[c1] + getRandomFractionFast() * 0.01f; // Add small random noise
        float tw2_perturbed = instance.TW_Width[c2] + getRandomFractionFast() * 0.01f;

        // Primary criterion: Time Window Tightness (ascending)
        // Customers with tighter time windows (smaller width) are more constrained and should be placed first
        if (tw1_perturbed != tw2_perturbed) {
            return tw1_perturbed < tw2_perturbed;
        }

        // Secondary criterion: Demand (descending)
        // Customers with higher demand are more constrained by vehicle capacity, prioritize them
        if (instance.demand[c1] != instance.demand[c2]) {
            return instance.demand[c1] > instance.demand[c2];
        }

        // Tertiary criterion: Service Time (descending)
        // Customers requiring longer service times might be harder to fit into tight routes
        if (instance.serviceTime[c1] != instance.serviceTime[c2]) {
             return instance.serviceTime[c1] > instance.serviceTime[c2];
        }

        // Fallback: If all criteria are identical (highly unlikely with perturbation),
        // use customer ID for a stable and deterministic tie-break.
        return c1 < c2;
    });
}