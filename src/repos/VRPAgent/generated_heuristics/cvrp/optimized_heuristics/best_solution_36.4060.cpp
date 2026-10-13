#include "AgentDesigned.h"
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <utility>
#include <limits>

#include "Utils.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846F
#endif

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_NUM_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_NUM_CUSTOMERS_TO_REMOVE = 28;
    const int MAX_STRATEGY_ATTEMPTS = 50;
    const int MAX_SAFEGUARD_ATTEMPTS = 100;

    const float PROB_INITIAL_SEGMENT_REMOVAL = 0.20f;
    const int MIN_SEGMENT_LENGTH_INITIAL_SELECTION = 2;
    const int MAX_SEGMENT_LENGTH_INITIAL_SELECTION = 5;

    const float PROB_NEIGHBOR_EXPANSION = 0.60f;
    const float PROB_TOUR_SEGMENT_EXPANSION = 0.25f;
    const float PROB_TOUR_ADJACENT_EXPANSION = 0.15f;

    const int MIN_SEGMENT_LENGTH_EXPANSION = 2;
    const int MAX_SEGMENT_LENGTH_EXPANSION = 5;
    const int MIN_NEIGHBORS_TO_CONSIDER = 5;
    const int MAX_NEIGHBORS_TO_CONSIDER = 15;
    const float PROB_ADD_SECOND_TOUR_NEIGHBOR_ADJACENT = 0.40f;

    std::vector<char> is_selected(sol.instance.numCustomers + 1, 0);
    std::vector<int> selectedCustomersVector;
    selectedCustomersVector.reserve(MAX_NUM_CUSTOMERS_TO_REMOVE);

    int numCustomersToRemove = getRandomNumber(MIN_NUM_CUSTOMERS_TO_REMOVE, MAX_NUM_CUSTOMERS_TO_REMOVE);
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }
    if (numCustomersToRemove == 0) {
        return {};
    }

    bool initial_customers_added = false;
    if (getRandomFractionFast() < PROB_INITIAL_SEGMENT_REMOVAL && !sol.tours.empty() && numCustomersToRemove > 0) {
        int tour_idx_to_remove_from = getRandomNumber(0, (int)sol.tours.size() - 1);
        const Tour& targetTour = sol.tours[tour_idx_to_remove_from];
        if (!targetTour.customers.empty()) {
            int segment_len = getRandomNumber(MIN_SEGMENT_LENGTH_INITIAL_SELECTION, MAX_SEGMENT_LENGTH_INITIAL_SELECTION);
            segment_len = std::min(segment_len, (int)targetTour.customers.size());
            segment_len = std::min(segment_len, numCustomersToRemove);

            if (segment_len > 0) {
                int start_segment_idx = getRandomNumber(0, (int)targetTour.customers.size() - 1);
                for (int i = 0; i < segment_len; ++i) {
                    int customer_id = targetTour.customers[(start_segment_idx + i) % targetTour.customers.size()];
                    if (customer_id != 0 && !is_selected[customer_id]) {
                        is_selected[customer_id] = 1;
                        selectedCustomersVector.push_back(customer_id);
                        initial_customers_added = true;
                    }
                }
            }
        }
    }

    if (!initial_customers_added && selectedCustomersVector.empty()) {
        int seed_customer_id = getRandomNumber(1, sol.instance.numCustomers);
        is_selected[seed_customer_id] = 1;
        selectedCustomersVector.push_back(seed_customer_id);
    }

    while (selectedCustomersVector.size() < (size_t)numCustomersToRemove) {
        bool customer_added_in_current_iteration = false;
        int strategy_attempt_count = 0;

        while (strategy_attempt_count < MAX_STRATEGY_ATTEMPTS && selectedCustomersVector.size() < (size_t)numCustomersToRemove) {
            if (selectedCustomersVector.empty()) {
                break;
            }

            int pivot_idx = getRandomNumber(0, (int)selectedCustomersVector.size() - 1);
            int pivot_customer_id = selectedCustomersVector[pivot_idx];

            float strategy_choice_rand = getRandomFractionFast();

            if (strategy_choice_rand < PROB_NEIGHBOR_EXPANSION) {
                const std::vector<int>& neighborhood = sol.instance.adj[pivot_customer_id];
                if (!neighborhood.empty()) {
                    int num_neighbors_to_consider = std::min((int)neighborhood.size(), getRandomNumber(MIN_NEIGHBORS_TO_CONSIDER, MAX_NEIGHBORS_TO_CONSIDER));
                    if (num_neighbors_to_consider > 0) {
                        int chosen_neighbor_idx = getRandomNumber(0, num_neighbors_to_consider - 1);
                        int candidate_customer_id = neighborhood[chosen_neighbor_idx];
                        if (candidate_customer_id != 0 && !is_selected[candidate_customer_id]) {
                            is_selected[candidate_customer_id] = 1;
                            selectedCustomersVector.push_back(candidate_customer_id);
                            customer_added_in_current_iteration = true;
                            break;
                        }
                    }
                }
            } else if (strategy_choice_rand < PROB_NEIGHBOR_EXPANSION + PROB_TOUR_SEGMENT_EXPANSION) {
                int tour_idx = sol.customerToTourMap[pivot_customer_id];
                if (tour_idx >= 0 && tour_idx < (int)sol.tours.size()) {
                    const Tour& current_tour = sol.tours[tour_idx];
                    const std::vector<int>& tour_customers = current_tour.customers;
                    if (tour_customers.size() > 1) {
                        int effective_start_segment_idx = getRandomNumber(0, (int)tour_customers.size() - 1);

                        int segment_len = getRandomNumber(MIN_SEGMENT_LENGTH_EXPANSION, MAX_SEGMENT_LENGTH_EXPANSION);
                        segment_len = std::min(segment_len, numCustomersToRemove - (int)selectedCustomersVector.size());
                        segment_len = std::min(segment_len, (int)tour_customers.size());

                        int customers_added_this_segment = 0;
                        for (int i = 0; i < segment_len; ++i) {
                            int customer_id = tour_customers[(effective_start_segment_idx + i) % tour_customers.size()];
                            if (customer_id != 0 && !is_selected[customer_id]) {
                                is_selected[customer_id] = 1;
                                selectedCustomersVector.push_back(customer_id);
                                customers_added_this_segment++;
                                if (selectedCustomersVector.size() >= (size_t)numCustomersToRemove) break;
                            }
                        }
                        if (customers_added_this_segment > 0) {
                            customer_added_in_current_iteration = true;
                            break;
                        }
                    }
                }
            } else {
                int tour_idx = sol.customerToTourMap[pivot_customer_id];
                if (tour_idx >= 0 && tour_idx < (int)sol.tours.size()) {
                    const Tour& current_tour = sol.tours[tour_idx];
                    const std::vector<int>& tour_customers = current_tour.customers;

                    if (!tour_customers.empty() && tour_customers.size() > 1) {
                        auto it = std::find(tour_customers.begin(), tour_customers.end(), pivot_customer_id);
                        if (it != tour_customers.end()) {
                            int pivot_in_tour_idx = std::distance(tour_customers.begin(), it);

                            int candidate_customer_id = -1;
                            int selected_relative_direction = 0;

                            int next_idx = (pivot_in_tour_idx + 1) % tour_customers.size();
                            int prev_idx = (pivot_in_tour_idx - 1 + tour_customers.size()) % tour_customers.size();

                            int potential_neighbor_1 = (getRandomFractionFast() < 0.5f) ? tour_customers[next_idx] : tour_customers[prev_idx];
                            int potential_neighbor_2 = (potential_neighbor_1 == tour_customers[next_idx]) ? tour_customers[prev_idx] : tour_customers[next_idx];

                            if (potential_neighbor_1 != 0 && !is_selected[potential_neighbor_1]) {
                                candidate_customer_id = potential_neighbor_1;
                                selected_relative_direction = (potential_neighbor_1 == tour_customers[next_idx]) ? 1 : -1;
                            } else if (potential_neighbor_2 != 0 && !is_selected[potential_neighbor_2]) {
                                candidate_customer_id = potential_neighbor_2;
                                selected_relative_direction = (potential_neighbor_2 == tour_customers[next_idx]) ? 1 : -1;
                            }

                            if (candidate_customer_id != -1) {
                                is_selected[candidate_customer_id] = 1;
                                selectedCustomersVector.push_back(candidate_customer_id);
                                customer_added_in_current_iteration = true;

                                if (selectedCustomersVector.size() < (size_t)numCustomersToRemove && getRandomFractionFast() < PROB_ADD_SECOND_TOUR_NEIGHBOR_ADJACENT) {
                                    int second_customer_pos = (pivot_in_tour_idx + selected_relative_direction * 2 + tour_customers.size()) % tour_customers.size();
                                    int second_customer_id = tour_customers[second_customer_pos];
                                    if (second_customer_id != 0 && !is_selected[second_customer_id]) {
                                        is_selected[second_customer_id] = 1;
                                        selectedCustomersVector.push_back(second_customer_id);
                                    }
                                }
                                break;
                            }
                        }
                    }
                }
            }
            strategy_attempt_count++;
        }

        if (!customer_added_in_current_iteration && selectedCustomersVector.size() < (size_t)numCustomersToRemove) {
            int safeguard_attempt_count = 0;
            while (safeguard_attempt_count < MAX_SAFEGUARD_ATTEMPTS && selectedCustomersVector.size() < (size_t)numCustomersToRemove) {
                int random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                if (!is_selected[random_unselected_customer]) {
                    is_selected[random_unselected_customer] = 1;
                    selectedCustomersVector.push_back(random_unselected_customer);
                    customer_added_in_current_iteration = true;
                    break;
                }
                safeguard_attempt_count++;
            }
            if (!customer_added_in_current_iteration && selectedCustomersVector.size() < (size_t)numCustomersToRemove) {
                 break;
            }
        }
    }
    return selectedCustomersVector;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float PROB_DIST_DEPOT = 0.20f;
    const float PROB_DEMAND = 0.15f;
    const float PROB_DIST_CENTROID = 0.10f;
    const float PROB_ANGULAR = 0.10f;
    const float PROB_NN_CHAIN = 0.15f;
    const float PROB_COMBINED_DEMAND_DIST = 0.10f;
    const float PROB_REMOVED_NEIGHBOR_CONNECTIVITY = 0.10f;
    const float PROB_RANDOM = 0.10f;

    const float STOCHASTIC_FACTOR_RANGE_DIST_DEPOT = 0.2F;
    const float NOISE_MAGNITUDE_ADDITIVE = 1e-3f;
    const float POLAR_ANGLE_DIST_WEIGHT = 0.15f;
    const float COMBINED_SCORE_ALPHA = 1.0f;
    const float COMBINED_SCORE_BETA = 0.5f;
    const float STOCHASTIC_FACTOR_NN_CHAIN = 0.15F;
    const float EPSILON = 1e-6f;

    const int MAX_NEIGHBORS_CONNECTIVITY_SCORE = 10;
    const float CONNECTIVITY_INV_DIST_WEIGHT = 1.0f;
    const float CONNECTIVITY_COUNT_WEIGHT = 100.0f;

    static thread_local std::mt19937 gen(std::random_device{}());

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size());

    float choice = getRandomFractionFast();
    bool sort_descending = getRandomFractionFast() < 0.5f;

    float cumulative_prob = 0.0f;

    cumulative_prob += PROB_DIST_DEPOT;
    if (choice < cumulative_prob) {
        for (int customer_id : customers) {
            float distance_to_depot = instance.distanceMatrix[0][customer_id];
            float stochastic_factor = 1.0F + (getRandomFractionFast() - 0.5F) * STOCHASTIC_FACTOR_RANGE_DIST_DEPOT;
            float score = distance_to_depot * stochastic_factor;
            customer_scores.push_back({score, customer_id});
        }
    } else {
        cumulative_prob += PROB_DEMAND;
        if (choice < cumulative_prob) {
            for (int customer_id : customers) {
                float demand = static_cast<float>(instance.demand[customer_id]);
                float score = demand + (getRandomFractionFast() - 0.5f) * NOISE_MAGNITUDE_ADDITIVE;
                customer_scores.push_back({score, customer_id});
            }
        } else {
            cumulative_prob += PROB_DIST_CENTROID;
            if (choice < cumulative_prob) {
                float sum_x = 0.0f, sum_y = 0.0f;
                for (int customer_id : customers) {
                    sum_x += instance.nodePositions[customer_id][0];
                    sum_y += instance.nodePositions[customer_id][1];
                }
                float centroid_x = sum_x / (float)customers.size();
                float centroid_y = sum_y / (float)customers.size();

                for (int customer_id : customers) {
                    float dx = instance.nodePositions[customer_id][0] - centroid_x;
                    float dy = instance.nodePositions[customer_id][1] - centroid_y;
                    float dist = std::sqrt(dx*dx + dy*dy);
                    float score = dist + (getRandomFractionFast() - 0.5f) * NOISE_MAGNITUDE_ADDITIVE;
                    customer_scores.push_back({score, customer_id});
                }
            } else {
                cumulative_prob += PROB_ANGULAR;
                if (choice < cumulative_prob) {
                    float depot_x = instance.nodePositions[0][0];
                    float depot_y = instance.nodePositions[0][1];

                    float max_overall_dist_from_depot = 0.0f;
                    for (int customer_id : customers) {
                        max_overall_dist_from_depot = std::max(max_overall_dist_from_depot, instance.distanceMatrix[0][customer_id]);
                    }
                    if (max_overall_dist_from_depot < EPSILON) max_overall_dist_from_depot = 1.0f;

                    for (int customer_id : customers) {
                        float cx = instance.nodePositions[customer_id][0];
                        float cy = instance.nodePositions[customer_id][1];

                        float angle_from_depot = std::atan2(cy - depot_y, cx - depot_x);
                        if (angle_from_depot < 0) angle_from_depot += 2.0F * M_PI;

                        float distance_to_depot = instance.distanceMatrix[0][customer_id];
                        float normalized_distance_component = (distance_to_depot / (max_overall_dist_from_depot + EPSILON));
                        float score = angle_from_depot + normalized_distance_component * POLAR_ANGLE_DIST_WEIGHT;
                        score += (getRandomFractionFast() - 0.5f) * NOISE_MAGNITUDE_ADDITIVE;
                        customer_scores.push_back({score, customer_id});
                    }
                } else {
                    cumulative_prob += PROB_NN_CHAIN;
                    if (choice < cumulative_prob) {
                        std::vector<int> sortedCustomers;
                        std::vector<char> visited_map(instance.numCustomers + 1, 0);
                        sortedCustomers.reserve(customers.size());

                        for (int customer_id : customers) {
                            visited_map[customer_id] = 1;
                        }

                        int currentCustomer = customers[getRandomNumber(0, (int)customers.size() - 1)];

                        sortedCustomers.push_back(currentCustomer);
                        visited_map[currentCustomer] = 0;

                        while (sortedCustomers.size() < customers.size()) {
                            float min_effective_distance = std::numeric_limits<float>::max();
                            int nextCustomer = -1;

                            for (int customer_id : customers) {
                                if (visited_map[customer_id]) {
                                    float direct_dist = instance.distanceMatrix[currentCustomer][customer_id];
                                    float effective_dist = direct_dist * (1.0f + (getRandomFractionFast() - 0.5f) * STOCHASTIC_FACTOR_NN_CHAIN);

                                    if (effective_dist < min_effective_distance) {
                                        min_effective_distance = effective_dist;
                                        nextCustomer = customer_id;
                                    }
                                }
                            }

                            if (nextCustomer != -1) {
                                sortedCustomers.push_back(nextCustomer);
                                visited_map[nextCustomer] = 0;
                                currentCustomer = nextCustomer;
                            } else {
                                for (int customer_id : customers) {
                                    if (visited_map[customer_id]) {
                                        sortedCustomers.push_back(customer_id);
                                        visited_map[customer_id] = 0;
                                        currentCustomer = customer_id;
                                        break;
                                    }
                                }
                            }
                        }
                        customers = sortedCustomers;
                        return;
                    } else {
                        cumulative_prob += PROB_COMBINED_DEMAND_DIST;
                        if (choice < cumulative_prob) {
                            float max_demand_in_removed = 1.0f;
                            float max_dist_to_depot_in_removed = 1.0f;
                            for (int customer_id : customers) {
                                max_demand_in_removed = std::max(max_demand_in_removed, static_cast<float>(instance.demand[customer_id]));
                                max_dist_to_depot_in_removed = std::max(max_dist_to_depot_in_removed, instance.distanceMatrix[0][customer_id]);
                            }

                            for (int customer_id : customers) {
                                float demand_norm = static_cast<float>(instance.demand[customer_id]) / (max_demand_in_removed + EPSILON);
                                float dist_norm = instance.distanceMatrix[0][customer_id] / (max_dist_to_depot_in_removed + EPSILON);
                                float score = COMBINED_SCORE_ALPHA * demand_norm + COMBINED_SCORE_BETA * dist_norm;
                                score += (getRandomFractionFast() - 0.5f) * NOISE_MAGNITUDE_ADDITIVE;
                                customer_scores.push_back({score, customer_id});
                            }
                        } else {
                            cumulative_prob += PROB_REMOVED_NEIGHBOR_CONNECTIVITY;
                            if (choice < cumulative_prob) {
                                if (customers.empty()) {
                                    return;
                                }

                                std::vector<char> removed_customer_flags(instance.numCustomers + 1, 0);
                                for(int cust_id : customers) {
                                    removed_customer_flags[cust_id] = 1;
                                }

                                for (int c1_id : customers) {
                                    float score = 0.0f;
                                    int num_removed_neighbors_found = 0;
                                    const std::vector<int>& neighbors = instance.adj[c1_id];

                                    for (size_t i = 0; i < neighbors.size() && num_removed_neighbors_found < MAX_NEIGHBORS_CONNECTIVITY_SCORE; ++i) {
                                        int neighbor_id = neighbors[i];
                                        if (neighbor_id != 0 && removed_customer_flags[neighbor_id]) {
                                            num_removed_neighbors_found++;
                                            if (instance.distanceMatrix[c1_id][neighbor_id] > EPSILON) {
                                                score += CONNECTIVITY_INV_DIST_WEIGHT / instance.distanceMatrix[c1_id][neighbor_id];
                                            } else {
                                                score += CONNECTIVITY_INV_DIST_WEIGHT * 1000.0f;
                                            }
                                        }
                                    }
                                    score += static_cast<float>(num_removed_neighbors_found) * CONNECTIVITY_COUNT_WEIGHT;
                                    score += (getRandomFractionFast() - 0.5f) * NOISE_MAGNITUDE_ADDITIVE;
                                    customer_scores.push_back({score, c1_id});
                                }
                            } else {
                                std::shuffle(customers.begin(), customers.end(), gen);
                                return;
                            }
                        }
                    }
                }
            }
        }
    }

    std::sort(customer_scores.begin(), customer_scores.end(), [&](const std::pair<float, int>& a, const std::pair<float, int>& b) {
        return sort_descending ? (a.first > b.first) : (a.first < b.first);
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }
}