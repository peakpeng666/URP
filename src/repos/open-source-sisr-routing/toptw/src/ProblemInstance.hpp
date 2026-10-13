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
using TimeType = double;

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

    // Customers' x coordinate
    double x;

    // Customers' y coordinate
    double y;

    // Customers' demand
    int score;

    DistanceType knn_2_dist_score;
    DistanceType knn_5_dist_score;

    // TW start
    TimeType service_start;

    // TW end
    TimeType service_end;

    // TW duration
    TimeType service_length;
};

// Class representing a problem instance for a vehicle routing problem
class ProblemInstance
{
public:
    // Miscellaneous information from the input files
    std::string name;

    // Total number of nodes
    int dimension;

    // Number of vehicles allowed
    int vehicles;

    // Number of vehicles needed to serve all customers
    int max_vehicles;

    // Number of customers
    int customer_count;

    // Node index of start depot
    int start_depot_index;

    // Node index of end depot
    int end_depot_index;

    // Vehicle capacity
    int capacity;

    // Vector of all nodes (customers and depot)
    std::vector<Node> nodes;

    // Distance matrix between nodes
    Matrix distance_matrix;

    // Adjacency matrix between nodes (used by the SISRs algorithm)
    std::vector<std::vector<int>> adjacency_matrix;

    // Reads the problem instance from a file
    friend bool readProblemFileTOPTW(const std::string &file_path, ProblemInstance &instance);

    friend bool readProblemFileJson(const std::string &path, ProblemInstance &instance);

    // Computes additional data
    friend void preprocessProblem(ProblemInstance &instance);

    // Aux. funtion to get distance of 2 nodes
    DistanceType computeNodesDistance(int node_a, int node_b);

    // Basic command line print
    void print() const;

    // Rounding down precision
    int precision = 2;

    ProblemInstance()
        : name(""),
          dimension(0),
          max_vehicles(0),
          vehicles(0),
          customer_count(0),
          start_depot_index(0),
          end_depot_index(0),
          capacity(0),
          nodes(),
          distance_matrix(),
          adjacency_matrix(),
          precision(2)
    {
    }
};