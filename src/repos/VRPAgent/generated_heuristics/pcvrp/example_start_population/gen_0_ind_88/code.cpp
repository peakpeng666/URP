#include <random>
#include <unordered_set>
#include <algorithm> // Required for std::min, std::sort
#include <vector>    // Required for std::vector, std::pair

// Forward declarations for functions from Utils.h as per problem description.
// These functions are assumed to be available from the `Utils.h` header.
int getRandomNumber(int min, int max);
float getRandomFraction(float min = 0.0, float max = 1.0);
float getRandomFractionFast();
std::vector<int> argsort(const std::vector<float>& values);

// Structure definitions (as provided in problem description)
// These would typically be in their respective header files (e.g., Instance.h, Solution.h, Tour.h)
// but are included here to form a complete, self-contained code block as requested.

struct Tour {
    std::vector<int> customers; // Customers in the tour, excluding depot
    int demand = 0; // Total demand of the tour
    float costs = 0;  // Collected prizes minus the travel costs of the tour
};

struct Instance {
    int numNodes; // Total number of nodes including depot
    int numCustomers; // Total number of customers (excluding depot)
    int vehicleCapacity; // Capacity of the vehicle (identical for all vehicles)
    std::vector<int> demand; // Demand of each node (with the depot at index 0 having a demand of 0)
    std::vector<std::vector<float>> distanceMatrix; //Distance matrix between nodes
    std::vector<std::vector<float>> nodePositions; // Node positions in 2D space
    std::vector<std::vector<int>> adj; // Adjacency list for each node, sorted by distance
    std::vector<float> prizes; // The prize of each node
    float total_prizes; //Sum of all prizes
};

struct Solution {
    const Instance& instance; // Reference to the instance to avoid copying
    float totalCosts; // Objective function value: Sum of all collected prizes minus the travel costs of the tours
    std::vector<Tour> tours; // List of tours in the solution
    std::vector<int> customerToTourMap; // Map from each customer to its tour index.
};

// Global static thread_local random generator for thread-safety and consistent seeding across calls.
// This ensures each thread has its own generator, initialized once, providing good randomness.
static thread_local std::mt19937 llm_gen(std::random_device{}());

// Heuristic for selecting a subset of customers to remove from the solution.
// The goal is to select a small number of customers that are somewhat geographically
// connected or proximate to each other, with stochastic elements for diversity.
std::vector<int> select_by_llm_1(const Solution& sol) {
    // Determine the number of customers to remove, introducing stochasticity.
    // For large instances (500+ customers), 15-30 customers is a small fraction.
    std::uniform_int_distribution<> dist_num_to_remove(15, 30);
    int numCustomersToRemove = dist_num_to_remove(llm_gen);

    std::unordered_set<int> selectedCustomersSet; // Stores the IDs of customers selected for removal.
    std::vector<int> candidatesToExplore; // Queue/pool of customers whose neighbors should be explored.

    // Step 1: Select an initial "seed" customer to start the removal cluster.
    // Customer IDs are 1-indexed (1 to numCustomers). Node 0 is the depot.
    std::uniform_int_distribution<> dist_customer_id(1, sol.instance.numCustomers);
    int seed_customer = dist_customer_id(llm_gen);
    
    selectedCustomersSet.insert(seed_customer);
    candidatesToExplore.push_back(seed_customer);

    int current_candidate_idx = 0; // Index to iterate through `candidatesToExplore`.

    // Step 2: Expand from the seed customer to select more nearby customers.
    // Continue until the target number of customers is reached.
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        if (current_candidate_idx >= candidatesToExplore.size()) {
            // All currently identified candidates have been processed, but we still need more customers.
            // To ensure `numCustomersToRemove` is met, select a new random, unselected customer as a seed.
            // This allows for selecting multiple disconnected groups if needed, but the primary
            // mechanism aims for connected clusters.
            int new_seed = -1;
            int safety_counter = 0;
            // Attempt to find a new unselected seed. Limit attempts to prevent infinite loops.
            while (safety_counter < sol.instance.numCustomers * 2 && new_seed == -1) {
                int temp_seed = dist_customer_id(llm_gen);
                if (selectedCustomersSet.find(temp_seed) == selectedCustomersSet.end()) {
                    new_seed = temp_seed;
                }
                safety_counter++;
            }
            
            if (new_seed != -1) {
                selectedCustomersSet.insert(new_seed);
                candidatesToExplore.push_back(new_seed);
                current_candidate_idx = candidatesToExplore.size() - 1; // Start exploring neighbors from this new seed.
            } else {
                // No more unselected customers available to pick as new seeds.
                // This means almost all customers are already selected, so break.
                break; 
            }
        }

        int current_customer_node_idx = candidatesToExplore[current_candidate_idx];
        current_candidate_idx++; // Move to the next candidate for the next iteration.

        // Explore a limited number of closest neighbors of the current customer from the `adj` list.
        // `instance.adj` is 0-indexed where index 0 is depot, and index `i` is customer `i`.
        const auto& neighbors_of_current = sol.instance.adj[current_customer_node_idx];
        
        // Randomly determine how many closest neighbors to consider. This adds diversity.
        // We consider 3 to 10 of the closest neighbors.
        std::uniform_int_distribution<> dist_neighbors_to_consider(3, std::min((int)neighbors_of_current.size(), 10));
        int neighbors_to_consider_count = dist_neighbors_to_consider(llm_gen);

        std::uniform_real_distribution<> dist_prob_add(0.0, 1.0); // For probabilistic selection.
        
        // Iterate through the chosen number of closest neighbors.
        for (int i = 0; i < neighbors_to_consider_count && selectedCustomersSet.size() < numCustomersToRemove; ++i) {
            int neighbor_node_id = neighbors_of_current[i];
            
            // Only consider actual customers (ID > 0), not the depot (ID 0).
            if (neighbor_node_id == 0) continue; 

            // Add the neighbor to the selected set probabilistically (e.g., 80% chance).
            // This introduces stochasticity to the cluster formation.
            if (dist_prob_add(llm_gen) < 0.8) {
                if (selectedCustomersSet.find(neighbor_node_id) == selectedCustomersSet.end()) {
                    selectedCustomersSet.insert(neighbor_node_id);
                    candidatesToExplore.push_back(neighbor_node_id); // Add to candidates for future exploration.
                }
            }
        }
    }

    // Convert the set of selected customers to a vector and return.
    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Heuristic for ordering the removed customers before they are reinserted.
// The greedy reinsertion process inserts customers one by one. This order can significantly
// impact the final solution quality.
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    // Vector to store customers along with their calculated scores for sorting.
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    // Parameter for stochastic scoring: controls the magnitude of random noise relative to the base score.
    // A higher `noise_scale_factor` introduces more randomness, leading to a wider exploration of reinsertion orders.
    // This value is a heuristic and might require tuning based on performance.
    float noise_scale_factor = 0.3f; // Example: potential noise range up to 30% of the base score.
    std::uniform_real_distribution<> dist_noise_multiplier(0.0, 1.0); // Multiplier for the noise magnitude.

    // Calculate a score for each customer to guide the sorting.
    for (int customer_id : customers) {
        // Base score: Prioritize customers with high prize and low distance to the depot.
        // `instance.prizes[customer_id]` and `instance.distanceMatrix[customer_id][0]` are correct,
        // as customer IDs (1-indexed) map directly to their data in 0-indexed arrays/matrices.
        
        float base_score = instance.prizes[customer_id];
        // Add 1.0f to the distance to prevent division by zero or very large scores from tiny distances,
        // and to ensure a positive denominator.
        base_score /= (1.0f + instance.distanceMatrix[customer_id][0]);
        
        // Add a stochastic component to the base score.
        // The noise is proportional to the base score itself, meaning higher-value customers
        // might experience a wider range of perturbation, which makes sense as their placement
        // could have a larger impact. This ensures diversity in the reinsertion order.
        float stochastic_score = base_score + (dist_noise_multiplier(llm_gen) * base_score * noise_scale_factor);
        
        scored_customers.emplace_back(stochastic_score, customer_id);
    }

    // Sort customers in descending order based on their stochastic score.
    // Customers with higher scores (indicating higher prize potential relative to depot distance, plus noise)
    // will be attempted for reinsertion first.
    std::sort(scored_customers.begin(), scored_customers.end(), [](const auto& a, const auto& b) {
        return a.first > b.first; // Sort by score from highest to lowest.
    });

    // Update the original `customers` vector with the newly sorted order.
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}