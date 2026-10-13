.. _installation:

=======================
How to Install DACBench
=======================

This is a guide on how to install DACBench and its benchmarks. Alternatively, you can also
use `pre-built containers <containers>`.

.. role:: bash(code)
    :language: bash

First clone our GitHub repository:

.. code-block:: bash

    git clone https://github.com/automl/DACBench.git
    cd DACBench
    git submodule update --init --recursive

We recommend installing within a virtual environment, e.g. using uv:

.. code-block:: bash

    pip install uv
    uv venv --python 3.10
    source .venv/bin/activate

Now install DACBench with:

.. code-block:: bash

    make install

To also install all dependecies used in the examples, instead run:

.. code-block:: bash

    make install-dev

You should now have DACBench installed in the base version. This includes on the artificial
benchmarks, all others have separate installation dependencies. The full list of options is:

- cma - installs the IOHProfiler versions of CMA step size and CMA algorithm control
- sgd - installs the SGD benchmark
- theory - installs the theory benchmark
- all - installs all benchmark dependencies
- example - installs example dependencies
- docs - installs documentation dependencies
- dev - installs dev dependencies

Please not that in order to use the FastDownward benchmarks, you don't have to select
different dependencies, but you have to build the planner. We recommend using cmake 3.10.2 for
this:

.. code-block:: bash

    ./dacbench/envs/rl-plan/fast-downward/build.py

In the top level directory, you will find folders for tests, examples, code coverage reporting and documentation.
The code itself can be found in the 'dacbench' folder.
If you want to take advantage of our pre-run static and random baselines (10 runs each with 1000 episodes), you can download them `here <https://www.tnt.uni-hannover.de/en/project/dacbench/>`_.
