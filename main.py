from fastapi import FastAPI
from SDK.molinete_test import ZKTecoDevice
from SDK.rfid.ConnectionTurnstile import ConnectionTurnstile


app = FastAPI(
    title="ZKTeco C2-260 API",
    description="This API for controlling the C2-260",
    version="1.0.0"
)

device = ZKTecoDevice()
#device_zkem = ConnectionTurnstile()
state_device = {"status":"disconnected"}

def connect_to_device(ip="10.122.0.201",port=14370):
    device.connect(ip,port)
   # device_zkem.connect(ip,port)
    global state_device
    state_device = {"status":"connected"}
    
    return state_device

connect_to_device()

@app.get('/')
def root():
    return {"message":"API is working!"}

@app.get('/status')
def status():
    return state_device
        
@app.post('/open/')
def open_turnstile(seconds: int=5):
    door = device.control_device(operation_id=1,door_id=1,state=seconds)
    if door == True:
        return {"message":"Турникет открыт на {} секунд".format(seconds)}
    else:
        return {"message":"Ошибка при открытии турникета"}

"""
@app.get('/get-users')
def get_users():
    users = device_zkem.get_users()
    if users is None:
        return {"message":"Ошибка при получении пользователей"}
    else:
        return {"users":users}"""
