import msgParser

class CarControl(object):
    '''
    An object holding all the control parameters of the car
    '''
    # TODO range check on set parameters

    def __init__(self, accel = 0.0, brake = 0.0, gear = 1, steer = 0.0, clutch = 0.0, focus = 0, meta = 0):
        '''Constructor'''
        self.parser = msgParser.MsgParser()
        
        self.actions = None
        
        self.accel = accel
        self.brake = brake
        self.gear = gear
        self.steer = steer
        self.clutch = clutch
        self.focus = focus
        self.meta = meta
    
    def toMsg(self):
        self.actions = {}
        
        self.actions['accel'] = [self.accel]
        self.actions['brake'] = [self.brake]
        self.actions['gear'] = [self.gear]
        self.actions['steer'] = [self.steer]
        self.actions['clutch'] = [self.clutch]
        self.actions['focus'] = [self.focus]
        self.actions['meta'] = [self.meta]
        
        return self.parser.stringify(self.actions)
    
    # Getter & Setter methods
    def setAccel(self, accel: float):
        self.accel = accel
    
    def getAccel(self) -> float:
        return self.accel
    
    def setBrake(self, brake: float):
        self.brake = brake
    
    def getBrake(self) -> float:
        return self.brake
    
    def setGear(self, gear: int):
        self.gear = gear
    
    def getGear(self) -> int:
        return self.gear
    
    def setSteer(self, steer: float):
        self.steer = steer
    
    def getSteer(self) -> float:
        return self.steer
    
    def setClutch(self, clutch: float):
        self.clutch = clutch
    
    def getClutch(self) -> float:
        return self.clutch
    
    def setMeta(self, meta: int):
        self.meta = meta
    
    def getMeta(self) -> int:
        return self.meta
        