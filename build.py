import PyInstaller.__main__
import customtkinter
import os
import sys

# 1. Получаем путь к библиотеке customtkinter, чтобы вшить её в exe
ctk_path = os.path.dirname(customtkinter.__file__)

# 2. Определяем разделитель путей (для Windows это точка с запятой)
separator = ';' if os.name == 'nt' else ':'

# 3. Параметры сборки
print("--- НАЧАЛО СБОРКИ ---")
print(f"Найден CustomTkinter: {ctk_path}")

PyInstaller.__main__.run([
    'render_manager.py',                  # Твой основной файл
    '--name=SETT_Render_Launcher',        # Имя будущей программы
    '--onefile',                          # Собрать всё в один .exe файл
    '--windowed',                         # Не показывать черное окно консоли при запуске
    f'--add-data={ctk_path}{separator}customtkinter', # Добавляем файлы темы
    '--clean',                            # Очистить кэш сборки
    '--noconfirm',                        # Не спрашивать подтверждение перезаписи
])

print("\n--- СБОРКА ЗАВЕРШЕНА ---")
print("Ищи файл .exe в папке 'dist'")