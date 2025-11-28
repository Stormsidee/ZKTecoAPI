import ctypes
from ctypes import create_string_buffer


def buscar_dispositivos():
    """
    Поиск устройств ZKTeco в локальной сети с помощью функции SearchDevice.
    """
    try:
        # Загрузка библиотеки PullSDK
        # plcommpro = ctypes.windll.LoadLibrary(r"C:\Sdk-Zkteco\Plcommpro.dll")
        plcommpro = ctypes.windll.LoadLibrary(r"./SDK/plcommpro.dll")
        # Настройка параметров для поиска
        comm_type = "UDP"  # Используем UDP для поиска устройств в сети
        address = "255.255.255.255"  # Широковещательный адрес
        buffer_size = 64 * 1024  # Размер буфера (64 КБ)
        dev_buf = create_string_buffer(buffer_size)  # Буфер для хранения результатов

        # Вызов функции SearchDevice
        ret = plcommpro.SearchDevice(comm_type.encode("utf-8"), address.encode("utf-8"), dev_buf)

        if ret > 0:
            print(f"Найдено устройств: {ret}")
            # Декодировать буфер и вывести результаты
            devices = dev_buf.value.decode("utf-8", errors="ignore").strip().split("\r\n")
            for i, device in enumerate(devices, 1):
                if device:
                    print(f"Устройство {i}: {device}")
        else:
            print("Устройства в сети не найдены.")

    except Exception as e:
        print(f"Ошибка во время поиска устройств: {e}")


if __name__ == "__main__":
    buscar_dispositivos()

