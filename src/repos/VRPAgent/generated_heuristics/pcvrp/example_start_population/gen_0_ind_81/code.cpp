#include "AgentDesigned.h" // Assuming this pulls in Solution.h, Tour.h, Instance.h
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm> // For std::min, std::sort
#include <utility>   // For std::pair

// Customer selection
std::vector<int> select_by_llm_1(const Solution& sol) {
    std::unordered_set<int> selectedCustomersSet;
    std::vector<int> currentSelectedCustomersList; // Stores customers already selected, to pick neighbors from

    int numCustomers = sol.instance.numCustomers;
    int numCustomersToRemove = getRandomNumber(15, 35); // Number of customers to remove, 15 to 35

    // Pre-collect visited and unvisited customers for efficient random selection
    std::vector<int> visited_customers;
    std::vector<int> unvisited_customers;
    for (int i = 1; i <= numCustomers; ++i) { // Customer IDs are 1-indexed
        if (sol.customerToTourMap[i] != -1) {
            visited_customers.push_back(i);
        } else {
            unvisited_customers.push_back(i);
        }
    }

    // Step 1: Select an initial seed customer
    int seed_customer = -1;
    // Prioritize picking a visited customer to perturb existing routes (70% chance)
    if (getRandomFractionFast() < 0.7 && !visited_customers.empty()) {
        seed_customer = visited_customers[getRandomNumber(0, visited_customers.size() - 1)];
    } else if (!unvisited_customers.empty()) {
        // Otherwise, try picking an unvisited customer to encourage new solutions
        seed_customer = unvisited_customers[getRandomNumber(0, unvisited_customers.size() - 1)];
    } else if (!visited_customers.empty()) { // Fallback if no unvisited ones but visited are available
        seed_customer = visited_customers[getRandomNumber(0, visited_customers.size() - 1)];
    } else { // Should not happen with 500+ customers, but for robustness
        seed_customer = getRandomNumber(1, numCustomers);
    }

    if (seed_customer != -1) {
        selectedCustomersSet.insert(seed_customer);
        currentSelectedCustomersList.push_back(seed_customer);
    }

    // Step 2: Grow the selection by iteratively adding nearby customers
    int attempts_without_new_customer = 0;
    // To prevent infinite loops if no new distinct neighbors are found
    const int max_attempts_without_new = 5; 

    while (selectedCustomersSet.size() < numCustomersToRemove && !currentSelectedCustomersList.empty() && attempts_without_new_customer < max_attempts_without_new) {
        // Randomly pick a customer from the already selected list to find new neighbors
        int source_customer_idx = getRandomNumber(0, currentSelectedCustomersList.size() - 1);
        int source_customer = currentSelectedCustomersList[source_customer_idx];

        const std::vector<int>& neighbors = sol.instance.adj[source_customer];
        bool new_customer_added_in_loop = false;

        // Determine how many closest neighbors to consider, with some randomness
        // This ensures diversity in which part of the neighborhood is explored
        int neighbors_to_consider = std::min((int)neighbors.size(), getRandomNumber(5, 15));

        for (int i = 0; i < neighbors_to_consider; ++i) {
            int candidate_neighbor = neighbors[i];
            if (candidate_neighbor == 0) continue; // Skip depot (node 0)
            
            // Only add if not already selected
            if (selectedCustomersSet.find(candidate_neighbor) == selectedCustomersSet.end()) {
                // Bias selection towards closer neighbors (smaller 'i' means closer in adj list)
                // Probability decreases linearly with distance rank
                float selection_prob = (float)(neighbors_to_consider - i) / neighbors_to_consider;
                if (getRandomFractionFast() < selection_prob) {
                    selectedCustomersSet.insert(candidate_neighbor);
                    currentSelectedCustomersList.push_back(candidate_neighbor);
                    new_customer_added_in_loop = true;
                    break; // Found one, move to select next customer
                }
            }
        }

        if (!new_customer_added_in_loop) {
            attempts_without_new_customer++;
        } else {
            attempts_without_new_customer = 0; // Reset counter if a new customer was added
        }
    }

    // Step 3: If target number of customers not reached, fill with truly random customers
    // This happens if the "growing" strategy stalled or could not find enough distinct neighbors
    while (selectedCustomersSet.size() < numCustomersToRemove) {
        int random_customer = getRandomNumber(1, numCustomers); // Ensure customer ID is valid (1 to numCustomers)
        selectedCustomersSet.insert(random_customer);
    }

    return std::vector<int>(selectedCustomersSet.begin(), selectedCustomersSet.end());
}

// Function selecting the order in which to remove the customers
void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size()); // Pre-allocate memory for efficiency

    for (int customer_id : customers) {
        float score = 0.0;
        float prize = instance.prizes[customer_id];
        float demand = instance.demand[customer_id];
        float dist_to_depot = instance.distanceMatrix[0][customer_id]; // Distance from depot (node 0)

        // Base score: Prioritize customers with high prize (more desirable to reinsert)
        score = prize;

        // Adjust score based on demand: Penalize high demand (harder to insert)
        // Reward low/zero demand (easier to insert)
        if (demand > 0) {
            score /= demand;
        } else {
            score *= 2.0; // Bonus for customers with zero demand
        }

        // Adjust score based on distance to depot: Slightly penalize those far from the depot
        // Use a small coefficient to ensure prize/demand impact is dominant
        score -= dist_to_depot * 0.05;

        // Add stochasticity: A small random perturbation to the score
        // This adds diversity to the ordering over many iterations
        // The perturbation is proportional to the score (0.05*score) plus a fixed small value (0.1)
        // to ensure some perturbation even for very low base scores.
        score += getRandomFractionFast() * (score * 0.05 + 0.1);

        scored_customers.push_back({score, customer_id});
    }

    // Sort customers in descending order of their calculated score (higher score first)
    std::sort(scored_customers.begin(), scored_customers.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return a.first > b.first;
    });

    // Update the original 'customers' vector with the new sorted order
    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}