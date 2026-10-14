import numpy as np

# Define the source points (from Bild A) in homogeneous coordinates
# src_x = [689, 315, 0] cm
# src_y = [654, 0, 182] cm
src = np.array([[689, 315, 0],
                [654, 0, 182],
                [1, 1, 1]])  # 3x3 matrix: rows are x, y, 1

# Define the destination points (from Bild B) in homogeneous coordinates
# dst_x = [-3.623839, 3.699600, 3.348589] m
# dst_y = [0.429019, -0.185444, -3.869853] m
dst = np.array([[-3.623839, 3.699600, 3.348589],
                [0.429019, -0.185444, -3.869853],
                [1, 1, 1]])  # 3x3 matrix: rows are x, y, 1

# Compute the transformation matrix T such that dst = T @ src
# T = dst @ np.linalg.inv(src)
T = dst @ np.linalg.inv(src)

# Compute the inverse transformation matrix T_inv
T_inv = np.linalg.inv(T)
T_invi = src @ np.linalg.inv(dst)
print(T_invi)

# Display the results
np.set_printoptions(precision=20, suppress=False)
#print('Transformation matrix T:')
#print(T)
#print('Inverse transformation matrix T_inv:')
#print(T_inv)

# Precomputed transformation matrix T
T = np.array([
    [-4.0255135545355699e-03, -8.8958668663665103e-03, 4.9676367696787045e+00],
    [9.1997013696830821e-03, -4.3214454315924659e-03, -3.0833499314501713e+00],
    [4.3368086899420177e-19, 0.0000000000000000e+00, 1.0000000000000000e+00]
])

# Precomputed inverse transformation matrix T_inv
T_inv = np.array([
    [-4.3547437288959770e+01, 8.9644127324147519e+01, 4.9273206454173476e+02],
    [-9.2705883902784905e+01, -4.0565315898804826e+01, 3.3545209364520503e+02],
    [1.8885690445946579e-17, -3.8876943038163164e-17, 9.9999999999999978e-01]
])

# Function to transform angle from A (degrees) to B (radians)
# Based on research, in ROS 2 with RViz2 and SLAM for Turtlebot 4:
# Angles are in radians, 0 along positive x-axis, increasing counterclockwise to positive y-axis (same convention as in A, but in radians).
def transform_angle_A_to_B(theta_A_deg, T):
    theta_A_rad = np.deg2rad(theta_A_deg)
    v_A = np.array([np.cos(theta_A_rad), np.sin(theta_A_rad)])
    A = T[:2, :2]  # Linear part of T
    v_B = A @ v_A
    angle_B_rad = np.arctan2(v_B[1], v_B[0])
    # Normalize to [0, 2*pi) or (-pi, pi] as needed; here using arctan2 range (-pi, pi]
    return angle_B_rad

# Function to transform angle from B (radians) to A (degrees)
def transform_angle_B_to_A(angle_B_rad, T_inv):
    v_B = np.array([np.cos(angle_B_rad), np.sin(angle_B_rad)])
    A_inv = T_inv[:2, :2]  # Linear part of inverse T
    v_A = A_inv @ v_B
    theta_A_rad = np.arctan2(v_A[1], v_A[0])
    theta_A_deg = np.rad2deg(theta_A_rad)
    return theta_A_deg

# Forward transformation: from A to B
def forward_transformation(x_A, y_A, alpha_A):
    point_A = np.array([x_A, y_A, 1])
    point_B = T @ point_A
    x_B = point_B[0]
    y_B = point_B[1]
    alpha_B = transform_angle_A_to_B(alpha_A, T)
    return x_B, y_B, alpha_B

# Back transformation: from B to A
def back_transformation(x_B, y_B, alpha_B):
    point_B = np.array([x_B, y_B, 1])
    point_A = T_inv @ point_B
    x_A = point_A[0]
    y_A = point_A[1]
    alpha_A = transform_angle_B_to_A(alpha_B, T_inv)
    return x_A, y_A, alpha_A

# Example: Forward transformation
x_A_ex = 689
y_A_ex = 654
alpha_A_ex = 0
x_B_ex, y_B_ex, alpha_B_ex = forward_transformation(x_A_ex, y_A_ex, alpha_A_ex)
#print('Forward transformation example:')
#print(f'x_B: {x_B_ex}, y_B: {y_B_ex}, alpha_B (rad): {alpha_B_ex}')

# Example: Back transformation
x_A_back, y_A_back, alpha_A_back = back_transformation(x_B_ex, y_B_ex, alpha_B_ex)
#print('Back transformation example:')
#print(f'x_A: {x_A_back}, y_A: {y_A_back}, alpha_A (deg): {alpha_A_back}')