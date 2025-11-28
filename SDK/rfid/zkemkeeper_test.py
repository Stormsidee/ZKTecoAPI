"""
Скрипт для проверки доступных функций COM-интерфейса zkemkeeper.
Используйте этот скрипт, чтобы определить, какие функции
поддерживаются вашей конкретной версией SDK ZKTeco.
"""

import os
import sys
import time
from datetime import datetime

try:
    import pythoncom
    import win32com.client
except ImportError:
    print("Для работы этого скрипта требуется PyWin32. Установите его командой: pip install pywin32")
    sys.exit(1)


def test_zkemkeeper_functions():
    """Проверка различных функций zkemkeeper для определения совместимости"""
    print("=" * 60)
    print("     ТЕСТ ДОСТУПНЫХ ФУНКЦИЙ В ZKEMKEEPER.DLL     ")
    print("=" * 60)

    try:
        # Инициализация COM
        pythoncom.CoInitialize()
        zkem = win32com.client.Dispatch("zkemkeeper.ZKEM.1")

        print("COM‑интерфейс zkemkeeper успешно инициализирован")

        # Проверка подключения
        ip = input("Введите IP‑адрес устройства (по умолчанию 10.122.0.201): ") or "10.122.0.201"
        port = input("Введите порт устройства (по умолчанию 14370): ") or "14370"

        print(f"Пробую подключиться к {ip}:{port}...")

        # Попытка подключения
        if zkem.Connect_Net(ip, int(port)):
            print("✓ Успешное подключение к устройству")
            machine_id = 1  # Идентификатор устройства по умолчанию

            # Таблица тестируемых функций
            functions_to_test = [
                # Базовые функции
                ("GetFirmwareVersion", lambda: zkem.GetFirmwareVersion(machine_id)),
                ("GetDeviceMAC", lambda: zkem.GetDeviceMAC(machine_id)),
                ("GetSerialNumber", lambda: zkem.GetSerialNumber(machine_id)),
                ("GetDeviceIP", lambda: zkem.GetDeviceIP(machine_id)),
                ("GetProductCode", lambda: zkem.GetProductCode(machine_id)),
                ("GetVendor", lambda: zkem.GetVendor()),
                ("GetPlatform", lambda: zkem.GetPlatform(machine_id)),
                ("GetCardFun", lambda: zkem.GetCardFun(machine_id)),

                # Функции контроля доступа
                ("EnableDevice", lambda: zkem.EnableDevice(machine_id, True)),
                ("DisableDevice", lambda: zkem.DisableDevice(machine_id)),
                ("GetLastError", lambda: zkem.GetLastError()),

                # Функции для событий в реальном времени
                ("RegEvent", lambda: zkem.RegEvent(machine_id, 0xFFFF)),  # 0xFFFF = все события
                ("GetRTLog", lambda: zkem.GetRTLog(machine_id)),

                # Специальные функции для работы с картами
                ("GetStrCardNumber", lambda: zkem.GetStrCardNumber()),
                ("ReadCard", lambda: zkem.ReadCard(machine_id, "")),
                ("GetHIDEventCardNumAsStr", lambda: zkem.GetHIDEventCardNumAsStr()),
                ("PollCard", lambda: zkem.PollCard()),

                # Функция для чтения событий журнала
                ("ReadGeneralLogData", lambda: zkem.ReadGeneralLogData(machine_id)),
            ]

            # Проверка каждой функции и вывод результата
            results = []
            print("\n--- Тест функций SDK ---")
            for func_name, func_call in functions_to_test:
                try:
                    result = func_call()
                    print(f"✓ {func_name}: доступна (результат: {result})")
                    results.append((func_name, True, str(result)))
                except Exception as e:
                    print(f"✗ {func_name}: недоступна или ошибка ({str(e)})")
                    results.append((func_name, False, str(e)))

            # Специальный тест: чтение карты в реальном времени
            print("\n--- Специальный тест: чтение карты в реальном времени ---")
            print("Поднесите карту к считывателю в течение ближайших 10 секунд...")

            # Включение событий в реальном времени (если доступно)
            try:
                zkem.RegEvent(machine_id, 0xFFFF)
                card_detected = False
                start_time = time.time()

                while time.time() - start_time < 10 and not card_detected:
                    # Попытка нескольких методов обнаружения карты
                    try:
                        # Метод 1: PollCard
                        if hasattr(zkem, "PollCard") and zkem.PollCard():
                            card_num = zkem.GetStrCardNumber()
                            print(f"✓ Карта обнаружена (PollCard): {card_num}")
                            card_detected = True
                            break
                    except Exception:
                        pass

                    # Метод 2: GetLastEvent
                    try:
                        if hasattr(zkem, "GetLastEvent") and zkem.GetLastEvent():
                            card_num = zkem.GetStrCardNumber()
                            if card_num:
                                print(f"✓ Карта обнаружена (GetLastEvent): {card_num}")
                                card_detected = True
                                break
                    except Exception:
                        pass

                    # Короткая пауза
                    time.sleep(0.2)

                if not card_detected:
                    print("✗ В отведённое время карта не была обнаружена")
            except Exception as e:
                print(f"✗ Ошибка при попытке чтения карты: {e}")

            # Сводка по доступности функций
            print("\n--- Сводка по функциям ---")
            available = sum(1 for _, status, _ in results if status)
            print(f"Доступно функций: {available} из {len(functions_to_test)}")

            # Отключение устройства
            zkem.Disconnect()
            print("\nУстройство отключено")

        else:
            print("✗ Не удалось подключиться к устройству")
            try:
                error_code = zkem.GetLastError()
                print(f"Код ошибки: {error_code}")
            except Exception:
                pass

        print("\n--- Завершено ---")

    except Exception as e:
        print(f"Общая ошибка: {e}")
    finally:
        # Освобождение ресурсов COM
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    # Проверка наличия файла zkemkeeper.dll
    if os.path.exists("zkemkeeper.dll"):
        print("✓ Файл zkemkeeper.dll найден")
    else:
        print("✗ Файл zkemkeeper.dll не найден — скрипт может работать некорректно")

    test_zkemkeeper_functions()
