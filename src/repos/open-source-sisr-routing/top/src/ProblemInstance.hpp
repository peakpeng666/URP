#pragma once

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <stdio.h>
#include <cmath>
#include <list>
#include <algorithm>

#include "../lib/json.hpp"

using DistanceType = double;

struct Matrix
{
public:
    Matrix();
    Matrix(size_t dimension);

    DistanceType *operator[](int r)
    {
        return &data[r * dimension];
    }

private:
    size_t dimension;
    std::vector<DistanceType> data;
};

// Struct representing a node (customer or depot) in the problem instance
struct Node
{
    // id is indexed from 1
    int id;
    double x;
    double y;
    int score;

    DistanceType knn_2_dist_score;
    DistanceType knn_5_dist_score;
};

// Class representing a problem instance for a vehicle routing problem
class ProblemInstance
{
public:
    // Miscellaneous information from the input files
    std::string name;

    // Total number of nodes
    int dimension;

    // Number of vehicles
    int vehicles;

    // Number of customers
    int customer_count;

    // Node indices of depots
    int start_depot_index;
    int end_depot_index;

    // Backup of the original end depot index for final export
    int end_depot_original_index;

    // Available time budget per path
    DistanceType time_limit;

    // Vector of all nodes (customers and depot)
    std::vector<Node> nodes;

    // Distance matrix between nodes
    Matrix distance_matrix;

    // Adjacency matrix between nodes (used by the SISRs algorithm)
    std::vector<std::vector<int>> adjacency_matrix;

    // Reads the problem instance from a file
    friend bool readProblemFileTOP(const std::string &path, ProblemInstance &instance);

    friend bool readProblemFileJson(const std::string &path, ProblemInstance &instance);

    // Computes additional data
    friend void preprocessProblem(ProblemInstance &instance);

    // Aux. funtion to get distance of 2 nodes
    DistanceType computeNodesDistance(int node_a, int node_b);

    void print() const;
};