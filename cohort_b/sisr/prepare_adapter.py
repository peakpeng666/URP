"""Prepare explicit observation/seed adapter; does not compile or run solver.
Copies original to adapted/, keeping original source/algorithm logic available.
"""
from pathlib import Path
import shutil,difflib,json,hashlib
root=Path(__file__).resolve().parent;original=root/'cvrp';adapted=root/'adapted'
if adapted.exists():raise SystemExit('adapted already exists; refusing overwrite')
shutil.copytree(original,adapted)
h=adapted/'src/Sisrs.hpp';s=h.read_text();s=s.replace('#include <random>','#include <random>\n#include <functional>');s=s.replace('public:\n    // Best discovered solution','public:\n    void setSeed(unsigned long seed) { gen.seed(seed); }\n    std::function<void(const Solution&)> observer;\n    std::function<bool()> shouldStop;\n    // Best discovered solution');h.write_text(s)
c=adapted/'src/Sisrs.cpp';s=c.read_text();s=s.replace('improvements.push_back(std::make_pair(0, sol_best->total_cost));','improvements.push_back(std::make_pair(0, sol_best->total_cost));\n    if (observer) observer(*sol_best);');s=s.replace('for (int i = 0; i < n_iter; ++i)\n    {','for (int i = 0; i < n_iter; ++i)\n    {\n        if (shouldStop && shouldStop()) break;');s=s.replace('improvements.push_back(std::make_pair(i + 1, sol_best->total_cost));','improvements.push_back(std::make_pair(i + 1, sol_best->total_cost));\n                    if (observer) observer(*sol_best);');c.write_text(s)
patch=[]
for name in ['src/Sisrs.hpp','src/Sisrs.cpp']:
 patch+=list(difflib.unified_diff((original/name).read_text().splitlines(True),(adapted/name).read_text().splitlines(True),fromfile='original/'+name,tofile='adapted/'+name))
(root/'observer_seed.patch').write_text(''.join(patch))
