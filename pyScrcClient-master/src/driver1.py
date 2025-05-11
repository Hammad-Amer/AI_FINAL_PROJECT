import msgParser
import carState
import carControl
import csv
import os
import time
from pynput import keyboard

class Driver(object):
    '''
    A driver object for the SCRC
    '''

    def __init__(self, stage):
        '''Constructor'''
        self.WARM_UP = 0
        self.QUALIFYING = 1
        self.RACE = 2
        self.UNKNOWN = 3
        self.stage = stage

        self.parser  = msgParser.MsgParser()
        self.state   = carState.CarState()
        self.control = carControl.CarControl()

        self.steer_lock = 0.785398
        self.prev_rpm   = None

        file_exists      = os.path.exists('training_data.csv')
        self.log_file    = open('training_data.csv', mode='a', newline='')
        self.csv_writer  = csv.writer(self.log_file)
        self.header_written = False

        # Manual driving state
        self.keys = {'w':False, 'a':False, 's':False, 'd':False}

        # Reverse‐hold logic state
        self.reverse_request_time = None
        self.in_reverse = False

        # Start keyboard listener
        listener = keyboard.Listener(on_press=self.on_press,
                                     on_release=self.on_release)
        listener.daemon = True
        listener.start()

    def on_press(self, key):
        try:
            c = key.char.lower()
            if c in self.keys:
                self.keys[c] = True
        except AttributeError:
            pass

    def on_release(self, key):
        try:
            c = key.char.lower()
            if c in self.keys:
                self.keys[c] = False
        except AttributeError:
            pass

    def init(self):
        '''Return init string with rangefinder angles'''
        self.angles = [0]*19
        for i in range(5):
            self.angles[i]       = -90 + i*15
            self.angles[18 - i]  =  90 - i*15
        for i in range(5,9):
            self.angles[i]       = -20 + (i-5)*5
            self.angles[18 - i]  =  20 - (i-5)*5
        return self.parser.stringify({'init': self.angles})

#     def drive(self, msg):
#         self.state.setFromMsg(msg)

#         if any(self.keys.values()):
#             steer = 0.0
#             if self.keys['a']:
#                 steer = 1.0
#             elif self.keys['d']:
#                 steer = -1.0

# # -           accel = 1.0 if self.keys['w'] else 0.0
# #             brake = 1.0 if self.keys['s'] else 0.0
#             forward_in = self.keys['w']
#             backward_in = self.keys['s']

#             # Gear logic (auto/reverse)
# # -           self.gear(accel, brake)
#             self.gear(1.0 if forward_in else 0.0, 1.0 if backward_in else 0.0)

# # -           # Apply manual controls
# # -           self.control.setSteer(steer)
# # -           self.control.setAccel(accel)
# # -           self.control.setBrake(brake)
#             # If in reverse, use S as throttle; otherwise W as throttle
#             if self.control.getGear() == -1:
#                 self.control.setAccel(1.0 if backward_in else 0.0)
#                 self.control.setBrake(0.0)
#             else:
#                 self.control.setAccel(1.0 if forward_in else 0.0)
#                 self.control.setBrake(1.0 if backward_in else 0.0)
#             self.control.setSteer(steer)

#         else:
#             # No keys → zero controls
#             self.control.setSteer(0.0)
#             self.control.setAccel(0.0)
#             self.control.setBrake(0.0)

#         self.log_data()
#         return self.control.toMsg()

    def drive(self, msg):
        self.state.setFromMsg(msg)

        self.steer()
        self.gear()
        self.speed()

        self.log_data()
        return self.control.toMsg()

    def steer(self):
        angle = self.state.angle
        dist  = self.state.trackPos
        self.control.setSteer((angle - dist*0.5) / self.steer_lock)



    def gear(self):
        rpm = self.state.getRpm()
        gear = self.state.getGear()

        # Define thresholds with hysteresis to prevent flickering
        upshift_rpm = 8300
        downshift_rpm = 3500
        rpm_buffer = 500  # buffer to avoid flickering

        # If in neutral, shift to first
        if gear == 0:
            gear = 1
        elif rpm > (upshift_rpm + rpm_buffer) and gear < 6:
            gear += 1
        elif rpm < (downshift_rpm - rpm_buffer) and gear > 1:
            gear -= 1

        self.control.setGear(gear)
        self.prev_rpm = rpm
    # def gear(self, accel, brake):
    #     rpm   = self.state.getRpm()
    #     gear  = self.state.getGear()
    #     speed = self.state.getSpeedX()

    #     # Create/update shift timer
    #     if not hasattr(self, 'last_shift_time'):
    #         self.last_shift_time = 0

    #     SHIFT_COOLDOWN = 0.5  # seconds between shifts to avoid flickering

    #     # 1) Engage reverse if stopped + brake held >0.8 for 0.5s
    #     if speed < 1.0 and brake > 0.8:
    #         if self.reverse_request_time is None:
    #             self.reverse_request_time = time.time()
    #         elif time.time() - self.reverse_request_time > 0.5:
    #             gear = -1
    #             self.in_reverse = True
    #     else:
    #         self.reverse_request_time = None

    #     # 2) If in reverse, exit when pressing accel
    #     if self.in_reverse:
    #         if accel > 0.5:
    #             gear = 1
    #             self.in_reverse = False
    #         else:
    #             gear = -1

    #     # 3) Normal forward shifting (only if not in reverse)
    #     elif not self.in_reverse:
    #         current_time = time.time()
    #         if gear == 0:
    #             gear = 1
    #             self.last_shift_time = current_time
    #         elif current_time - self.last_shift_time > SHIFT_COOLDOWN:
    #             # Hysteresis: add buffer for upshift/downshift
    #             if rpm > 6800 and gear < 6:
    #                 gear += 1
    #                 self.last_shift_time = current_time
    #             elif rpm < 3000 and gear > 1:
    #                 gear -= 1
    #                 self.last_shift_time = current_time

    #     self.control.setGear(gear)
    #     self.prev_rpm = rpm

    def speed(self):
        target_speed = 300
        speed = self.state.getSpeedX()
        if speed < target_speed:
            accel = 1.0; brake = 0.0
        else:
            accel = 0.0; brake = 0.1
        self.control.setAccel(accel)
        self.control.setBrake(brake)

    def log_data(self):
        timestamp     = time.time()
        track_sensors = self.state.getTrack() or [0.0]*19

        raw_opps    = self.state.getOpponentsDist() or []
        sorted_opps = sorted((d if d is not None else float('inf')) for d in raw_opps)
        nearest5    = sorted_opps[:5] + [0.0]*max(0,5-len(sorted_opps))

        if not self.header_written:
            base = [
                'time','speedX','speedY','speedZ','rpm','gear',
                'steer','accel','brake','trackPos','angle',
                'distFromStart','trackDist',
                'focusLeft','focusCenter','focusRight',
                'fuel','damage','racePos',
                'wheelSpinFL','wheelSpinFR','wheelSpinRL','wheelSpinRR'
            ]
            header = base + [f"track{i}" for i in range(19)] + [f"opponent{i+1}_dist" for i in range(5)]
            self.csv_writer.writerow(header)
            self.header_written = True

        row = [
            timestamp,
            self.state.getSpeedX(),
            self.state.getSpeedY(),
            self.state.getSpeedZ(),
            self.state.getRpm(),
            self.state.getGear(),
            self.control.getSteer(),
            self.control.getAccel(),
            self.control.getBrake(),
            self.state.getTrackPos(),
            self.state.getAngle(),
            self.state.getDistFromStart(),
            self.state.getTrackDist(),
            self.state.getFocusLeft(),
            self.state.getFocusCenter(),
            self.state.getFocusRight(),
            self.state.getFuel(),
            self.state.getDamage(),
            self.state.getRacePos(),
            self.state.getWheelSpinFL(),
            self.state.getWheelSpinFR(),
            self.state.getWheelSpinRL(),
            self.state.getWheelSpinRR()
        ] + track_sensors + nearest5

        self.csv_writer.writerow(row)

    def onShutDown(self):
        self.log_file.close()

    def onRestart(self):
        pass