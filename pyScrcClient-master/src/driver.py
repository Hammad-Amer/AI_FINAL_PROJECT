
import warnings
import msgParser
import carState
import carControl
import keyboard
import time
import os
import csv
import numpy as np
import joblib
from datetime import datetime
import tensorflow as tf

class Driver(object):

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
        
        self.max_steering = 0.785398  
        self.maxspeed = 100
        self.old_rpm = None
        
        
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = os.path.join(log_dir, f"telemetry_{timestamp}.csv")
        self.create_csv()
        
        
        self.acceleration_step = 0.1
        self.manual_influence = 0.0    
        self.target_position = 0.0       
        self.position_change_rate = 0.05 
        self.stds = np.load('../models/stds.npy', allow_pickle=True)
        self.means = np.load('../models/means.npy', allow_pickle=True)
        
        
        
        self.max_steering = 0.785398
        self.maxspeed = 300
        self.old_rpm = None
        self.curr_steer = 0.0  
        self.steer_step = 0.04    
        self.return_rate = 0.10  

        self.shift_delay = 0  
        self.shift_delay_time = 10  
        
        self.load_ai_model()
        
        self.ai_mode = True

        
    
            
    def create_csv(self):
        '''Create CSV file with headers for telemetry data'''
        with open(self.csv_filename, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'angle', 'curLapTime', 'damage', 'distFromStart', 
                'distRaced', 'fuel', 'gear', 'lastLapTime', 'racePos', 'rpm',
                'speedX', 'speedY', 'speedZ', 'trackPos', 'z', 'opponents','wheelSpinVel','focus','track',
                'accel_input', 'brake_input', 'steer_input', 'gear_input',
                'key_w', 'key_s', 'key_a', 'key_d' 
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            

    def load_ai_model(self):
        '''Load the trained TFLite model and scaler'''
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        tflite_path = os.path.join(model_dir, "model_driver.tflite")
        scaler_path = os.path.join(model_dir, "torcs_scaler.joblib")
        try:
            
            self.tflite_interpreter = tf.lite.Interpreter(model_path=tflite_path)
            self.tflite_interpreter.allocate_tensors()
            
            self.tflite_input_details = self.tflite_interpreter.get_input_details()
            self.tflite_output_details = self.tflite_interpreter.get_output_details()

            self.scaler = joblib.load(scaler_path)
            
            self.model_loaded = True
        except Exception as e:
            
            exit(1)
            
            self.model_loaded = False
            self.ai_mode = False

    def handle_controls_AI(self):
        try:
            global count
            count = 0
            current_time = time.time()
            gear = self.control.getGear()
            rpm = self.state.getRpm()
            speed = self.state.getSpeedX()
            distRaced = self.state.getDistRaced()
            
            # Initialize shift tracking if not exists
            if not hasattr(self, 'shift_counter'):
                self.shift_counter = 0
                self.last_shift_time = current_time
            
            # Check if we need to enforce delay (after every 2 shifts)
            can_shift = True
            if self.shift_counter >= 2:
                if (current_time - self.last_shift_time) < 0.5:
                    can_shift = False
                else:
                    self.shift_counter = 0  # Reset counter after delay
            
            if rpm >= 8300 and gear < 6 and can_shift:
                gear += 1
                count = 0
                self.shift_counter += 1
                self.last_shift_time = current_time
            elif rpm <= 2500 and gear > 1 and can_shift:
                gear -= 1
                count = 0
                self.shift_counter += 1
                self.last_shift_time = current_time
                
            # Special cases (reverse gear logic) - these bypass the shift counter
            if int(distRaced) > 2 and speed < 4:
                count += 1
            if 20 <= count < 1200 * 3:
                gear = -1
                count += 1
                self.shift_counter = 0  # Reset counter for special case
            if count >= 1200 * 3:
                gear = 1
                count = 0
                self.shift_counter = 0  # Reset counter for special case
                
            self.control.setGear(gear)

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning, message="X does not have valid feature names")
                scaled_state = self.model_prepare().astype(np.float32)

            self.tflite_interpreter.set_tensor(self.tflite_input_details[0]['index'], scaled_state)
            self.tflite_interpreter.invoke()

            predictions = self.tflite_interpreter.get_tensor(self.tflite_output_details[0]['index'])[0]

            acceleration = float(predictions[0])  
            brake = float(predictions[1])        
            clutch = float(predictions[2])        
            steering = float(predictions[3])      
            
            # Clamp values to valid ranges
            acceleration = max(0.0, min(1.0, acceleration))
            brake = max(0.0, min(1.0, brake))
            clutch = max(0.0, min(1.0, clutch))
            steering = max(-1.0, min(1.0, steering))
            
            # Reduce acceleration if shifting too frequently
            if not can_shift and acceleration > 0.5:
                acceleration *= 0.8  # Reduce acceleration by 20% when in cooldown
            
            self.control.setAccel(acceleration)
            self.control.setBrake(brake)
            self.control.setSteer(steering)
            self.control.setClutch(clutch) 
        except Exception as e:
            self.ai_mode = False
            self.input_keyboard()

    def init(self):
        
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
        
        
        if keyboard.is_pressed('m'):
            
            
            if self.model_loaded:
                self.ai_mode = not self.ai_mode
                mode_name = "AI" if self.ai_mode else "Manual"
                
        
        if self.ai_mode and self.model_loaded:
            self.handle_controls_AI()
        else:
            self.input_keyboard()
        
        
        self.log_data()
        
        return self.control.toMsg()
    
    def model_prepare(self):

        features = np.ndarray((71,), dtype=np.float64)
        features[0] = self.state.angle
        features[1] = self.state.distFromStart
        features[2] = self.state.distRaced
        features[3] = self.state.fuel
        
        features[4] =  self.state.gear
        features[5:41] = self.state.opponents
        features[41] = self.state.racePos
        features[42] = self.state.rpm
        features[43] = self.state.speedX
        features[44] = self.state.speedY
        features[45] = self.state.speedZ
        features[46:65] = self.state.track
        features[65] = self.state.trackPos
        features[66:70] = self.state.wheelSpinVel
        features[70] = self.state.z

        scaled_features = (features - self.means) / self.stds
        
        scaled_features = scaled_features.reshape(1, -1)
        
        
        return scaled_features.reshape(1, -1)
    
    def log_data(self):
        
        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                'timestamp', 'angle', 'curLapTime', 'damage', 'distFromStart', 
                'distRaced', 'fuel', 'gear', 'lastLapTime', 'racePos', 'rpm',
                'speedX', 'speedY', 'speedZ', 'trackPos','opponents','wheelSpinVel','focus','track', 'z',
                'accel_input', 'brake_input', 'steer_input', 'gear_input',
                'key_w', 'key_s', 'key_a', 'key_d'  
            ])
            
       
            data = {
                'timestamp': time.time(),
                'angle': self.state.angle,
                'curLapTime': self.state.curLapTime,
                'damage': self.state.damage,
                'distFromStart': self.state.distFromStart,
                'distRaced': self.state.distRaced,
                'fuel': self.state.fuel,
                'gear': self.state.gear,
                'lastLapTime': self.state.lastLapTime,
                'racePos': self.state.racePos,
                'rpm': self.state.rpm,
                'speedX': self.state.speedX,
                'speedY': self.state.speedY,
                'speedZ': self.state.speedZ,
                'trackPos': self.state.trackPos,
                'opponents': self.state.opponents,
                'wheelSpinVel': self.state.wheelSpinVel,
                'focus': self.state.focus,
                'track': self.state.track,
                'z': self.state.z,
                'accel_input': self.control.getAccel(),
                'brake_input': self.control.getBrake(),
                'steer_input': self.control.getSteer(),
                'gear_input': self.control.getGear(),
                
                'key_w': 1 if keyboard.is_pressed('w') else 0,
                'key_s': 1 if keyboard.is_pressed('s') else 0,
                'key_a': 1 if keyboard.is_pressed('a') else 0,
                'key_d': 1 if keyboard.is_pressed('d') else 0
            }
            
            writer.writerow(data)

    
    
    
    def input_keyboard(self):

        accel = self.control.getAccel()
        brake = self.control.getBrake()
        steer = self.curr_steer
        gear = self.control.getGear()
        speed = self.state.getSpeedX()
        rpm = self.state.getRpm()
        
        
        accel *= 0.9
        brake *= 0.9
 
        if self.shift_delay > 0:
            self.shift_delay -= 1
         
        if keyboard.is_pressed('w'):
            if gear == -1: 
                
                gear = 1
            accel += self.acceleration_step
            brake = 0
            if accel > 1.0:
                accel = 1.0
        
        if keyboard.is_pressed('s'):
            if gear == -1:
                
                accel += self.acceleration_step
                brake = 0
                if accel > 1.0:
                    accel = 1.0
            else:
                
                brake += self.acceleration_step
                accel = 0
                if brake > 1.0:
                    brake = 1.0
                
                

                if abs(speed) < 2.0 and brake > 0.5:
                    gear =  -1

        if self.shift_delay == 0 and gear >= -1:  
            if gear == -1:
                

                if keyboard.is_pressed('w'):
                    gear = 1
                    self.shift_delay = self.shift_delay_time
            else:
                
                if gear == 0:  
                    gear = 1
                elif gear > 0: 
                    if rpm > 8000 and gear < 6 and accel > 0.0:
                        gear += 1
                        self.shift_delay = self.shift_delay_time
                    elif rpm < 3000 and gear > 1:
                        gear -= 1
                        self.shift_delay = self.shift_delay_time
                    elif speed < 5 and gear > 1: 
                        gear = 1
                        self.shift_delay = self.shift_delay_time

     
        if keyboard.is_pressed('a'): 
            self.curr_steer = min(1.0, self.curr_steer + self.steer_step)
        elif keyboard.is_pressed('d'): 
            self.curr_steer = max(-1.0, self.curr_steer - self.steer_step)
        else:
            if abs(self.curr_steer) < self.return_rate:
                self.curr_steer = 0
            elif self.curr_steer > 0:
                self.curr_steer -= self.return_rate
            else:
                self.curr_steer += self.return_rate

        steer = self.curr_steer
        
        self.control.setAccel(accel)
        self.control.setBrake(brake)
        self.control.setSteer(steer)
        self.control.setGear(gear)
        
        self.old_rpm = rpm
    
    def onShutDown(self):
        self.log_file.close()

    def onRestart(self):
        pass