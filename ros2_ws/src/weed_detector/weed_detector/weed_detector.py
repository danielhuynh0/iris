#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np
from keras.models import load_model

class WeedDetector(Node):
    def init(self):
        super().init('weed_detector')

        self.declare_parameter('model_path', 'deepweeds_binary_final.h5')
        model_path = self.get_parameter('model_path').get_parameter_value().string_value


        self.model = load_model(model_path)
        self.get_logger().info(f"Weed detection model loaded from {model_path}")


        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image,
            '/camera/rgb/image_raw',
            self.image_callback,
            10
        )

        self.result_pub = self.create_publisher(String, '/weed_detection_result', 10)

    def image_callback(self, msg):
        try:
            cv_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge Error: {str(e)}")
            return

        img_resized = cv2.resize(cv_img, (224, 224))
        img_array = img_resized.astype(np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        prediction = self.model.predict(img_array)[0][0]
        label = "Weed" if prediction > 0.5 else "Not Weed"
        confidence = prediction if prediction > 0.5 else 1 - prediction
        result_str = f"{label} ({confidence * 100:.2f}%)"
        self.result_pub.publish(String(data=result_str))
        self.get_logger().info(f"Prediction: {result_str}")

        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)  

            cv2.rectangle(cv_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(cv_img, "Main Object", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)

        cv2.imshow("Main Object Localization", cv_img)
        cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = WeedDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()