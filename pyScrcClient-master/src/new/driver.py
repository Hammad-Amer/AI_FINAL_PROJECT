import msgParser
import carState
import carControl
import csv
import os

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

        self.parser = msgParser.MsgParser()
        self.state = carState.CarState()
        self.control = carControl.CarControl()

        self.steer_lock = 0.785398
        self.prev_rpm = None

        file_exists = os.path.exists('training_data.csv')
        self.log_file = open('training_data.csv', mode='a', newline='')
        self.csv_writer = csv.writer(self.log_file)

        if not file_exists:
            # Write header only if the file doesn't already exist
            self.csv_writer.writerow(
                ['speedX', 'speedY', 'angle', 'trackPos'] +
                [f'track{i}' for i in range(19)] +
                ['steer', 'accel', 'brake']
            )
        

    def init(self):
        '''Return init string with rangefinder angles'''
        self.angles = [0 for x in range(19)]

        for i in range(5):
            self.angles[i] = -90 + i * 15
            self.angles[18 - i] = 90 - i * 15

        for i in range(5, 9):
            self.angles[i] = -20 + (i-5) * 5
            self.angles[18 - i] = 20 - (i-5) * 5

        return self.parser.stringify({'init': self.angles})

    def drive(self, msg):
        self.state.setFromMsg(msg)

        self.steer()
        self.gear()
        self.speed()

        self.log_data()

        return self.control.toMsg()

    def steer(self):
        angle = self.state.angle
        dist = self.state.trackPos
        self.control.setSteer((angle - dist * 0.5) / self.steer_lock)

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

    def speed(self):
        target_speed = 300
        speed = self.state.getSpeedX()

        if speed < target_speed:
            accel = 1.0
            brake = 0.0
        else:
            accel = 0.0
            brake = 0.1

        self.control.setAccel(accel)
        self.control.setBrake(brake)

    def log_data(self):
        row = [
            self.state.getSpeedX(),
            self.state.getSpeedY(),
            self.state.getAngle(),
            self.state.getTrackPos()
        ] + self.state.track + [
            self.control.getSteer(),
            self.control.getAccel(),
            self.control.getBrake()
        ]
        self.csv_writer.writerow(row)

    def onShutDown(self):
        self.log_file.close()

    def onRestart(self):
        pass
