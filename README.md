# Context-aware-voice-control-for-the-Turtlebot-4-Standard

### Running the simulation

1. Open 2 new terminals and source them:

colcon build

source /opt/ros/humble/setup.bash

source ~/ros2_ws/install/setup.bash

3. Run the following commands in these 2 terminals

ros2 run prompt prompt_google2

ros2 run chat chat --stu

NOTE:

Make sure to use a valid API_KEY for the Gemini 2.5 Pro API

This can be done by running the following 2 commands before running the prompt_google2 node:

export AI_PROVIDER=google

export GOOGLE_API_KEY='YOUR_API_KEY'

### Execute on the real Turtlebot 4 Standard

1. create a new ROS 2 workspace on the turtlebot

2. copy the audio_recorder and action_executor packages in your new workspace on the turtlebot

3. Start the following nodes on your turtlebot for the localization and navigation

ros2 launch turtlebot4_navigation localization.launch.py map:=/home/harry/ros2_ws/src/map/map.yaml

ros2 launch turtlebot4_navigation nav2.launch.py

ros2 launch turtlebot4_viz view_robot.launch.py

5. Open 4 new terminals and source them (2 on your computer and 2 on the turtlebot):

colcon build

source /opt/ros/humble/setup.bash

source ~/ros2_ws/install/setup.bash

7. run the following node in this order:

ros2 run audio_recorder audio_recorder

ros2 run transcriber transcriber_assembly

ros2 run prompt prompt_google2

ros2 run action_executor action_executor
