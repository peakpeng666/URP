#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::sort, std::min, std::max
#include <vector>    // For std::vector
#include "Utils.h"   // For getRandomNumber, getRandomFraction

// Constants for customer selection (Step 1)
const int MIN_CUSTOMERS_TO_REMOVE = 10;
const int MAX_CUSTOMERS_TO_REMOVE = 25;
const float P_NEIGHBOR_WALK = 0.85f; // Probability of trying to pick a neighbor
const int NUM_NEIGHBORS_TO_CHECK = 10; // How many closest neighbors to check from adj list

// Customer selection heuristic
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;

    // Determine the number of customers to remove, ensuring it's within bounds
    int num_to_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    
    // Adjust if trying to remove more customers than available
    if (num_to_remove > sol.instance.numCustomers) {
        num_to_remove = sol.instance.numCustomers;
    }
    // Ensure at least one customer is removed if customers exist
    if (num_to_remove == 0 && sol.instance.numCustomers > 0) {
        num_to_remove = 1;
    } else if (sol.instance.numCustomers == 0) { // Handle case with no customers
        return {};
    }

    // Start by selecting a random customer
    int current_customer = getRandomNumber(1, sol.instance.numCustomers); // Customer IDs are 1-based
    selected_customers_set.insert(current_customer);

    // Iteratively select the remaining customers
    while (selected_customers_set.size() < num_to_remove) {
        int next_customer_to_add = -1;
        bool neighbor_found = false;

        // With high probability, try to pick a neighbor of the 'current_customer' (last added)
        if (getRandomFraction() < P_NEIGHBOR_WALK) {
            // Check a limited number of closest neighbors from the adjacency list
            for (int i = 0; i < std::min((int)sol.instance.adj[current_customer].size(), NUM_NEIGHBORS_TO_CHECK); ++i) {
                int neighbor_id = sol.instance.adj[current_customer][i];
                // Ensure neighbor_id is a valid customer ID (1 to numCustomers) and not already selected
                // (Node ID 0 is the depot, not a customer)
                if (neighbor_id >= 1 && neighbor_id <= sol.instance.numCustomers && 
                    selected_customers_set.find(neighbor_id) == selected_customers_set.end()) {
                    
                    next_customer_to_add = neighbor_id;
                    neighbor_found = true;
                    break; // Found an unselected neighbor, proceed
                }
            }
        }

        // If no suitable neighbor was found (or randomly chose not to do a neighbor walk)
        if (!neighbor_found) {
            // Pick a completely random customer that is not yet selected
            do {
                next_customer_to_add = getRandomNumber(1, sol.instance.numCustomers);
            } while (selected_customers_set.find(next_customer_to_add) != selected_customers_set.end());
        }
        
        selected_customers_set.insert(next_customer_to_add);
        current_customer = next_customer_to_add; // Update 'current_customer' for the next iteration's walk
    }

    // Convert the unordered_set of selected customers to a vector
    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Constants for customer ordering (Step 3)
const float WEIGHT_TW_TIGHTNESS = 0.5f;     // Weight for time window tightness
const float WEIGHT_SERVICE_TIME = 0.3f;     // Weight for service time
const float WEIGHT_DEMAND = 0.2f;           // Weight for demand
const float SORTING_NOISE_MAGNITUDE = 0.05f; // Magnitude of random noise for tie-breaking and stochasticity

// Function selecting the order in which to reinsert the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Calculate max values for normalization within the currently selected subset of customers.
    // This helps in relative scoring within the removed group, making the normalization more sensitive
    // to the specific characteristics of the customers being reinserted.
    float max_tw_width = 0.0f;
    float max_service_time = 0.0f;
    int max_demand = 0;

    for (int customer_id : customers) {
        // Ensure customer_id is valid for indexing instance data (0 is depot)
        if (customer_id >= 1 && customer_id <= instance.numCustomers) {
            max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
            max_service_time = std::max(max_service_time, instance.serviceTime[customer_id]);
            max_demand = std::max(max_demand, instance.demand[customer_id]);
        }
    }

    // Store customer IDs along with their calculated "difficulty" scores
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); // Pre-allocate memory for efficiency

    for (int customer_id : customers) {
        // Skip invalid customer IDs (should not happen if `customers` vector is correctly populated)
        if (customer_id < 1 || customer_id > instance.numCustomers) {
            continue; 
        }

        // Calculate normalized components. Handle potential division by zero if max values are 0.
        // Time window tightness: smaller TW_Width means tighter, thus (1.0f - normalized_width)
        float normalized_tw_tightness = (max_tw_width > 0) ? (1.0f - instance.TW_Width[customer_id] / max_tw_width) : 0.0f;
        // Service time: larger serviceTime means harder
        float normalized_service_time = (max_service_time > 0) ? (instance.serviceTime[customer_id] / max_service_time) : 0.0f;
        // Demand: larger demand means harder
        float normalized_demand = (max_demand > 0) ? (static_cast<float>(instance.demand[customer_id]) / max_demand) : 0.0f;

        // Combine normalized components with weights to form a composite "difficulty" score.
        // A higher score indicates a "harder" customer to place, meaning it should be inserted earlier.
        float score = normalized_tw_tightness * WEIGHT_TW_TIGHTNESS +
                      normalized_service_time * WEIGHT_SERVICE_TIME +
                      normalized_demand * WEIGHT_DEMAND;

        // Add a small amount of random noise for stochasticity and to break ties.
        // This ensures diversity in sorting order over millions of iterations.
        score += getRandomFraction(-SORTING_NOISE_MAGNITUDE, SORTING_NOISE_MAGNITUDE);

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers based on their calculated score in descending order (harder customers first)
    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                  return a.first > b.first; // Sort in descending order of score
              });

    // Update the original `customers` vector with the new sorted order
    for (size_t i = 0; i < scored_customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}