#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <utility>
#include <limits> // For std::numeric_limits
#include "Utils.h"

// Customer selection heuristic for LNS
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomers;
    // Determine the number of customers to remove.
    // For 500+ customers, a small fixed range ensures consistent behavior.
    int numCustomersToRemove = getRandomNumber(10, 50);

    // Adjust if the instance has fewer customers than the target removal count
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    
    // Probabilities for different selection strategies
    const float PROB_SAME_TOUR = 0.6;      // High probability to select from the same tour
    const float PROB_NEARBY_CUSTOMER = 0.3; // Medium probability to select a geographically nearby customer
                                           // Remaining probability (0.1) for completely random selection

    while (selectedCustomers.size() < numCustomersToRemove) {
        int currentCandidate = -1;

        if (selectedCustomers.empty()) {
            // Always start with a completely random customer if the set is empty
            currentCandidate = getRandomNumber(1, sol.instance.numCustomers);
        } else {
            // Select a base customer from those already chosen
            // Convert set to vector for random access. For small sets, this overhead is minimal.
            std::vector<int> current_selected_vec(selectedCustomers.begin(), selectedCustomers.end());
            int base_customer = current_selected_vec[getRandomNumber(0, current_selected_vec.size() - 1)];

            float rand_choice = getRandomFractionFast();

            if (rand_choice < PROB_SAME_TOUR) {
                // Try to select a customer from the same tour as the base customer
                const Tour& base_tour = sol.tours[sol.customerToTourMap[base_customer]];
                if (base_tour.customers.size() > 1) { // Ensure there's more than just the base customer in the tour
                    currentCandidate = base_tour.customers[getRandomNumber(0, base_tour.customers.size() - 1)];
                }
            } else if (rand_choice < PROB_SAME_TOUR + PROB_NEARBY_CUSTOMER) {
                // Try to select a geographically nearby customer using the adjacency list
                // Ensure base_customer is a valid index for instance.adj (customers are 1 to numCustomers)
                if (base_customer >= 1 && base_customer <= sol.instance.numCustomers && !sol.instance.adj[base_customer].empty()) {
                    int potential_neighbor_node = sol.instance.adj[base_customer][getRandomNumber(0, sol.instance.adj[base_customer].size() - 1)];
                    // Ensure the neighbor is actually a customer (not the depot and within customer range)
                    if (potential_neighbor_node >= 1 && potential_neighbor_node <= sol.instance.numCustomers) {
                        currentCandidate = potential_neighbor_node;
                    }
                }
            }
            
            // Fallback to a completely random customer if no suitable candidate was found
            // or if the chosen candidate was already selected or invalid.
            if (currentCandidate == -1 || selectedCustomers.count(currentCandidate) > 0) {
                 currentCandidate = getRandomNumber(1, sol.instance.numCustomers);
            }
        }
        selectedCustomers.insert(currentCandidate);
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

// Function selecting the order in which to reinsert the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    // Sort customers based on a "difficulty" heuristic.
    // Tighter time windows and higher demand typically make a customer "harder" to reinsert.
    // Adding a stochastic element ensures diversity across iterations.

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    const float TW_WEIGHT = 1000.0;     // Weight for time window tightness (higher values make it more dominant)
    const float DEMAND_WEIGHT = 1.0;    // Weight for demand
    const float STOCHASTIC_WEIGHT = 0.5; // Weight for stochastic perturbation
    const float EPSILON = 0.001;        // Small value to prevent division by zero if TW_Width can be 0.0

    for (int customer_id : customers) {
        float score = 0.0;
        // Customer IDs are expected to be in the range [1, instance.numCustomers].
        if (customer_id >= 1 && customer_id <= instance.numCustomers) {
             // Calculate a "hardness" score. Higher score means harder to place.
             // 1. Time window tightness: Smaller width means tighter, so 1 / (width + epsilon) gives a higher value.
             score += TW_WEIGHT * (1.0 / (instance.TW_Width[customer_id] + EPSILON));
             // 2. Demand: Higher demand makes it harder.
             score += DEMAND_WEIGHT * instance.demand[customer_id];
             // 3. Stochastic noise: Small random value to break ties and add diversity.
             score += STOCHASTIC_WEIGHT * getRandomFractionFast();
        } else {
             // Assign a very low score for invalid customer IDs to sort them last.
             score = -std::numeric_limits<float>::max();
        }
        scored_customers.push_back({score, customer_id});
    }

    // Sort in descending order of score (hardest customers first)
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first;
    });

    // Update the original customers vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}