// Observation/seed harness; original search methods remain unchanged.
#include "Sisrs.hpp"
#include <chrono>
#include <limits>
int main(int argc,char**argv){
 if(argc!=2)throw std::invalid_argument("config path required");
 nlohmann::json envelope;std::cin>>envelope;auto p=envelope.at("payload");
 if(p.at("K").get<int>() != p.at("demands").size()-1)throw std::invalid_argument("SISR cohort requires unrestricted fleet K=n");
 auto deadline=envelope.at("deadline_ns").get<long long>();
 auto now=[](){return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();};
 ProblemInstance problem;problem.name="sanitized";problem.dimension=p.at("demands").size();problem.customer_count=problem.dimension-1;problem.capacity=p.at("capacity");problem.depot_index=0;problem.vehicles=problem.customer_count;
 for(int i=0;i<problem.dimension;i++){
  Node n;n.id=i+1;n.x=p["coordinates"][i][0];n.y=p["coordinates"][i][1];n.demand=p["demands"][i];problem.nodes.push_back(n);
 }
 preprocessProblem(problem);
 long long edges=0;
 for(int i=0;i<problem.dimension;i++)for(int j=0;j<problem.dimension;j++){
  double dx=p["coordinates"][i][0].get<double>()-p["coordinates"][j][0].get<double>();
  double dy=p["coordinates"][i][1].get<double>()-p["coordinates"][j][1].get<double>();
  auto expected=(long long)std::floor(std::hypot(dx,dy)+0.5);
  if(expected!=problem.distance_matrix[i][j])throw std::invalid_argument("EUC2D_MISMATCH");
  edges++;
 }
 std::cout<<nlohmann::json{{"event","metric_verified"},{"edges",edges}}.dump()<<std::endl;
 Sisrs solver(problem,argv[1],false);solver.setSeed(p.at("seed").get<unsigned long>());
 solver.shouldStop=[&](){return now()>=deadline;};
 long long best=std::numeric_limits<long long>::max();
 solver.observer=[&](const Solution& s){
  if(now()>=deadline||!s.absent_customers.empty())return;
  nlohmann::json routes=nlohmann::json::array();
  std::vector<int> counts(problem.dimension,0);long long cost=0;
  for(auto&r:s.routes){
   if(r.customers.empty())continue;
   nlohmann::json route=nlohmann::json::array();route.push_back(0);int prev=0,load=0;
   for(auto node:r.customers){if(node==0||node<0||node>=problem.dimension)throw std::invalid_argument("bad customer");counts[node]++;load+=problem.nodes[node].demand;cost+=problem.distance_matrix[prev][node];route.push_back(node);prev=node;}
   if(load>problem.capacity)return;cost+=problem.distance_matrix[prev][0];route.push_back(0);routes.push_back(route);
  }
  for(int i=1;i<problem.dimension;i++)if(counts[i]!=1)return;
  if(cost!=s.total_cost)throw std::invalid_argument("cost mismatch");
  if(cost<best){std::cout<<nlohmann::json{{"event","incumbent"},{"routes",routes},{"cost",cost}}.dump()<<std::endl;best=cost;}
 };
 solver.localSearch();
}
