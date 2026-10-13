#include "Solution.hpp"
#include "ProblemInstance.hpp"

Route::Route()
    : cost(0), score(0), ruined(false)
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

void Route::updateRouteVariables(ProblemInstance &p, int pos_index)
{
    if (customers.empty())
    {
        latest_arrivals[0] = p.nodes[p.end_depot_index].service_end;
        return;
    }

    int customers_count = customers.size();

    int begin = 1;
    if (pos_index == 0 || pos_index == -1)
    {
        earliest_departures[0] = std::max(p.nodes[customers[0]].service_start, p.distance_matrix[p.start_depot_index][customers[0]]) + p.nodes[customers[0]].service_length + p.nodes[p.start_depot_index].service_start;
    }
    else
    {
        begin = pos_index;
    }

    for (int j = begin; j < customers_count; ++j)
    {
        earliest_departures[j] = std::max(earliest_departures[j - 1] + p.distance_matrix[customers[j - 1]][customers[j]],
                                          p.nodes[customers[j]].service_start) +
                                 p.nodes[customers[j]].service_length;
    }

    begin = customers_count - 2;
    if (pos_index == customers_count - 1 || pos_index == -1)
    {
        latest_arrivals[customers_count] = p.nodes[p.end_depot_index].service_end;
        latest_arrivals[customers_count - 1] = std::min(latest_arrivals[customers_count] - p.distance_matrix[customers[customers_count - 1]][p.end_depot_index] - p.nodes[customers[customers_count - 1]].service_length,
            p.nodes[customers[customers_count - 1]].service_end);
    }
    else
    {
        begin = pos_index;
    }

    for (int j = begin; j >= 0; --j)
    {
        latest_arrivals[j] = std::min(latest_arrivals[j + 1] - p.distance_matrix[customers[j]][customers[j + 1]] - p.nodes[customers[j]].service_length,
                                      p.nodes[customers[j]].service_end);
    }
}

void Route::print(ProblemInstance &p, std::ostream &out)
{
    out << "cost: " << cost << " ruined: " << ruined << " score: " << score << std::endl;

    out << "customs: ";
    for (int customer : customers)
    {
        out << customer << ", ";
    }
    out << std::endl
              << "starts: ";
    for (int customer : customers)
    {
        out << p.nodes[customer].service_start << ", ";
    }
    out << std::endl
              << "ends: ";
    for (int customer : customers)
    {
        out << p.nodes[customer].service_end << ", ";
    }
    out << std::endl
              << "durations: ";
    for (int customer : customers)
    {
        out << p.nodes[customer].service_length << ", ";
    }
    out << std::endl
              << "distances: ";
    for (int i = 0; i < customers.size() - 1; ++i)
    {
        out << p.distance_matrix[customers[i]][customers[i + 1]] << " " << customers[i] << " " << customers[i + 1] << ", ";
    }
    out << std::endl
              << "earliest dep: ";
    for (int i = 0; i < customers.size(); ++i)
    {
        out << earliest_departures[i] << ", ";
    }
    out << std::endl
              << "latest arr: ";
    for (int i = 0; i < customers.size() + 1; ++i)
    {
        out << latest_arrivals[i] << ", ";
    }
    out << std::endl;
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
    route.earliest_departures.insert(route.earliest_departures.begin() + position, 0);
    route.latest_arrivals.insert(route.latest_arrivals.begin() + position, 0);
    route.cost += insertion_cost;
    total_cost += insertion_cost;
    total_score += problem.nodes[customer].score;
    route.score += problem.nodes[customer].score;
    customer_to_route[customer] = route_index;
    route.updateRouteVariables(problem, position);
}

void Solution::removeFromRoute(int route_index, const std::vector<int> &removed_customers)
{
    if (removed_customers.empty())
    {
        return;
    }

    auto &route = routes[route_index];
    total_cost -= route.cost;
    for (int customer : removed_customers)
    {
        route.customers.erase(std::remove(route.customers.begin(), route.customers.end(), customer), route.customers.end());
        absent_customers.push_back(customer);
        customer_to_route[customer] = -1;
        route.score -= problem.nodes[customer].score;
        total_score -= problem.nodes[customer].score;
    }
    route.earliest_departures.resize(route.customers.size());
    route.latest_arrivals.resize(route.customers.size() + 1);

    route.updateRouteCost(problem);

    route.updateRouteVariables(problem, -1);
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

    for (int j = 0; j < problem.vehicles; ++j)
    {
        out << "[" << j << "] ";
        Route &route = routes[j];
        if (route.customers.empty())
        {
            out << "This route is currently empty" << std::endl;
        }
        else
        {
            route.print(problem);
        }
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