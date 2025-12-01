import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import threading
import subprocess
import time
import re
import sys
import datetime

# --- Appearance Settings ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class BlenderRenderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Main Window Setup
        self.title("Blender Render Manager")
        self.geometry("650x700") 
        self.resizable(True, True) 

        # Data Variables
        self.blender_exe_path = tk.StringVar()
        self.project_path = tk.StringVar()
        self.start_frame = tk.StringVar(value="1")
        self.end_frame = tk.StringVar(value="250")
        
        # New Option: Persistent Data
        self.use_persistent_data = ctk.BooleanVar(value=False)
        
        # Logic Variables
        self.is_rendering = False
        self.process = None
        self.start_time_render = None
        self.current_log_file = None 
        
        # Stats variables
        self.frames_finished_count = 0
        self.last_completed_frame = -1 # To prevent double counting mult-pass renders

        # Determine path for settings file and logs
        if getattr(sys, 'frozen', False):
            self.app_folder = os.path.dirname(sys.executable)
        else:
            self.app_folder = os.path.dirname(os.path.abspath(__file__))
        
        self.settings_file = os.path.join(self.app_folder, "settings.json")

        # Load settings and draw UI
        self.load_settings()
        self.create_widgets()

    def create_widgets(self):
        # --- BLOCK 1: Blender Selection ---
        self.frame_setup = ctk.CTkFrame(self)
        self.frame_setup.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.frame_setup, text="Path to blender.exe:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        setup_inner = ctk.CTkFrame(self.frame_setup, fg_color="transparent")
        setup_inner.pack(fill="x", padx=10, pady=10)

        self.entry_blender = ctk.CTkEntry(setup_inner, textvariable=self.blender_exe_path)
        self.entry_blender.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.btn_browse_blender = ctk.CTkButton(setup_inner, text="Browse", width=80, command=self.select_blender_exe)
        self.btn_browse_blender.pack(side="right")

        # --- BLOCK 2: Project Selection ---
        self.frame_project = ctk.CTkFrame(self)
        self.frame_project.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.frame_project, text="Project File (.blend):", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        proj_inner = ctk.CTkFrame(self.frame_project, fg_color="transparent")
        proj_inner.pack(fill="x", padx=10, pady=5)

        self.entry_project = ctk.CTkEntry(proj_inner, textvariable=self.project_path, placeholder_text="Select .blend file")
        self.entry_project.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.btn_browse_project = ctk.CTkButton(proj_inner, text="Browse", width=80, command=self.select_project)
        self.btn_browse_project.pack(side="right")

        # Frame Range Settings
        self.frame_range = ctk.CTkFrame(self.frame_project, fg_color="transparent")
        self.frame_range.pack(fill="x", padx=10, pady=(0, 5))
        
        ctk.CTkLabel(self.frame_range, text="Start Frame:").pack(side="left", padx=(0, 5))
        ctk.CTkEntry(self.frame_range, textvariable=self.start_frame, width=60).pack(side="left")
        
        ctk.CTkLabel(self.frame_range, text="End Frame:").pack(side="left", padx=(15, 5))
        ctk.CTkEntry(self.frame_range, textvariable=self.end_frame, width=60).pack(side="left")

        # Options Frame (Persistent Data)
        self.frame_options = ctk.CTkFrame(self.frame_project, fg_color="transparent")
        self.frame_options.pack(fill="x", padx=10, pady=(0, 10))
        
        # Checkbox for Persistent Data
        self.chk_persistent = ctk.CTkCheckBox(
            self.frame_options, 
            text="Use Persistent Data (Faster Animation)", 
            variable=self.use_persistent_data,
            font=("Roboto", 11)
        )
        self.chk_persistent.pack(side="left", padx=0)

        # --- BLOCK 3: Status and Progress ---
        self.frame_progress = ctk.CTkFrame(self)
        self.frame_progress.pack(pady=10, padx=20, fill="x")

        self.lbl_status = ctk.CTkLabel(self.frame_progress, text="Waiting to start...", font=("Roboto", 14))
        self.lbl_status.pack(pady=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(self.frame_progress)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=20, pady=10)

        # Detailed Statistics
        self.lbl_frames = ctk.CTkLabel(self.frame_progress, text="Frames: 0 / 0 (Remaining: 0)")
        self.lbl_frames.pack(pady=2)

        self.lbl_time = ctk.CTkLabel(self.frame_progress, text="Estimated time: -- h -- m -- s", font=("Roboto", 13, "bold"))
        self.lbl_time.pack(pady=(0, 5))
        
        # New Label for Last Frame Time
        self.lbl_last_frame = ctk.CTkLabel(self.frame_progress, text="Last frame time: ...", font=("Roboto", 11), text_color="gray70")
        self.lbl_last_frame.pack(pady=(0, 10))

        # --- BLOCK 4: Control Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5, padx=20, fill="x")

        self.btn_start = ctk.CTkButton(btn_frame, text="START RENDER", fg_color="#2CC985", hover_color="#229A65", height=40, command=self.start_render_thread)
        self.btn_start.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.btn_stop = ctk.CTkButton(btn_frame, text="STOP", fg_color="#C92C2C", hover_color="#9A2222", height=40, state="disabled", command=self.stop_render)
        self.btn_stop.pack(side="right", expand=True, fill="x", padx=(10, 0))

        # --- BLOCK 5: Console ---
        ctk.CTkLabel(self, text="Process Log:", font=("Roboto", 10)).pack(anchor="w", padx=25)
        self.textbox = ctk.CTkTextbox(self, height=120, font=("Consolas", 11))
        self.textbox.pack(pady=(0, 10), padx=20, fill="both")

        # --- BLOCK 6: Footer ---
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.pack(side="bottom", anchor="e", padx=20, pady=(0, 10))

        ctk.CTkLabel(footer_frame, text="Made by Pavel Postnikov for SETT", font=("Roboto", 10), text_color="gray70").pack(anchor="e")
        ctk.CTkLabel(footer_frame, text="SETT Render Launcher v 2.0", font=("Roboto", 10, "bold"), text_color="gray70").pack(anchor="e")

    # --- File Operations ---
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.blender_exe_path.set(data.get("blender_path", ""))
                    # Optional: Load persistent data setting if you want to remember it
                    # self.use_persistent_data.set(data.get("persistent_data", False))
            except:
                pass

    def save_settings(self):
        data = {
            "blender_path": self.blender_exe_path.get(),
            # "persistent_data": self.use_persistent_data.get() # Uncomment to save this setting
        }
        try:
            with open(self.settings_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def select_blender_exe(self):
        filename = filedialog.askopenfilename(title="Find blender.exe", filetypes=[("Executable", "*.exe")])
        if filename:
            self.blender_exe_path.set(filename)
            self.save_settings()

    def select_project(self):
        filename = filedialog.askopenfilename(title="Select Project", filetypes=[("Blender File", "*.blend")])
        if filename:
            self.project_path.set(filename)

    # --- Render Logic ---
    def start_render_thread(self):
        if not self.blender_exe_path.get() or not self.project_path.get():
            messagebox.showwarning("Warning", "Select Blender.exe and project file!")
            return
        
        try:
            s_frame = int(self.start_frame.get())
            e_frame = int(self.end_frame.get())
            if s_frame > e_frame:
                messagebox.showerror("Error", "Start Frame cannot be greater than End Frame!")
                return
        except ValueError:
             messagebox.showerror("Error", "Frames must be valid numbers!")
             return

        # UI Preparation
        self.is_rendering = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Starting Blender...", text_color="white")
        self.textbox.delete("0.0", "end")
        
        # Reset Stats
        self.frames_finished_count = 0
        self.last_completed_frame = -1
        
        # --- LOGGING SETUP ---
        try:
            logs_dir = os.path.join(self.app_folder, "Logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Format: YYYY-MM-DD_HH-MM-SS.txt
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.current_log_file = os.path.join(logs_dir, f"{timestamp}.txt")
            
            self.log(f"--- Render Session Started: {timestamp} ---")
            self.log(f"Blender: {self.blender_exe_path.get()}")
            self.log(f"Project: {self.project_path.get()}")
            self.log(f"Range: {s_frame} to {e_frame}")
            self.log(f"Persistent Data: {self.use_persistent_data.get()}")
            self.log("-" * 40)
            
        except Exception as e:
            self.log(f"Error initializing log file: {e}")

        threading.Thread(target=self.run_blender_process, daemon=True).start()

    def run_blender_process(self):
        exe = self.blender_exe_path.get()
        blend = self.project_path.get()
        start = int(self.start_frame.get())
        end = int(self.end_frame.get())
        
        project_folder = os.path.dirname(blend)

        # Base Command
        command = [exe, "-b", blend]
        
        # --- Inject Persistent Data Command (If Checked) ---
        if self.use_persistent_data.get():
            # This Python one-liner attempts to set use_persistent_data=True for the current scene's Cycles settings
            # We use try/except to avoid crashing if the scene isn't using Cycles
            py_cmd = "import bpy; \ntry: bpy.context.scene.cycles.use_persistent_data = True\nexcept: pass"
            command.extend(["--python-expr", py_cmd])

        # Append Frame Range and Animation flag
        command.extend(["-s", str(start), "-e", str(end), "-a"])
        
        self.log(f"Command: {' '.join(command)}")
        self.start_time_render = time.time()
        
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                cwd=project_folder, 
                encoding='utf-8', 
                errors='replace', 
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            total_frames_to_render = end - start + 1
            
            for line in self.process.stdout:
                if not self.is_rendering:
                    break
                
                # Log to UI and File
                self.log(line.strip())

                # --- 1. Check for "Time: MM:SS.ms" (Exact Time Reported by Blender) ---
                # Example: "Time: 02:04.96 (Saving: 00:00.22)"
                time_match = re.search(r"Time:\s*(\d+):(\d+)\.(\d+)", line)
                if time_match:
                    minutes = int(time_match.group(1))
                    seconds = int(time_match.group(2))
                    milliseconds = int(time_match.group(3))
                    
                    exact_duration = (minutes * 60) + seconds + (milliseconds / 100.0)
                    
                    self.update_progress_ui(
                        self.frames_finished_count, # Use the count we gathered from "Saved"
                        total_frames_to_render, 
                        current_active_frame=start + self.frames_finished_count,
                        last_frame_duration=exact_duration
                    )
                    continue

                # --- 2. Check for "Saved: ...2296.png" (Frame Finished) ---
                if "Saved:" in line or "Сохранено:" in line:
                    frame_match = re.search(r"(\d+)\.[a-zA-Z0-9]+['\"]?$", line.strip())
                    
                    if frame_match:
                        finished_frame_num = int(frame_match.group(1))
                        
                        # Prevent double counting for multi-pass renders
                        if finished_frame_num != self.last_completed_frame:
                            self.frames_finished_count += 1
                            self.last_completed_frame = finished_frame_num
                            
                            self.update_progress_ui(
                                self.frames_finished_count, 
                                total_frames_to_render, 
                                current_active_frame=finished_frame_num,
                                last_frame_duration=None 
                            )

            self.process.wait()
            
            if self.is_rendering:
                self.finish_render(success=self.process.returncode == 0)

        except Exception as e:
            self.log(f"Critical Error: {str(e)}")
            self.finish_render(success=False)

    def update_progress_ui(self, frames_done_count, total_frames_count, current_active_frame, last_frame_duration=None):
        # Progress Ratio
        progress = frames_done_count / total_frames_count
        self.progress_bar.set(progress)
        
        # Calculate Average Time based on total elapsed
        elapsed_total = time.time() - self.start_time_render
        
        frames_left = total_frames_count - frames_done_count
        time_str = "Calculating..."
        
        if frames_done_count > 0:
            avg_time_per_frame = elapsed_total / frames_done_count
            time_left_seconds = int(frames_left * avg_time_per_frame)
            
            hours = time_left_seconds // 3600
            minutes = (time_left_seconds % 3600) // 60
            seconds = time_left_seconds % 60
            
            time_str = f"{hours} h {minutes:02} m {seconds:02} s"
        
        # Update Labels
        self.lbl_status.configure(text=f"Progress: {int(progress*100)}%")
        self.lbl_frames.configure(text=f"Finished Frame: {current_active_frame} / {self.end_frame.get()} (Remaining: {frames_left})")
        self.lbl_time.configure(text=f"Estimated time left: {time_str}")
        
        # Update Last Frame Time if provided
        if last_frame_duration is not None:
            m = int(last_frame_duration // 60)
            s = int(last_frame_duration % 60)
            self.lbl_last_frame.configure(text=f"Last frame time: {m}m {s}s")

    def stop_render(self):
        if self.process:
            self.is_rendering = False
            self.process.terminate()
            self.log("\n!!! FORCED STOP BY USER !!!")
            self.finish_render(success=False)

    def finish_render(self, success):
        self.is_rendering = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        
        if success:
            self.lbl_status.configure(text="DONE!", text_color="#2CC985")
            self.progress_bar.set(1)
            self.log("Render completed successfully.")
            messagebox.showinfo("Success", "Render completed successfully!")
        else:
            self.lbl_status.configure(text="STOPPED/ERROR", text_color="#C92C2C")
            self.log("Render process finished with errors or was stopped.")

    def log(self, message):
        # 1. Update UI
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")
        
        # 2. Write to File (Append mode)
        if self.current_log_file:
            try:
                with open(self.current_log_file, "a", encoding="utf-8") as f:
                    f.write(message + "\n")
            except Exception:
                pass 

if __name__ == "__main__":
    app = BlenderRenderApp()
    app.mainloop()