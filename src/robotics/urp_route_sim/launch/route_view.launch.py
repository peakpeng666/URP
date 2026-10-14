from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    share = get_package_share_directory('urp_route_sim')
    return LaunchDescription([
        SetEnvironmentVariable('ROS_LOCALHOST_ONLY', '1'),
        DeclareLaunchArgument('scene_file', description='Local exported route-scene v1 JSON'),
        DeclareLaunchArgument('calibration_file', default_value=''),
        DeclareLaunchArgument('rviz', default_value='true'),
        Node(package='urp_route_sim', executable='route_markers', output='screen',
             parameters=[{'scene_file':LaunchConfiguration('scene_file'),
                          'calibration_file':LaunchConfiguration('calibration_file')}]),
        Node(package='rviz2', executable='rviz2',
             arguments=['-d',os.path.join(share,'config','route_view.rviz')],
             condition=IfCondition(LaunchConfiguration('rviz'))),
    ])
