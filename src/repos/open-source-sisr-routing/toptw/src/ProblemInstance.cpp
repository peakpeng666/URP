#include "ProblemInstance.hpp"

Matrix::Matrix() : dimension(0) {}

Matrix::Matrix(size_t dim)
    : dimension(dim), data(dim * dim, DistanceType()) {}

void ProblemInstance::print() const
{
    std::cout << "ProblemInstance:" << std::endl;
    std::cout << "Name: " << name << std::endl;
    std::cout << "Dimension: " << dimension << std::endl;
    std::cout << "Vehicles max: " << max_vehicles << std::endl;
    std::cout << "Vehicles allowed: " << vehicles << std::endl;
    std::cout << "Customer Count: " << customer_count << std::endl;
    std::cout << "Start Depot Index Indiex: " << start_depot_index << " ";
    std::cout << std::endl;
    std::cout << "Capacity: " << capacity << std::endl;

    std::cout << "Nodes:" << std::endl;
    for (const Node &node : nodes)
    {
        std::cout << node.id << ": x: " << node.x << " y: " << node.y << " demand: "
                  << " tw start: " << node.service_start << " tw end: " << node.service_end
                  << " tw duration: " << node.service_length << std::endl;
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
        // benchmarks work with rounded distances
        // Cordeua (p*)
        if (precision == 2)
        {
            return static_cast<DistanceType>(static_cast<int>(distance * 100.)) / 100;
        }
        // Solomon (c* r* rc*)
        return static_cast<DistanceType>(static_cast<int>(distance * 10.)) / 10;
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

void preprocessProblem(ProblemInstance &instance)
{   
    computeDistanceMatrix(instance);
    computeAdjacencyMatrix(instance);
    computeKNNS(instance);
}

// Homberger and Gehring (1999)
// Customer data are indexed from 0 in this problem file type
bool readProblemFileTOPTW(const std::string &file_path, ProblemInstance &instance)
{
    std::ifstream file(file_path);

    if (!file.is_open())
    {
        std::cerr << "Error: Could not open file " << file_path << std::endl;
        return false;
    }

    std::string line;
    std::string temp;
    
    // Read first 2 lines describing the problem
    if (std::getline(file, line))
    {
        std::istringstream iss(line);
        iss >> temp >> instance.vehicles >> instance.customer_count;
    }
    instance.dimension = instance.customer_count + 1;

    // Nothing relevant on this line
    if (std::getline(file, line))
    {
    }

    // Length of the input line may vary
    std::vector<double> temp_storage;
    double number;

    // Read nodes
    while (std::getline(file, line))
    {
        std::istringstream iss(line);
        
        Node node;

        // First 5 values in the row are always usefull
        iss >> node.id >> node.x >> node.y >> node.service_length >> node.score;

        // Unknown number of irrelevant values follows
        while (iss >> number) {
            temp_storage.push_back(number);
        }
        
        node.service_start = temp_storage[temp_storage.size() - 2];
        node.service_end = temp_storage[temp_storage.size() - 1];

        instance.nodes.push_back(node);
    }
    instance.dimension = instance.customer_count + 1;
    instance.start_depot_index = 0;
    instance.end_depot_index = 0;

    file.close();

    return true;
}
