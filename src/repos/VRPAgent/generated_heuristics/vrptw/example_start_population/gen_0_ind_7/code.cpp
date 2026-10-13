#include "AgentDesigned.h"
#include <random>
#include <unordered_set>
#include <algorithm>
#include <vector>
#include <utility>
#include "Utils.h"

static thread_local std::mt19937 gen_select(std::random_device{}());
static thread_local std::mt19 घूमट37 gen_sort(std::random_device{}());

std::vector<int> select_by_llm_1(const Solution& sol) {
    std::vector<int> selected_customers;
    std::unordered_set<int> selected_set;

    int num_customers_to_remove = getRandomNumber(15, 30);
    if (num_customers_to_remove > sol.instance.numCustomers) {
        num_customers_to_remove = sol.instance.numCustomers;
    }

    int first_customer_idx = getRandomNumber(1, sol.instance.numCustomers);
    selected_customers.push_back(first_customer_idx);
    selected_set.insert(first_customer_idx);

    while (selected_customers.size() < num_customers_to_remove) {
        int anchor_customer_idx = selected_customers[getRandomNumber(0, selected_customers.size() - 1)];

        std::vector<int> candidate_neighbors;

        int tour_idx = sol.customerToTourMap[anchor_customer_idx];
        if (tour_idx >= 0 && tour_idx < sol.tours.size()) {
            const Tour& tour = sol.tours[tour_idx];
            for (size_t i = 0; i < tour.customers.size(); ++i) {
                if (tour.customers[i] == anchor_customer_idx) {
                    if (i > 0) {
                        candidate_neighbors.push_back(tour.customers[i - 1]);
                    }
                    if (i + 1 < tour.customers.size()) {
                        candidate_neighbors.push_back(tour.customers[i + 1]);
                    }
                    break;
                }
            }
        }

        int num_adj_to_consider = std::min((int)sol.instance.adj[anchor_customer_idx].size(), getRandomNumber(5, 15));
        for (int i = 0; i < num_adj_to_consider; ++i) {
            candidate_neighbors.push_back(sol.instance.adj[anchor_customer_idx][i]);
        }
        
        std::shuffle(candidate_neighbors.begin(), candidate_neighbors.end(), gen_select);

        int chosen_customer_idx = -1;
        for (int c : candidate_neighbors) {
            if (c >= 1 && c <= sol.instance.numCustomers && selected_set.find(c) == selected_set.end()) {
                chosen_customer_idx = c;
                break;
            }
        }

        if (chosen_customer_idx != -1) {
            selected_customers.push_back(chosen_customer_idx);
            selected_set.insert(chosen_customer_idx);
        } else {
            int random_unselected_customer = -1;
            int counter = 0;
            do {
                random_unselected_customer = getRandomNumber(1, sol.instance.numCustomers);
                counter++;
            } while (selected_set.count(random_unselected_customer) && counter < sol.instance.numCustomers * 2);

            if (random_unselected_customer != -1 && selected_set.find(random_unselected_customer) == selected_set.end()) {
                selected_customers.push_back(random_unselected_customer);
                selected_set.insert(random_unselected_customer);
            } else {
                break;
            }
        }
    }
    return selected_customers;
}

void sort_by_llm_1(std::vector<int>& customers, const Instance& instance) {
    if (customers.empty()) {
        return;
    }

    std::vector<std::pair<float, int>> sort_data;
    sort_data.reserve(customers.size());

    int sorting_strategy_choice = getRandomNumber(0, 3);

    for (int customer_id : customers) {
        float key = 0.0f;

        switch (sorting_strategy_choice) {
            case 0:
                key = instance.TW_Width[customer_id];
                key += getRandomFractionFast() * 0.001f;
                break;
            case 1:
                key = instance.startTW[customer_id];
                key += getRandomFractionFast() * 0.001f;
                break;
            case 2:
                key = -instance.distanceMatrix[0][customer_id];
                key += getRandomFractionFast() * 0.001f;
                break;
            case 3:
            default:
                key = getRandomFractionFast();
                break;
        }
        sort_data.emplace_back(key, customer_id);
    }

    std::sort(sort_data.begin(), sort_data.end(), [](const auto& a, const auto& b) {
        return a.first < b.first;
    });

    for (size_t i = 0; i < customers.size(); ++i) {
        customers[i] = sort_data[i].second;
    }
}