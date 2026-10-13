#include "ProblemInstance.hpp"
#include <unordered_set>

Matrix::Matrix() : dimension(0) {}

Matrix::Matrix(size_t dim)
    : dimension(dim), data(dim * dim, DistanceType()) {}

void ProblemInstance::print() const
{
    std::cout << "ProblemInstance:" << std::endl;
    std::cout << "Name: " << name << std::endl;
    std::cout << "Dimension: " << dimension << std::endl;
    std::cout << "Vehicles: " << vehicles << std::endl;
    std::cout << "Length limit: " << time_limit << std::endl;
    std::cout << "Customer Count: " << customer_count << std::endl;
    std::cout << "Depot Indices: ";
    std::cout << start_depot_index << " ";
    std::cout << end_depot_index << " ";
    std::cout << std::endl;

    std::cout << "Nodes:" << std::endl;
    for (const Node &node : nodes)
    {
        std::cout << node.id << ": x: " << node.x << " y: " << node.y << " score: "
                  << node.score << std::endl;
    }
}

// Calculates Euclidean distance between 2 nodes
DistanceType ProblemInstance::computeNodesDistance(int node_a, int node_b)
{
    double dx = nodes[node_a].x - nodes[node_b].x;
    double dy = nodes[node_a].y - nodes[node_b].y;

    double distance = std::sqrt(dx * dx + dy * dy);

    if constexpr (std::is_integral<DistanceType>::value)
    {
        return static_cast<DistanceType>(std::round(distance));
    }
    else
    {
        return static_cast<DistanceType>(distance);
    }
}

// Calculates distances of all nodes between each other
void computeDistanceMatrix(ProblemInstance &p)
{
    p.distance_matrix = Matrix(p.dimension);

    for (int i = 0; i < p.dimension; ++i)
    {
        for (int j = i + 1; j < p.dimension; ++j)
        {
            DistanceType distance = p.computeNodesDistance(i, j);
            p.distance_matrix[i][j] = distance;
            p.distance_matrix[j][i] = distance;
        }
    }
}

// For each node sort all other nodes based on their distance
void computeAdjacencyMatrix(ProblemInstance &instance)
{
    instance.adjacency_matrix.resize(instance.dimension);

    for (int i = 0; i < instance.dimension; ++i)
    {
        std::vector<std::pair<DistanceType, int>> distances;

        for (int j = 0; j < instance.dimension; ++j)
        {
            distances.push_back(std::make_pair(instance.distance_matrix[i][j], j));
        }

        std::sort(distances.begin(), distances.end());

        instance.adjacency_matrix[i].resize(distances.size());
        for (int k = 0; k < distances.size(); ++k)
        {
            instance.adjacency_matrix[i][k] = distances[k].second;
        }
    }
}

// For each node sort all other nodes based on their distance
void computeKNNS(ProblemInstance &instance)
{
    for (int i = 0; i < instance.dimension; ++i)
    {
        DistanceType sum2 = instance.distance_matrix[i][instance.adjacency_matrix[i][1]] + instance.distance_matrix[i][instance.adjacency_matrix[i][2]];

        instance.nodes[i].knn_2_dist_score = instance.nodes[i].score / (sum2);

        DistanceType sum5 = 0;
        for (int j = 1; j < 6; ++j)
        {
            sum5 += instance.distance_matrix[i][instance.adjacency_matrix[i][j]];
        }

        instance.nodes[i].knn_5_dist_score = instance.nodes[i].score / sum5;
    }
}

void clearUnreachableNodes(ProblemInstance &p)
{
    std::vector<int> unreachable_node_ids;
    int new_end_depot = p.end_depot_index;

    for (int i = 0; i < p.dimension; ++i)
    {
        if (p.computeNodesDistance(i, p.start_depot_index) + p.computeNodesDistance(i, p.end_depot_index) > p.time_limit)
        {
            if (i < p.end_depot_index)
            {
                --new_end_depot;
            }
            unreachable_node_ids.push_back(i);
        }
    }

    p.customer_count -= unreachable_node_ids.size();
    p.dimension -= unreachable_node_ids.size();

    p.nodes.erase(
        std::remove_if(p.nodes.begin(), p.nodes.end(), [&](const Node &node)
                       { return std::find(unreachable_node_ids.begin(), unreachable_node_ids.end(), node.id) != unreachable_node_ids.end(); }),
        p.nodes.end());

    p.end_depot_index = new_end_depot;
}

void preprocessProblem(ProblemInstance &instance)
{
    clearUnreachableNodes(instance);
    if (instance.customer_count == 0)
    {
        std::cout << "The problem is empty." << std::flush;
        return;
    }
    computeDistanceMatrix(instance);
    computeAdjacencyMatrix(instance);
    computeKNNS(instance);
}

// Reads problem instance from a file
bool readProblemFileTOP(const std::string &path, ProblemInstance &instance)
{
    std::ifstream file(path);

    if (!file.is_open())
    {
        std::cerr << "Error: Could not open file " << path << std::endl;
        return false;
    }

    std::string line;

    std::string temp;

    // Read n
    if (std::getline(file, line))
    {
        std::replace(line.begin(), line.end(), ';', ' ');
        std::istringstream iss(line);
        iss >> temp >> instance.dimension;
    }
    instance.customer_count = instance.dimension - 2;
    instance.start_depot_index = 0;
    instance.end_depot_index = instance.dimension - 1;
    instance.end_depot_original_index = instance.dimension - 1;

    // Read m
    if (std::getline(file, line))
    {
        std::replace(line.begin(), line.end(), ';', ' ');
        std::istringstream iss(line);
        iss >> temp >> instance.vehicles;
    }

    // Read tmax
    if (std::getline(file, line))
    {
        std::replace(line.begin(), line.end(), ';', ' ');
        std::istringstream iss(line);
        iss >> temp >> instance.time_limit;
    }

    // Section with customers coordinates
    instance.nodes.reserve(instance.dimension);
    int i = 0;
    while (std::getline(file, line))
    {
        if (line.empty())
            continue;

        std::replace(line.begin(), line.end(), ';', ' ');
        Node node;
        std::istringstream iss(line);
        node.id = i;
        iss >> node.x >> node.y >> node.score;
        instance.nodes.push_back(node);
        ++i;
    }

    file.close();

    return true;
}