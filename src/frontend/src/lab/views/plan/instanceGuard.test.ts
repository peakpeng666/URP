import { describe,it,expect } from 'vitest';
import { parseEditableInstance } from './planModel';

describe('instance editor rendering safety',()=>{
  const graph={capacity:2,depot:0,coordinates:{'0':[0,0],'1':[1,0]},arcs:[[0,1,100]],customers:[{id:0,node:1,demand:1}]};
  const cvrp={capacity:2,depot:0,coordinates:[[0,0],[1,0]],demands:[0,1]};
  it('never renders old graph coordinates as a CVRP point array after a scenario switch',()=>{
    expect(parseEditableInstance(JSON.stringify(graph),'turn_routing')).toEqual(graph);
    expect(parseEditableInstance(JSON.stringify(graph),'euclidean_cvrp')).toBeNull();
    expect(parseEditableInstance(JSON.stringify(cvrp),'euclidean_cvrp')).toEqual(cvrp);
    expect(parseEditableInstance(JSON.stringify(cvrp),'turn_routing')).toBeNull();
  });
  it('keeps valid JSON with missing or malformed task fields out of the form',()=>{
    for(const value of ['{}','null','[]','{"coordinates":{}}',JSON.stringify({...graph,customers:[null]})])
      expect(parseEditableInstance(value,'turn_routing')).toBeNull();
  });
});
