#include "AgentDesigned.h" // This includes required headers like Solution.h, Instance.h, Tour.h
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::shuffle, std::sort, std::min
#include <cfloat>    // For FLT_MAX
#include <utility>   // For std::pair

// Assuming Utils.h is properly included and provides these functions:
// int getRandomNumber(int min, int max);
// float getRandomFraction(float min = 0.0, float max = 1.0); // Assuming this returns a float in [0.0, 1.0]

// Helper function to select an item probabilistically based on scores (roulette wheel selection)
// Takes a vector of (score, customer_id) pairs and returns a selected customer_id.
// Higher scores correspond to higher probability of selection.
int select_customer_probabilistically(const std::vector<std::pair<float, int>>& candidates) {
    if (candidates.empty()) {
        return -1; // No customers to select
    }

    float total_score = 0.0f;
    for (const auto& p : candidates) {
        total_score += p.first;
    }

    // If total_score is zero or negative (should not happen with calculated scores),
    // fall back to uniform random selection among candidates.
    if (total_score <= 0.0f) {
        return candidates[getRandomNumber(0, candidates.size() - 1)].second;
    }

    float random_target = getRandomFraction() * total_score;

    float cumulative_score = 0.0f;
    for (const auto& p : candidates) {
        cumulative_score += p.first;
        if (cumulative_score >= random_target) {
            return p.second;
        }
    }

    // Fallback in case of floating point inaccuracies; should ideally not be reached.
    // If random_target is slightly larger than max cumulative_score due to precision, pick the last one.
    return candidates.back().second;
}

// Step 1: Customer selection heuristic for LNS (select_by_llm_1)
// This heuristic aims to select a set of customers that are somewhat geographically clustered
// by starting with a random seed and then iteratively picking customers close to already selected ones,
// while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_set;    // For efficient lookup of selected customers
    std::vector<int> result_customers;        // Stores the final list of selected customers

    // Determine the number of customers to remove (between 10 and 20, inclusive)
    int num_customers_to_remove = getRandomNumber(10, 20);

    // Ensure the number of customers to remove does not exceed the total number of customers
    if (num_customers_to_remove > sol.instance.numCustomers) {
        num_customers_to_remove = sol.instance.numCustomers;
    }
    if (num_customers_to_remove == 0) {
        return {}; // Return empty vector if no customers are to be removed
    }

    // 1. Select the first customer randomly. This serves as the initial "seed" for the cluster.
    int initial_customer_id = getRandomNumber(1, sol.instance.numCustomers);
    selected_set.insert(initial_customer_id);
    result_customers.push_back(initial_customer_id);

    // 2. Iteratively select the remaining customers based on their proximity to the already selected ones.
    // This creates a "growth" effect, encouraging selected customers to be near others.
    while (result_customers.size() < num_customers_to_remove) {
        std::vector<std::pair<float, int>> unselected_candidates_with_scores;

        // Iterate through all possible customers to find suitable candidates
        for (int customer_id = 1; customer_id <= sol.instance.numCustomers; ++customer_id) {
            if (selected_set.count(customer_id)) {
                continue; // Skip if this customer has already been selected
            }

            float min_dist_to_selected = FLT_MAX; // Initialize with a very large float value

            // Calculate the minimum distance from the current candidate customer to any already selected customer
            for (int s_id : result_customers) {
                // distanceMatrix[node1][node2] holds the travel time/distance between two nodes
                min_dist_to_selected = std::min(min_dist_to_selected, sol.instance.distanceMatrix[customer_id][s_id]);
            }
            
            // Assign a score inversely proportional to the minimum distance.
            // Customers closer to the already selected set will receive a higher score.
            // A small constant (0.01f) is added to the denominator to prevent division by zero
            // if distance is exactly 0 and to smooth the score for very small distances.
            float score = 1.0f / (min_dist_to_selected + 0.01f); 
            unselected_candidates_with_scores.push_back({score, customer_id});
        }
        
        // If no more unselected customers are available (e.g., all customers selected), break the loop.
        if (unselected_candidates_with_scores.empty()) {
            break; 
        }

        // Use probabilistic selection (roulette wheel) to choose the next customer to add.
        // This introduces the required stochastic behavior.
        int next_customer_to_add = select_customer_probabilistically(unselected_candidates_with_scores);
        selected_set.insert(next_customer_to_add);
        result_customers.push_back(next_customer_to_add);
    }

    return result_customers;
}

// Step 3: Ordering heuristic for removed customers (sort_by_llm_1)
// This heuristic determines the order in which the removed customers will be reinserted.
// It prioritizes customers that are typically "harder" to place (e.g., tight time windows, high demand)
// and adds stochastic noise to ensure diversity in reinsertion order across iterations.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return; // Nothing to sort if the list is empty
    }

    std::vector<std::pair<float, int>> customer_priorities;
    
    // Define the amplitude of the random noise added to scores.
    // This value influences how much the random element affects the final sorting order.
    // It may need tuning based on the typical range of calculated base scores.
    const float NOISE_AMPLITUDE = 20.0f;

    for (int customer_id : customers) {
        // Calculate a base priority score for each customer.
        // Higher scores indicate a higher priority for reinsertion (e.g., more constrained customers).
        
        // Component 1: Time Window Tightness
        // Customers with smaller time window widths (TW_Width) are considered more constrained.
        // The score is inversely proportional to TW_Width. Multiplying by 100.0f scales this component.
        // Adding 1.0f to the denominator prevents division by zero if TW_Width can be 0.
        float tw_priority = 100.0f / (instance.TW_Width[customer_id] + 1.0f); 

        // Component 2: Demand
        // Customers with higher demand are generally harder to fit into vehicle capacity.
        // Their demand value directly contributes to their priority.
        float demand_priority = static_cast<float>(instance.demand[customer_id]); 

        // Component 3: Service Time
        // Customers requiring longer service times tie up a vehicle for a longer duration,
        // which can make them harder to insert. Their service time contributes to priority.
        float service_time_priority = instance.serviceTime[customer_id]; 
        
        // Combine the components into a single base score.
        // An additive combination is used to ensure all factors contribute.
        float base_score = tw_priority + demand_priority + service_time_priority;

        // Add stochastic noise to the base score.
        // (getRandomFraction() - 0.5f) generates a random number in the range [-0.5, 0.5],
        // making the noise centered around zero. NOISE_AMPLITUDE scales this noise.
        // This introduces the necessary stochasticity for diversity across LNS iterations.
        float noisy_score = base_score + (getRandomFraction() - 0.5f) * NOISE_AMPLITUDE;
        
        customer_priorities.push_back({noisy_score, customer_id});
    }

    // Sort the customers based on their noisy priority scores in descending order.
    // Customers with higher (noisy) priority scores will appear earlier in the list.
    std::sort(customer_priorities.begin(), customer_priorities.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; // Sort from highest score to lowest
              });

    // Update the input 'customers' vector with the new sorted order of customer IDs.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_priorities[i].second;
    }
}