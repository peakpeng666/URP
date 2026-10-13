#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::remove
#include <vector>
#include <cmath> // For std::pow
#include <limits> // For std::numeric_limits

// Helper struct to store customer ID and its calculated score
struct CustomerScore {
    int id;
    float score;
};

// Custom comparator for CustomerScore to sort in ascending order based on score
bool compareCustomerScoreAsc(const CustomerScore& a, const CustomerScore& b) {
    return a.score < b.score;
}

// Custom comparator for CustomerScore to sort in descending order based on score
bool compareCustomerScoreDesc(const CustomerScore& a, const CustomerScore& b) {
    return a.score > b.score;
}

// Step 1: Customer selection heuristic
// This heuristic selects a cluster of related customers to remove.
// It starts with a random customer and iteratively adds customers that are
// geographically close and/or belong to the same tour as already selected customers,
// while incorporating stochasticity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    const Instance& instance = sol.instance;

    // Determine the number of customers to remove.
    // The range is dynamically set between 10 and 50 customers,
    // clamped by the total number of customers in the instance.
    int minCustomersToRemove = std::max(1, std::min(instance.numCustomers, 10));
    int maxCustomersToRemove = std::min(instance.numCustomers, 50);
    
    // Ensure minCustomersToRemove doesn't exceed maxCustomersToRemove
    minCustomersToRemove = std::min(minCustomersToRemove, maxCustomersToRemove);

    int numCustomersToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);

    // If there are no customers in the instance, return an empty vector.
    if (instance.numCustomers == 0) {
        return {};
    }

    // Select an initial random anchor customer to start the removal cluster.
    int initial_anchor_customer = getRandomNumber(1, instance.numCustomers);
    selectedCustomersSet.insert(initial_anchor_customer);

    // Create a list of all customers not yet selected.
    std::vector<int> unselectedCustomers;
    unselectedCustomers.reserve(instance.numCustomers);
    for (int i = 1; i <= instance.numCustomers; ++i) {
        if (i != initial_anchor_customer) {
            unselectedCustomers.push_back(i);
        }
    }

    // Iteratively add customers to the removal set until the desired count is reached.
    // This process is inspired by Shaw removal, focusing on similarity/relatedness.
    while (selectedCustomersSet.size() < numCustomersToRemove && !unselectedCustomers.empty()) {
        // Pick a random seed customer from the already selected customers.
        // This ensures new removals are "connected" to the existing cluster.
        std::vector<int> currentSelectedVec(selectedCustomersSet.begin(), selectedCustomersSet.end());
        int seed_customer_idx = getRandomNumber(0, (int)currentSelectedVec.size() - 1);
        int seed_customer_id = currentSelectedVec[seed_customer_idx];

        std::vector<CustomerScore> candidates;
        candidates.reserve(unselectedCustomers.size());

        // Calculate a similarity score for each unselected customer relative to the seed customer.
        // A lower score indicates higher similarity (more desirable for removal).
        for (int customer_id : unselectedCustomers) {
            float dist = instance.distanceMatrix[seed_customer_id][customer_id];
            
            // Base score is distance.
            float score = dist;
            // Apply a bonus (reduce score) if the customer is on the same tour as the seed.
            // This encourages removal of customers from the same route segments.
            if (sol.customerToTourMap[seed_customer_id] == sol.customerToTourMap[customer_id]) {
                score *= 0.5f; 
            }
            // Add a small random perturbation to the score to break ties and introduce
            // additional stochasticity, ensuring diversity over many iterations.
            score += getRandomFractionFast() * 0.001f; 

            candidates.push_back({customer_id, score});
        }

        if (candidates.empty()) {
            break; // No more candidates to select, shouldn't happen under normal circumstances if numCustomersToRemove is small.
        }

        // Sort candidates by their similarity score in ascending order (most similar first).
        std::sort(candidates.begin(), candidates.end(), compareCustomerScoreAsc);

        // Select one customer stochastically from the top similar candidates.
        // This avoids always picking the absolute closest customer, enhancing exploration.
        // It biases selection towards the top 10% of candidates in the sorted list.
        int top_k = std::min((int)candidates.size(), 
                             std::max(1, (int)(candidates.size() / 10))); // Top 10% or at least 1 customer
        
        // Use a power distribution to bias selection towards the beginning of the sorted list (more similar).
        // A higher exponent (e.g., 2.0f) means stronger bias.
        int selected_idx_in_candidates = static_cast<int>(std::pow(getRandomFractionFast(), 2.0f) * top_k);
        
        // Ensure the calculated index is within valid bounds.
        selected_idx_in_candidates = std::min(selected_idx_in_candidates, (int)candidates.size() - 1);
        if (selected_idx_in_candidates < 0) selected_idx_in_candidates = 0; // Fallback if candidates.size() is 1 or calculation yields <0

        int next_customer_to_remove = candidates[selected_idx_in_candidates].id;
        selectedCustomersSet.insert(next_customer_to_remove);

        // Efficiently remove the selected customer from the list of unselected customers.
        auto it = std::remove(unselectedCustomers.begin(), unselectedCustomers.end(), next_customer_to_remove);
        unselectedCustomers.erase(it, unselectedCustomers.end());
    }

    // Convert the set of selected customers to a vector and return it.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}


// Step 3: Ordering of the removed customers for reinsertion
// This heuristic sorts the customers to be reinserted based on a priority score.
// The score considers factors like customer demand and distance from the depot,
// aiming to place "harder" customers first when more reinsertion options are available.
// Stochasticity is incorporated to diversify the reinsertion order.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<CustomerScore> customer_scores;
    customer_scores.reserve(customers.size());

    // Calculate a reinsertion priority score for each customer.
    // Higher score means higher priority (inserted earlier).
    // Factors:
    //   - Customer demand: High demand customers are typically harder to fit into tours.
    //   - Distance from depot: Customers far from the depot might be more critical to place.
    // Stochasticity is added directly to the score to ensure different reinsertion orders
    // even for customers with similar deterministic scores.
    for (int customer_id : customers) {
        float score = 0.0f;
        // Demand component with a higher weight, as capacity is a hard constraint.
        score += static_cast<float>(instance.demand[customer_id]) * 0.6f;
        // Distance from depot component.
        score += instance.distanceMatrix[0][customer_id] * 0.4f;

        // Add a small random perturbation to the score. This is crucial for diversity
        // and to avoid local optima caused by deterministic reinsertion order.
        score += getRandomFractionFast() * 0.01f; 
        
        customer_scores.push_back({customer_id, score});
    }

    // Sort customers in descending order of their calculated priority score.
    // This strategy aims to reinsert the "hardest" customers first.
    std::sort(customer_scores.begin(), customer_scores.end(), compareCustomerScoreDesc);

    // Update the original customers vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].id;
    }
}