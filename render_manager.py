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

# --- Appearance Settings ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class BlenderRenderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Main Window Setup
        self.title("Blender Render Manager")
        self.geometry("650x650") # Increased height to fit footer
        self.resizable(True, True) # Enabled resizing for adaptability

        # Data Variables
        self.blender_exe_path = tk.StringVar()
        self.project_path = tk.StringVar()
        self.start_frame = tk.StringVar(value="1")
        self.end_frame = tk.StringVar(value="250")
        
        # Logic Variables
        self.is_rendering = False
        self.process = None
        self.start_time_render = None

        # Determine path for settings file (works for both .py and .exe)
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        self.settings_file = os.path.join(application_path, "settings.json")

        # Load settings and draw UI
        self.load_settings()
        self.create_widgets()

    def create_widgets(self):
        # --- BLOCK 1: Blender Selection (Setup once) ---
        self.frame_setup = ctk.CTkFrame(self)
        self.frame_setup.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(self.frame_setup, text="Path to blender.exe:", font=("Roboto", 12, "bold")).pack(anchor="w", padx=10, pady=(10, 0))
        
        setup_inner = ctk.CTkFrame(self.frame_setup, fg_color="transparent")
        setup_inner.pack(fill="x", padx=10, pady=10)

        self.entry_blender = ctk.CTkEntry(setup_inner, textvariable=self.blender_exe_path)
        self.entry_blender.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.btn_browse_blender = ctk.CTkButton(setup_inner, text="Browse", width=80, command=self.select_blender_exe)
        self.btn_browse_blender.pack(side="right")

        # --- BLOCK 2: Project Selection (Dynamic) ---
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
        self.frame_range.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.frame_range, text="Start Frame:").pack(side="left", padx=(0, 5))
        ctk.CTkEntry(self.frame_range, textvariable=self.start_frame, width=60).pack(side="left")
        
        ctk.CTkLabel(self.frame_range, text="End Frame:").pack(side="left", padx=(15, 5))
        ctk.CTkEntry(self.frame_range, textvariable=self.end_frame, width=60).pack(side="left")

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
        self.lbl_time.pack(pady=(0, 10))

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
            except:
                pass

    def save_settings(self):
        data = {"blender_path": self.blender_exe_path.get()}
        try:
            with open(self.settings_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            self.log(f"Error saving settings: {e}")

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
        
        # Validation: Start Frame cannot be > End Frame
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
        
        threading.Thread(target=self.run_blender_process, daemon=True).start()

    def run_blender_process(self):
        exe = self.blender_exe_path.get()
        blend = self.project_path.get()
        start = self.start_frame.get()
        end = self.end_frame.get()

        # Build Command
        command = [exe, "-b", blend, "-s", start, "-e", end, "-a"]
        
        self.log(f"Running: {' '.join(command)}")
        self.start_time_render = time.time()
        
        try:
            # Hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding='utf-8', # Force UTF-8 decoding to fix charmap error
                errors='replace', # Replace unreadable characters instead of crashing
                bufsize=1,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            total_frames_count = int(end) - int(start) + 1
            
            # Read Blender output
            for line in self.process.stdout:
                if not self.is_rendering:
                    break
                
                # Show log
                self.textbox.insert("end", line)
                self.textbox.see("end")

                # Parse frame
                match = re.search(r"Fra:(\d+)", line)
                if match:
                    current_frame_abs = int(match.group(1))
                    
                    # Calculations
                    frames_done = current_frame_abs - int(start) + 1
                    
                    if frames_done < 1: frames_done = 1
                    if frames_done > total_frames_count: frames_done = total_frames_count

                    progress = frames_done / total_frames_count
                    
                    self.update_progress_ui(progress, frames_done, total_frames_count, current_frame_abs)

            self.process.wait()
            
            if self.is_rendering:
                self.finish_render(success=self.process.returncode == 0)

        except Exception as e:
            self.log(f"Critical Error: {str(e)}")
            self.finish_render(success=False)

    def update_progress_ui(self, progress, frames_done, total_frames, current_abs_frame):
        # 1. Update Bar
        self.progress_bar.set(progress)
        
        # 2. Time Math
        elapsed_time = time.time() - self.start_time_render
        avg_time_per_frame = elapsed_time / frames_done
        frames_left = total_frames - frames_done
        time_left_seconds = int(frames_left * avg_time_per_frame)
        
        # Format HH:MM:SS
        hours = time_left_seconds // 3600
        minutes = (time_left_seconds % 3600) // 60
        seconds = time_left_seconds % 60
        
        time_str = f"{hours} h {minutes:02} m {seconds:02} s"
        
        # 3. Update Text
        self.lbl_status.configure(text=f"Rendering: {int(progress*100)}%")
        self.lbl_frames.configure(text=f"Frame {current_abs_frame} of {self.end_frame.get()} (Remaining: {frames_left})")
        self.lbl_time.configure(text=f"Time remaining: {time_str}")

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
            messagebox.showinfo("Success", "Render completed successfully!")
        else:
            self.lbl_status.configure(text="STOPPED", text_color="#C92C2C")

    def log(self, message):
        self.textbox.insert("end", message + "\n")
        self.textbox.see("end")

if __name__ == "__main__":
    app = BlenderRenderApp()
    app.mainloop()