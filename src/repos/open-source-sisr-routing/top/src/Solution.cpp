#include "Solution.hpp"
#include "ProblemInstance.hpp"

Route::Route()
    : cost(), score(0), ruined(false)
{
}

void Route::updateRouteCost(ProblemInstance &p)
{
    cost = 0;
    if (customers.empty())
    {
        cost = p.distance_matrix[p.start_depot_index][p.end_depot_index];
        return;
    }

    // Distances from the depot to the first and last served customers
    cost += p.distance_matrix[p.start_depot_index][customers.front()];
    cost += p.distance_matrix[customers.back()][p.end_depot_index];

    // Distances between the running customers
    for (int j = 0; j < customers.size() - 1; ++j)
    {
        cost += p.distance_matrix[customers[j]][customers[j + 1]];
    }
}

Solution::Solution(ProblemInstance &p)
    : total_score(0), total_cost(0), problem(p), customer_to_route(p.dimension, -1)
{
}

Solution::Solution(const Solution &other)
    : total_score(other.total_score),
      total_cost(other.total_cost),
      problem(other.problem),
      absent_customers(other.absent_customers),
      customer_to_route(other.customer_to_route),
      routes(other.routes)
{
}

Solution &Solution::operator=(const Solution &other)
{
    if (this == &other)
        return *this;

    total_score = other.total_score;
    total_cost = other.total_cost;
    problem = other.problem;
    absent_customers = other.absent_customers;
    routes = other.routes;
    customer_to_route = other.customer_to_route;

    return *this;
}

void Solution::insertIntoRoute(int route_index, int customer, int position, DistanceType insertion_cost)
{
    auto &route = routes[route_index];

    route.customers.insert(route.customers.begin() + position, customer);
    route.cost += insertion_cost;
    total_cost += insertion_cost;
    total_score += problem.nodes[customer].score;
    route.score += problem.nodes[customer].score;
    customer_to_route[customer] = route_index;
}

void Solution::removeFromRoute(int route_index, const std::vector<int> &removed_customers)
{
    if (removed_customers.empty())
    {
        return;
    }

    auto &route = routes[route_index];
    total_score -= route.score;
    total_cost -= route.cost;

    for (int customer : removed_customers)
    {
        route.customers.erase(std::remove(route.customers.begin(), route.customers.end(), customer), route.customers.end());
        absent_customers.push_back(customer);
        customer_to_route[customer] = -1;
        route.score -= problem.nodes[customer].score;
    }

    route.updateRouteCost(problem);

    total_score += route.score;
    total_cost += route.cost;
}

void Solution::resetRoutes()
{
    total_cost = 0;
    for (Route &route : routes)
    {
        // Reset ruined flag
        route.ruined = false;
        route.updateRouteCost(problem);
        total_cost += route.cost;
    }
}

void Solution::printSolution(std::ostream &out)
{
    out << "Solution uses " << routes.size()
        << " routes, with total score: " << total_score << " and cost " << total_cost << std::endl;

    int i = 0;
    for (int j = 0; j < routes.size(); ++j)
    {
        out << "[" << i << "] ";
        out << "cost: " << routes[j].cost << " ruined: " << routes[j].ruined << " score: " << routes[j].score << " customers: ";

        for (int customer : routes[j].customers)
        {
            out << customer << ", ";
            //out << problem.nodes[customer].x << ", " << problem.nodes[customer].y;
        }
        out << std::endl;
        i++;
    }
    out << "Absent customers: ";
    if (absent_customers.size() == 0)
    {
        out << "none";
    }
    for (int i = 0; i < absent_customers.size(); ++i)
    {
        out << absent_customers[i] << ", ";
    }
    out << " customer_to_route mapping: \n";
    for (int i = 0; i < customer_to_route.size(); ++i)
    {
        out << i << " - " << customer_to_route[i] << ", ";
    }
    out << std::endl
        << std::endl;
}