#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm> // For std::shuffle, std::sort
#include <vector>
#include <numeric>   // For std::iota
#include "Utils.h"

// For thread-local random number generation
static thread_local std::mt19937 gen(std::random_device{}());

// Helper function to get a random customer index (1 to numCustomers)
int getRandomCustomerIndex(const Instance& instance) {
    return getRandomNumber(1, instance.numCustomers);
}

// Helper to pick a seed customer (can be visited or unvisited, with a bias)
int pickSeedCustomer(const Solution& sol) {
    int start_node = -1;
    // Attempt to pick a customer for a few tries to ensure we get a valid one quickly
    // For 500+ customers, a few tries are almost guaranteed to succeed
    for (int i = 0; i < 50; ++i) { 
        int candidate_node = getRandomCustomerIndex(sol.instance);
        // Introduce stochasticity: 20% chance to prefer unvisited customers
        if (getRandomFractionFast() < 0.2f) { 
            if (sol.customerToTourMap[candidate_node] == -1) { // Is unvisited
                start_node = candidate_node;
                break;
            }
        } else { // 80% chance to prefer visited customers
            if (sol.customerToTourMap[candidate_node] != -1) { // Is visited
                start_node = candidate_node;
                break;
            }
        }
    }
    // Fallback: if after many tries no specific type was found (very unlikely), just pick any random customer
    if (start_node == -1) {
        start_node = getRandomCustomerIndex(sol.instance);
    }
    return start_node;
}

// Step 1: Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selected_customers_set;
    std::vector<int> candidate_expansion_nodes; // Nodes whose neighbors can be picked next

    // Determine the number of customers to remove (stochastic)
    // Small number: 10-30 customers, adapting to instance size but not exceeding 5%
    int num_to_remove = getRandomNumber(10, std::min(30, (int)(sol.instance.numCustomers * 0.05)));
    if (num_to_remove < 1) num_to_remove = 1; // Ensure at least one customer is removed

    // 1. Pick an initial seed customer
    int initial_seed = pickSeedCustomer(sol);
    selected_customers_set.insert(initial_seed);
    candidate_expansion_nodes.push_back(initial_seed);

    // 2. Expand the cluster until the desired number of customers is reached
    while (selected_customers_set.size() < num_to_remove) {
        // If candidate_expansion_nodes is empty, it means all reachable neighbors from existing
        // selected nodes have been explored or added. Pick a new seed to continue growing.
        if (candidate_expansion_nodes.empty()) {
            int new_seed = pickSeedCustomer(sol);
            if (selected_customers_set.find(new_seed) == selected_customers_set.end()) { // Only add if not already selected
                selected_customers_set.insert(new_seed);
                candidate_expansion_nodes.push_back(new_seed);
            }
            if (selected_customers_set.size() == num_to_remove) break; // Break if target size reached
            if (candidate_expansion_nodes.empty()) continue; // If new seed was already selected, try again
        }

        // Stochastic selection of a node from the candidate_expansion_nodes to expand from
        int expansion_idx = getRandomNumber(0, candidate_expansion_nodes.size() - 1);
        int current_node = candidate_expansion_nodes[expansion_idx];

        bool found_new_neighbor = false;
        // Get neighbors of current_node, which are pre-sorted by distance in instance.adj
        std::vector<int> current_node_neighbors = sol.instance.adj[current_node];

        // Shuffle neighbors to introduce stochasticity in selection order from closest neighbors
        std::shuffle(current_node_neighbors.begin(), current_node_neighbors.end(), gen);

        for (int neighbor_node : current_node_neighbors) {
            // Only consider neighbors that are actual customers (index > 0)
            if (neighbor_node == 0) continue; 
            
            if (selected_customers_set.find(neighbor_node) == selected_customers_set.end()) { // If not already selected
                selected_customers_set.insert(neighbor_node);
                candidate_expansion_nodes.push_back(neighbor_node); // Add the new node to expansion candidates
                found_new_neighbor = true;
                break; // Add only one new neighbor per iteration to control growth
            }
        }

        if (!found_new_neighbor) {
            // If current_node has no unselected neighbors, remove it from candidates to avoid re-checking
            candidate_expansion_nodes.erase(candidate_expansion_nodes.begin() + expansion_idx);
        }
    }

    return std::vector<int>(selected_customers_set.begin(), selected_customers_set.end());
}


// Step 3: Ordering of the removed customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Structure to hold customer ID and its calculated reinsertion score
    struct CustomerScore {
        int customer_id;
        float score;
    };

    std::vector<CustomerScore> scored_customers;
    scored_customers.reserve(customers.size());

    // Calculate scores for each customer based on multiple criteria
    // Objective: prioritize customers that are "more important" or "easier to place profitably"
    // Criteria:
    // 1. Prize-to-Demand ratio: High value implies potentially profitable customers
    // 2. Connectivity/Degree: Customers with more neighbors might be easier to connect to existing tours
    for (int customer_id : customers) {
        float prize_per_demand = instance.prizes[customer_id];
        // Avoid division by zero if demand can be 0 for customers (usually not for PCVRP customers)
        if (instance.demand[customer_id] > 0) {
            prize_per_demand /= instance.demand[customer_id];
        }
        
        // Use connectivity (number of neighbors)
        float connectivity_score = (float)instance.adj[customer_id].size();

        // Combine scores with fixed weights. These weights can be tuned.
        // Add a small random perturbation for diversity (stochasticity)
        float combined_score = (0.6f * prize_per_demand) + (0.4f * connectivity_score);
        combined_score += getRandomFractionFast() * 0.01f; // Small noise for tie-breaking and diversity

        scored_customers.push_back({customer_id, combined_score});
    }

    // Sort customers in descending order of their calculated scores
    std::sort(scored_customers.begin(), scored_customers.end(), 
              [](const CustomerScore& a, const CustomerScore& b) {
                  return a.score > b.score; // Sort in descending order
              });

    // Update the original 'customers' vector with the sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].customer_id;
    }
}