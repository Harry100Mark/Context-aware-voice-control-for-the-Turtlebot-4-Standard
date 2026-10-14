import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist, PoseStamped
import json
import time
import math
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

class ActionExecutorNode(Node):
    def __init__(self):
        super().__init__('action_executor')
        self.subscription = self.create_subscription(
            String,
            '/action_command',
            self.command_callback,
            10)
        self.stop_subscription = self.create_subscription(
            String,
            '/action_stop',
            self.stop_callback,
            10)
        self.cmd_vel_publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        # Annahme: Bumper-Topic mit String-Nachricht ("front", "left", "right" oder leer)
        self.bumper_subscription = self.create_subscription(
            String,
            '/bumper',
            self.bumper_callback,
            10)
        self.bumper_triggered = False
        self.bumper_side = ""  # "front", "left", "right"
        self.navigator: BasicNavigator | None = None
        self.active_action = False
        self.nav_goal_pose = None
        self.nav_start_time = None
        self.nav_timeout = 120.0
        self.nav_monitor_timer = None
        self._init_navigator()

    def _init_navigator(self):
        try:
            self.navigator = BasicNavigator()
            time.sleep(2.0)  # Fallback-Pause
        except Exception as e:
            self.navigator = None

    def command_callback(self, msg):
        if self.active_action and "Stoppen" not in msg.data:
            return  # Ignoriere, wenn aktiv, außer Stop (aber Stop über separates Topic)
        try:
            action_json = json.loads(msg.data)
            if not isinstance(action_json, dict):
                return
            action = action_json.get('Aktion')
            params = action_json.get('Parameter', {})
            if action == 'Distanz_zurücklegen':
                self.execute_distance(params)
            elif action == 'Drehen':
                self.execute_turn(params)
            elif action == 'Navigieren':
                self.execute_navigate(params)
            elif action == 'Stoppen':
                self.stop_action()
            else:
                pass
        except json.JSONDecodeError:
            pass

    def stop_callback(self, msg):
        if msg.data == "stop":
            self.stop_action()

    def bumper_callback(self, msg):
        self.bumper_side = msg.data
        self.bumper_triggered = bool(self.bumper_side)

    def stop_action(self):
        if self.navigator and self.navigator.isTaskComplete() is False:
            self.navigator.cancelTask()
        twist = Twist()
        self.cmd_vel_publisher.publish(twist)
        self.active_action = False
        self.nav_goal_pose = None
        self.bumper_triggered = False
        self.get_logger().info('Aktion gestoppt.')

    def execute_distance(self, params):
        self.active_action = True
        speed = float(params.get('Lineargeschwindigkeit', 0.5))
        distance = float(params.get('Distanz', 0.0))
        forward = params.get('soll_Vorwärts', True)
        if speed <= 0 or distance <= 0:
            self.active_action = False
            return
        self.get_logger().info(f'Distanz zurücklegen: {distance} m, forward={forward}')
        twist = Twist()
        twist.linear.x = speed if forward else -speed
        duration = distance / speed
        start_time = time.time()
        rate = 0.1
        while time.time() - start_time < duration:
            if self.bumper_triggered:
                twist.linear.x = 0.0
                self.cmd_vel_publisher.publish(twist)
                self.get_logger().info('Bumper aktiviert - Distanz zurücklegen gestoppt.')
                self.active_action = False
                self.bumper_triggered = False
                return
            self.cmd_vel_publisher.publish(twist)
            time.sleep(rate)
        twist.linear.x = 0.0
        self.cmd_vel_publisher.publish(twist)
        self.active_action = False
        self.get_logger().info('Distanz zurückgelegt.')

    def execute_turn(self, params):
        self.active_action = True
        angular_speed_deg = float(params.get('Winkelgeschwindigkeit', 10.0))
        angle_deg = float(params.get('Winkel', 0.0))
        clockwise = params.get('im_Uhrzeigersinn', False)
        if angular_speed_deg <= 0 or angle_deg <= 0:
            self.active_action = False
            return
        self.get_logger().info(f'Drehen: {angle_deg} Grad, clockwise={clockwise}')
        angular_speed_rad = math.radians(angular_speed_deg)
        angle_rad = math.radians(angle_deg)
        twist = Twist()
        twist.angular.z = -angular_speed_rad if clockwise else angular_speed_rad
        duration = angle_rad / angular_speed_rad
        start_time = time.time()
        rate = 0.1
        while time.time() - start_time < duration:
            self.cmd_vel_publisher.publish(twist)
            time.sleep(rate)
        twist.angular.z = 0.0
        self.cmd_vel_publisher.publish(twist)
        self.active_action = False
        self.get_logger().info('Drehen abgeschlossen.')

    def execute_navigate(self, params):
        self.active_action = True
        target_pos = params.get('Zielposition', {})
        x = float(target_pos.get('x', 0.0))
        y = float(target_pos.get('y', 0.0))
        zielorientierung_deg = params.get('Zielorientierung')
        yaw_quat = (0.0, 0.0, 0.0, 1.0)
        if zielorientierung_deg is not None:
            deg = float(zielorientierung_deg) % 360.0
            yaw = math.radians(deg)
            yaw_quat = (0.0, 0.0, math.sin(yaw/2.0), math.cos(yaw/2.0))
        self.get_logger().info(f'Navigiere zu: x={x}, y={y}')
        if self.navigator is None:
            self.active_action = False
            return
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = x
        goal_pose.pose.position.y = y
        goal_pose.pose.orientation.x = yaw_quat[0]
        goal_pose.pose.orientation.y = yaw_quat[1]
        goal_pose.pose.orientation.z = yaw_quat[2]
        goal_pose.pose.orientation.w = yaw_quat[3]
        self.nav_goal_pose = goal_pose
        self._start_navigation()
        if self.nav_monitor_timer is None:
            self.nav_monitor_timer = self.create_timer(0.5, self._nav_monitor_cb)

    def _start_navigation(self):
        self.navigator.goToPose(self.nav_goal_pose)
        self.nav_start_time = time.time()

    def _nav_monitor_cb(self):
        if not self.active_action or self.navigator is None or self.nav_goal_pose is None:
            return
        if (time.time() - self.nav_start_time) > self.nav_timeout:
            self.navigator.cancelTask()
            self.get_logger().info('Navigation Timeout.')
            self._nav_reset()
            return
        if self.bumper_triggered:
            self.get_logger().info(f'Bumper aktiviert ({self.bumper_side}) - Starte Recovery.')
            self.navigator.cancelTask()
            # Recovery: 10cm zurück (rückwärts fahren)
            self._drive_distance(-0.10, 0.2)  # -0.1m bei 0.2 m/s
            # 40 Grad wegdrehen (je nach Seite: left -> counterclockwise, right -> clockwise, front -> z.B. clockwise)
            clockwise = self.bumper_side == "left"  # Wegdrehen: wenn left bumper, dreh clockwise weg
            if self.bumper_side == "front":
                clockwise = True  # Beliebig
            self._turn_angle(40.0, 30.0, clockwise)  # 40 Grad bei 30 deg/s
            # 5cm vorwärts
            self._drive_distance(0.05, 0.2)
            self.bumper_triggered = False
            self.bumper_side = ""
            # Navigation fortsetzen
            self._start_navigation()
            return
        done = self.navigator.isTaskComplete()
        if not done:
            return
        result = self.navigator.getResult()
        if result == TaskResult.SUCCEEDED:
            self.get_logger().info('Navigation erfolgreich.')
        elif result == TaskResult.FAILED:
            self.get_logger().info('Navigation fehlgeschlagen.')
        self._nav_reset()

    def _nav_reset(self):
        self.active_action = False
        self.nav_goal_pose = None
        self.nav_start_time = None

    def _drive_distance(self, distance: float, speed: float):
        forward = distance > 0
        abs_dist = abs(distance)
        twist = Twist()
        twist.linear.x = speed if forward else -speed
        duration = abs_dist / speed
        start_time = time.time()
        rate = 0.1
        while time.time() - start_time < duration:
            self.cmd_vel_publisher.publish(twist)
            time.sleep(rate)
        twist.linear.x = 0.0
        self.cmd_vel_publisher.publish(twist)

    def _turn_angle(self, angle_deg: float, angular_speed_deg: float, clockwise: bool):
        angular_speed_rad = math.radians(angular_speed_deg)
        angle_rad = math.radians(angle_deg)
        twist = Twist()
        twist.angular.z = -angular_speed_rad if clockwise else angular_speed_rad
        duration = angle_rad / angular_speed_rad
        start_time = time.time()
        rate = 0.1
        while time.time() - start_time < duration:
            self.cmd_vel_publisher.publish(twist)
            time.sleep(rate)
        twist.angular.z = 0.0
        self.cmd_vel_publisher.publish(twist)

def main(args=None):
    rclpy.init(args=args)
    node = ActionExecutorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()