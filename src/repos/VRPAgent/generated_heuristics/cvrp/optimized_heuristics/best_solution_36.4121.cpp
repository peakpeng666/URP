#include "AgentDesigned.h"
#include <random>
#include <unordered_set> 
#include <algorithm>
#include <vector>
#include <utility>
#include <numeric>
#include <limits>
#include "Utils.h"

static thread_local std::mt19937 shuffle_gen(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    const float MIN_REMOVE_PERCENT = 0.03f;
    const float MAX_REMOVE_PERCENT = 0.06f;
    const float PROB_ADD_NEIGHBOR = 0.60f;
    const int MIN_ADJ_NEIGHBORS_TO_CONSIDER_RANDOM_RANGE = 7;
    const int MAX_ADJ_NEIGHBORS_TO_CONSIDER_RANDOM_RANGE = 22;
    const int MIN_TOUR_CUSTOMERS_TO_CONSIDER_RANDOM_RANGE = 6;
    const int MAX_TOUR_CUSTOMERS_TO_CONSIDER_RANDOM_RANGE = 17;

    std::vector<char> is_selected(sol.instance.numCustomers + 1, 0); 
    std::vector<int> candidatesToExplore;
    std::vector<int> selectedCustomersOrder;

    int numCustomers = sol.instance.numCustomers;
    if (numCustomers == 0) {
        return {};
    }

    int minCustomersToRemove = std::max(1, static_cast<int>(numCustomers * MIN_REMOVE_PERCENT));
    int maxCustomersToRemove = static_cast<int>(numCustomers * MAX_REMOVE_PERCENT);
    
    maxCustomersToRemove = std::min(maxCustomersToRemove, numCustomers);
    if (minCustomersToRemove > maxCustomersToRemove) {
        minCustomersToRemove = maxCustomersToRemove;
    }
    
    int targetNumToRemove = getRandomNumber(minCustomersToRemove, maxCustomersToRemove);
    if (targetNumToRemove == 0 && numCustomers > 0) {
        targetNumToRemove = 1;
    }
    if (targetNumToRemove == 0) return {};

    int startNode = getRandomNumber(1, numCustomers);
    if (is_selected[startNode] == 0) {
        is_selected[startNode] = 1;
        candidatesToExplore.push_back(startNode);
        selectedCustomersOrder.push_back(startNode);
    }
    
    size_t currentQueueIdx = 0;
    
    while (selectedCustomersOrder.size() < static_cast<size_t>(targetNumToRemove)) {
        int currentCustomer = -1;
        if (currentQueueIdx < candidatesToExplore.size()) {
            currentCustomer = candidatesToExplore[currentQueueIdx++];
        } else {
            int newStartNode = -1;
            int attempts = 0;
            const int maxFallbackAttempts = numCustomers; 

            while (attempts < maxFallbackAttempts) {
                int potentialNewSeed = getRandomNumber(1, numCustomers);
                if (is_selected[potentialNewSeed] == 0) {
                    newStartNode = potentialNewSeed;
                    break; 
                }
                attempts++;
            }

            if (newStartNode != -1) {
                is_selected[newStartNode] = 1;
                candidatesToExplore.push_back(newStartNode);
                selectedCustomersOrder.push_back(newStartNode);
                currentCustomer = newStartNode;
            } else {
                break; 
            }
        }
        
        if (currentCustomer == -1) continue;
        if (selectedCustomersOrder.size() == static_cast<size_t>(targetNumToRemove)) break;
        
        std::vector<int> potentialCandidatesForAddition;
        potentialCandidatesForAddition.reserve(MAX_ADJ_NEIGHBORS_TO_CONSIDER_RANDOM_RANGE + MAX_TOUR_CUSTOMERS_TO_CONSIDER_RANDOM_RANGE + 5); 

        const auto& adjNeighbors = sol.instance.adj[currentCustomer];
        int numAdjToConsider = std::min((int)adjNeighbors.size(), getRandomNumber(MIN_ADJ_NEIGHBORS_TO_CONSIDER_RANDOM_RANGE, MAX_ADJ_NEIGHBORS_TO_CONSIDER_RANDOM_RANGE));
        for (int i = 0; i < numAdjToConsider; ++i) {
            int neighbor = adjNeighbors[i];
            if (neighbor != 0 && is_selected[neighbor] == 0) {
                potentialCandidatesForAddition.push_back(neighbor);
            }
        }

        int tourIdx = sol.customerToTourMap[currentCustomer];
        if (tourIdx != -1 && static_cast<size_t>(tourIdx) < sol.tours.size()) {
            const Tour& tour = sol.tours[tourIdx];
            std::vector<int> shuffledTourCustomers = tour.customers;
            std::shuffle(shuffledTourCustomers.begin(), shuffledTourCustomers.end(), shuffle_gen);
            
            int tourCustomersLimit = std::min((int)shuffledTourCustomers.size(), getRandomNumber(MIN_TOUR_CUSTOMERS_TO_CONSIDER_RANDOM_RANGE, MAX_TOUR_CUSTOMERS_TO_CONSIDER_RANDOM_RANGE));
            for (int tourCustomer : shuffledTourCustomers) {
                if (tourCustomer != 0 && is_selected[tourCustomer] == 0) {
                    potentialCandidatesForAddition.push_back(tourCustomer);
                    tourCustomersLimit--;
                    if (tourCustomersLimit <= 0) break;
                }
            }
        }

        std::shuffle(potentialCandidatesForAddition.begin(), potentialCandidatesForAddition.end(), shuffle_gen);
        
        for (int candidate : potentialCandidatesForAddition) {
            if (selectedCustomersOrder.size() == static_cast<size_t>(targetNumToRemove)) break;
            
            if (is_selected[candidate] == 0) {
                bool shouldAdd = (getRandomFractionFast() < PROB_ADD_NEIGHBOR);
                if (!shouldAdd && (selectedCustomersOrder.size() == static_cast<size_t>(targetNumToRemove) - 1)) {
                    shouldAdd = true; 
                }

                if (shouldAdd) {
                    is_selected[candidate] = 1;
                    candidatesToExplore.push_back(candidate);
                    selectedCustomersOrder.push_back(candidate);
                }
            }
        }
    }

    std::vector<int> result;
    result.reserve(targetNumToRemove);
    for (int customer : selectedCustomersOrder) {
        if (result.size() < static_cast<size_t>(targetNumToRemove)) {
            result.push_back(customer);
        } else {
            break;
        }
    }
    
    while (result.size() < static_cast<size_t>(targetNumToRemove) && result.size() < static_cast<size_t>(numCustomers)) {
        int randomCustomer = getRandomNumber(1, numCustomers);
        if (is_selected[randomCustomer] == 0) {
            result.push_back(randomCustomer);
            is_selected[randomCustomer] = 1;
        }
    }

    return result;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    const float PROB_SORT_BY_PIVOT_DIST = 0.35f;
    const float PROB_SORT_BY_TOTAL_DIST = 0.60f;
    const float PROB_SORT_BY_COMPOSITE = 0.85f;
    const float PROB_SORT_BY_NEAREST_NEIGHBOR = 0.95f;

    const float PROB_COMPOSITE_DEPOT_DIST = 0.35f;
    const float PROB_COMPOSITE_DEMAND = 0.70f;
    const float MIN_WEIGHT_ADDITION = 0.1f;
    const float PROB_SIGN_FLIP = 0.50f;
    
    const float PROB_REVERSE_SORT = 0.50f;
    const float SMALL_NOISE_FACTOR = 0.0001f;

    float r = getRandomFractionFast();
    std::vector<std::pair<float, int>> sort_pairs;
    bool use_sort_pairs_method = true;

    if (r < PROB_SORT_BY_PIVOT_DIST) { 
        int pivotCustomerIdx = getRandomNumber(0, static_cast<int>(customers.size() - 1));
        int pivotCustomer = customers[pivotCustomerIdx];

        sort_pairs.reserve(customers.size());
        for (int customer_id : customers) {
            float distance = (float)instance.distanceMatrix[pivotCustomer][customer_id];
            float noise = (getRandomFractionFast() - 0.5f) * distance * SMALL_NOISE_FACTOR;
            sort_pairs.push_back({distance + noise, customer_id});
        }
    } else if (r < PROB_SORT_BY_TOTAL_DIST) {
        sort_pairs.reserve(customers.size());
        for (int c1 : customers) {
            float total_distance_to_others = 0.0f;
            for (int c2 : customers) {
                if (c1 != c2) {
                    total_distance_to_others += instance.distanceMatrix[c1][c2];
                }
            }
            float noise = (getRandomFractionFast() - 0.5f) * total_distance_to_others * SMALL_NOISE_FACTOR;
            sort_pairs.push_back({total_distance_to_others + noise, c1});
        }
    } else if (r < PROB_SORT_BY_COMPOSITE) { 
        sort_pairs.reserve(customers.size());
        float alt_r = getRandomFractionFast();
        if (alt_r < PROB_COMPOSITE_DEPOT_DIST) { 
            for (int c_id : customers) {
                float distance = (float)instance.distanceMatrix[0][c_id];
                float noise = (getRandomFractionFast() - 0.5f) * distance * SMALL_NOISE_FACTOR;
                sort_pairs.push_back({distance + noise, c_id});
            }
        } else if (alt_r < PROB_COMPOSITE_DEMAND) {
            for (int c_id : customers) {
                float demand = static_cast<float>(instance.demand[c_id]);
                float noise = (getRandomFractionFast() - 0.5f) * demand * SMALL_NOISE_FACTOR;
                sort_pairs.push_back({demand + noise, c_id});
            }
        } else { 
            int pivotCustomer = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];

            float weight_demand = getRandomFractionFast() + MIN_WEIGHT_ADDITION; 
            float weight_depot_dist = getRandomFractionFast() + MIN_WEIGHT_ADDITION; 
            float weight_pivot_dist = getRandomFractionFast() + MIN_WEIGHT_ADDITION;

            float sign_demand = (getRandomFractionFast() < PROB_SIGN_FLIP) ? 1.0f : -1.0f;
            float sign_depot_dist = (getRandomFractionFast() < PROB_SIGN_FLIP) ? 1.0f : -1.0f;
            float sign_pivot_dist = (getRandomFractionFast() < PROB_SIGN_FLIP) ? 1.0f : -1.0f;
            
            for (int customer_id : customers) {
                float customer_demand = static_cast<float>(instance.demand[customer_id]);
                float customer_depot_dist = static_cast<float>(instance.distanceMatrix[0][customer_id]);
                float customer_pivot_dist = static_cast<float>(instance.distanceMatrix[pivotCustomer][customer_id]);
                
                float score = (sign_demand * weight_demand * customer_demand) + 
                              (sign_depot_dist * weight_depot_dist * customer_depot_dist) +
                              (sign_pivot_dist * weight_pivot_dist * customer_pivot_dist);
                
                float noise = (getRandomFractionFast() - 0.5f) * SMALL_NOISE_FACTOR * 100.0f; 
                sort_pairs.push_back({score + noise, customer_id});
            }
        }
    } else if (r < PROB_SORT_BY_NEAREST_NEIGHBOR) {
        use_sort_pairs_method = false;
        std::vector<int> sorted_result;
        sorted_result.reserve(customers.size());

        std::vector<char> remaining_customers_flags(instance.numCustomers + 1, 0);
        int num_remaining = 0;
        for (int c : customers) {
            remaining_customers_flags[c] = 1;
            num_remaining++;
        }

        int current_customer = -1;
        if (num_remaining > 0) {
            current_customer = customers[getRandomNumber(0, static_cast<int>(customers.size() - 1))];
            sorted_result.push_back(current_customer);
            remaining_customers_flags[current_customer] = 0;
            num_remaining--;
        }

        while (num_remaining > 0) {
            int best_next_customer = -1;
            float min_dist = std::numeric_limits<float>::max();

            for (int candidate_customer_id : customers) {
                if (remaining_customers_flags[candidate_customer_id] == 1) {
                    float dist = static_cast<float>(instance.distanceMatrix[current_customer][candidate_customer_id]);
                    if (dist < min_dist) {
                        min_dist = dist;
                        best_next_customer = candidate_customer_id;
                    }
                }
            }

            if (best_next_customer != -1) {
                sorted_result.push_back(best_next_customer);
                remaining_customers_flags[best_next_customer] = 0;
                num_remaining--;
                current_customer = best_next_customer;
            } else {
                for (int customer_id : customers) {
                    if (remaining_customers_flags[customer_id] == 1) {
                        current_customer = customer_id;
                        sorted_result.push_back(current_customer);
                        remaining_customers_flags[current_customer] = 0;
                        num_remaining--;
                        break;
                    }
                }
            }
        }
        customers = sorted_result;
    } else { 
        use_sort_pairs_method = false;
        std::shuffle(customers.begin(), customers.end(), shuffle_gen);
    }

    if (use_sort_pairs_method) {
        bool reverseSort = getRandomFractionFast() < PROB_REVERSE_SORT; 
        if (reverseSort) {
            std::sort(sort_pairs.begin(), sort_pairs.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                if (a.first != b.first) return a.first > b.first;
                return a.second < b.second; 
            });
        } else {
            std::sort(sort_pairs.begin(), sort_pairs.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
                if (a.first != b.first) return a.first < b.first;
                return a.second < b.second;
            });
        }

        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = sort_pairs[i].second;
        }
    }
    
    int numSwaps = getRandomNumber(0, 2);
    if (numSwaps > 0 && customers.size() >= 2) {
        for (int i = 0; i < numSwaps; ++i) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size()) - 1);
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}