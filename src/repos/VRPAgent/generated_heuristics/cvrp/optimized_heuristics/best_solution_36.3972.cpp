#include "AgentDesigned.h"
#include <random>
#include <algorithm>
#include <vector>
#include <utility>
#include <numeric>
#include <limits>
#include <functional>
#include "Utils.h"

static thread_local std::mt19937 local_rand_generator(std::random_device{}());

enum CustomerSelectState : char {
    CS_UNTOUCHED = 0,
    CS_POTENTIAL_CANDIDATE = 1,
    CS_SELECTED = 2
};

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 15;
    const int MAX_CUSTOMERS_TO_REMOVE = 25;
    const float P_TOUR_SEGMENT_REMOVAL = 0.38f;
    const float SEGMENT_LENGTH_MIN_FACTOR = 0.5f;
    const float P_ADD_SPATIAL_INITIAL = 0.75f;
    const float P_ADD_TOUR_INITIAL = 0.70f;
    const float P_ADD_SPATIAL_PROPAGATION = 0.75f;
    const float P_ADD_TOUR_PROPAGATION = 0.70f;
    const float P_REPROPAGATE_FROM_SELECTED = 0.15f;
    const int MAX_RANDOM_SELECTION_RETRIES = 100;

    std::vector<int> selectedCustomersVec;
    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (sol.instance.numCustomers == 0 || sol.tours.empty()) {
        return {};
    }
    numCustomersToRemove = std::min(numCustomersToRemove, sol.instance.numCustomers);
    if (numCustomersToRemove == 0 && sol.instance.numCustomers > 0) {
        numCustomersToRemove = 1;
    }

    selectedCustomersVec.reserve(static_cast<size_t>(numCustomersToRemove));

    std::vector<int> customer_pos_in_tour_map(sol.instance.numCustomers + 1, -1);
    for (int tour_idx = 0; tour_idx < static_cast<int>(sol.tours.size()); ++tour_idx) {
        const auto& tour_customers = sol.tours[static_cast<size_t>(tour_idx)].customers;
        for (int i = 0; i < static_cast<int>(tour_customers.size()); ++i) {
            if (tour_customers[static_cast<size_t>(i)] > 0 && tour_customers[static_cast<size_t>(i)] <= sol.instance.numCustomers) {
                 customer_pos_in_tour_map[static_cast<size_t>(tour_customers[static_cast<size_t>(i)])] = i;
            }
        }
    }

    std::vector<int> potentialCandidatesVec;
    potentialCandidatesVec.reserve(static_cast<size_t>(numCustomersToRemove * 5)); 
    
    std::vector<CustomerSelectState> customer_state(sol.instance.numCustomers + 1, CS_UNTOUCHED);

    auto add_candidate = [&](int customer_id) {
        if (customer_id > 0 && customer_id <= sol.instance.numCustomers &&
            customer_state[static_cast<size_t>(customer_id)] == CS_UNTOUCHED) { 
            potentialCandidatesVec.push_back(customer_id);
            customer_state[static_cast<size_t>(customer_id)] = CS_POTENTIAL_CANDIDATE; 
        }
    };

    int initial_seed_customer = -1;

    if (getRandomFractionFast() < P_TOUR_SEGMENT_REMOVAL) { 
        std::vector<int> non_empty_tour_indices;
        for(size_t i = 0; i < sol.tours.size(); ++i) {
            if (sol.tours[i].customers.size() > 1) { 
                non_empty_tour_indices.push_back(static_cast<int>(i));
            }
        }

        if (!non_empty_tour_indices.empty()) {
            int tour_to_disrupt_idx = non_empty_tour_indices[getRandomNumber(0, static_cast<int>(non_empty_tour_indices.size()) - 1)];
            const auto& target_tour_customers = sol.tours[static_cast<size_t>(tour_to_disrupt_idx)].customers;
            
            if (!target_tour_customers.empty()) {
                int max_segment_len = std::min(static_cast<int>(target_tour_customers.size()), numCustomersToRemove);
                if (max_segment_len == 0) max_segment_len = 1;

                int segment_length = getRandomNumber(std::max(1, static_cast<int>(max_segment_len * SEGMENT_LENGTH_MIN_FACTOR)), max_segment_len);
                int segment_start_idx = getRandomNumber(0, static_cast<int>(target_tour_customers.size()) - 1);

                for (int i = 0; i < segment_length; ++i) {
                    int cust_to_add = target_tour_customers[static_cast<size_t>((segment_start_idx + i) % target_tour_customers.size())];
                    if (cust_to_add > 0 && cust_to_add <= sol.instance.numCustomers &&
                        customer_state[static_cast<size_t>(cust_to_add)] == CS_UNTOUCHED) {
                        selectedCustomersVec.push_back(cust_to_add);
                        customer_state[static_cast<size_t>(cust_to_add)] = CS_SELECTED;
                        if (initial_seed_customer == -1) initial_seed_customer = cust_to_add; 
                        if (selectedCustomersVec.size() >= static_cast<size_t>(numCustomersToRemove)) {
                            return selectedCustomersVec;
                        }
                    }
                }
            }
        }
    }

    if (initial_seed_customer == -1 || selectedCustomersVec.empty()) {
        initial_seed_customer = getRandomNumber(1, sol.instance.numCustomers);
        if (customer_state[static_cast<size_t>(initial_seed_customer)] == CS_UNTOUCHED) {
            selectedCustomersVec.push_back(initial_seed_customer);
            customer_state[static_cast<size_t>(initial_seed_customer)] = CS_SELECTED;
        } else {
            if (selectedCustomersVec.empty()) { 
                 selectedCustomersVec.push_back(initial_seed_customer);
                 customer_state[static_cast<size_t>(initial_seed_customer)] = CS_SELECTED;
            }
        }
    }

    int k_spatial_neighbors_for_seed = getRandomNumber(5, 10);
    const std::vector<int>& adj_list_seed = sol.instance.adj[static_cast<size_t>(initial_seed_customer)];
    for (size_t i = 0; i < adj_list_seed.size() && i < static_cast<size_t>(k_spatial_neighbors_for_seed); ++i) {
        if (getRandomFractionFast() < P_ADD_SPATIAL_INITIAL) {
            add_candidate(adj_list_seed[i]);
        }
    }

    int seed_tour_idx = sol.customerToTourMap[static_cast<size_t>(initial_seed_customer)];
    if (seed_tour_idx != -1 && seed_tour_idx < static_cast<int>(sol.tours.size())) {
        int seed_pos_in_tour = customer_pos_in_tour_map[static_cast<size_t>(initial_seed_customer)];
        if (seed_pos_in_tour != -1) {
            const std::vector<int>& tour_customers = sol.tours[static_cast<size_t>(seed_tour_idx)].customers;
            if (seed_pos_in_tour > 0 && getRandomFractionFast() < P_ADD_TOUR_INITIAL) {
                add_candidate(tour_customers[static_cast<size_t>(seed_pos_in_tour - 1)]);
            }
            if (seed_pos_in_tour < static_cast<int>(tour_customers.size()) - 1 && getRandomFractionFast() < P_ADD_TOUR_INITIAL) {
                add_candidate(tour_customers[static_cast<size_t>(seed_pos_in_tour + 1)]);
            }
        }
    }
    
    while (selectedCustomersVec.size() < static_cast<size_t>(numCustomersToRemove)) {
        int next_customer_to_add = -1;

        if (!potentialCandidatesVec.empty()) {
            int rand_idx = getRandomNumber(0, static_cast<int>(potentialCandidatesVec.size()) - 1);
            next_customer_to_add = potentialCandidatesVec[static_cast<size_t>(rand_idx)];

            potentialCandidatesVec[static_cast<size_t>(rand_idx)] = potentialCandidatesVec.back();
            potentialCandidatesVec.pop_back();
            customer_state[static_cast<size_t>(next_customer_to_add)] = CS_UNTOUCHED; 
        } else {
            for (int retry = 0; retry < MAX_RANDOM_SELECTION_RETRIES; ++retry) {
                int potential_next = getRandomNumber(1, sol.instance.numCustomers);
                if (customer_state[static_cast<size_t>(potential_next)] == CS_UNTOUCHED) { 
                    next_customer_to_add = potential_next;
                    break;
                }
            }
            if (next_customer_to_add == -1) { 
                break;
            }
        }

        if (next_customer_to_add != -1 && customer_state[static_cast<size_t>(next_customer_to_add)] == CS_UNTOUCHED) {
            selectedCustomersVec.push_back(next_customer_to_add);
            customer_state[static_cast<size_t>(next_customer_to_add)] = CS_SELECTED;

            int k_spatial_neighbors_for_propagation = getRandomNumber(3, 7);
            const std::vector<int>& current_adj_list = sol.instance.adj[static_cast<size_t>(next_customer_to_add)];
            for (size_t i = 0; i < current_adj_list.size() && i < static_cast<size_t>(k_spatial_neighbors_for_propagation); ++i) {
                if (getRandomFractionFast() < P_ADD_SPATIAL_PROPAGATION) {
                    add_candidate(current_adj_list[i]);
                }
            }

            int current_tour_idx = sol.customerToTourMap[static_cast<size_t>(next_customer_to_add)];
            if (current_tour_idx != -1 && current_tour_idx < static_cast<int>(sol.tours.size())) {
                int current_pos_in_tour = customer_pos_in_tour_map[static_cast<size_t>(next_customer_to_add)];
                if (current_pos_in_tour != -1) {
                    const std::vector<int>& tour_customers = sol.tours[static_cast<size_t>(current_tour_idx)].customers;
                    if (current_pos_in_tour > 0 && getRandomFractionFast() < P_ADD_TOUR_PROPAGATION) {
                        add_candidate(tour_customers[static_cast<size_t>(current_pos_in_tour - 1)]);
                    }
                    if (current_pos_in_tour < static_cast<int>(tour_customers.size()) - 1 && getRandomFractionFast() < P_ADD_TOUR_PROPAGATION) {
                        add_candidate(tour_customers[static_cast<size_t>(current_pos_in_tour + 1)]);
                    }
                }
            }

            if (getRandomFractionFast() < P_REPROPAGATE_FROM_SELECTED && selectedCustomersVec.size() > 1 &&
                selectedCustomersVec.size() < static_cast<size_t>(numCustomersToRemove)) {
                int random_selected_idx = getRandomNumber(0, static_cast<int>(selectedCustomersVec.size()) - 1);
                int customer_to_expand_from = selectedCustomersVec[static_cast<size_t>(random_selected_idx)];

                int k_spatial_neighbors_from_selected = getRandomNumber(2, 5);
                const std::vector<int>& adj_list_from_selected = sol.instance.adj[static_cast<size_t>(customer_to_expand_from)];
                for (size_t i = 0; i < adj_list_from_selected.size() && i < static_cast<size_t>(k_spatial_neighbors_from_selected); ++i) {
                    if (getRandomFractionFast() < P_ADD_SPATIAL_PROPAGATION) { 
                        add_candidate(adj_list_from_selected[i]);
                    }
                }
                int rand_sel_tour_idx = sol.customerToTourMap[static_cast<size_t>(customer_to_expand_from)];
                if (rand_sel_tour_idx != -1 && rand_sel_tour_idx < static_cast<int>(sol.tours.size())) {
                    int rand_sel_pos_in_tour = customer_pos_in_tour_map[static_cast<size_t>(customer_to_expand_from)];
                    if (rand_sel_pos_in_tour != -1) {
                        const std::vector<int>& tour_customers = sol.tours[static_cast<size_t>(rand_sel_tour_idx)].customers;
                        if (rand_sel_pos_in_tour > 0 && getRandomFractionFast() < P_ADD_TOUR_PROPAGATION) add_candidate(tour_customers[static_cast<size_t>(rand_sel_pos_in_tour - 1)]);
                        if (rand_sel_pos_in_tour < static_cast<int>(tour_customers.size()) - 1 && getRandomFractionFast() < P_ADD_TOUR_PROPAGATION) add_candidate(tour_customers[static_cast<size_t>(rand_sel_pos_in_tour + 1)]);
                    }
                }
            }
        }
    }
    return selectedCustomersVec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    const int STRATEGY_DEPOT_DIST_THRESHOLD = 30;
    const int STRATEGY_PIVOT_DIST_THRESHOLD = 55;
    const int STRATEGY_DEMAND_THRESHOLD = 65;
    const int STRATEGY_NN_CHAIN_THRESHOLD = 80; 
    const int STRATEGY_AVG_DIST_OTHERS_THRESHOLD = 90; 
    const int STRATEGY_COMBINED_THRESHOLD = 95;

    const float DEPOT_DIST_PERTURB_SCALE = 0.2f;
    
    const float PIVOT_CHOICE_FROM_REMOVED_PROB = 0.7f;
    const float PIVOT_DIST_PERTURB_SCALE = 0.15f;
    const float PIVOT_SORT_ASC_PROB = 0.5f;

    const float DEMAND_PERTURB_SCALE = 0.1f;

    const float NN_STOCHASTIC_PROB = 0.63f; 
    const float NN_NOISE_FACTOR_MIN = 0.05f;
    const float NN_NOISE_FACTOR_RANGE = 0.10f;

    const float COMBINED_PERTURB_SCALE = 0.1f;
    const float COMBINED_DEMAND_WEIGHT = 1.5f;
    const float COMBINED_DISTANCE_WEIGHT = 0.85f; 
    const float COMBINED_PROXIMITY_WEIGHT = 1.0f;
    const float EPSILON = 1e-6f;

    const float POST_SORT_SWAP_PROB = 0.60f; 
    const float POST_SORT_REVERSE_PROB = 0.25f; 

    int strategy_choice = getRandomNumber(0, 99); 

    std::vector<std::pair<float, int>> customer_scores;
    customer_scores.reserve(customers.size()); 

    auto calculate_max_value =
        [&](const std::function<float(int)>& getter) {
        float max_val = 0.0f;
        for (int customer_id : customers) {
            float val = getter(customer_id);
            if (val > max_val) {
                max_val = val;
            }
        }
        return std::max(max_val, 1.0f);
    };


    if (strategy_choice < STRATEGY_DEPOT_DIST_THRESHOLD) { 
        float max_dist_in_subset = calculate_max_value([&](int id){ return static_cast<float>(instance.distanceMatrix[0][static_cast<size_t>(id)]); });

        for (int customer_id : customers) {
            float base_score = static_cast<float>(instance.distanceMatrix[0][static_cast<size_t>(customer_id)]);
            float score = base_score + getRandomFractionFast() * DEPOT_DIST_PERTURB_SCALE * max_dist_in_subset;
            customer_scores.push_back({score, customer_id});
        }

        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });

    } else if (strategy_choice < STRATEGY_PIVOT_DIST_THRESHOLD) { 
        int pivot_customer_id;
        if (getRandomFractionFast() < PIVOT_CHOICE_FROM_REMOVED_PROB && !customers.empty()) {
            pivot_customer_id = customers[static_cast<size_t>(getRandomNumber(0, static_cast<int>(customers.size()) - 1))];
        } else {
            pivot_customer_id = 0;
        }

        float max_dist_to_pivot = calculate_max_value([&](int id){ return static_cast<float>(instance.distanceMatrix[static_cast<size_t>(pivot_customer_id)][static_cast<size_t>(id)]); });

        for (int customer_id : customers) {
            float base_score = static_cast<float>(instance.distanceMatrix[static_cast<size_t>(pivot_customer_id)][static_cast<size_t>(customer_id)]);
            float score = base_score + getRandomFractionFast() * PIVOT_DIST_PERTURB_SCALE * max_dist_to_pivot;
            customer_scores.push_back({score, customer_id});
        }

        bool sort_ascending_pivot = (getRandomFractionFast() < PIVOT_SORT_ASC_PROB);
        if (sort_ascending_pivot) {
            std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
                return a.first < b.first;
            });
        } else {
            std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
                return a.first > b.first;
            });
        }

    } else if (strategy_choice < STRATEGY_DEMAND_THRESHOLD) { 
        float max_demand_in_subset = calculate_max_value([&](int id){ return static_cast<float>(instance.demand[static_cast<size_t>(id)]); });

        for (int customer_id : customers) {
            float base_score = static_cast<float>(instance.demand[static_cast<size_t>(customer_id)]);
            float score = base_score + getRandomFractionFast() * DEMAND_PERTURB_SCALE * max_demand_in_subset;
            customer_scores.push_back({score, customer_id});
        }
        std::sort(customer_scores.begin(), customer_scores.end(), [](const auto& a, const auto& b) {
            return a.first > b.first;
        });

    } else if (strategy_choice < STRATEGY_NN_CHAIN_THRESHOLD) { 
        std::vector<int> sortedCustomers;
        sortedCustomers.reserve(customers.size());
        
        std::vector<int> remainingCustomersVec = customers; 

        int initialCustomerIdx = getRandomNumber(0, static_cast<int>(remainingCustomersVec.size()) - 1);
        int currentCustomer = remainingCustomersVec[static_cast<size_t>(initialCustomerIdx)];

        sortedCustomers.push_back(currentCustomer);
        if (initialCustomerIdx != static_cast<int>(remainingCustomersVec.size()) - 1) {
            std::swap(remainingCustomersVec[static_cast<size_t>(initialCustomerIdx)], remainingCustomersVec.back());
        }
        remainingCustomersVec.pop_back();

        while (!remainingCustomersVec.empty()) {
            int nextCustomer = -1;
            float minDist = std::numeric_limits<float>::max();
            int nextCustomerIdxInRemainingVec = -1;

            bool use_stochastic_nn = (getRandomFractionFast() < NN_STOCHASTIC_PROB); 
            float noise_factor = 0.0f;
            if (use_stochastic_nn) {
                noise_factor = NN_NOISE_FACTOR_MIN + getRandomFractionFast() * NN_NOISE_FACTOR_RANGE; 
            }
            
            for (int i = 0; i < static_cast<int>(remainingCustomersVec.size()); ++i) {
                int remainingCust = remainingCustomersVec[static_cast<size_t>(i)];
                float dist = static_cast<float>(instance.distanceMatrix[static_cast<size_t>(currentCustomer)][static_cast<size_t>(remainingCust)]);
                float score_to_compare = dist;
                if (use_stochastic_nn) {
                    score_to_compare += getRandomFractionFast() * (dist * noise_factor + 1.0f); 
                }
                
                if (score_to_compare < minDist) {
                    minDist = score_to_compare;
                    nextCustomer = remainingCust;
                    nextCustomerIdxInRemainingVec = i;
                }
            }

            if (nextCustomer == -1 && !remainingCustomersVec.empty()) { 
                nextCustomer = remainingCustomersVec[0]; 
                nextCustomerIdxInRemainingVec = 0;
            }

            sortedCustomers.push_back(nextCustomer);
            
            if (nextCustomerIdxInRemainingVec != -1) { 
                if (nextCustomerIdxInRemainingVec != static_cast<int>(remainingCustomersVec.size()) - 1) {
                    std::swap(remainingCustomersVec[static_cast<size_t>(nextCustomerIdxInRemainingVec)], remainingCustomersVec.back());
                }
                remainingCustomersVec.pop_back();
            }
            currentCustomer = nextCustomer;
        }
        customers = sortedCustomers;
        return;
    } else if (strategy_choice < STRATEGY_AVG_DIST_OTHERS_THRESHOLD) {
        for (int customer_id : customers) {
            float total_dist_to_others = 0.0f;
            int count = 0;
            for (int other_customer_id : customers) {
                if (customer_id != other_customer_id) {
                    total_dist_to_others += static_cast<float>(instance.distanceMatrix[static_cast<size_t>(customer_id)][static_cast<size_t>(other_customer_id)]);
                    count++;
                }
            }
            float avg_dist = (count > 0) ? (total_dist_to_others / count) : 0.0f;
            
            avg_dist += getRandomFractionFast() * 0.1f * avg_dist; 
            customer_scores.push_back({avg_dist, customer_id});
        }
        
        std::sort(customer_scores.rbegin(), customer_scores.rend());
    } else if (strategy_choice < STRATEGY_COMBINED_THRESHOLD) {
        float max_demand_in_subset = calculate_max_value([&](int id){ return static_cast<float>(instance.demand[static_cast<size_t>(id)]); });
        float max_dist_in_subset = calculate_max_value([&](int id){ return static_cast<float>(instance.distanceMatrix[0][static_cast<size_t>(id)]); });
        
        float max_proximity_val = 0.0f;
        if (customers.size() > 1) {
            for (int c1 : customers) {
                float current_cust_proximity_sum = 0.0f;
                for (int c2 : customers) {
                    if (c1 != c2) {
                        current_cust_proximity_sum += 1.0f / (static_cast<float>(instance.distanceMatrix[static_cast<size_t>(c1)][static_cast<size_t>(c2)]) + EPSILON);
                    }
                }
                if (current_cust_proximity_sum > max_proximity_val) {
                    max_proximity_val = current_cust_proximity_sum;
                }
            }
            max_proximity_val = std::max(max_proximity_val, 1.0f);
        } else {
             max_proximity_val = 1.0f;
        }

        for (int customer_id : customers) {
            float demand_component = static_cast<float>(instance.demand[static_cast<size_t>(customer_id)]);
            float distance_component = static_cast<float>(instance.distanceMatrix[0][static_cast<size_t>(customer_id)]);
            
            float proximity_to_other_removed_customers = 0.0f;
            if (customers.size() > 1) {
                for (int other_customer_id : customers) {
                    if (customer_id != other_customer_id) {
                        proximity_to_other_removed_customers += 1.0f / (static_cast<float>(instance.distanceMatrix[static_cast<size_t>(customer_id)][static_cast<size_t>(other_customer_id)]) + EPSILON);
                    }
                }
            }
            
            float normalized_demand = (max_demand_in_subset > EPSILON) ? (demand_component / max_demand_in_subset) : 0.0f;
            float normalized_distance = (max_dist_in_subset > EPSILON) ? (distance_component / max_dist_in_subset) : 0.0f;
            float normalized_proximity = (max_proximity_val > EPSILON) ? (proximity_to_other_removed_customers / max_proximity_val) : 0.0f;

            float base_score = normalized_demand * COMBINED_DEMAND_WEIGHT + 
                               (1.0f - normalized_distance) * COMBINED_DISTANCE_WEIGHT + 
                               normalized_proximity * COMBINED_PROXIMITY_WEIGHT;
            float score = base_score + getRandomFractionFast() * COMBINED_PERTURB_SCALE;
            customer_scores.push_back({score, customer_id});
        }
        std::sort(customer_scores.rbegin(), customer_scores.rend());
    } else {
        std::shuffle(customers.begin(), customers.end(), local_rand_generator);
        return;
    }

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = customer_scores[i].second;
    }

    float post_sort_perturb_rand = getRandomFractionFast();
    if (post_sort_perturb_rand < POST_SORT_SWAP_PROB) { 
        int num_swaps = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 2), 2));
        for (int i = 0; i < num_swaps; ++i) {
            if (customers.size() < 2) break;
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int max_swap_retries = 5;
            for (int retry = 0; retry < max_swap_retries; ++retry) {
                if (idx1 != idx2) break;
                idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            }
            if (idx1 != idx2) {
                std::swap(customers[static_cast<size_t>(idx1)], customers[static_cast<size_t>(idx2)]);
            }
        }
    } else if (post_sort_perturb_rand < POST_SORT_SWAP_PROB + POST_SORT_REVERSE_PROB) { 
        std::reverse(customers.begin(), customers.end());
    }
}