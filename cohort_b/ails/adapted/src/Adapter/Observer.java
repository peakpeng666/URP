package Adapter;
import Solution.Solution;
import Solution.Node;
import Solution.Route;
public final class Observer {
 public static void emit(Solution s) {
  if(!s.feasible())return;
  StringBuilder b=new StringBuilder("{\"event\":\"incumbent\",\"cost\":"+s.f+",\"routes\":[");
  boolean first=true;
  for(int i=0;i<s.numRoutes;i++){
   Route r=s.routes[i];if(r.first.next==r.first)continue;
   if(!first)b.append(',');first=false;b.append("[0");Node n=r.first.next;int guard=0;
   while(n!=r.first){if(++guard>s.getSize())throw new RuntimeException("cycle");b.append(',').append(n.name);n=n.next;}
   b.append(",0]");
  }
  b.append("]}");System.out.println(b);System.out.flush();
 }
}
