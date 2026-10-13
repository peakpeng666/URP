# Title
Uninitialized member `ar_nbArcsDistance` is read before assignment in `Params::preleveDonnees` (type-34 sanity check)

# Body
## Description
`Params.h` declares `int ar_nbArcsDistance;` without constructor initialization. In `Params::preleveDonnees`, the NEARP-TP (type 34) branch performs a sanity check **before** the member is assigned:

```cpp
// Params.cpp (~L205)
if (ar_nbArcsDistance < 0 || ar_nbArcsDistance > 1000000)
    throw string("PARSING ERROR : Incorrect number of arcs. ...");
...
// Params.cpp (~L209)
ar_nbArcsDistance = 1 + totalArcs + 2*totalEdges ;
```

Reading the uninitialized member is undefined behavior. Whether a valid type-34 instance loads depends on leftover stack/heap contents: we observed intermittent `PARSING ERROR : Incorrect number of arcs.` throws on **valid** NEARP-TP instances, including the shipped `Instances/MCGRP-TP/BHW1-TP.dat`.

## Reproduce
Build with `-DTURN_PENALTIES` (g++ 16.1.0, WinLibs UCRT, Windows x64) and load a valid type-34 instance repeatedly; the throw is intermittent depending on prior memory contents.

## Workaround we use (no source change)
In gdb: `break Params.cpp:204`, `run`, `set variable ar_nbArcsDistance = 0`, `continue`.

## Suggested fix
Initialize `ar_nbArcsDistance = 0;` in the `Params` constructor (or move the sanity check after the assignment at L209).

## Secondary observation
With the same g++ 16.1.0, `-O1/-O2/-O3` builds segfault during optimization on type-30/type-34 instances that run fine at `-O0` (the shipped makefile defaults to `-O3`). Possibly UB-sensitive code; reproducible on request.
