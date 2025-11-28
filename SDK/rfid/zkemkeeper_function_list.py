"""
Скрипт для извлечения списка функций из библиотеки zkemkeeper.dll через COM.

Этот скрипт подключается к COM‑компоненту zkemkeeper и перечисляет
все доступные функции, а также (по возможности) информацию
о параметрах и возвращаемых значениях.
"""

import os
import sys
import time
from datetime import datetime

try:
    import pythoncom
    import win32com.client
    import win32com.client.gencache
    from win32com.client import makepy
except ImportError:
    print("Для работы этого скрипта требуется PyWin32. Установите его командой: pip install pywin32")
    sys.exit(1)


def create_zkemkeeper_types():
    """Пытается сгенерировать информацию о типах для zkemkeeper"""
    try:
        # Форсировать генерацию файлов кэша типов
        win32com.client.gencache.EnsureModule("{00853A19-BD51-419B-9269-2DABE57EB61F}", 0, 1, 0)
        print("Генерация информации о типах для zkemkeeper завершена")
        return True
    except Exception:
        print("Не удалось сгенерировать информацию о типах для zkemkeeper")
        return False


def extract_zkemkeeper_methods():
    """Извлекает все доступные методы объекта COM zkemkeeper"""
    try:
        # Инициализация COM
        pythoncom.CoInitialize()

        # Создать экземпляр COM‑объекта
        zk = win32com.client.Dispatch("zkemkeeper.ZKEM.1")

        # Получить список всех методов
        method_names = [m for m in dir(zk) if not m.startswith("_")]

        # Организовать методы по категориям
        categories = {
            "Подключение": [],
            "Контроль доступа": [],
            "Карты": [],
            "Пользователи": [],
            "Журналы": [],
            "Система": [],
            "Прочее": [],
        }

        # Классифицировать методы
        for method in method_names:
            if method.startswith(("Connect", "Disconnect", "SetCommPassword", "GetLastError")):
                categories["Подключение"].append(method)
            elif method.startswith(("Get", "Set")) and ("Door" in method or "Lock" in method or "Alarm" in method):
                categories["Контроль доступа"].append(method)
            elif "Card" in method:
                categories["Карты"].append(method)
            elif "User" in method or "Enroll" in method or "Fingerprint" in method:
                categories["Пользователи"].append(method)
            elif "Log" in method or "Record" in method or "Attendance" in method:
                categories["Журналы"].append(method)
            elif method.startswith(("Get", "Set")) and ("Time" in method or "Date" in method or "Device" in method):
                categories["Система"].append(method)
            else:
                categories["Прочее"].append(method)

        return categories, method_names

    except Exception as e:
        print(f"Ошибка при извлечении методов: {e}")
        return None, []
    finally:
        pythoncom.CoUninitialize()


def try_connect_device():
    """Пробует подключиться к устройству ZKTeco"""
    try:
        pythoncom.CoInitialize()
        zk = win32com.client.Dispatch("zkemkeeper.ZKEM.1")

        print("\n==== ТЕСТ ПОДКЛЮЧЕНИЯ ====")
        print("Этот раздел пытается подключиться к устройству ZKTeco,")
        print("чтобы проверить, что COM‑интерфейс работает корректно.")

        # Запрос параметров подключения
        ip = input("Введите IP‑адрес устройства (по умолчанию 10.122.0.201): ") or "10.122.0.201"
        port_str = input("Введите порт устройства (по умолчанию 14370): ") or "14370"
        port = int(port_str)

        print(f"\nПробую подключиться к {ip}:{port}...")

        # Попытка подключения
        if zk.Connect_Net(ip, port):
            print("✓ Успешное подключение к устройству")
            device_id = 1

            print("\n==== ИНФОРМАЦИЯ ОБ УСТРОЙСТВЕ ====")
            # Версия прошивки
            try:
                success, firmware = zk.GetFirmwareVersion(device_id)
                if success:
                    print(f"Прошивка: {firmware}")
            except Exception:
                print("Не удалось получить версию прошивки")

            # Серийный номер
            try:
                success, serial = zk.GetSerialNumber(device_id)
                if success:
                    print(f"Серийный номер: {serial}")
            except Exception:
                print("Не удалось получить серийный номер")

            # Модель
            try:
                success, model = zk.GetProductCode(device_id)
                if success:
                    print(f"Модель: {model}")
            except Exception:
                print("Не удалось получить модель")

            # Производитель
            try:
                success, vendor = zk.GetVendor()
                if success:
                    print(f"Производитель: {vendor}")
            except Exception:
                print("Не удалось получить производителя")

            # Отключение
            zk.Disconnect()
            print("\n✓ Устройство отключено")
            return True
        else:
            print("✗ Не удалось подключиться к устройству")
            error = zk.GetLastError()
            print(f"  Код ошибки: {error}")
            return False
    except Exception as e:
        print(f"Ошибка во время теста подключения: {e}")
        return False
    finally:
        pythoncom.CoUninitialize()


def save_methods_to_file():
    """Сохраняет список методов в файл"""
    categories, all_methods = extract_zkemkeeper_methods()

    if not categories:
        print("Не удалось получить список методов")
        return

    result_file = os.path.join("C:/Users/PC-HP/Desktop/rfid", "zkemkeeper_methods.txt")

    with open(result_file, "w", encoding="utf-8") as f:
        f.write("ДОСТУПНЫЕ МЕТОДЫ В ZKEMKEEPER.DLL\n")
        f.write("=" * 40 + "\n")
        f.write(f"Дата генерации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"Всего найдено методов: {len(all_methods)}\n\n")

        f.write("МЕТОДЫ ПО КАТЕГОРИЯМ:\n")
        f.write("=" * 40 + "\n\n")

        for category, methods in categories.items():
            f.write(f"\n{category.upper()} ({len(methods)} методов):\n")
            f.write("-" * 40 + "\n")
            for method in sorted(methods):
                f.write(f"  - {method}\n")

        f.write("\n\nПОЛНЫЙ СПИСОК МЕТОДОВ:\n")
        f.write("=" * 40 + "\n\n")

        for i, method in enumerate(sorted(all_methods), 1):
            f.write(f"{i:3}. {method}\n")

    print(f"\nСписок методов сохранён в {result_file}")


def main():
    print("ЭКСТРАКТОР ФУНКЦИЙ ИЗ ZKEMKEEPER.DLL")
    print("=" * 40)
    print("Этот скрипт извлекает доступные методы zkemkeeper.dll")
    print("через COM‑интерфейс, который является рекомендуемым")
    print("способом работы с этим компонентом.")

    print("\nДоступные действия:")
    print("1. Показать методы по категориям")
    print("2. Сохранить методы в файл")
    print("3. Проверить подключение к устройству ZKTeco")
    print("4. Выход")

    choice = input("\nВыберите действие (1-4): ")

    if choice == "1":
        # Создать информацию о типах (опционально)
        create_zkemkeeper_types()

        # Извлечь и показать методы
        categories, all_methods = extract_zkemkeeper_methods()
        if categories:
            print(f"\nНайдено всего {len(all_methods)} методов\n")

            for category, methods in categories.items():
                print(f"\n{category.upper()} ({len(methods)} методов):")
                print("-" * 40)
                for method in sorted(methods):
                    print(f"  - {method}")

    elif choice == "2":
        create_zkemkeeper_types()
        save_methods_to_file()

    elif choice == "3":
        try_connect_device()

    elif choice == "4":
        print("Выход...")

    else:
        print("Неверный вариант")


if __name__ == "__main__":
    main()

