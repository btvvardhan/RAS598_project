#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
from ultralytics import YOLO
from visualization_msgs.msg import Marker
from geometry_msgs.msg import PointStamped
from tf2_ros import Buffer, TransformListener
from tf2_geometry_msgs import do_transform_point
import cv2
import numpy as np
import os
import csv

class RockLocator(Node):
    def __init__(self):
        super().__init__('rock_locator')
        self.bridge = CvBridge()
        self.model = YOLO('/home/vijay/ros2_project/src/ros2_project/ros2_project/ros2_project/best.pt')

        self.rgb_sub = self.create_subscription(Image, '/synced/rgb_camera', self.image_callback, 10)
        self.depth_sub = self.create_subscription(Image, '/synced/depth_camera', self.depth_callback, 10)
        self.caminfo_sub = self.create_subscription(CameraInfo, '/synced/rgb_camera/camera_info', self.caminfo_callback, 10)

        self.marker_pub = self.create_publisher(Marker, '/rock_marker', 10)
        self.image_pub = self.create_publisher(Image, '/final_image', 10)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.camera_info = None
        self.latest_depth = None

        # Setup CSV logging
        log_path = os.path.expanduser('~/rock_detections_log.csv')
        self.csv_file = open(log_path, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['timestamp', 'label', 'confidence', 'x', 'y', 'z'])  # header

        self.get_logger().info(f"📄 Logging rock detections to: {log_path}")

    def caminfo_callback(self, msg):
        self.camera_info = msg

    def depth_callback(self, msg):
        self.latest_depth = msg

    def image_callback(self, msg):
        if self.camera_info is None or self.latest_depth is None:
            self.get_logger().warn("Missing camera info or depth image.")
            return

        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        depth_image = self.bridge.imgmsg_to_cv2(self.latest_depth, desired_encoding='passthrough')

        results = self.model(cv_image)
        fx = self.camera_info.k[0]
        fy = self.camera_info.k[4]
        cx = self.camera_info.k[2]
        cy = self.camera_info.k[5]

        boxes = results[0].boxes
        for i in range(len(boxes)):
            x1, y1, x2, y2 = map(int, boxes.xyxy[i].tolist())
            cls_id = int(boxes.cls[i].item()) if boxes.cls is not None else -1
            conf = float(boxes.conf[i].item()) if boxes.conf is not None else 0.0

            # Draw the bounding box
            label = self.model.names[cls_id] if cls_id in self.model.names else f'class_{cls_id}'
            cv2.rectangle(cv_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(cv_image, f'{label} {conf:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 0), 2)

            u = int((x1 + x2) / 2)
            v = int((y1 + y2) / 2)

            if u < 0 or v < 0 or v >= depth_image.shape[0] or u >= depth_image.shape[1]:
                self.get_logger().warn(f"Invalid pixel: {u}, {v}")
                continue

            Z = float(depth_image[v, u])
            if Z == 0.0 or np.isnan(Z):
                self.get_logger().warn(f"Invalid depth at {u},{v}")
                continue

            X = (u - cx) * Z / fx
            Y = (v - cy) * Z / fy

            point_cam = PointStamped()
            point_cam.header.frame_id = self.camera_info.header.frame_id
            point_cam.header.stamp = msg.header.stamp
            point_cam.point.x = X
            point_cam.point.y = Y
            point_cam.point.z = Z

            try:
                tf = self.tf_buffer.lookup_transform('world', point_cam.header.frame_id, rclpy.time.Time())
                point_world = do_transform_point(point_cam, tf)

                marker = Marker()
                marker.header.frame_id = 'world'
                marker.header.stamp = self.get_clock().now().to_msg()
                marker.type = Marker.SPHERE
                marker.pose.position = point_world.point
                marker.scale.x = marker.scale.y = marker.scale.z = 0.3
                marker.color.r = 1.0
                marker.color.g = 0.3
                marker.color.b = 0.2
                marker.color.a = 1.0
                marker.id = i

                self.marker_pub.publish(marker)

                timestamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

                self.get_logger().info(f"[Rock {i}] {label}: {conf:.2f} @ "
                                       f"({point_world.point.x:.2f}, {point_world.point.y:.2f}, {point_world.point.z:.2f})")

                self.csv_writer.writerow([
                    f"{timestamp:.6f}",
                    label,
                    f"{conf:.2f}",
                    f"{point_world.point.x:.3f}",
                    f"{point_world.point.y:.3f}",
                    f"{point_world.point.z:.3f}"
                ])

            except Exception as e:
                self.get_logger().warn(f"TF transform failed: {e}")

        # 🔄 Publish annotated image
        annotated_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8')
        annotated_msg.header = msg.header
        self.image_pub.publish(annotated_msg)

    def destroy_node(self):
        self.csv_file.close()
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = RockLocator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

