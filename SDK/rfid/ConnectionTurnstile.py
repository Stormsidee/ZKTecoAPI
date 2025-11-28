"""
Модуль для подключения и чтения RFID‑карт с турникета ZKTeco C2‑260,
основанный на наборе протестированных функций устройства.
"""
import time
import sys
from datetime import datetime

try:
    import pythoncom
    import win32com.client
except ImportError:
    print("Для работы этого скрипта требуется PyWin32. Установите его командой: pip install pywin32")
    print("Выполняю: pip install pywin32")
    import subprocess

    subprocess.call([sys.executable, "-m", "pip", "install", "pywin32"])
    print("Пожалуйста, перезапустите скрипт после установки.")
    sys.exit(1)


class ConnectionTurnstile:
    def __init__(self):
        """Инициализирует подключение к турникету ZKTeco"""
        self.device_id = 1  # Идентификатор устройства по умолчанию
        self.zkem = None
        self.connected = False
        self.device_info = {}

        # Инициализировать COM
        try:
            pythoncom.CoInitialize()
            self.zkem = win32com.client.Dispatch("zkemkeeper.ZKEM.1")
            print("COM‑интерфейс zkemkeeper успешно инициализирован")
        except Exception as e:
            print(f"Ошибка при инициализации zkemkeeper: {e}")
            sys.exit(1)

    def connect(self, ip="10.122.0.201", port=14370):
        """Подключается к устройству ZKTeco с указанными параметрами"""
        if not self.zkem:
            print("COM‑интерфейс не инициализирован.")
            return False

        try:
            print(f"Подключаюсь к {ip}:{port}...")
            if self.zkem.Connect_Net(ip, port):
                self.connected = True
                print("✓ Подключение успешно установлено")

                # Получить базовую информацию об устройстве
                self._get_device_info()

                # Разрешить устройству отправлять события
                if self.zkem.EnableDevice(self.device_id, True):
                    print("✓ Устройство успешно включено")
                else:
                    print("✗ Не удалось включить устройство")

                return True
            else:
                print("✗ Ошибка при подключении к устройству")
                error_code = self.zkem.GetLastError()
                print(f"  Код ошибки: {error_code}")
                return False
        except Exception as e:
            print(f"Ошибка во время подключения: {e}")
            return False

    def disconnect(self):
        """Отключается от устройства"""
        if self.connected and self.zkem:
            try:
                self.zkem.Disconnect()
                print("Устройство отключено")
                self.connected = False
                return True
            except Exception as e:
                print(f"Ошибка при отключении: {e}")
        return False

    def _get_device_info(self):
        """Получает и сохраняет информацию об устройстве"""
        if not self.connected:
            return

        try:
            # Использовать функции, которые корректно отработали в тестах
            self.device_info["firmware"] = self.zkem.GetFirmwareVersion(self.device_id)[1]
            self.device_info["mac"] = self.zkem.GetDeviceMAC(self.device_id)[1]
            self.device_info["serial"] = self.zkem.GetSerialNumber(self.device_id)[1]
            self.device_info["ip"] = self.zkem.GetDeviceIP(self.device_id)[1]
            self.device_info["product_code"] = self.zkem.GetProductCode(self.device_id)[1]
            self.device_info["vendor"] = self.zkem.GetVendor()[1]
            self.device_info["platform"] = self.zkem.GetPlatform(self.device_id)[1]

            print("\n=== Информация об устройстве ===")
            print(f"Модель: {self.device_info.get('product_code', 'Неизвестно')}")
            print(f"Прошивка: {self.device_info.get('firmware', 'Неизвестно')}")
            print(f"Серийный номер: {self.device_info.get('serial', 'Неизвестно')}")
            print(f"MAC‑адрес: {self.device_info.get('mac', 'Неизвестно')}")
            print(f"IP‑адрес: {self.device_info.get('ip', 'Неизвестно')}")
            print(f"Производитель: {self.device_info.get('vendor', 'Неизвестно')}")
            print(f"Платформа: {self.device_info.get('platform', 'Неизвестно')}")
            print("=" * 40)

        except Exception as e:
            print(f"Ошибка при получении информации об устройстве: {e}")

    def read_cards(self, duration=None):
        """
        Читает RFID‑карты в течение заданного времени или бесконечно.

        Аргументы:
            duration: Время в секундах для чтения карт. None — читать без ограничений.
        """
        if not self.connected:
            print("Нет активного подключения к устройству.")
            return

        try:
            print("\nОжидание поднесения карты...")
            print("Нажмите Ctrl+C для остановки.")

            # Зарегистрировать события
            self.zkem.RegEvent(self.device_id, 0xFFFF)

            start_time = time.time()

            while True:
                # Ограничение по времени, если передано duration
                if duration is not None and (time.time() - start_time) > duration:
                    print("\nВремя ожидания чтения карт истекло.")
                    break

                # Попробовать получить номер карты
                try:
                    result, card_number = self.zkem.GetStrCardNumber()
                    if result and card_number and card_number != "0":
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{timestamp}] Обнаружена карта: {card_number}")
                except Exception:
                    pass

                time.sleep(0.2)

        except KeyboardInterrupt:
            print("\nЧтение карт остановлено пользователем.")
        except Exception as e:
            print(f"Ошибка при чтении карт: {e}")

    def get_users(self):
        """Получает список пользователей/карт, зарегистрированных на устройстве"""
        if not self.connected:
            print("Нет активного подключения к устройству.")
            return

        print("\nПолучаю список зарегистрированных пользователей...")

        try:
            # Заблокировать устройство на время считывания
            self.zkem.EnableDevice(self.device_id, False)
            time.sleep(0.5)

            # Получить всех пользователей
            if not self.zkem.ReadAllUserID(self.device_id):
                print("✗ Не удалось прочитать информацию о пользователях")
                self.zkem.EnableDevice(self.device_id, True)
                return

            print("\n=== Зарегистрированные пользователи/карты ===")
            count = 0

            # Основной способ чтения пользователей
            try:
                while True:
                    result, user_id = self.zkem.SSR_GetAllUserInfo(self.device_id)
                    if not result:
                        break

                    # Пытаемся получить номер карты
                    card_result, card_number = self.zkem.GetStrCardNumber()

                    if card_result and card_number and card_number != "0":
                        count += 1
                        print(f"Пользователь #{count}: ID={user_id}, Карта={card_number}")
            except Exception:
                if count == 0:
                    print("Не удалось получить пользователей основным методом")

            # Если никого не нашли — попробовать альтернативный метод
            if count == 0:
                try:
                    # Перебор возможных ID
                    for i in range(1, 100):
                        user_id = str(i)
                        # Попытка получить информацию о пользователе
                        if self.zkem.SSR_GetUserInfo(self.device_id, user_id):
                            card_result, card_number = self.zkem.GetStrCardNumber()
                            if card_result and card_number and card_number != "0":
                                count += 1
                                print(f"Пользователь #{count}: ID={user_id}, Карта={card_number}")
                except Exception:
                    pass

            if count == 0:
                print("Пользователи с привязанными картами не найдены.")
            else:
                print(f"Всего найдено пользователей/карт: {count}")

        except Exception as e:
            print(f"Ошибка при получении списка пользователей: {e}")
        finally:
            self.zkem.EnableDevice(self.device_id, True)


def main():
    """Главная функция для проверки подключения к турникету"""
    print("=" * 60)
    print("     СИСТЕМА ПОДКЛЮЧЕНИЯ К ТУРНИКЕТУ ZKTECO C2‑260")
    print("=" * 60)

    conn = ConnectionTurnstile()

    # Запрос параметров подключения
    ip = input("Введите IP‑адрес устройства (по умолчанию 10.122.0.201): ") or "10.122.0.201"
    port_str = input("Введите порт устройства (по умолчанию 14370): ") or "14370"
    port = int(port_str)

    if conn.connect(ip, port):
        try:
            while True:
                print("\n" + "=" * 50)
                print("         МЕНЮ ОПЕРАЦИЙ")
                print("=" * 50)
                print("1. Чтение RFID‑карт")
                print("2. Показать информацию об устройстве")
                print("3. Получить список пользователей/карт")
                print("4. Выход")
                print("=" * 50)

                option = input("Выберите пункт меню: ")

                if option == "1":
                    # Спросить длительность чтения
                    dur_str = input("Введите длительность чтения в секундах (Enter — без ограничений): ")
                    duration = int(dur_str) if dur_str else None

                    conn.read_cards(duration)
                    input("\nНажмите Enter для продолжения...")

                elif option == "2":
                    conn._get_device_info()
                    input("\nНажмите Enter для продолжения...")

                elif option == "3":
                    conn.get_users()
                    input("\nНажмите Enter для продолжения...")

                elif option == "4":
                    print("Завершение программы...")
                    break

                else:
                    print("Неверный пункт меню. Пожалуйста, выберите корректный вариант.")

        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем.")
        finally:
            conn.disconnect()

    print("Программа завершена.")


if __name__ == "__main__":
    main()

