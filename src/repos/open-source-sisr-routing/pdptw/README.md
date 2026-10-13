# Open-source C++ implementation of Slack Induction by String Removals for pickup and delivery problem with time windows

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
* --output-agg <path-to-agg-output-file>        Path to the output file to save (append) the aggregated run result (instance name, best no. vehicles, best distance, runtime).
* -v, --verbose                                 False by default. Enables a verbose mode, printing the search progress every 100,000 iterations.
* -h, --help                                    Prints manual for the CLI arguments.

## Data

### Instances

The solver is compatible with benchmark instances originating in [1]. The instances are available within the __benchmark_instances__ folder.

We obtained the benchmark instances from https://www.sintef.no/projectweb/top/pdptw/


### Solutions

The JSON solution files include the resulting routes (including their start/end depot stops), summary data and the parameter
setup used in the given run. Depot location has the index 0, the remaining customer pickup/delivery location indices start from 1.

## Literature

[1] LI, H.; LIM, A. A metaheuristic for the pickup and delivery problem with time windows. 
In: Proceedings 13th IEEE International Conference on Tools with Artificial Intelligence. ICTAI 2001. 2001, pp. 160–167.
