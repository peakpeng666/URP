#include <cassert>
#include <functional>
#include <iostream>
#include <map>
#include <tf2_ros/buffer.h>
#include <tf2_ros/create_timer_interface.h>

class ManualTimers : public tf2_ros::CreateTimerInterface {
public:
  uint64_t next=1;
  std::map<uint64_t,tf2_ros::TimerCallbackType> callbacks;
  tf2_ros::TimerHandle createTimer(rclcpp::Clock::SharedPtr, const tf2::Duration &,
      tf2_ros::TimerCallbackType callback) override {
    auto id=next++;callbacks[id]=callback;return id;
  }
  void cancel(const tf2_ros::TimerHandle &) override {}
  void reset(const tf2_ros::TimerHandle &) override {}
  void remove(const tf2_ros::TimerHandle & id) override { callbacks.erase(id); }
  void fire(uint64_t id) { auto callback=callbacks.at(id); callback(id); }
};
int main() {
  auto timers=std::make_shared<ManualTimers>();
  tf2_ros::Buffer buffer(std::make_shared<rclcpp::Clock>(RCL_SYSTEM_TIME));
  buffer.setCreateTimerInterface(timers);
  auto put=[&](int sec){
    geometry_msgs::msg::TransformStamped t;
    t.header.frame_id="map";t.child_frame_id="base";
    t.header.stamp.sec=sec;t.transform.rotation.w=1;buffer.setTransform(t,"semantics");
  };
  auto at=[](int sec){return tf2::TimePoint(std::chrono::seconds(sec));};
  put(1);
  int calls=0;
  auto immediate=buffer.waitForTransform("map","base",at(1),tf2::durationFromSec(1),
    [&](auto future){assert(future.get().header.stamp.sec==1);++calls;});
  assert(calls==1 && immediate.get().header.stamp.sec==1 && timers->callbacks.empty());
  auto deferred=buffer.waitForTransform("map","base",at(2),tf2::durationFromSec(1),
    [&](auto future){assert(future.get().header.stamp.sec==2);++calls;});
  assert(calls==1 && timers->callbacks.size()==1);
  put(2);
  assert(calls==2 && deferred.get().header.stamp.sec==2 && timers->callbacks.empty());
  bool timeout=false;
  auto expired=buffer.waitForTransform("map","base",at(3),tf2::durationFromSec(1),
    [&](auto future){try{future.get();}catch(const tf2::TimeoutException &){timeout=true;}++calls;});
  timers->fire(timers->callbacks.begin()->first);
  assert(timeout && calls==3 && timers->callbacks.empty());
  put(3);assert(calls==3);
  std::cout<<"PASS immediate, deferred, timeout and no callback after timeout"<<std::endl;
}
