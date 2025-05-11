import msgParser
import carState
import carControl
import csv
import os
from pynput import keyboard
import threading

class Driver(object):
    '''
    A driver object for the SCRC — manual version
    '''

    def __init__(self, stage):
        self.WARM_UP = 0
        self.QUALIFYING = 1
        self.RACE = 2
        self.UNKNOWN = 3
        self.stage = stage

        self.parser = msgParser.MsgParser()
        self.state = carState.CarState()
        self.control = carControl.CarControl()

        # Steering state
        self.keys = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "gear_up": False,
            "gear_down": False
        }

        self.current_gear = 1

        # CSV Logging
        file_exists = os.path.exists('manual_data.csv')
        self.log_file = open('manual_data.csv', mode='a', newline='')
        self.csv_writer = csv.writer(self.log_file)

        if not file_exists:
            self.csv_writer.writerow(
                ['speedX', 'speedY', 'angle', 'trackPos'] +
                [f'track{i}' for i in range(19)] +
                ['steer', 'accel', 'brake', 'gear', 'rpm']
            )

        # Start key listener in background thread
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()

    def on_press(self, key):
        try:
            if key.char == 'a':
                self.keys["left"] = True
            elif key.char == 'd':
                self.keys["right"] = True
            elif key.char == 'w':
                self.keys["up"] = True
            elif key.char == 's':
                self.keys["down"] = True
            elif key.char == 'i':
                self.keys["gear_up"] = True
            elif key.char == 'j':
                self.keys["gear_down"] = True
        except AttributeError:
            pass

    def on_release(self, key):
        try:
            if key.char == 'a':
                self.keys["left"] = False
            elif key.char == 'd':
                self.keys["right"] = False
            elif key.char == 'w':
                self.keys["up"] = False
            elif key.char == 's':
                self.keys["down"] = False
            elif key.char == 'i':
                self.keys["gear_up"] = False
            elif key.char == 'j':
                self.keys["gear_down"] = False
        except AttributeError:
            pass

    def init(self):
        self.angles = [0 for x in range(19)]

        for i in range(5):
            self.angles[i] = -90 + i * 15
            self.angles[18 - i] = 90 - i * 15

        for i in range(5, 9):
            self.angles[i] = -20 + (i - 5) * 5
            self.angles[18 - i] = 20 - (i - 5) * 5

        return self.parser.stringify({'init': self.angles})

    def drive(self, msg):
        self.state.setFromMsg(msg)

        # Manual control logic
        steering = 0.0
        if self.keys["left"]:
            steering += 1  # Left turn (negative steering)
        if self.keys["right"]:
            steering -= 1  # Right turn (positive steering)

        accel = 1.0 if self.keys["up"] else 0.0
        brake = 1.0 if self.keys["down"] else 0.0

        # Gear logic
        if self.keys["gear_up"]:
            self.current_gear = min(self.current_gear + 1, 6)
            self.keys["gear_up"] = False
        if self.keys["gear_down"]:
            self.current_gear = max(self.current_gear - 1, 1)
            self.keys["gear_down"] = False

        # Apply controls
        self.control.setSteer(steering)
        self.control.setAccel(accel)
        self.control.setBrake(brake)
        self.control.setGear(self.current_gear)

        # Log data
        row = [
            self.state.getSpeedX(),
            self.state.getSpeedY(),
            self.state.getAngle(),
            self.state.getTrackPos()
        ] + self.state.track + [
            steering,
            accel,
            brake,
            self.current_gear,
            self.state.getRpm()
        ]
        self.csv_writer.writerow(row)

        return self.control.toMsg()
