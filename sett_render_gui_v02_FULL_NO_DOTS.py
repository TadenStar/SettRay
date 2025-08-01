
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import subprocess
import threading
import time
import os
import json
import re
import sys

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except Exception:  # pragma: no cover - pillow not installed
    PIL_AVAILABLE = False

# --- Styling constants ---
THEME_BG = "#f0f2fa"
THEME_ACCENT = "#5b64f2"
THEME_DARK = "#1f2233"
THEME_BUTTON = "#3c3f58"
THEME_SUCCESS = "#4CAF50"

# Render settings window
class SettingsWindow(tk.Toplevel):
    def __init__(self, master, settings, save_callback=None):
        super().__init__(master)
        self.title("Render Settings")
        self.geometry("400x400")
        self.resizable(False, False)
        self.configure(bg=THEME_BG)

        self.settings = settings
        self._save_callback = save_callback

        # Simplify
        self.use_simplify = tk.BooleanVar(value=settings.get("use_simplify", False))
        simplify_check = tk.Checkbutton(
            self,
            text="Enable Simplify",
            variable=self.use_simplify,
            command=self.toggle_texture_limit,
            bg=THEME_BG,
        )
        simplify_check.pack(anchor="w", padx=10, pady=(10, 0))

        self.texture_limit_label = tk.Label(self, text="Texture Limit", bg=THEME_BG)
        self.texture_limit_combo = ttk.Combobox(self, values=[128, 256, 512, 1024, 2048, 4096, 8192])
        self.texture_limit_combo.set(settings.get("texture_limit", 2048))

        # Light Clamping
        tk.Label(self, text="Indirect Light Clamping", bg=THEME_BG).pack(anchor="w", padx=10, pady=(10, 0))
        self.clamping = tk.DoubleVar(value=settings.get("clamp_indirect", 3.0))
        tk.Entry(self, textvariable=self.clamping).pack(padx=10, fill="x")
        tk.Label(self, text="10 - it's a regular value", bg=THEME_BG, font=("Segoe UI", 8)).pack(anchor="w", padx=10)

        # Persistent Data
        self.use_persistent_data = tk.BooleanVar(value=settings.get("persistent_data", False))
        tk.Checkbutton(
            self,
            text="Enable Persistent Data",
            variable=self.use_persistent_data,
            bg=THEME_BG,
        ).pack(anchor="w", padx=10, pady=(10, 0))

        # Use Tiling
        self.use_tiling = tk.BooleanVar(value=settings.get("use_tiling", False))
        tiling_check = tk.Checkbutton(
            self,
            text="Enable Tiling",
            variable=self.use_tiling,
            command=self.toggle_tile_inputs,
            bg=THEME_BG,
        )
        tiling_check.pack(anchor="w", padx=10, pady=(10, 0))

        # Tile Size
        self.tile_size_label = tk.Label(self, text="Tile Size (x, y)", bg=THEME_BG)
        tile_frame = tk.Frame(self, bg=THEME_BG)
        self.tile_x = tk.IntVar(value=settings.get("tile_x", 64))
        self.tile_y = tk.IntVar(value=settings.get("tile_y", 64))
        tk.Entry(tile_frame, textvariable=self.tile_x, width=10).pack(side="left", padx=5)
        tk.Entry(tile_frame, textvariable=self.tile_y, width=10).pack(side="left", padx=5)

        # Noise Threshold
        tk.Label(self, text="Noise Threshold", bg=THEME_BG).pack(anchor="w", padx=10, pady=(10, 0))
        self.noise_threshold = tk.DoubleVar(value=settings.get("noise_threshold", 0.05))
        tk.Entry(self, textvariable=self.noise_threshold).pack(padx=10, fill="x")

        # Save Button
        tk.Button(
            self,
            text="Save Settings",
            command=self.save_and_close,
            bg=THEME_ACCENT,
            fg="white",
        ).pack(pady=20)

        self.tile_frame = tile_frame
        self.toggle_texture_limit()
        self.toggle_tile_inputs()

    def toggle_texture_limit(self):
        if self.use_simplify.get():
            self.texture_limit_label.pack(anchor="w", padx=10, pady=(5, 0))
            self.texture_limit_combo.pack(padx=10, fill="x")
        else:
            self.texture_limit_label.pack_forget()
            self.texture_limit_combo.pack_forget()

    def toggle_tile_inputs(self):
        if self.use_tiling.get():
            self.tile_size_label.pack(anchor="w", padx=10, pady=(5, 0))
            self.tile_frame.pack(padx=10)
        else:
            self.tile_size_label.pack_forget()
            self.tile_frame.pack_forget()

    def save_and_close(self):
        self.settings["use_simplify"] = self.use_simplify.get()
        self.settings["texture_limit"] = int(self.texture_limit_combo.get()) if self.use_simplify.get() else None
        self.settings["clamp_indirect"] = float(self.clamping.get())
        self.settings["persistent_data"] = self.use_persistent_data.get()
        self.settings["use_tiling"] = self.use_tiling.get()
        self.settings["tile_x"] = self.tile_x.get() if self.use_tiling.get() else None
        self.settings["tile_y"] = self.tile_y.get() if self.use_tiling.get() else None
        self.settings["noise_threshold"] = float(self.noise_threshold.get())
        if callable(self._save_callback):
            self._save_callback()
        self.destroy()


# === Main GUI Code ===

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import subprocess
import threading
import time
import os
import re
import json

if PIL_AVAILABLE:
    from PIL import Image, ImageTk

SETTINGS_FILE = "sett_config.json"


class SegmentedProgressBar(tk.Canvas):
    """A custom progress bar with segmented gradient animation."""

    def __init__(self, master, width=400, height=20, segments=20, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=THEME_BG,
            **kwargs,
        )
        self.segments = segments
        self.progress = 0
        self.phase = 0
        self.after(100, self._animate)

    def set(self, value: float) -> None:
        self.progress = max(0, min(100, value))
        self._draw()

    def _gradient_color(self, t: float) -> str:
        base = tuple(int(THEME_ACCENT.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
        light = [min(255, int(c + (255 - c) * 0.4)) for c in base]
        r = int(base[0] * (1 - t) + light[0] * t)
        g = int(base[1] * (1 - t) + light[1] * t)
        b = int(base[2] * (1 - t) + light[2] * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _draw(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        seg_width = width / self.segments
        filled = self.segments * self.progress / 100

        for i in range(self.segments):
            x0 = i * seg_width + 1
            x1 = x0 + seg_width - 2
            if i < filled:
                color = self._gradient_color(((self.phase + i * 5) % 100) / 100)
                self.create_rectangle(x0, 1, x1, height - 1, fill=color, width=0)
            else:
                self.create_rectangle(x0, 1, x1, height - 1, fill=THEME_BG, width=0)

        self.create_rectangle(0, 0, width, height, outline="#a3a3a3", width=1)

    def _animate(self) -> None:
        self.phase = (self.phase + 2) % 100
        self._draw()
        self.after(100, self._animate)


class BlenderRenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SettRay")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        self.root.configure(bg=THEME_BG)

        # Use Calibri for all text if available
        self.root.option_add("*Font", "Calibri 10")

        self.blender_path = tk.StringVar()
        self.project_path = tk.StringVar()
        self.progress = tk.DoubleVar()
        self.estimated_time = tk.StringVar(value="Waiting...")
        self.start_time = None

        # Container for user-defined render settings
        self.settings = {}

        self.load_settings()

        self.content = tk.Frame(root, bg=THEME_BG)
        self.content.pack(padx=20, pady=20, fill="both", expand=True)

        self.footer = tk.Frame(root, bg=THEME_DARK, height=50)
        self.footer.pack(side="bottom", fill="x")

        self.show_main_screen()

    def _clear_frames(self):
        for widget in self.content.winfo_children():
            widget.destroy()
        for widget in self.footer.winfo_children():
            widget.destroy()

    def _create_title_image(self):
        """Return a PhotoImage with blurred shadow for the title.

        If Pillow is unavailable, return ``None`` so the caller can fall
        back to a simple text label. This prevents crashes when launching
        the application without the optional dependency installed.
        """
        if not PIL_AVAILABLE:
            return None

        font_path = os.path.join(os.path.dirname(__file__), "Calibri.ttf")
        if not os.path.exists(font_path):
            try:
                import requests
                url = "https://github.com/google/fonts/raw/main/apache/calibri/Calibri-Regular.ttf"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(font_path, "wb") as f:
                        f.write(response.content)
            except Exception:
                pass

        try:
            font = ImageFont.truetype(font_path, 32 * 4)
        except Exception:
            font = ImageFont.load_default()

        text = "SETTRAY"
        # Determine text size to center it inside the image
        dummy = Image.new("RGBA", (10, 10))
        d = ImageDraw.Draw(dummy)
        text_w, text_h = d.textsize(text, font=font)
        width = max(600, text_w + 20)
        height = text_h + 20

        img = Image.new("RGBA", (width, height), THEME_BG)
        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw_shadow = ImageDraw.Draw(shadow)
        x = (width - text_w) // 2
        y = (height - text_h) // 2
        draw_shadow.text((x, y), text, font=font, fill=(128, 128, 128, int(255 * 0.4)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(3))
        img.paste(shadow, (3, 3), shadow)
        draw = ImageDraw.Draw(img)
        draw.text((x, y), text, font=font, fill=THEME_ACCENT)
        return ImageTk.PhotoImage(img)

    def show_main_screen(self):
        self._clear_frames()
        self._build_main_screen()
        self._build_footer(show_settings_button=True)

    def _build_main_screen(self):
        self.style = ttk.Style()
        self.style.configure(
            "Accent.Horizontal.TProgressbar",
            troughcolor=THEME_BG,
            background=THEME_ACCENT,
        )

        self.title_photo = self._create_title_image()
        if self.title_photo is not None:
            title_canvas = tk.Canvas(
                self.content,
                width=self.title_photo.width(),
                height=self.title_photo.height(),
                bg=THEME_BG,
                highlightthickness=0,
                bd=0,
            )
            title_canvas.pack(pady=(0, 20))
            title_canvas.create_image(
                self.title_photo.width() // 2,
                self.title_photo.height() // 2,
                image=self.title_photo,
            )
        else:
            tk.Label(
                self.content,
                text="SettRay",
                font=("Segoe UI", 32, "bold"),
                fg=THEME_ACCENT,
                bg=THEME_BG,
            ).pack(pady=(0, 20))

        blender_frame = tk.Frame(self.content, bg=THEME_BG)
        blender_frame.pack(anchor="center", pady=(0, 10))
        tk.Label(
            blender_frame,
            text="> Blender file",
            bg=THEME_BG,
        ).pack(side="left")
        tk.Entry(blender_frame, textvariable=self.blender_path, width=40).pack(side="left", padx=5)
        tk.Button(blender_frame, text="Browse", command=self.select_blender).pack(side="left", padx=5)

        project_frame = tk.Frame(self.content, bg=THEME_BG)
        project_frame.pack(anchor="center", pady=(0, 20))
        tk.Label(
            project_frame,
            text="> Project File",
            bg=THEME_BG,
        ).pack(side="left")
        self.project_entry = tk.Entry(project_frame, textvariable=self.project_path, width=40)
        self.project_entry.pack(side="left", padx=5)
        tk.Button(project_frame, text="Browse", command=self.select_project).pack(side="left", padx=5)

        tk.Button(
            self.content,
            text="Settings",
            command=self.show_settings_screen,
            bg=THEME_BUTTON,
            fg="white",
        ).pack(pady=(0, 10))

        self.launch_button = tk.Button(
            self.content,
            text="Launch Render",
            bg=THEME_ACCENT,
            fg="white",
            command=self.launch_render,
        )
        self.launch_button.pack()

        self.status_label = tk.Label(
            self.content,
            textvariable=self.estimated_time,
            bg=THEME_BG,
        )
        self.status_label.pack(pady=(10, 0))

        self.progress_bar = SegmentedProgressBar(self.content, width=400, height=20)
        self.progress_bar.pack()

        tk.Button(self.content, text="Open Output Folder", command=self.open_output_folder).pack(pady=(10, 0))

    def _build_footer(self, show_settings_button=True):
        if PIL_AVAILABLE:
            try:
                logo_img = Image.open("SettLogo.png")
                logo_img = logo_img.resize((98, 34), Image.ANTIALIAS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                tk.Label(self.footer, image=self.logo_photo, bg=THEME_DARK).place(x=10, y=5)
            except Exception:
                pass

        tk.Label(
            self.footer,
            text="v0.3 Alpha",
            fg="white",
            bg=THEME_DARK,
            font=("Calibri", 8),
        ).place(relx=1.0, rely=1.0, x=-10, y=-10, anchor="se")

        tk.Button(
            self.footer,
            text="Render Settings",
            command=lambda: SettingsWindow(self.root, self.settings, self.save_settings),
            bg=THEME_BUTTON,
            fg="white",
            font=("Calibri", 8),
        ).place(x=100, y=36)

        if show_settings_button:
            tk.Button(
                self.footer,
                text="Settings",
                command=self.show_settings_screen,
                bg=THEME_BUTTON,
                fg="white",
                font=("Calibri", 8),
            ).place(x=10, y=36)

        tk.Label(
            self.footer,
            text="Made by Pavel Postnikov for SETT",
            fg="white",
            bg=THEME_DARK,
            font=("Calibri", 8),
        ).pack(side="right", padx=10)

    def show_settings_screen(self):
        self._clear_frames()

        tk.Label(self.content, text="SETTINGS", font=("Calibri", 16, "bold"), fg=THEME_ACCENT, bg=THEME_BG).pack(pady=(0, 10))

        form = tk.Frame(self.content, bg=THEME_BG)
        form.pack(pady=10)

        tk.Label(form, text="Variable A", bg=THEME_BG).grid(row=0, column=0, sticky="w")
        self.var_a = tk.StringVar()
        tk.Entry(form, textvariable=self.var_a).grid(row=0, column=1, padx=5, pady=2)

        self.var_b = tk.BooleanVar()
        tk.Checkbutton(form, text="Variable B", variable=self.var_b, bg=THEME_BG).grid(row=1, column=0, columnspan=2, sticky="w")

        tk.Label(form, text="Variable C", bg=THEME_BG).grid(row=2, column=0, sticky="w")
        options = [str(v) for v in range(128, 8097, 128)]
        self.var_c = tk.StringVar(value=options[0])
        ttk.Combobox(form, values=options, textvariable=self.var_c, state="readonly").grid(row=2, column=1, padx=5, pady=2)

        self._build_footer(show_settings_button=False)
        tk.Button(self.footer, text="Back", command=self.show_main_screen, bg=THEME_BUTTON, fg="white", font=("Calibri", 8)).place(x=10, y=36)


    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                self.blender_path.set(data.get("blender_path", ""))
                # Populate saved render settings if available
                self.settings = data.get("settings", {})

    def save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump({
                "blender_path": self.blender_path.get(),
                "settings": self.settings,
            }, f)

    def select_blender(self):
        path = filedialog.askopenfilename(title="Select Blender.exe", filetypes=[("EXE files", "*.exe")])
        if path:
            self.blender_path.set(path)
            self.save_settings()

    def select_project(self):
        path = filedialog.askopenfilename(title="Select .blend project", filetypes=[("Blender Projects", "*.blend")])
        if path:
            self.project_path.set(path)

    def parse_frame_range(self):
        blender = self.blender_path.get()
        blend = self.project_path.get()
        try:
            cmd = [blender, "-b", blend, "--python-expr", "import bpy; print(f'START:{bpy.context.scene.frame_start},END:{bpy.context.scene.frame_end}')"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            match = re.search(r'START:(\d+),END:(\d+)', result.stdout)
            if match:
                return int(match.group(1)), int(match.group(2))
        except:
            pass
        return 1, 100


    def launch_render(self):
        if not self.blender_path.get() or not self.project_path.get():
            messagebox.showerror("Error", "Please select Blender.exe and a .blend file")
            return

        self.progress.set(0)
        self.progress_bar.set(0)
        self.estimated_time.set("Starting render")
        self.start_time = time.time()
        self.launch_button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.run_render)
        thread.start()

    def run_render(self):
        blender = self.blender_path.get()
        blend = self.project_path.get()
        start_frame, end_frame = self.parse_frame_range()
        total_frames = end_frame - start_frame + 1

        command = [
            blender, "--background", blend, "-a", "--", "--cycles-device", "OPTIX"
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")

        for line in process.stdout:
            print(line.strip())
            frame_match = re.search(r"Fra:(\d+)", line)
            if frame_match:
                current_frame = int(frame_match.group(1))
                elapsed = time.time() - self.start_time
                rendered_frames = current_frame - start_frame
                fps = elapsed / rendered_frames if rendered_frames else 1
                eta = int((total_frames - rendered_frames) * fps)
                self.progress.set(rendered_frames / total_frames * 100)
                self.progress_bar.set(self.progress.get())
                self.estimated_time.set(f"Progress: {rendered_frames}/{total_frames} | ETA: {eta//60} min {eta%60} sec")

        total_elapsed = int(time.time() - self.start_time)
        self.show_completion_screen(total_elapsed)

    def show_completion_screen(self, elapsed_seconds):
        for widget in self.content.winfo_children():
            widget.destroy()

        tk.Label(
            self.content,
            text="Complete",
            font=("Segoe UI", 18, "bold"),
            fg=THEME_SUCCESS,
            bg=THEME_BG,
        ).pack(pady=20)
        mins, secs = divmod(elapsed_seconds, 60)
        tk.Label(
            self.content,
            text=f"Render Time: {mins} min {secs} sec",
            font=("Segoe UI", 12),
            bg=THEME_BG,
        ).pack(pady=(0, 10))

        tk.Button(
            self.content,
            text="New Render",
            command=self.reset_ui,
            bg=THEME_ACCENT,
            fg="white",
        ).pack()

    def reset_ui(self):
        for widget in self.content.winfo_children():
            widget.destroy()
        self.__init__(self.root)  # перезапускаем GUI

    def open_output_folder(self):
        blend_path = self.project_path.get()
        if not blend_path:
            messagebox.showinfo("Notice", "Please select a project first.")
            return

        folder = os.path.dirname(blend_path)
        if os.name == "nt":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.call(["open", folder])
        else:
            subprocess.call(["xdg-open", folder])

if __name__ == "__main__":
    root = tk.Tk()
    app = BlenderRenderGUI(root)
    root.mainloop()
