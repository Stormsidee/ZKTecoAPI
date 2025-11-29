from fastapi import FastAPI, Response, Request
import hashlib
from SDK.molinete_test import ZKTecoDevice
from datetime import datetime


app = FastAPI(
    title="ZKTeco C2-260 API",
    description="This API for controlling the C2-260",
    version="1.0.0"
)

device = ZKTecoDevice()
state_device = {"status":"unactive"}
state_pusk_sdk = {"status":"unactive"}

def connect_to_device(ip="10.122.0.201",port=14370):
    device.connect(ip,port)
    global state_device
    state_device = {"status":"active"}
    
    return state_device

connect_to_device()


#----------PUSH SDK------------#
cmd_queue = {}
reg_devices = {}

@app.api_route("/iclock/cdata", methods=["GET", "POST"])
async def handle_cdata(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    if request.method == "GET":
        if sn in reg_devices:
            device = reg_devices[sn]
            response = f"""registry=ok
RegistryCode={device['registry_code']}
ServerVersion=1.0.0
ServerName=MyServer
PushProtVer=3.1.2
ErrorDelay=60
RequestDelay=30
TransTimes=00:00;12:00
TransInterval=2
TransTables=User Transaction
Realtime=1
SessionID={device['session_id']}
TimeoutSec=10"""
        else:
            response = "OK"
        
        return Response(content=response, media_type="text/plain")
    
    else:
        body = await request.body()
        body_text = body.decode('utf-8')
        table = query_params.get('table', '')
        
        print(f"📥 Данные от {sn}, таблица: {table}")
        
        # Обрабатываем события открытия двери
        if table == "rtlog":
            await handle_access_event(sn, body_text)
        
        if sn in reg_devices:
            reg_devices[sn]['last_seen'] = datetime.now()
        
        return Response(content="OK", media_type="text/plain")

@app.api_route("/iclock/registry", methods=["POST"])
async def handle_registry(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    body = await request.body()
    body_text = body.decode('utf-8')
    
    print(f"📍 Регистрация устройства {sn}")
    print(f"📦 Данные: {body_text}")
    
    registry_code = hashlib.md5(f"{sn}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    session_id = hashlib.md5(f"{sn}_session".encode()).hexdigest()
    
    reg_devices[sn] = {
        'registry_code': registry_code,
        'session_id': session_id,
        'last_seen': datetime.now()
    }
    
    cmd_queue[sn] = []
    
    return Response(content=f"RegistryCode={registry_code}", media_type="text/plain")

@app.api_route("/iclock/push", methods=["GET", "POST"])
async def handle_push(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    if sn not in reg_devices:
        return Response(content="Error", media_type="text/plain")
    
    device = reg_devices[sn]
    
    config = f"""ServerVersion=1.0.0
ServerName=MyServer
ErrorDelay=60
RequestDelay=30
TransTimes=00:00;12:00
TransInterval=2
TransTables=User Transaction
Realtime=1
SessionID={device['session_id']}
TimeoutSec=10"""
    
    return Response(content=config, media_type="text/plain")

@app.api_route("/iclock/getrequest", methods=["GET"])
async def handle_getrequest(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    if sn not in cmd_queue:
        return Response(content="", media_type="text/plain")
    
    if cmd_queue[sn]:
        command = cmd_queue[sn].pop(0)
        print(f"📤 Отправляю команду для {sn}: {command}")
        return Response(content=command, media_type="text/plain")
    
    return Response(content="", media_type="text/plain")

@app.api_route("/iclock/devicecmd", methods=["POST"])
async def handle_devicecmd(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    body = await request.body()
    body_text = body.decode('utf-8')
    
    print(f"✅ Результат команды от {sn}: {body_text}")
    
    return Response(content="OK", media_type="text/plain")

@app.api_route("/iclock/ping", methods=["GET"])
async def handle_ping(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    if sn in reg_devices:
        reg_devices[sn]['last_seen'] = datetime.now()
    
    return Response(content="OK", media_type="text/plain")

@app.api_route("/iclock/querydata", methods=["POST"])
async def handle_querydata(request: Request):
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    table_name = query_params.get('tablename', '')
    count = query_params.get('count', '')
    
    print(f"📊 QUERY DATA от {sn}")
    print(f"📋 Таблица: {table_name}, количество: {count}")
    print(f"🔧 Параметры: {query_params}")
    
    body = await request.body()
    body_text = body.decode('utf-8')
    print(f"📦 Данные: {body_text}")
    
    return Response(content="OK", media_type="text/plain")

#------------------------------#

@app.get('/')
def root():
    return {"message":"API is working!"}

@app.post("/get_users")
async def test_add_command(sn: str = "CMOU210460005"):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    
    command = "C:415:DATA QUERY tablename=user,fielddesc=*,filter=*"
    cmd_queue[sn].append(command)
    
    return {"status": "Command added", "device": sn}

@app.post('/control/free-open')
def free_open(sn: str = "CMOU210460005"):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    
    command = "C:221:CONTROL DEVICE 010101FF"
    cmd_queue[sn].append(command)

    return {"status": "Command added", "device": sn}

@app.post('/control/free-close')
def free_close(sn: str = "CMOU210460005"):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    
    command = "C:221:CONTROL DEVICE 01010100"
    cmd_queue[sn].append(command)

    return {"status": "Command added", "device": sn}

@app.get('/status')
def status():
    if reg_devices != {}:
        global state_pusk_sdk
        state_pusk_sdk = {"status":"active"}
    return {"pusk_sdk":state_pusk_sdk,
            "pull_sdk":state_device}
        
@app.post('/open/')
def open_turnstile(seconds: int=5):
    door = device.control_device(operation_id=1,door_id=1,state=seconds)
    if door == True:
        return {"message":"Турникет открыт на {} секунд".format(seconds)}
    else:
        return {"message":"Ошибка при открытии турникета"}
    
async def handle_access_event(sn: str, data: str):
    event_data = {}
    for item in data.split('\t'):
        if '=' in item:
            key, value = item.split('=', 1)
            event_data[key.strip()] = value.strip()
    
    cardno = event_data.get('cardno', '0')
    event = event_data.get('event', '')
    pin = event_data.get('pin', '0')
    
    if event == '1': 
        print(f"🚪 ДВЕРЬ ОТКРЫТА! Карта: {cardno}, Пользователь: {pin}")
    
    elif event == '2': 
        print(f"❌ ДОСТУП ЗАПРЕЩЕН! Карта: {cardno}, Пользователь: {pin}")
    
    elif event == '6': 
        print(f"🔘 ОТКРЫТО КНОПКОЙ ВЫХОДА")
    
    elif event == '8': 
        print(f"🖥️ ОТКРЫТО УДАЛЕННО (через API)")

