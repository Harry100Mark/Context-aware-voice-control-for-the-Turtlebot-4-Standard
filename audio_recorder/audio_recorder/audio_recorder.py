import pyaudio
import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import ByteMultiArray
from geometry_msgs.msg import PoseStamped, Twist
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from tf2_ros import Buffer, TransformListener, LookupException, ConnectivityException, ExtrapolationException
import rclpy.time
import rclpy.duration
import time

try:
    from tuning import Tuning
except ImportError:
    Tuning = None

try:
    from nav2_simple_commander.robot_navigator import BasicNavigator
except Exception:
    BasicNavigator = None

class AudioRecorderNode(Node):
    def __init__(self):
        super().__init__('audio_recorder')
        self.publisher = self.create_publisher(ByteMultiArray, '/audio_file', 10)
        self.pose_publisher = self.create_publisher(PoseStamped, '/audio_record_pose', 10)

        self.p = pyaudio.PyAudio()
        self.device_index = None
        for i in range(self.p.get_device_count()):
            if 'ReSpeaker 4 Mic Array' in self.p.get_device_info_by_index(i).get('name'):
                self.device_index = i
                break
        if self.device_index is None:
            self.get_logger().error('ReSpeaker 4 Mic Array device not found')
            return

        self.rate = 16000
        self.channels = 6
        self.width = 2
        self.chunk = 1024

        # Initialize ReSpeaker tuning interface for hardware VAD
        if Tuning is None:
            self.get_logger().error('tuning module not installed - cannot perform hardware VAD')
            return
        try:
            self.tuning = Tuning()
            self.get_logger().info('ReSpeaker hardware VAD initialized')
        except Exception as e:
            self.get_logger().error(f'Failed to initialize tuning interface: {e}')
            return

        self.recording = False
        self.frames = []  # List of mono byte frames
        self.last_speech_time = time.time()

        self.stream = self.p.open(
            rate=self.rate,
            format=self.p.get_format_from_width(self.width),
            channels=self.channels,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk
        )

        self.timer = self.create_timer(0.1, self.audio_callback)

        # For pose
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self, spin_thread=True)
        self.last_amcl_pose = None
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self._amcl_pose_cb, 10)
        self.navigator = None
        if BasicNavigator is not None:
            try:
                self.navigator = BasicNavigator()
            except Exception as e:
                self.get_logger().warn(f'BasicNavigator could not be initialized: {e}')

        # For checking if moving
        self.current_twist = Twist()
        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)

    def audio_callback(self):
        # Check hardware VAD status from ReSpeaker
        try:
            is_speech = self.tuning.is_voice()
        except Exception as e:
            self.get_logger().warn(f'Failed to read VAD status: {e}')
            is_speech = False

        now = time.time()
        
        if is_speech:
            self.last_speech_time = now

        # Read audio data
        raw_chunk = self.stream.read(self.chunk, exception_on_overflow=False)
        samples_all = np.frombuffer(raw_chunk, dtype=np.int16)
        if samples_all.size == 0 or samples_all.size % self.channels != 0:
            return
        # Use channel 5: the processed output from XMOS chip (noise reduction, echo cancellation)
        mono = samples_all.reshape(-1, self.channels)[:, 5].copy()
        byte_mono = mono.tobytes()

        # Start recording on speech detection
        if not self.recording and is_speech:
            if self.is_not_moving():
                self._publish_current_pose()
                self.recording = True
                self.frames = []
                self.get_logger().info('Recording started (hardware VAD)')
            else:
                return  # Do not start if moving

        # Collect frames while recording
        if self.recording:
            self.frames.append(byte_mono)

        # Stop recording after silence threshold
        if self.recording and (now - self.last_speech_time) >= 1.0:
            if self.is_not_moving():
                self._publish_audio()
                self.get_logger().info('Recording stopped and published')
            else:
                self.get_logger().info('Recording stopped but not published (robot moving)')
            self.recording = False
            self.frames = []

    def _publish_audio(self):
        if not self.frames:
            return
        raw_mono = b''.join(self.frames)
        msg = ByteMultiArray()
        msg.data = raw_mono
        self.publisher.publish(msg)

    def is_not_moving(self):
        return abs(self.current_twist.linear.x) < 0.01 and abs(self.current_twist.angular.z) < 0.01

    def _odom_cb(self, msg: Odometry):
        self.current_twist = msg.twist.twist

    def _publish_current_pose(self):
        pose = self._get_pose_via_navigator() or self._get_pose_via_amcl() or self._get_pose_via_tf()
        if pose is None:
            self.get_logger().warn('Could not get current pose')
            return
        self.pose_publisher.publish(pose)

    def _get_pose_via_navigator(self) -> PoseStamped | None:
        if self.navigator is None:
            return None
        for name in ['getCurrentPose', 'get_current_pose']:
            if hasattr(self.navigator, name):
                try:
                    return getattr(self.navigator, name)()
                except Exception:
                    pass
        return None

    def _amcl_pose_cb(self, msg: PoseWithCovarianceStamped):
        self.last_amcl_pose = msg

    def _get_pose_via_amcl(self) -> PoseStamped | None:
        if self.last_amcl_pose is None:
            return None
        ps = PoseStamped()
        ps.header = self.last_amcl_pose.header
        ps.pose = self.last_amcl_pose.pose.pose
        return ps

    def _get_pose_via_tf(self) -> PoseStamped | None:
        try:
            transform = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.3))
            ps = PoseStamped()
            ps.header = transform.header
            ps.pose.position.x = transform.transform.translation.x
            ps.pose.position.y = transform.transform.translation.y
            ps.pose.position.z = transform.transform.translation.z
            ps.pose.orientation = transform.transform.rotation
            return ps
        except (LookupException, ConnectivityException, ExtrapolationException):
            return None

    def destroy_node(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = AudioRecorderNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()