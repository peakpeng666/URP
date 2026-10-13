# DACBench Examples

We have several examples of how to use DACBench, how each benchmark works and how to use DACBench in RL.
Generally, examples are either in notebooks with can be run sequentially or executed as:

```
python examples/<example_script>.py
```

## Trying Out DACBench Features

Some examples specifically deal with DACBench features outside of the benchmarks themselves.
These are:
- 'logger.py' shows how to use the logging function in combination with some of our logging wrappers in a multi-run experiment setting
- 'container.py' contains an example of how to use the containerized version of the benchmarks - be aware that you should build the container first before using it!
- 'run_dacbench.py' uses the built-in benchmark runner in combination with our Random Agent
- 'multi_agent.py' demonstrates how the multi-agent version of the benchmarks works

## Getting Familiar With The Benchmarks

To demonstrate how the instances as well as rewards and state information works, we have a notebook for each benchmark letting you inspect important parts about the creating and run process. These notebooks are named '*benchmark*.ipynb', located in the 'benchmark_notebooks' directory, and are meant as an introduction to each specific domain.

## Doing DAC by RL

DAC by RL has been the most used DAC approach, therefore we also include two scripts of how to integrate the environments in RL loops:
- 'tabular_rl.py' uses a simple tabular agent with the Luby benchmark
- 'cleanrl_ppo.py' runs a deep PPO agent on a set of parallel instances of the benchmark of your choice. This is in essence an example of using DACBench in a state-of-the-art RL training script.