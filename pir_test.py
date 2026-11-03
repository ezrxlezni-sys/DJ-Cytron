import pyRTOS
import time
from gpiozero import MotionSensor

pir_one = MotionSensor(27)
pir_two = MotionSensor(26)

def motion_detection_task(self):
    while True:
        if pir_one.motion_detected or pir_two.motion_detected:
            print("Motion detected! Playing radio.")
        yield [pyRTOS.timeout(1)]  # Wait for 1 second before checking again

# Add the task
pyRTOS.add_task(pyRTOS.Task(motion_detection_task))

# Start the RTOS
pyRTOS.start()
