# Open-source C++ implementation of Slack Induction by String Removals for team orienteering problem with time windows

### Authors: Martin Pajerský, Václav Sobotka, Hana Rudová, Faculty of Informatics, Masaryk University, Brno, Czech Republic

## Getting started

### Prerequisites

You'll need the following tools installed on your system:

* **C++ Compiler** (supporting C++20 or newer)
* **CMake** (version 3.10 or newer)

### Building the project

Follow these steps to build the project from the source code:

1.  **Create a build directory and run CMake:**
    ```bash
    cd <project-dir>
    mkdir build
    cd build
    cmake ..
    ```

2.  **Compile the code:**
    ```bash
    cmake --build .
    ```
    The main executable called __solver__ will be located in the `build/` directory.

---

### Running the solver

The minimum required set of solver arguments includes the paths to the instance and configuration files:

```bash
    cd <project-dir>
    ./build/solver --instance <path-to-input> --configuration <path-to-config>
```

Additionally, the following optional named arguments are available:

* --output-json <path-to-json-output-file>      Path to the output file to save the JSON-style result.
* --output-agg <path-to-agg-output-file>        Path to the output file to save (append) the aggregated run result (instance name, best solution value, runtime).
* -v, --verbose                                 False by default. Enables a verbose mode, printing the search progress every 100,000 iterations.
* -h, --help                                    Prints manual for the CLI arguments.

## Data

### Instances

The solver is compatible with benchmark instances originating in [1]. The instances are available within the __benchmark_instances__ folder.

The benchmark instances are commonly solved in variants with 1 to 4 vehicles. The instance file stays the same, and the 
number of vehicles is set in the configuration file.

The instances were obtained from https://www.mech.kuleuven.be/en/cib/op#autotoc-item-autotoc-6

### Solutions

The JSON solution files include the resulting routes (including their start/end depot stops), summary data and the parameter
setup used in the given run. Start and end depot locations have the index 0. The remaining customer location indices 
start from 1 and go up to the number of customers in the problem.


## Literature

[1] Montemanni, R., Gambardella, L.M.: Ant colony system for team orienteering
problems with time windows. Foundations of Computing and Decision Sciences
34, 287–306 (2009)