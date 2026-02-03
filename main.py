from fastapi import FastAPI, Response, Request, Query
import hashlib, secrets,requests
from SDK.molinete_test import ZKTecoDevice
from datetime import datetime
import time,asyncio



app = FastAPI(
    title="ZKTeco C2-260 API",
    description="This API for controlling the C2-260",
    version="1.0.0"
)


state_push_sdk = {"status":"unactive"}

def zk_encode_time(dt_str: str) -> int:
    """
    Конвертирует 'DD-MM-YYYY HH:MM:SS' в ZKTeco seconds (Appendix 5)
    """
    dt = datetime.strptime(dt_str, "%d-%m-%Y %H:%M:%S")

    year = dt.year
    mon = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    sec = dt.second

    tt = ((year - 2000) * 12 * 31 + (mon - 1) * 31 + (day - 1)) * 24 * 60 * 60 \
         + (hour * 60 + minute) * 60 + sec

    return tt


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


        if table == "rtlog":
            await handle_access_event(sn, body_text)
        
        if sn in reg_devices:
            reg_devices[sn]['last_seen'] = datetime.now()
        
        return Response(content="OK", media_type="text/plain")

def generate_token(registry_code, sn , session_id):
    data = f"{registry_code}{sn}{session_id}"
    return hashlib.md5(data.encode()).hexdigest()

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


@app.post("/iclock/devicecmd")
async def handle_devicecmd(request: Request):
    body = await request.body()
    body_text = body.decode('utf-8')
    query_params = dict(request.query_params)
    sn = query_params.get('SN', '')
    
    print(f"✅ Результат команды от {sn}: {body_text}")
    
    params = {}
    for pair in body_text.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            params[key.strip()] = value.strip()
    
    if 'Return' in params:
        return_code = int(params['Return'])
        if return_code >= 0:
            print(f"✅ Команда {params.get('ID')} выполнена успешно")
        else:
            print(f"❌ Ошибка команды {params.get('ID')}: код {return_code}")
    
    if 'CMD' in params and 'QUERY' in params['CMD']:
        cmd_id = params.get('ID')
        if hasattr(app.state, 'response_futures') and cmd_id in app.state.response_futures:
            future = app.state.response_futures.pop(cmd_id)
            if not future.done():
                future.set_result(body_text)
    
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

async def handle_access_event(sn: str, data: str):
    event_data = {}
    for item in data.split('\t'):
        if '=' in item:
            key, value = item.split('=', 1)
            event_data[key.strip()] = value.strip()
    
    cardno_hex = event_data.get('cardno', '0')
    event = event_data.get('event', '')
    pin = event_data.get('pin', '0')
    
    if cardno_hex != '0' and cardno_hex != '':
        try:
            cardno_hex = cardno_hex.lower().replace('0x', '').strip()
            cardno_decimal = int(cardno_hex, 16)
            
            if event == '0': 
                print(f"✅ Карта {cardno_decimal} (HEX: {cardno_hex}) (пользователь {pin}) - ДОСТУП РАЗРЕШЕН")
            elif event == '27': 
                print(f"❌ Карта {cardno_decimal} (HEX: {cardno_hex}) (пользователь {pin}) - ДОСТУП ЗАПРЕЩЕН")
            elif event == '29': 
                print(f"⚠️ Карта {cardno_decimal} (HEX: {cardno_hex}) (пользователь {pin}) - СРОК ДЕЙСТВИЯ ИСТЕК ИЛИ НЕ НАЧАЛСЯ")
            else:
                print(f"🎫 Карта {cardno_decimal} (HEX: {cardno_hex}) приложена (событие {event})")
                
        except ValueError:
            print(f"⚠️ Ошибка конвертации карты {cardno_hex}")
    elif event == '8': 
        print(f"🖥️ ОТКРЫТО УДАЛЕННО (через API)")

#------------------------------#


@app.get('/')
def root():
    return {"message":"API is working!"}

@app.get('/check-users')
async def check_users(sn: str = "CMOU210460005"):
    """
    Проверяет всех пользователей и их карты
    """
    if sn not in cmd_queue:
        return {"error": f"Device {sn} not registered"}
    
    cmd_id = int(time.time() % 10000)
    
    command1 = f"C:{cmd_id}:DATA QUERY tablename=user,fielddesc=*,filter=*"
    
    cmd_id2 = cmd_id + 1
    command2 = f"C:{cmd_id2}:DATA QUERY tablename=mulcarduser,fielddesc=*,filter=*"
    cmd_id3 = cmd_id2 + 1
    command3 = f"C:{cmd_id3}:DATA QUERY tablename=userauthorize,fielddesc=*,filter=*"
    
    cmd_queue[sn].append(command1)
    cmd_queue[sn].append(command2)
    cmd_queue[sn].append(command3)
    
    return {
        "status": "queries_sent",
        "device": sn,
        "queries": [
            {"id": cmd_id, "table": "user", "cmd": command1},
            {"id": cmd_id2, "table": "mulcarduser", "cmd": command2},
            {"id": cmd_id3, "table": "mulcarduser", "cmd": command3}
        ]
    }

@app.get('/status')
def status():
    if reg_devices != {}:
        global state_push_sdk
        state_push_sdk = {"status":"active"}
    return {"pusk_sdk":state_push_sdk}
        
@app.post('/open/')
def open_turnstile(sn: str = "CMOU210460005", seconds: int = 5, door: int = 1):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    
    if seconds < 10:
        command = f"C:221:CONTROL DEVICE 01010{door}0{seconds}"
    else:
        command = f"C:221:CONTROL DEVICE 01010{door}{seconds}"
    cmd_queue[sn].append(command)

    return {"status": "Command added", "device": sn}

@app.post('/cmd')
def cmd_send(sn: str = "CMOU210460005", cmd: str = ""):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    
    command = f"C:221:CONTROL DEVICE {cmd}"
    cmd_queue[sn].append(command)

    return {"status": "Command added", "device": sn}

@app.post('/passage')
def passage_mode(sn: str = "CMOU210460005",mode: str = "off"):
    if sn not in cmd_queue:
        return {"error": "Device not found"}
    if mode == "on":
        command = f"C:221:CONTROL DEVICE 010102FF00"
    elif mode == "off":
        command = f"C:221:CONTROL DEVICE 0101020000"
    cmd_queue[sn].append(command)

    return {"status": "Command added", "device": sn}


@app.post('/add-card')
async def add_card(
    cardno: str, 
    name: str = "",
    starttime: str = "0",
    endtime: str = "0",
    pin: str = None,
    sn: str = "CMOU210460005"):
    
    time1 = zk_encode_time(starttime)
    time2 = zk_encode_time(endtime)
    
    if sn not in reg_devices:
        return {"error": f"Device {sn} not registered"}
    
    if pin is None:
        pin = int(time.time() % 1000000)
    
    cardno_hex = cardno.replace('0x', '').replace('0X', '').lower()
    
    if len(cardno_hex) < 8:
        cardno_hex = cardno_hex.zfill(8)
    
    print(f"🎫 Карта: {cardno} -> очищенная: {cardno_hex} (нижний регистр!)")
    
    cmd_id1 = int(time.time() % 10000)
    command1 = f"C:{cmd_id1}:DATA UPDATE user CardNo=\tPin={pin}\tPassword=\tGroup=0\tStartTime={time1}\tEndTime={time2}\tName={name}\tPrivilege=0"
    
    cmd_id2 = cmd_id1 + 1
    command2 = f"C:{cmd_id2}:DATA UPDATE mulcarduser Pin={pin}\tCardNo={cardno_hex}\tLossCardFlag=0\tCardType=0"

    cmd_id3 = cmd_id2 + 1
    command3 = f"C:{cmd_id3}:DATA UPDATE userauthorize Pin={pin}\tAuthorizeTimezoneId=1\tAuthorizeDoorId=1\tDevID=3"
    
    print(f"🔥 Команда 1: {command1}")
    print(f"🔥 Команда 2: {command2}")
    print(f"🔥 Команда 3: {command3}")
    
    if sn in cmd_queue:
        cmd_queue[sn].append(command1)
        cmd_queue[sn].append(command2)
        cmd_queue[sn].append(command3)
        
        return {
            "status": "commands_added",
            "device": sn,
            "user": {
                "pin": pin,
                "name": name,
                "cardno_hex": cardno_hex,
                "cardno_dec": int(cardno_hex, 16)
            },
            "commands": [
                {"id": cmd_id1, "cmd": command1},
                {"id": cmd_id2, "cmd": command2},
                {"id": cmd_id3, "cmd": command3}
            ]
        }
    
    return {"error": "Failed to add commands"}


@app.post('/delete-user')
def delete_users(pin:str = None,sn: str = "CMOU210460005"):
    cmd_id1 = int(time.time() % 10000)
    if pin == None:
        command1 = f"C:{cmd_id1}:DATA DELETE user Pin=*"
        command2 = f"C:{cmd_id1+1}:DATA DELETE mulcarduser Pin=*"
        command3 = f"C:{cmd_id1+2}:DATA DELETE userauthorize Pin=*"
    else:
        command1 = f"C:{cmd_id1}:DATA DELETE user Pin={pin}"
        command2 = f"C:{cmd_id1+1}:DATA DELETE mulcarduser Pin={pin}"
        command3 = f"C:{cmd_id1+2}:DATA DELETE userauthorize Pin={pin}"
    

    if sn in cmd_queue:
        cmd_queue[sn].append(command1)
        cmd_queue[sn].append(command2)
        cmd_queue[sn].append(command3)
        
        return {
            "status": "commands_added",
            "device": sn,
            "commands": [
                {"id": cmd_id1, "cmd": command1},
                {"id": cmd_id1, "cmd": command2},
                {"id": cmd_id1, "cmd": command3}
            ]
        }
    
    return {"error": "Failed to add commands"}

