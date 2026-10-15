// Small CPU-only concurrent API reproducer, no ROS nodes, DDS, or simulation.
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <tf2_ros/buffer.h>
#include <tf2_ros/create_timer_interface.h>
using namespace std::chrono_literals;
class NoExpiryTimers : public tf2_ros::CreateTimerInterface {
  std::atomic<uint64_t> next{1};
public:
  tf2_ros::TimerHandle createTimer(rclcpp::Clock::SharedPtr, const tf2::Duration &,
                                  tf2_ros::TimerCallbackType) override { return next++; }
  void cancel(const tf2_ros::TimerHandle &) override {}
  void reset(const tf2_ros::TimerHandle &) override {}
  void remove(const tf2_ros::TimerHandle &) override {}
};
int main() {
  auto clock=std::make_shared<rclcpp::Clock>(RCL_SYSTEM_TIME);
  tf2_ros::Buffer buffer(clock);
  buffer.setCreateTimerInterface(std::make_shared<NoExpiryTimers>());
  std::atomic<int64_t> tick{1000};
  std::atomic<uint64_t> writes{0},requests{0},callbacks{0};
  std::atomic<bool> stop{false};
  std::thread writer([&] {
    while(!stop) {
      auto n=++tick;
      geometry_msgs::msg::TransformStamped t;
      t.header.frame_id="map";t.child_frame_id="base";t.transform.rotation.w=1;
      t.header.stamp.sec=n/1000;t.header.stamp.nanosec=(n%1000)*1000000;
      buffer.setTransform(t,"urp_cpu_repro"); ++writes;
      std::this_thread::sleep_for(100us);
    }
  });
  std::thread reader([&] {
    while(!stop) {
      buffer.waitForTransform("map","base",tf2::TimePoint(std::chrono::milliseconds(tick+1)),
        tf2::durationFromSec(10),[&](const auto &){++callbacks;});
      ++requests;std::this_thread::sleep_for(100us);
    }
  });
  for(int i=0;i<10;++i) {
    std::this_thread::sleep_for(1s);
    std::cout<<"second="<<i+1<<" writes="<<writes<<" requests="<<requests<<" callbacks="<<callbacks<<std::endl;
  }
  stop=true; writer.join();reader.join();
  std::cout<<"CLEAN_EXIT"<<std::endl;
}
