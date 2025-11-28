import ctypes
from ctypes import create_string_buffer

plcommpro = None


def conectar_molinete(ip, puerto):
    """Подключение к турникету по IP и порту через plcommpro.dll"""
    global plcommpro
    try:
        plcommpro = ctypes.windll.LoadLibrary(r"./SDK/plcommpro.dll")

        params = f"protocol=TCP,ipaddress={ip},port={puerto},timeout=4000,passwd="

        constr = create_string_buffer(params.encode("utf-8"))

        hcommpro = plcommpro.Connect(constr)

        if hcommpro != 0:
            print(f"Подключено к турникету {ip}:{puerto}")
            return hcommpro
        else:
            print("Ошибка подключения к турникету.")
            return None

    except Exception as e:
        print(f"Ошибка во время подключения: {e}")
        return None


if __name__ == "__main__":
    ip_molinete = "10.122.0.201"
    puerto_molinete = 14370

    hcommpro = conectar_molinete(ip_molinete, puerto_molinete)

    if hcommpro:
        print("Подключение выполнено успешно.")
    else:
        print("Не удалось подключиться.")

