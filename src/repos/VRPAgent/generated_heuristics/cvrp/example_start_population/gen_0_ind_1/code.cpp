#include "AgentDesigned.h" // Includes Solution, Instance, Tour structs
#include <random>          // For std::mt19937, std::random_device (though not directly used, good practice)
#include <unordered_set>   // For std::unordered_set
#include <vector>          // For std::vector
#include <algorithm>       // For std::sort, std::min, std::max
#include <limits>          // For std::numeric_limits

// Assuming Utils.h functions like getRandomNumber and getRandomFractionFast are available globally
// or implicitly included via AgentDesigned.h.

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> selected_customers_vec;

    // Determine the number of customers to remove stochastically.
    // The range is dynamically chosen between 2% and 4% of total customers,
    // clamped between 10 and 20 to ensure a small, manageable number for large instances.
    int numCustomersToRemove = getRandomNumber(std::max(10, (int)(sol.instance.numCustomers * 0.02f)),
                                               std::min(20, (int)(sol.instance.numCustomers * 0.04f)));
    if (numCustomersToRemove < 1) { // Ensure at least one customer is selected
        numCustomersToRemove = 1;
    } else if (numCustomersToRemove > sol.instance.numCustomers) { // Cannot remove more customers than available
        numCustomersToRemove = sol.instance.numCustomers;
    }

    // Pick an initial random seed customer
    int seed_customer = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers_set.insert(seed_customer);
    selected_customers_vec.push_back(seed_customer);

    // Iteratively select remaining customers, prioritizing proximity to already selected ones
    while (selected_customers_vec.size() < numCustomersToRemove) {
        // Stochastic selection of an anchor customer from the already selected ones
        int anchor_idx = getRandomNumber(0, selected_customers_vec.size() - 1);
        int current_anchor = selected_customers_vec[anchor_idx];

        std::vector<int> potential_next_customers;
        // Iterate through nearest neighbors of the anchor.
        // instance.adj[current_anchor] contains node IDs sorted by distance.
        for (int neighbor_node_id : sol.instance.adj[current_anchor]) {
            // Check if it's a customer (ID between 1 and numCustomers inclusive)
            // and not already selected.
            if (neighbor_node_id >= 1 && neighbor_node_id <= sol.instance.numCustomers &&
                selected_customers_set.find(neighbor_node_id) == selected_customers_set.end()) {
                potential_next_customers.push_back(neighbor_node_id);
                // To maintain speed and add stochasticity, limit the number of closest neighbors
                // considered to find a candidate.
                if (potential_next_customers.size() >= 5) { // Consider up to 5 closest available neighbors
                    break;
                }
            }
        }

        int next_customer_id = -1;
        if (!potential_next_customers.empty()) {
            // Pick one randomly from the available close neighbors
            next_customer_id = potential_next_customers[getRandomNumber(0, potential_next_customers.size() - 1)];
        } else {
            // Fallback: If no suitable unselected neighbors found near the anchor,
            // pick a completely random unselected customer from the entire set of customers.
            int attempts = 0;
            const int max_attempts = 1000; // Cap attempts for robustness against very rare cases
            while (attempts < max_attempts) {
                int rand_cust = getRandomNumber(1, sol.instance.numCustomers);
                if (selected_customers_set.find(rand_cust) == selected_customers_set.end()) {
                    next_customer_id = rand_cust;
                    break;
                }
                attempts++;
            }
            // If still no customer found after max_attempts (highly unlikely given small removal count),
            // it implies all customers might be selected or a logic error. Break to avoid infinite loop.
            if (next_customer_id == -1) {
                break;
            }
        }
        
        selected_customers_set.insert(next_customer_id);
        selected_customers_vec.push_back(next_customer_id);
    }

    return selected_customers_vec;
}


// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Calculate the range of distances from the depot for all customers in the instance.
    // This provides a stable basis for scaling the stochastic noise.
    float min_dist_from_depot = std::numeric_limits<float>::max();
    float max_dist_from_depot = 0.0f;
    for (int i = 1; i <= instance.numCustomers; ++i) {
        float dist = instance.distanceMatrix[0][i];
        if (dist < min_dist_from_depot) min_dist_from_depot = dist;
        if (dist > max_dist_from_depot) max_dist_from_depot = dist;
    }

    // Calculate the effective range. Add a small constant if the range is very narrow
    // to ensure there's always a base for noise calculation and avoid division by zero.
    float distance_range = max_dist_from_depot - min_dist_from_depot;
    if (distance_range < 1.0f) { // Use a small but meaningful lower bound for the range
        distance_range = 100.0f; // Arbitrary reasonable default for noise scaling
    }

    // Store customers along with their calculated noisy scores for sorting.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // NOISE_FACTOR determines the magnitude of random variation relative to the distance_range.
    // A value of 0.05f means noise can shift the score by up to 5% of the total distance range.
    const float NOISE_FACTOR = 0.05f; 

    for (int customer_id : customers) {
        // Base score: distance from the depot. Prioritizes customers farthest from the depot.
        float base_score = instance.distanceMatrix[0][customer_id]; 
        
        // Generate symmetric random noise in the range [-NOISE_FACTOR * distance_range, NOISE_FACTOR * distance_range].
        // getRandomFractionFast() returns a float in [0.0, 1.0].
        // (getRandomFractionFast() * 2.0f - 1.0f) scales it to [-1.0, 1.0].
        float noise = (getRandomFractionFast() * 2.0f - 1.0f) * NOISE_FACTOR * distance_range;
        
        scored_customers.push_back({base_score + noise, customer_id});
    }

    // Sort customers in descending order based on their noisy score.
    // This places customers with higher (farthest/noisy) scores first.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the new sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}