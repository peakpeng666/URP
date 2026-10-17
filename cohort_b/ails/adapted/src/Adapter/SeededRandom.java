package Adapter;
import java.util.Random;
import java.util.HashMap;
public final class SeededRandom {
 private static final long seed=Long.parseLong(System.getProperty("urp.seed","0"));
 private static final HashMap<String,Integer> counts=new HashMap<>();
 public static Random next(String label) {
  int count=counts.getOrDefault(label,0);counts.put(label,count+1);
  long hash=0xcbf29ce484222325L;
  for(char c:label.toCharArray()){hash^=c;hash*=0x100000001b3L;}
  return new Random(seed ^ hash ^ (0x9e3779b97f4a7c15L*count));
 }
}
