import os
import cv2
import time
import numpy as np
import tensorflow as tf

# Load TFLite model
tflite_model_path = "/home/myrios/iot/yolo_bird/best_float32.tflite"
print(f"[INFO] Loading TFLite model from {tflite_model_path}")
interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()

# Get input/output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_shape = tuple(input_details[0]['shape'][1:3])  # (640, 640)

print("[INFO] Model Loaded Successfully")

while True:
    print("[INFO] Capturing image using libcamera-still...")
    
    # Capture an image using libcamera
    os.system("libcamera-still -o frame.jpg --width 640 --height 480 -n")  # -n disables preview

    # Load the captured image
    frame = cv2.imread("frame.jpg")

    if frame is None:
        print("[ERROR] Could not read frame.")
        continue

    print("[INFO] Running inference on captured frame...")

    # Resize and normalize image for TFLite model
    frame_resized = cv2.resize(frame, input_shape)
    input_data = np.expand_dims(frame_resized, axis=0).astype(np.float32)  # Add batch dimension
    input_data = input_data / 255.0  # Normalize to [0,1]

    # Run inference
    interpreter.set_tensor(input_details[0]["index"], input_data)
    interpreter.invoke()

    # Get output tensors
    output = interpreter.get_tensor(output_details[0]["index"])[0]  # Shape: (5, 8400)

    # Extract bounding boxes and confidence scores
    num_boxes = output.shape[1]  # 8400 possible detections
    for i in range(num_boxes):
        confidence = output[4, i]  # 5th value is confidence score
        if confidence > 0.5:  # Confidence threshold
            x_center, y_center, width, height = output[:4, i]

            # Convert center format to (x_min, y_min, x_max, y_max)
            x_min = int((x_center - width / 2) * frame.shape[1])
            y_min = int((y_center - height / 2) * frame.shape[0])
            x_max = int((x_center + width / 2) * frame.shape[1])
            y_max = int((y_center + height / 2) * frame.shape[0])

            # Draw bounding box (Blue) and label
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
            cv2.putText(frame, f"Bird: {confidence:.2f}", (x_min, y_min - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    print("[INFO] Displaying processed frame...")

    # Display the output frame
    cv2.imshow("YOLO Bird Detection", frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("[INFO] Exiting...")
        break

cv2.destroyAllWindows()
