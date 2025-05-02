import cv2
import numpy as np
from ultralytics import YOLO
from sense_hat import SenseHat
# from picamera2 import Picamera2

# Initialize Sense HAT
sense = SenseHat()
previous_bird_locations = {"inside": [], "outside": []}
bird_count = 0

# Load YOLO model
model = YOLO("/home/myrios/Documents/IoTA/IOTA_APP/models/best.pt")

# Video Source
video_path = "/home/myrios/Downloads/test_video.mp4"
cap = cv2.VideoCapture(video_path)

# Define circular detection zone
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
cx_frame, cy_frame = frame_width // 2, frame_height // 2
radius = int(min(frame_width, frame_height) * 0.5)  # Adjustable multiplier

def generate_frames(r):
    """Generate YOLO-detected frames for Flask video streaming with Sense HAT updates."""
    global previous_bird_locations, bird_count
    radius = int(min(frame_width, frame_height) * r)
    
    frame_count = 0
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break  # Stop if the video ends

        # Process every 5th frame for speed
        if frame_count % 5 == 0:
            bird_count = 0  # Reset bird count
            bird_locations = {"inside": [], "outside": []}

            # Run YOLO inference
            results = model.predict(frame)
            annotated_frame = results[0].plot()  # Use YOLO's built-in annotations

            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2  # Object center

                    # Check if the bird is inside the detection circle
                    distance = np.sqrt((cx - cx_frame) ** 2 + (cy - cy_frame) ** 2)
                    if distance <= radius:
                        bird_count += 1
                        bird_locations["inside"].append((cx, cy))
                        cv2.circle(annotated_frame, (cx, cy), 5, (0, 0, 255), -1)  # Red dot inside
                    else:
                        bird_locations["outside"].append((cx, cy))
                        cv2.circle(annotated_frame, (cx, cy), 5, (255, 0, 0), -1)  # Blue dot outside

            # Update Sense HAT display
            update_sense_hat(bird_locations, frame_width, frame_height)
            print(f"Current radius: {radius}")
            previous_bird_locations = bird_locations.copy()
        else:
            bird_locations = previous_bird_locations.copy()
            annotated_frame = frame  

        # Draw circular detection zone
        cv2.circle(annotated_frame, (cx_frame, cy_frame), radius, (255, 0, 0), 2)

        # Display bird count
        text = f"Birds Approaching: {bird_count}"
        cv2.putText(annotated_frame, text, (frame_width - 275, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        # Encode frame and yield it for Flask streaming
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        frame_count += 1

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

def get_bird_count():
    """Return the current bird count."""
    return bird_count
