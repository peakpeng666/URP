#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <vector>
#include <algorithm>
#include <queue>
#include <limits>
#include <utility>
#include "Utils.h"

static inline float getRandomFloatInRange(float min, float max) {
    return min + (max - min) * getRandomFraction();
}

std::vector<int> select_by_llm_1(const Solution& sol) {
    const int MIN_CUSTOMERS_TO_REMOVE = 10;
    const int MAX_CUSTOMERS_TO_REMOVE = 20;
    
    const float PROB_ADD_CANDIDATE_MIN = 0.5f; 
    const float PROB_ADD_CANDIDATE_MAX = 0.8f;
    float probAddCandidate = getRandomFloatInRange(PROB_ADD_CANDIDATE_MIN, PROB_ADD_CANDIDATE_MAX);

    const int MIN_GEOGRAPHIC_NEIGHBORS_TO_CONSIDER = 5;
    const int MAX_GEOGRAPHIC_NEIGHBORS_TO_CONSIDER = 15;
    int numGeographicNeighborsToConsider = getRandomNumber(MIN_GEOGRAPHIC_NEIGHBORS_TO_CONSIDER, MAX_GEOGRAPHIC_NEIGHBORS_TO_CONSIDER);

    const int MIN_TOUR_NEIGHBORS_TO_CONSIDER = 5;
    const int MAX_TOUR_NEIGHBORS_TO_CONSIDER = 15;
    int numTourNeighborsToConsider = getRandomNumber(MIN_TOUR_NEIGHBORS_TO_CONSIDER, MAX_TOUR_NEIGHBORS_TO_CONSIDER);

    int numCustomersToRemove = getRandomNumber(MIN_CUSTOMERS_TO_REMOVE, MAX_CUSTOMERS_TO_REMOVE);
    std::unordered_set<int> selectedCustomers;
    std::queue<int> candidatesToExplore;
    std::vector<int> currentRoundCandidates; 

    static thread_local std::mt19937 gen(std::random_device{}());

    if (sol.instance.numCustomers == 0 || numCustomersToRemove == 0) {
        return {};
    }
    if (numCustomersToRemove > sol.instance.numCustomers) {
        numCustomersToRemove = sol.instance.numCustomers;
    }

    int currentSeed = getRandomNumber(1, sol.instance.numCustomers);
    
    selectedCustomers.insert(currentSeed);
    candidatesToExplore.push(currentSeed);

    while (selectedCustomers.size() < numCustomersToRemove && !candidatesToExplore.empty()) {
        int customer = candidatesToExplore.front();
        candidatesToExplore.pop();

        currentRoundCandidates.clear();

        int neighborsCount = 0;
        for (int neighborId : sol.instance.adj[customer]) {
            if (neighborId == 0) continue; 
            if (selectedCustomers.count(neighborId) == 0) {
                currentRoundCandidates.push_back(neighborId);
            }
            neighborsCount++;
            if (neighborsCount >= numGeographicNeighborsToConsider) break;
        }

        int tourIdx = sol.customerToTourMap[customer];
        if (tourIdx != -1 && tourIdx < sol.tours.size()) {
            int tourCustomersCount = 0;
            for (int customerInTour : sol.tours[tourIdx].customers) {
                if (customerInTour == customer || customerInTour == 0) continue; 
                if (selectedCustomers.count(customerInTour) == 0) {
                    currentRoundCandidates.push_back(customerInTour);
                }
                tourCustomersCount++;
                if (tourCustomersCount >= numTourNeighborsToConsider) break;
            }
        }
        
        std::shuffle(currentRoundCandidates.begin(), currentRoundCandidates.end(), gen); 

        for (int candidateId : currentRoundCandidates) {
            if (selectedCustomers.size() == numCustomersToRemove) break;
            if (selectedCustomers.count(candidateId) == 0) {
                if (getRandomFraction() < probAddCandidate) {
                    selectedCustomers.insert(candidateId);
                    candidatesToExplore.push(candidateId);
                }
            }
        }
    }

    while (selectedCustomers.size() < numCustomersToRemove) {
        int customerId = getRandomNumber(1, sol.instance.numCustomers);
        if (selectedCustomers.count(customerId) == 0) {
            selectedCustomers.insert(customerId);
        }
    }

    return std::vector<int>(selectedCustomers.begin(), selectedCustomers.end());
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }
    
    static thread_local std::mt19937 gen(std::random_device{}());

    const int NUM_SORT_TYPES = 6; 
    int sortType = getRandomNumber(0, NUM_SORT_TYPES - 1);

    if (sortType == 0) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.TW_Width[c1] < instance.TW_Width[c2];
        });
    } else if (sortType == 1) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.demand[c1] > instance.demand[c2];
        });
    } else if (sortType == 2) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.distanceMatrix[0][c1] > instance.distanceMatrix[0][c2];
        });
    } else if (sortType == 3) { 
        std::sort(customers.begin(), customers.end(), [&](int c1, int c2) {
            return instance.serviceTime[c1] > instance.serviceTime[c2];
        });
    } else if (sortType == 4) { 
        std::shuffle(customers.begin(), customers.end(), gen);
    } else { 
        const float EPS = 1e-6f; 
        const float MIN_WEIGHT_VAL = 0.05f; 
        const float MAX_WEIGHT_VAL = 1.0f;  

        float min_startTW = std::numeric_limits<float>::max(), max_startTW = std::numeric_limits<float>::lowest();
        float min_tw_width = std::numeric_limits<float>::max(), max_tw_width = std::numeric_limits<float>::lowest();
        float min_demand = std::numeric_limits<float>::max(), max_demand = std::numeric_limits<float>::lowest();
        float min_serviceTime = std::numeric_limits<float>::max(), max_serviceTime = std::numeric_limits<float>::lowest();
        float min_distToDepot = std::numeric_limits<float>::max(), max_distToDepot = std::numeric_limits<float>::lowest();

        bool hasCustomers = false;
        for (int customer_id : customers) {
            hasCustomers = true;
            min_startTW = std::min(min_startTW, instance.startTW[customer_id]);
            max_startTW = std::max(max_startTW, instance.startTW[customer_id]);
            min_tw_width = std::min(min_tw_width, instance.TW_Width[customer_id]);
            max_tw_width = std::max(max_tw_width, instance.TW_Width[customer_id]);
            min_demand = std::min(min_demand, (float)instance.demand[customer_id]);
            max_demand = std::max(max_demand, (float)instance.demand[customer_id]);
            min_serviceTime = std::min(min_serviceTime, instance.serviceTime[customer_id]);
            max_serviceTime = std::max(max_serviceTime, instance.serviceTime[customer_id]);
            min_distToDepot = std::min(min_distToDepot, instance.distanceMatrix[0][customer_id]);
            max_distToDepot = std::max(max_distToDepot, instance.distanceMatrix[0][customer_id]);
        }
        if (!hasCustomers) return; 

        std::vector<std::pair<float, int>> customer_scores;
        customer_scores.reserve(customers.size());

        float w_startTW = getRandomFloatInRange(MIN_WEIGHT_VAL, MAX_WEIGHT_VAL);
        float w_tw_width = getRandomFloatInRange(MIN_WEIGHT_VAL, MAX_WEIGHT_VAL);
        float w_demand = getRandomFloatInRange(MIN_WEIGHT_VAL, MAX_WEIGHT_VAL);
        float w_serviceTime = getRandomFloatInRange(MIN_WEIGHT_VAL, MAX_WEIGHT_VAL);
        float w_distToDepot = getRandomFloatInRange(MIN_WEIGHT_VAL, MAX_WEIGHT_VAL);

        int dominant_criterion_idx = getRandomNumber(0, 4); 
        const float DOMINANT_FACTOR = getRandomFloatInRange(1.5f, 3.0f);
        switch (dominant_criterion_idx) {
            case 0: w_startTW *= DOMINANT_FACTOR; break;
            case 1: w_tw_width *= DOMINANT_FACTOR; break;
            case 2: w_demand *= DOMINANT_FACTOR; break;
            case 3: w_serviceTime *= DOMINANT_FACTOR; break;
            case 4: w_distToDepot *= DOMINANT_FACTOR; break;
        }

        float sum_weights = w_startTW + w_tw_width + w_demand + w_serviceTime + w_distToDepot;
        if (sum_weights > EPS) { 
            w_startTW /= sum_weights;
            w_tw_width /= sum_weights;
            w_demand /= sum_weights;
            w_serviceTime /= sum_weights;
            w_distToDepot /= sum_weights;
        } else { 
            w_startTW = w_tw_width = w_demand = w_serviceTime = w_distToDepot = 1.0f / 5.0f;
        }
        
        const float MIN_PERTURBATION_RANGE = 0.005f; 
        const float MAX_PERTURBATION_RANGE = 0.05f;  
        float perturbation_range = getRandomFloatInRange(MIN_PERTURBATION_RANGE, MAX_PERTURBATION_RANGE);

        for (int customer_id : customers) {
            float norm_startTW = (max_startTW - min_startTW < EPS) ? 0.0f : (instance.startTW[customer_id] - min_startTW) / (max_startTW - min_startTW + EPS);
            float norm_tw_width = (max_tw_width - min_tw_width < EPS) ? 0.0f : (instance.TW_Width[customer_id] - min_tw_width) / (max_tw_width - min_tw_width + EPS);
            float norm_demand = (max_demand - min_demand < EPS) ? 0.0f : ((float)instance.demand[customer_id] - min_demand) / (max_demand - min_demand + EPS);
            float norm_serviceTime = (max_serviceTime - min_serviceTime < EPS) ? 0.0f : (instance.serviceTime[customer_id] - min_serviceTime) / (max_serviceTime - min_serviceTime + EPS);
            float norm_distToDepot = (max_distToDepot - min_distToDepot < EPS) ? 0.0f : (instance.distanceMatrix[0][customer_id] - min_distToDepot) / (max_distToDepot - min_distToDepot + EPS);

            float score = 0.0f;
            score += (1.0f - norm_startTW) * w_startTW; 
            score += (1.0f - norm_tw_width) * w_tw_width; 
            score += norm_demand * w_demand;            
            score += norm_serviceTime * w_serviceTime;    
            score += norm_distToDepot * w_distToDepot;   

            score += getRandomFloatInRange(-perturbation_range, perturbation_range);
            
            customer_scores.push_back({score, customer_id});
        }
        std::sort(customer_scores.begin(), customer_scores.end(), [](const std::pair<float, int>& a, const std::pair<float, int>& b) {
            return a.first > b.first; 
        });
        for (size_t i = 0; i < customers.size(); ++i) {
            customers[i] = customer_scores[i].second;
        }
    }

    if (sortType != 4) { 
        int numSwaps = getRandomNumber(0, std::min(static_cast<int>(customers.size() / 4), 3)); 
        for (int i = 0; i < numSwaps; ++i) {
            int idx1 = getRandomNumber(0, static_cast<int>(customers.size() - 1));
            int idx2 = getRandomNumber(0, static_cast<int>(customers.size() - 1));
            std::swap(customers[idx1], customers[idx2]);
        }
    }
}