import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
import os
import time
import json

# Настройки темы (Dark Mode)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

VERSION = "v 0.4 (Modern)"
SETTINGS_FILE = "settings.json"

class BlenderRenderGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.title(f"Sett Blender Cycles Render - {VERSION}")
        self.geometry("700x550")
        self.resizable(False, False)

        # Загрузка сохраненных путей
        self.saved_settings = self.load_settings()

        # --- UI LAYOUT ---
        self.grid_columnconfigure(0, weight=1)

        # Заголовок
        self.header = ctk.CTkLabel(self, text="SETT RENDER LAUNCHER", font=("Roboto", 24, "bold"), text_color="#4056F4")
        self.header.grid(row=0, column=0, pady=(20, 10))

        # Фрейм выбора файлов
        self.files_frame = ctk.CTkFrame(self)
        self.files_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # Blender Path
        self.create_file_selector(self.files_frame, 0, "Blender.exe:", self.saved_settings.get("blender_path", ""), self.select_blender)
        self.blender_entry = self.files_frame.grid_slaves(row=0, column=1)[0] # Ссылка на поле ввода

        # Project Path
        self.create_file_selector(self.files_frame, 1, ".blend Project:", self.saved_settings.get("blend_path", ""), self.select_blend)
        self.blend_entry = self.files_frame.grid_slaves(row=1, column=1)[0]

        # Фрейм настроек рендера
        self.settings_frame = ctk.CTkFrame(self)
        self.settings_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Start / End Frames
        ctk.CTkLabel(self.settings_frame, text="Start Frame:").grid(row=0, column=0, padx=10, pady=10)
        self.entry_start = ctk.CTkEntry(self.settings_frame, width=60, placeholder_text="1")
        self.entry_start.grid(row=0, column=1, padx=5)
        
        ctk.CTkLabel(self.settings_frame, text="End Frame:").grid(row=0, column=2, padx=10, pady=10)
        self.entry_end = ctk.CTkEntry(self.settings_frame, width=60, placeholder_text="250")
        self.entry_end.grid(row=0, column=3, padx=5)

        # Кнопка запуска
        self.render_button = ctk.CTkButton(self, text="LAUNCH RENDER", height=50, font=("Roboto", 16, "bold"), 
                                           fg_color="#4056F4", hover_color="#3040bf", command=self.launch_render)
        self.render_button.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        # Статус и Прогресс
        self.status_label = ctk.CTkLabel(self, text="Ready to render", text_color="gray")
        self.status_label.grid(row=4, column=0)

        self.progress_bar = ctk.CTkProgressBar(self, width=500)
        self.progress_bar.grid(row=5, column=0, pady=(5, 20))
        self.progress_bar.set(0)

        # Кнопка папки
        self.open_folder_btn = ctk.CTkButton(self, text="Open Output Folder", command=self.open_output_folder, fg_color="transparent", border_width=1)
        self.open_folder_btn.grid(row=6, column=0, pady=5)

        # Footer
        self.footer = ctk.CTkLabel(self, text="Made by Pavel Postnikov for SETT", font=("Arial", 10), text_color="gray30")
        self.footer.grid(row=7, column=0, pady=10, sticky="s")

    def create_file_selector(self, parent, row, label_text, default_val, cmd):
        ctk.CTkLabel(parent, text=label_text).grid(row=row, column=0, padx=10, pady=10, sticky="e")
        entry = ctk.CTkEntry(parent, width=350)
        entry.grid(row=row, column=1, padx=5, pady=10)
        entry.insert(0, default_val)
        ctk.CTkButton(parent, text="Browse", width=80, command=cmd).grid(row=row, column=2, padx=10)

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_settings(self):
        data = {
            "blender_path": self.blender_entry.get(),
            "blend_path": self.blend_entry.get()
        }
        with open(SETTINGS_FILE, "w") as f:
            json.dump(data, f)

    def select_blender(self):
        path = filedialog.askopenfilename(filetypes=[("Blender Executable", "*.exe")])
        if path:
            self.blender_entry.delete(0, "end")
            self.blender_entry.insert(0, path)
            self.save_settings()

    def select_blend(self):
        path = filedialog.askopenfilename(filetypes=[("Blender File", "*.blend")])
        if path:
            self.blend_entry.delete(0, "end")
            self.blend_entry.insert(0, path)
            self.save_settings()

    def open_output_folder(self):
        path = self.blend_entry.get()
        if path:
            folder = os.path.dirname(path)
            if os.path.exists(folder):
                os.startfile(folder)
            else:
                messagebox.showerror("Error", "Folder not found.")

    def launch_render(self):
        blender = self.blender_entry.get()
        blend = self.blend_entry.get()
        start_frame = self.entry_start.get()
        end_frame = self.entry_end.get()

        if not os.path.exists(blender) or not os.path.exists(blend):
            messagebox.showerror("Error", "Invalid paths.")
            return

        # Блокировка интерфейса
        self.render_button.configure(state="disabled", text="RENDERING...")
        self.progress_bar.set(0)
        
        # Формирование команды
        cmd = [blender, "-b", blend, "-a"] # По умолчанию вся анимация
        
        # Если указаны кадры, меняем аргументы
        if start_frame and end_frame:
            cmd = [blender, "-b", blend, "-s", start_frame, "-e", end_frame, "-a"]

        threading.Thread(target=self.run_render, args=(cmd,), daemon=True).start()

    def run_render(self, cmd):
        self.start_time = time.time()
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Попытка угадать общее количество кадров для прогресс бара
            try:
                start = int(self.entry_start.get()) if self.entry_start.get() else 1
                end = int(self.entry_end.get()) if self.entry_end.get() else 250
                total_frames = end - start
                if total_frames <= 0: total_frames = 1
            except:
                total_frames = 250

            for line in process.stdout:
                if "Fra:" in line: # Парсинг лога Блендера
                    # Пример строки: "Fra:10 Mem:200M ..."
                    parts = line.split()
                    for part in parts:
                        if "Fra:" in part:
                            try:
                                current_frame = int(part.split(":")[1])
                                # Вычисление прогресса (0.0 до 1.0 для CustomTkinter)
                                progress = (current_frame - start) / total_frames
                                self.progress_bar.set(progress)
                                self.status_label.configure(text=f"Rendering Frame: {current_frame} / {end}")
                            except:
                                pass
            process.wait()
            
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.status_label.configure(text=f"Done! Time: {mins}m {secs}s", text_color="green")

        except Exception as e:
            self.status_label.configure(text=f"Error: {e}", text_color="red")
        
        self.render_button.configure(state="normal", text="LAUNCH RENDER")

if __name__ == "__main__":
    app = BlenderRenderGUI()
    app.mainloop()