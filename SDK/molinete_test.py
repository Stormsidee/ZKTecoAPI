from ctypes import windll, byref, create_string_buffer, c_int, c_char_p, c_long, c_ulong, c_void_p, c_bool, POINTER
import os
import sys
import time


class ZKTecoDevice:
    def __init__(self):
        self.commpro = None
        self.hcommpro = 0
        self.connected = False
        self.machine_number = 1

        # Загрузка библиотеки SDK
        try:
            self.commpro = windll.LoadLibrary(r"./SDK/plcommpro.dll")
            print("Библиотека SDK успешно загружена")
        except Exception as e:
            print(f"Ошибка при загрузке библиотеки: {e}")
            sys.exit(1)

    def connect(self, ip_address="10.122.0.201", port=14370, timeout=4000, password=""):
        if self.connected:
            print("Устройство уже подключено")
            return True

        try:
            params = f"protocol=TCP,ipaddress={ip_address},port={port},timeout={timeout},passwd={password}"
            constr = create_string_buffer(params.encode())
            self.hcommpro = self.commpro.Connect(constr)

            if self.hcommpro != 0:
                self.connected = True
                print(f"Подключено к устройству: {ip_address}:{port}")
                return True
            else:
                error_code = self.commpro.PullLastError()
                print(f"Ошибка подключения. Код: {error_code}. Проверьте IP и питание устройства.")
                return False
        except Exception as e:
            print(f"Ошибка во время подключения: {e}")
            return False

    def disconnect(self):
        if not self.connected:
            print("Нет активного подключения")
            return

        try:
            self.commpro.Disconnect(self.hcommpro)
            self.connected = False
            self.hcommpro = 0
            print("Отключено от устройства")
        except Exception as e:
            print(f"Ошибка при отключении: {e}")

    def get_device_info(self):
        if not self.connected:
            print("Нет активного подключения")
            return

        try:
            # Получить параметры устройства через GetDeviceParam
            buffer = create_string_buffer(2048)
            items = "DeviceID,Door1SensorType,Door1Drivertime,Door1Intertime,~ZKFPVersion"
            p_items = create_string_buffer(items.encode())
            ret = self.commpro.GetDeviceParam(self.hcommpro, buffer, 2048, p_items)

            if ret >= 0:
                print(f"Информация об устройстве: {buffer.value.decode()}")
            else:
                error_code = self.commpro.PullLastError()
                print(f"Ошибка при получении информации об устройстве. Код: {error_code}")

            # Проверить последние события
            rt_log = create_string_buffer(256)
            ret = self.commpro.GetRTLog(self.hcommpro, rt_log, 256)

            if ret >= 0:
                if ret == 0:
                    print("На устройстве нет последних событий")
                else:
                    print(f"Обнаружены последние события: {rt_log.value.decode()}")
            else:
                error_code = self.commpro.PullLastError()
                print(f"Ошибка при проверке событий устройства. Код: {error_code}")

        except Exception as e:
            print(f"Ошибка при получении информации об устройстве: {e}")

    def _clear_previous_events(self):
        """Внутренняя функция: очищает предыдущие события в устройстве"""
        try:
            rt_log = create_string_buffer(256)
            while True:
                ret = self.commpro.GetRTLog(self.hcommpro, rt_log, 256)
                if ret <= 0:
                    break
        except Exception:
            pass

    def read_card(self):
        if not self.connected:
            print("Нет активного подключения")
            return None

        try:
            print("Поднесите RFID‑карту к считывателю...")
            print("Ожидание чтения RFID‑карты (максимум 10 секунд)...")

            # Очистить предыдущие события
            self._clear_previous_events()

            # Ждать обнаружения RFID‑карты
            timeout = time.time() + 10  # 10 секунд тайм‑аут

            while time.time() < timeout:
                try:
                    # Буфер для номера HID‑карты
                    card_buffer = create_string_buffer(64)

                    # Получить номер HID‑карты из последнего события
                    ret = self.commpro.GetHIDEventCardNumAsStr(byref(card_buffer))

                    if ret:  # True — успех
                        card_number = card_buffer.value.decode("utf-8", errors="ignore").strip()
                        if card_number and card_number != "0":
                            print(f"Обнаружена RFID‑карта: {card_number}")
                            return card_number

                    # Дополнительно проверить события в реальном времени как резерв
                    rt_log = create_string_buffer(256)
                    ret_rt = self.commpro.GetRTLog(self.hcommpro, rt_log, 256)
                    if ret_rt > 0:
                        data = rt_log.value.decode("utf-8", errors="ignore")
                        if data:
                            print(f"Событие в реальном времени: {data}")

                    time.sleep(0.2)

                except Exception:
                    time.sleep(0.2)

            print("Карта не была обнаружена за отведённое время.")
            return None

        except Exception as e:
            print(f"Ошибка при чтении карты: {e}")
            return None

    def _print_error_description(self, error_code):
        """Выводит текстовое описание кода ошибки SDK"""
        error_descriptions = {
            0: "Успешно",
            -1: "Не удалось подключиться к устройству",
            -2: "Устройство не подключено",
            -3: "Ошибка проверки пароля",
            -4: "Устройство занято",
            -5: "Неверный параметр",
            -6: "Выделение памяти не удалось",
            -7: "Время ожидания истекло",
            -8: "Ошибка чтения/записи",
            -9: "Порт не открыт",
            -10: "Устройство не найдено",
            -11: "Операция не поддерживается",
            -12: "Ошибка формата данных",
            -13: "Ошибка доступа",
            -102: "Формат полей записи не соответствует формату таблицы",
            -103: "Последовательность полей не является согласованной",
            -104: "Ошибка данных событий в реальном времени",
            -105: "Ошибка данных при разборе информации",
            -106: "Переполнение данных: передано более 4 МБ данных",
            -107: "Ошибка получения структуры таблицы",
            -108: "Недопустимые параметры",
        }

        description = error_descriptions.get(error_code, f"Неизвестный код ошибки: {error_code}")
        print(f"Описание ошибки: {description}")

    def control_device(self, operation_id=1, door_id=1, index=1, state=3):
        """Управляет устройством (открыть дверь, сбросить тревогу и т.д.)"""
        if not self.connected:
            print("Нет активного подключения")
            return False

        try:
            print(f"Управление устройством — операция: {operation_id}, дверь: {door_id}, состояние: {state}")

            options = create_string_buffer(b"")
            ret = self.commpro.ControlDevice(
                self.hcommpro,
                operation_id,  # Идентификатор операции
                door_id,  # Номер двери
                index,  # Тип адреса (1 = выход двери, 2 = дополнительный выход)
                state,  # Время открытия в секундах
                0,  # Резерв
                options,  # Дополнительные параметры (пусто)
            )

            if ret >= 0:
                if operation_id == 1:
                    print(f"Дверь {door_id} активирована на {state} секунд(ы)")
                elif operation_id == 2:
                    print("Тревога отменена")
                elif operation_id == 3:
                    print("Устройство перезапущено")
                elif operation_id == 4:
                    status = "включён" if state == 1 else "выключен"
                    print(f"Режим \"нормально открыто\" {status}")
                return True
            else:
                error_code = self.commpro.PullLastError()
                print(f"Ошибка при управлении устройством. Код: {error_code}")
                self._print_error_description(error_code)
                return False

        except Exception as e:
            print(f"Ошибка при управлении устройством: {e}")
            return False

    def test_device_communication(self):
        """Проверка связи с устройством"""
        if not self.connected:
            print("Нет активного подключения")
            return False

        try:
            print("Проверяю связь с устройством...")

            # Попытка получить базовую информацию об устройстве
            buffer = create_string_buffer(1024)
            items = "DeviceID,~DeviceName,~SerialNumber,Door1SensorType"
            p_items = create_string_buffer(items.encode())
            ret = self.commpro.GetDeviceParam(self.hcommpro, buffer, 1024, p_items)

            if ret >= 0:
                device_info = buffer.value.decode("utf-8", errors="ignore")
                print(f"Связь успешна. Информация об устройстве: {device_info}")
                return True
            else:
                error_code = self.commpro.PullLastError()
                print(f"Ошибка связи. Код: {error_code}")
                self._print_error_description(error_code)
                return False

        except Exception as e:
            print(f"Ошибка при проверке связи: {e}")
            return False


def menu():
    device = ZKTecoDevice()

    while True:
        print("\n=== УПРАВЛЕНИЕ ТУРНИКЕТОМ TS 2011 PRO ===")
        print("1. Подключиться к устройству")
        print("2. Получить информацию об устройстве")
        print("3. Считать RFID‑карту")
        print("4. Активировать турникет (5 секунд)")
        print("5. Проверить связь с устройством")
        print("6. Отключиться")
        print("0. Выход")

        opcion = input("\nВыберите пункт меню: ")

        if opcion == "1":
            ip = input("IP‑адрес устройства [10.122.0.201]: ") or "10.122.0.201"
            device.connect(ip_address=ip)
        elif opcion == "2":
            device.get_device_info()
        elif opcion == "3":
            device.read_card()
        elif opcion == "4":
            device.control_device(operation_id=1, door_id=1, index=1, state=5)
        elif opcion == "5":
            device.test_device_communication()
        elif opcion == "6":
            device.disconnect()
        elif opcion == "0":
            if device.connected:
                device.disconnect()
            print("Программа завершена")
            break
        else:
            print("Неверный пункт меню. Повторите ввод.")


if __name__ == "__main__":
    menu()

