#include <random>
#include <vector>
#include <algorithm>
#include <utility>
#include <cmath>
#include <set>

extern int getRandomNumber(int min, int max);
extern float getRandomFraction(float min = 0.0, float max = 1.0);

struct Tour {
    std::vector<int> customers;
    int demand = 0;
    float costs = 0;
};

struct Instance {
    int numNodes;
    int numCustomers;
    int vehicleCapacity;
    std::vector<int> demand;
    std::vector<float> startTW;
    std::vector<float> endTW;
    std::vector<float> TW_Width;
    std::vector<float> serviceTime;
    std::vector<std::vector<float>> distanceMatrix;
    std::vector<std::vector<float>> nodePositions;
    std::vector<std::vector<int>> adj;
};

struct Solution {
    const Instance& instance;
    float totalCosts;
    std::vector<Tour> tours;
    std::vector<int> customerToTourMap;
};

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 8;
    const int MAX_CUSTOMERS_TO_REMOVE = 18;
    const int MAX_ATTEMPTS_FOR_CLUSTER_GROWTH = 9;
    const float TOUR_AFFINITY_PROBABILITY = 0.75f;
    const int NEIGHBORS_TO_CONSIDER = 20;
    const float CANDIDATE_SELECTION_EXPONENT = 3.0f;
    const float ADD_CANDIDATE_PROB = 0.90f;
    const int MAX_RANDOM_PROBES_FOR_NEW_SEED = 50;

    std::vector<char> is_selected(sol.instance.numCustomers + 1, 0);
    std::vector<int> selectedCustomers_vec;

    int n_remove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);

    if (sol.instance.numCustomers == 0) return {};
    if (n_remove > sol.instance.numCustomers) {
        n_remove = sol.instance.numCustomers;
    }
    if (n_remove == 0 && sol.instance.numCustomers > 0) {
        n_remove = 1;
    }
    if (n_remove == 0) {
        return {};
    }

    selectedCustomers_vec.reserve(n_remove);

    int c_seed = getRandomNumber(1, sol.instance.numCustomers);
    selectedCustomers_vec.push_back(c_seed);
    is_selected[c_seed] = 1;

    int attempts_without_adding = 0;
    std::vector<int> potential_candidates_storage;
    potential_candidates_storage.reserve(NEIGHBORS_TO_CONSIDER * 2);

    while (static_cast<int>(selectedCustomers_vec.size()) < n_remove) {
        potential_candidates_storage.clear();
        int c_new_candidate = -1;
        
        int c_anchor = selectedCustomers_vec[getRandomNumber(0, selectedCustomers_vec.size() - 1)];
        
        if (getRandomFraction() < TOUR_AFFINITY_PROBABILITY) {
            int tour_idx = sol.customerToTourMap[c_anchor];
            if (tour_idx != -1 && tour_idx < static_cast<int>(sol.tours.size())) {
                const std::vector<int>& tour_customers = sol.tours[tour_idx].customers;
                if (!tour_customers.empty()) {
                    int num_to_sample = std::min(NEIGHBORS_TO_CONSIDER, static_cast<int>(tour_customers.size() * 2));
                    for (int i = 0; i < num_to_sample; ++i) {
                        int random_tour_idx = getRandomNumber(0, tour_customers.size() - 1);
                        int cust_id = tour_customers[random_tour_idx];
                        if (is_selected[cust_id] == 0) {
                            potential_candidates_storage.push_back(cust_id);
                            if (static_cast<int>(potential_candidates_storage.size()) >= NEIGHBORS_TO_CONSIDER) break;
                        }
                    }
                }
            }
        }
        
        if (static_cast<int>(potential_candidates_storage.size()) < NEIGHBORS_TO_CONSIDER) {
            for (int neighbor_node : sol.instance.adj[c_anchor]) {
                if (neighbor_node >= 1 && neighbor_node <= sol.instance.numCustomers && is_selected[neighbor_node] == 0) {
                    potential_candidates_storage.push_back(neighbor_node);
                    if (static_cast<int>(potential_candidates_storage.size()) >= NEIGHBORS_TO_CONSIDER) {
                        break;
                    }
                }
            }
        }

        if (!potential_candidates_storage.empty()) {
            float r = getRandomFraction();
            float biased_random = r * r * r; 
            
            int chosenIndex = static_cast<int>(biased_random * potential_candidates_storage.size());
            if (chosenIndex >= static_cast<int>(potential_candidates_storage.size())) {
                chosenIndex = potential_candidates_storage.size() - 1;
            }
            c_new_candidate = potential_candidates_storage[chosenIndex];
        }

        if (c_new_candidate != -1 && is_selected[c_new_candidate] == 0 && getRandomFraction() < ADD_CANDIDATE_PROB) {
            selectedCustomers_vec.push_back(c_new_candidate);
            is_selected[c_new_candidate] = 1;
            attempts_without_adding = 0;
        } else {
            attempts_without_adding++;
            if (attempts_without_adding >= MAX_ATTEMPTS_FOR_CLUSTER_GROWTH) {
                int new_seed_candidate = -1;
                for (int i = 0; i < MAX_RANDOM_PROBES_FOR_NEW_SEED; ++i) {
                    int rand_cust_id = getRandomNumber(1, sol.instance.numCustomers);
                    if (is_selected[rand_cust_id] == 0) {
                        new_seed_candidate = rand_cust_id;
                        break;
                    }
                }
                
                if (new_seed_candidate != -1) {
                    selectedCustomers_vec.push_back(new_seed_candidate);
                    is_selected[new_seed_candidate] = 1;
                    attempts_without_adding = 0;
                } else { 
                    break; 
                }
            }
        }
    }
    return selectedCustomers_vec;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty() || customers.size() == 1) {
        return;
    }

    static thread_local std::mt19937 gen(std::random_device{}());

    const int NUM_SORTING_STRATEGIES = 10;
    const int SHUFFLE_STRATEGY_INDEX = 3; 
    const float STOCHASTIC_JITTER_MAGNITUDE = 0.035f; 
    const float TIE_BREAKING_JITTER_MAGNITUDE = 1e-4f;
    const int MAX_NEIGHBORS_FOR_DENSITY_CHECK = 6;
    const float EPSILON = 1e-6f;
    const float ZERO_TW_PENALTY_FACTOR = 1500.0f;
    const float DOMINANT_FACTOR_PROBABILITY = 0.2f;
    const float NEIGHBOR_DENSITY_WEIGHT = 60.0f;

    int strategy = getRandomNumber(0, NUM_SORTING_STRATEGIES - 1); 

    if (strategy == SHUFFLE_STRATEGY_INDEX) {
        std::shuffle(customers.begin(), customers.end(), gen);
        return;
    }

    std::vector<std::pair<float, int>> scored_customers;
    scored_customers.reserve(customers.size());

    auto add_stochastic_jitter = [&]() {
        return (1.0f + getRandomFraction(-STOCHASTIC_JITTER_MAGNITUDE, STOCHASTIC_JITTER_MAGNITUDE));
    };
    
    std::vector<char> is_current_removed_lookup;
    if (strategy == 6 || strategy == 9) { 
        is_current_removed_lookup.resize(instance.numCustomers + 1, 0);
        for (int cust_id : customers) {
            is_current_removed_lookup[cust_id] = 1;
        }
    }

    if (strategy == 0) { 
        for (int cust_id : customers) {
            float score = instance.TW_Width[cust_id];
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    } 
    else if (strategy == 1) {
        for (int cust_id : customers) {
            float score = -static_cast<float>(instance.demand[cust_id]);
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    } 
    else if (strategy == 2) {
        for (int cust_id : customers) {
            float score = -instance.serviceTime[cust_id];
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    } 
    else if (strategy == 4) {
        for (int cust_id : customers) {
            float score = -instance.distanceMatrix[0][cust_id];
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    } 
    else if (strategy == 5) {
        for (int cust_id : customers) {
            float score = instance.startTW[cust_id];
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    } 
    else if (strategy == 6) { 
        float w_tw_width = getRandomFraction();
        float w_demand = getRandomFraction();
        float w_start_tw = getRandomFraction();
        float w_depot_dist = getRandomFraction();
        float w_service_time = getRandomFraction();
        float w_neighbor_density = getRandomFraction();

        if (getRandomFraction() < DOMINANT_FACTOR_PROBABILITY) {
            int dominant_factor_idx = getRandomNumber(0, 5);
            w_tw_width = (dominant_factor_idx == 0) ? 1.0f : getRandomFraction() * 0.1f;
            w_demand = (dominant_factor_idx == 1) ? 1.0f : getRandomFraction() * 0.1f;
            w_start_tw = (dominant_factor_idx == 2) ? 1.0f : getRandomFraction() * 0.1f;
            w_depot_dist = (dominant_factor_idx == 3) ? 1.0f : getRandomFraction() * 0.1f;
            w_service_time = (dominant_factor_idx == 4) ? 1.0f : getRandomFraction() * 0.1f;
            w_neighbor_density = (dominant_factor_idx == 5) ? 1.0f : getRandomFraction() * 0.1f;
        }

        float sum_weights = w_tw_width + w_demand + w_start_tw + w_depot_dist + w_service_time + w_neighbor_density;
        if (sum_weights < EPSILON) { 
            w_tw_width = w_demand = w_start_tw = w_depot_dist = w_service_time = w_neighbor_density = 1.0f;
            sum_weights = 6.0f;
        }

        w_tw_width /= sum_weights;
        w_demand /= sum_weights;
        w_start_tw /= sum_weights;
        w_depot_dist /= sum_weights;
        w_service_time /= sum_weights;
        w_neighbor_density /= sum_weights;

        for (int cust_id : customers) {
            int neighbors_in_removed_count = 0;
            for (int i = 0; i < std::min(static_cast<int>(instance.adj[cust_id].size()), MAX_NEIGHBORS_FOR_DENSITY_CHECK); ++i) {
                int neighbor_node = instance.adj[cust_id][i];
                if (neighbor_node >= 1 && neighbor_node <= instance.numCustomers && is_current_removed_lookup[neighbor_node]) {
                    neighbors_in_removed_count++;
                }
            }
            float density_score = static_cast<float>(neighbors_in_removed_count) / MAX_NEIGHBORS_FOR_DENSITY_CHECK;

            float score =
                w_tw_width * instance.TW_Width[cust_id] +
                w_start_tw * instance.startTW[cust_id] +
                w_depot_dist * -instance.distanceMatrix[0][cust_id] +
                w_demand * (-static_cast<float>(instance.demand[cust_id]) / instance.vehicleCapacity) +
                w_service_time * -instance.serviceTime[cust_id] +
                w_neighbor_density * density_score * NEIGHBOR_DENSITY_WEIGHT;

            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    }
    else if (strategy == 7) { 
        for (int cust_id : customers) {
            float score = instance.endTW[cust_id];
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    }
    else if (strategy == 8) { 
        for (int cust_id : customers) {
            float score = -static_cast<float>(instance.demand[cust_id]); 
            if (instance.TW_Width[cust_id] > EPSILON) { 
                score /= instance.TW_Width[cust_id]; 
            } else { 
                score *= ZERO_TW_PENALTY_FACTOR;
            }
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    }
    else if (strategy == 9) { 
        for (int cust_id : customers) {
            int neighbors_in_removed_count = 0;
            for (int i = 0; i < std::min(static_cast<int>(instance.adj[cust_id].size()), MAX_NEIGHBORS_FOR_DENSITY_CHECK); ++i) {
                int neighbor_node = instance.adj[cust_id][i];
                if (neighbor_node >= 1 && neighbor_node <= instance.numCustomers && is_current_removed_lookup[neighbor_node]) {
                    neighbors_in_removed_count++;
                }
            }
            float score = instance.distanceMatrix[0][cust_id];
            score -= static_cast<float>(neighbors_in_removed_count) * NEIGHBOR_DENSITY_WEIGHT; 
            scored_customers.push_back({score * add_stochastic_jitter() + getRandomFraction(-TIE_BREAKING_JITTER_MAGNITUDE, TIE_BREAKING_JITTER_MAGNITUDE), cust_id});
        }
    }

    std::sort(scored_customers.begin(), scored_customers.end());

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = scored_customers[i].second;
    }
}