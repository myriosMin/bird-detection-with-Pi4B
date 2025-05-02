import os
import cv2
import time
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, Response, jsonify, request, send_file
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import mysql.connector
from sense_hat import SenseHat
import csv

# Flask app initialization
app = Flask(__name__)
socketio = SocketIO(app)

# Global variables to track the last notification time (avoid spamming)
last_notification_time = 0
NOTIFICATION_INTERVAL = 30  # Send alerts at most every 30 seconds

# MQTT Configuration (Raspberry Pi is the broker)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883

# Initialize MQTT Client
mqtt_client = mqtt.Client()
arduino_detected_bird = False

# MQTT Callback to receive messages from Arduino
def on_message(client, userdata, msg):
    global arduino_detected_bird
    topic = msg.topic
    payload = msg.payload.decode("utf-8").strip()

    if topic == "buzzer/activated":
        arduino_detected_bird = payload.lower() == "true"
        print(f"[MQTT] Arduino detected bird presence: {arduino_detected_bird}")
        
        # Check if inside bird count > 1 & Arduino also detects bird
        if bird_count > 1 and arduino_detected_bird:
            print("[ALERT] Birds approaching! Notifying staff.")
            socketio.emit("bird_alert", {"message": "Birds approaching! Staff action required."})

# MQTT Connection Callback
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected to broker")
    client.subscribe("buzzer/activated")  # Subscribe to buzzer status updates

# Set up MQTT Callbacks and start loop
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()  # Run MQTT in background thread

# Initialize Sense HAT
sense = SenseHat()

# Load TFLite model
tflite_model_path = "/home/myrios/iot/yolo_bird/best_float32.tflite"
print(f"[INFO] Loading TFLite model from {tflite_model_path}")
interpreter = tf.lite.Interpreter(model_path=tflite_model_path)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
input_shape = tuple(input_details[0]['shape'][1:3])  # (640, 640)
print("[INFO] Model Loaded Successfully")

# Define circular detection zone
frame_width, frame_height = 640, 480
cx_frame, cy_frame = frame_width // 2, frame_height // 2
radius = int(min(frame_width, frame_height) * 0.3)  # Adjustable detection radius

# Store detection data
bird_count = 0
previous_bird_locations = {"inside": [], "outside": []}

# MySQL Insert Function
def insert_into_mysql(timestamp, radius, bird_count_inside, bird_count_outside, bird_locations, pitch, arduino_detected_bird, deterrent_status):
    try:
        db = mysql.connector.connect(
            host="192.168.125.196",  # Min's Mac IP
            user="iot_user",
            password="mmpptt007",
            database="bird_detection"
        )
        cursor = db.cursor()

        sql = """INSERT INTO detections (timestamp, radius, bird_count_inside, bird_count_outside, 
                                         bird_locations, pitch, arduino_detected_bird, deterrent_status)
                 VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)"""
        values = (radius, bird_count_inside, bird_count_outside, str(bird_locations), 1500, arduino_detected_bird, True)

        cursor.execute(sql, values)
        db.commit()
        cursor.close()
        db.close()
        print("[INFO] Data inserted into MySQL.")
    except mysql.connector.Error as err:
        print(f"[ERROR] MySQL Insert Failed: {err}")

def non_maximum_suppression(boxes, scores, threshold=0.4):
    """Applies Non-Maximum Suppression (NMS) to remove overlapping detections."""
    if len(boxes) == 0:
        return [], []

    boxes = np.array(boxes)
    scores = np.array(scores)

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]  # Sort by confidence score (descending)

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        # Compute IoU (Intersection over Union)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter)

        # Keep boxes with IoU below threshold
        order = order[np.where(iou < threshold)[0] + 1]

    return boxes[keep], scores[keep]
    
def update_sense_hat(bird_locations, frame_width, frame_height):
    """Continuously updates the Sense HAT display with live bird positions."""
    sense.clear()

    # Define colors
    red = (255, 0, 0)  # Birds inside the area
    blue = (0, 0, 255)  # Birds outside the area
    white = (255, 255, 255)  # Center of detection zone

    # Scale bird positions to 8x8 grid
    for (cx, cy) in bird_locations["inside"]:
        mapped_x = int((cx / frame_width) * 7)
        mapped_y = int((cy / frame_height) * 7)
        sense.set_pixel(mapped_x, mapped_y, red)

    for (cx, cy) in bird_locations["outside"]:
        mapped_x = int((cx / frame_width) * 7)
        mapped_y = int((cy / frame_height) * 7)
        sense.set_pixel(mapped_x, mapped_y, blue)

    # Display center of detection zone
    sense.set_pixel(4, 4, white)
    
# Flask Routes
@app.route('/')
def home():
    """Render the dashboard."""
    return render_template('index.html')

@app.route('/api/bird_count')
def api_bird_count():
    """API to get current bird count."""
    return jsonify({"bird_count": bird_count})

@app.route('/api/update_radius', methods=['POST'])
def update_radius():
    """Update detection radius via API."""
    global radius
    data = request.json
    if not data or "radius" not in data:
        return jsonify({"error": "Invalid request"}), 400

    # Convert user percentage (0 to 100) to actual radius (90 to 240 pixels)
    user_radius_percentage = float(data["radius"])  # Expecting a value between 0-100
    new_radius = int(90 + (user_radius_percentage / 100) * (240 - 90))  # Map to 90-240 range

    # Ensure the value is within the correct limits
    radius = max(90, min(new_radius, 240))

    # Upload to MQTT
    mqtt_client.publish("bird/detection/range", str(int(radius/3)))
            
    return jsonify({"new_radius": radius, "user_display_value": user_radius_percentage})

def generate_frames():
    """Continuously captures images, runs detection, and streams processed frames."""
    global bird_count, bird_locations

    last_db_update = time.time()

    while True:
        # Capture image using libcamera
        print("[INFO] Capturing image using libcamera-still...")
        os.system("libcamera-still -o frame.jpg --width 640 --height 480 -n")
        frame = cv2.imread("frame.jpg")

        if frame is None:
            print("[ERROR] Could not read frame.")
            continue
        
        print("[INFO] Running inference on captured frame...")
        
        # Preprocess image
        frame_resized = cv2.resize(frame, input_shape)
        input_data = np.expand_dims(frame_resized, axis=0).astype(np.float32) / 255.0  # Normalize

        # Run inference
        interpreter.set_tensor(input_details[0]["index"], input_data)
        interpreter.invoke()
        output = interpreter.get_tensor(output_details[0]["index"])[0]

        # Extract detections
        num_boxes = output.shape[1]
        detected_boxes = []
        detected_scores = []

        for i in range(num_boxes):
            confidence = output[4, i]
            if confidence > 0.5:  # Confidence threshold
                x_center, y_center, width, height = output[:4, i]
                x_min = int((x_center - width / 2) * frame.shape[1])
                y_min = int((y_center - height / 2) * frame.shape[0])
                x_max = int((x_center + width / 2) * frame.shape[1])
                y_max = int((y_center + height / 2) * frame.shape[0])

                detected_boxes.append([x_min, y_min, x_max, y_max])
                detected_scores.append(confidence)
        
        # Apply Non-Maximum Suppression (NMS)
        filtered_boxes, filtered_scores = non_maximum_suppression(detected_boxes, detected_scores, threshold=0.4)
        bird_count = 0  # Reset bird count
        bird_locations = {"inside": [], "outside": []}

        for i, (x_min, y_min, x_max, y_max) in enumerate(filtered_boxes):
            confidence = filtered_scores[i]
            cx, cy = (x_min + x_max) // 2, (y_min + y_max) // 2
            distance = np.sqrt((cx - cx_frame) ** 2 + (cy - cy_frame) ** 2)

            if distance <= radius:
                bird_count += 1
                bird_locations["inside"].append((cx, cy))
                cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            else:
                bird_locations["outside"].append((cx, cy))
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1)

            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
            cv2.putText(frame, f"Bird: {confidence:.2f}", (x_min, y_min - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 0), 2)
        
        # Update Sense HAT display
        update_sense_hat(bird_locations, frame_width, frame_height)

        # Draw circular detection zone
        cv2.circle(frame, (cx_frame, cy_frame), radius, (255, 0, 0), 2)

        # Display bird count
        cv2.putText(frame, f"Birds Approaching: {bird_count}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        print("[INFO] Displaying processed frame...")
    
        # Publish MQTT Data
        mqtt_client.publish("bird/detection/presence", "true" if bird_count > 1 else "false")

        # Insert into MySQL every 10 seconds
        if time.time() - last_db_update >= 10:
            insert_into_mysql(time.time(), radius, len(bird_locations["inside"]), len(bird_locations["outside"]), 
                              bird_locations, 1500, arduino_detected_bird, True)
            last_db_update = time.time()

        # Encode frame for streaming
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Flask route for real-time detection feed."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
@app.route('/api/update_buzzer_pitch', methods=['POST'])
def update_buzzer_pitch():
    """Update buzzer pitch via API."""
    data = request.json
    if not data or "pitch" not in data:
        return jsonify({"error": "Invalid request"}), 400

    # Convert user percentage (0 to 100) to actual buzzer pitch (1500 to 2300 Hz)
    user_pitch_percentage = float(data["pitch"])  # Expecting a value between 0-100
    new_pitch = int(1500 + (user_pitch_percentage / 100) * (2300 - 1500))  # Map to 1500-2300 range

    # Ensure the value is within the correct limits
    pitch = max(1500, min(new_pitch, 2300))

    # Publish the updated pitch to MQTT
    mqtt_client.publish("buzzer/pitch", str())

    return jsonify({"new_pitch": pitch, "user_display_value": user_pitch_percentage})
    
@app.route('/api/update_deterrent_status', methods=['POST'])
def update_deterrent_status():
    """Toggle deterrent system ON/OFF via API."""
    data = request.json
    if not data or "status" not in data:
        return jsonify({"error": "Invalid request"}), 400

    # Convert user input to boolean
    deterrent_status = "true" if data["status"] else "false"

    # Publish the updated deterrent status to MQTT
    mqtt_client.publish("bird/detection/deterrent", deterrent_status)

    return jsonify({"new_status": deterrent_status})
    
@app.route('/api/bird_activity')
def bird_activity():
    """Fetch the last 10 bird detection records from MySQL."""
    try:
        db = mysql.connector.connect(
            host="192.168.125.196",  # Min's Mac's IP
            user="iot_user",
            password="mmpptt007",
            database="bird_detection"
        )
        cursor = db.cursor(dictionary=True)

        # Fetch the last 10 rows ordered by timestamp
        cursor.execute("SELECT timestamp, bird_count_inside, bird_count_outside FROM detections ORDER BY timestamp DESC LIMIT 10")
        records = cursor.fetchall()
        cursor.close()
        db.close()

        # Convert timestamps and sort records in chronological order
        records.reverse()

        # Prepare response data
        response_data = {
            "timestamps": [str(row["timestamp"]) for row in records],  # X-axis labels
            "inside_birds": [row["bird_count_inside"] for row in records],  # Large birds
            "outside_birds": [row["bird_count_outside"] for row in records]  # Small birds
        }
        return jsonify(response_data)

    except mysql.connector.Error as err:
        print(f"[ERROR] MySQL Query Failed: {err}")
        return jsonify({"error": "Database query failed"}), 500

@app.route('/download_csv')
def download_csv():
    """Generate and send the bird detection data as a CSV file."""
    try:
        db = mysql.connector.connect(
            host="192.168.125.196",
            user="iot_user",
            password="mmpptt007",
            database="bird_detection"
        )
        cursor = db.cursor()

        # Fetch all rows from the database
        cursor.execute("SELECT * FROM detections ORDER BY timestamp DESC")
        data = cursor.fetchall()

        # Define CSV file path
        csv_file = "/home/myrios/iot/detections.csv"

        # Write data to CSV
        with open(csv_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Radius", "Birds Inside", "Birds Outside", "Bird Locations", "Pitch", "Arduino Detected Bird", "Deterrent Status"])
            writer.writerows(data)

        cursor.close()
        db.close()

        return send_file(csv_file, as_attachment=True)
    
    except Exception as e:
        return jsonify({"error": str(e)})

@socketio.on('connect')
def handle_connect():
    print("[SocketIO] Client Connected.")
    
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
