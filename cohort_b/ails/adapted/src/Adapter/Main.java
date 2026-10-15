package Adapter;
import SearchMethod.InputParameters;
import SearchMethod.AILSII;
import Data.Instance;
import Data.Point;
public final class Main {
 public static void main(String[] args) {
  // file and seconds only. Reference objective/route arguments are forbidden.
  if(args.length!=2)throw new IllegalArgumentException("expected sanitized.vrp seconds");
  InputParameters reader=new InputParameters();
  reader.readingInput(new String[]{"-file",args[0],"-rounded","true","-limit",args[1],"-stoppingCriterion","Time"});
  Instance instance=new Instance(reader);Point[] pts=instance.getPoints();long edges=0;
  for(int i=0;i<pts.length;i++)for(int j=0;j<pts.length;j++){
   long expected=(long)Math.floor(Math.hypot(pts[i].x-pts[j].x,pts[i].y-pts[j].y)+0.5);
   if(instance.dist(i,j)!=expected)throw new IllegalArgumentException("EUC2D_MISMATCH "+i+" "+j);
   edges++;
  }
  System.out.println("{\"event\":\"metric_verified\",\"edges\":"+edges+",\"internal_max_routes\":"+instance.getMaxNumberRoutes()+"}");
  reader.getConfig().setVarphi(Math.min(reader.getConfig().getVarphi(),instance.getSize()-1));
  if(Boolean.getBoolean("urp.metricOnly"))return;
  AILSII solver=new AILSII(instance,reader);solver.setPrint(false);solver.search();Observer.emit(solver.getBestSolution());
 }
}
