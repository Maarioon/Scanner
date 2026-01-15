
import customtkinter as ctk
import tkinter as tk
import math
import threading
import json
import time
from datetime import datetime
import websocket # requires: pip install websocket-client

# ==========================================
# THEME CONFIGURATION (FITNESS STYLE)
# ==========================================
THEME = {
    "bg_dark": "#2B2B52",       # Deep Purple-Blue Background
    "card_bg": "#3F3F7A",       # Lighter Purple Card
    "card_highlight": "#5858A0",
    "accent_primary": "#E056FD",# Soft Pink/Magenta
    "accent_secondary": "#686DE0", # Soft Blue
    "accent_gold": "#F9CA24",   # Gold/Yellow for details
    "text_primary": "#FFFFFF",
    "text_secondary": "#B0B0D0",
    "font_header": ("Segoe UI", 26, "bold"),
    "font_body": ("Segoe UI", 14),
    "font_family": "Segoe UI",
    
    # Legacy Aliases for Compatibility
    "accent_cyan": "#686DE0",   # Maps to Secondary (Blue)
    "accent_magenta": "#E056FD",# Maps to Primary (Pink)
    "accent_green": "#00C853",  # Keep Green for Success/Connect
    "accent_purple": "#E056FD", # Maps to Primary
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ==========================================
# CUSTOM WIDGETS
# ==========================================
class HealthRing(ctk.CTkFrame):
    def __init__(self, master, score=98, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = ctk.CTkCanvas(self, width=160, height=160, bg=THEME["card_bg"], highlightthickness=0)
        self.canvas.pack()
        self.score = score
        self.draw()
        
    def draw(self):
        # Background Ring
        self.canvas.create_arc(10, 10, 150, 150, start=0, extent=359, width=15, style="arc", outline="#2C2C54")
        # Gradient/Color Ring (Simulated with solid)
        extent = (self.score / 100) * 359
        self.canvas.create_arc(10, 10, 150, 150, start=90, extent=-extent, width=15, style="arc", outline=THEME["accent_primary"])
        # Text
        self.canvas.create_text(80, 70, text=f"{self.score}", font=("Arial", 36, "bold"), fill="white")
        self.canvas.create_text(80, 100, text="Health", font=("Arial", 12), fill=THEME["text_secondary"])

    def update_score(self, new_score):
        self.score = new_score
        self.canvas.delete("all")
        self.draw()

class CyberGauge(ctk.CTkCanvas):
    def __init__(self, master, width=250, height=250, min_val=0, max_val=100, title="RPM", unit="", color=THEME["accent_cyan"], **kwargs):
        super().__init__(master, width=width, height=height, bg=THEME["card_bg"], highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.min_val = min_val
        self.max_val = max_val
        self.value = min_val
        self.title = title
        self.unit = unit
        self.color = color
        self.center_x = width // 2
        self.center_y = height // 2
        self.radius = (min(width, height) // 2) - 20
        self.start_angle = 135
        self.end_angle = 45
        self.full_extent = 270 # Degrees of the gauge
        
        # UI Setup
        self.draw_background()
        self.update_value(min_val)

    def draw_background(self):
        self.delete("all")
        # Draw background track
        self.create_arc(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            start=self.start_angle, extent=-self.full_extent,
            style="arc", width=15, outline="#222222"
        )
        
        # Draw text
        self.create_text(self.center_x, self.center_y + 30, text=self.title, fill=THEME["text_secondary"], font=(THEME["font_family"], 12))
        self.create_text(self.center_x, self.center_y + 50, text=self.unit, fill=THEME["text_secondary"], font=(THEME["font_family"], 10))
        
        # Value Text placeholder
        self.value_text = self.create_text(self.center_x, self.center_y - 10, text=str(int(self.min_val)), fill="white", font=(THEME["font_family"], 30, "bold"))

    def update_value(self, value):
        if value is None:
             value = self.min_val
             
        self.value = value
        
        # Clamp value
        val_clamped = max(self.min_val, min(self.max_val, value))
        
        # Calculate percentage
        percent = (val_clamped - self.min_val) / (self.max_val - self.min_val)
        extent = -(percent * self.full_extent)
        
        # Redraw Arc
        self.delete("prog_arc")
        self.create_arc(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            start=self.start_angle, extent=extent,
            style="arc", width=15, outline=self.color, tags="prog_arc"
        )
        
        # Update Text
        self.itemconfigure(self.value_text, text=f"{int(value)}")
        
        # Color shift for redline (simple visual flair)
        if percent > 0.85:
            self.itemconfigure("prog_arc", outline=THEME["accent_magenta"])
        else:
             self.itemconfigure("prog_arc", outline=self.color)


# ==========================================
# MAIN APPLICATION
# ==========================================

# ==========================================
# MAIN APPLICATION
# ==========================================

class MotoSmartApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MotoSmart Fitness Edition")
        self.geometry("450x850") # Tall phone-like aspect ratio
        self.configure(fg_color=THEME["bg_dark"])
        
        # State
        self.connected = False
        self.ws = None
        self.ws_thread = None
        self.hud_mode = False
        self.views = {}
        self.current_view = None
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # View Container
        self.view_container = ctk.CTkFrame(self, fg_color="transparent")
        self.view_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)
        
        # Initialize Views
        self.init_motosmart_home()
        self.init_dashboard_view()
        self.init_service_functions_view()
        self.init_dashboard_view()
        self.init_service_functions_view()
        self.init_marketplace_view()
        self.init_diagnostic_report_view() # NEW
        self.init_ai_view()
        self.init_tutorial_view()
        self.init_vci_connection_view()
        self.init_terminal_view()
        self.init_settings_view()
        self.init_assistance_view()
        
        # Diagzone Modules
        self.init_intelligent_diagnose_view()
        self.init_local_diagnose_view()
        self.init_voltage_view()
        self.init_adas_view()
        self.init_other_modules_view()
        self.init_user_info_view()
        self.init_info_center_view()
        self.init_history_view()
        self.init_software_update_view()
        
        # 2. Bottom Navigation (Soft floating pill)
        self.create_bottom_nav()
        
        self.show_view("home")
        
        # Websocket
        self.start_websocket()

    def create_bottom_nav(self):
        # "Floating Pill" Style
        nav = ctk.CTkFrame(self, height=70, fg_color=THEME["card_bg"], corner_radius=35)
        nav.place(relx=0.5, rely=0.92, anchor="center", relwidth=0.9)
        
        # Centered container
        btn_container = ctk.CTkFrame(nav, fg_color="transparent")
        btn_container.pack(expand=True, pady=10)
        
        self.nav_btn("🏠", "home", btn_container)
        self.nav_btn("📊", "dashboard", btn_container)
        self.nav_btn("🛒", "marketplace", btn_container)
        self.nav_btn("👤", "settings", btn_container)
        
    def nav_btn(self, text, view_name, parent):
        btn = ctk.CTkButton(parent, text=text, width=60, height=50, 
                            font=("Arial", 24), fg_color="transparent", hover_color=THEME["card_highlight"],
                            corner_radius=20, text_color="white",
                            command=lambda: self.show_view(view_name))
        btn.pack(side="left", padx=10)

    def init_motosmart_home(self):
        # Scrollable "Dashboard"
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        # Scroll container
        canvas = ctk.CTkScrollableFrame(view, fg_color="transparent", label_text="")
        canvas.pack(fill="both", expand=True)
        
        # 1. Header Section
        header = ctk.CTkFrame(canvas, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        
        # Profile Circle
        profile = ctk.CTkLabel(header, text="M", width=50, height=50, fg_color=THEME["accent_primary"], corner_radius=25, font=("Arial", 20, "bold"))
        profile.pack(side="left")
        
        # Text
        txt_frame = ctk.CTkFrame(header, fg_color="transparent")
        txt_frame.pack(side="left", padx=15)
        ctk.CTkLabel(txt_frame, text="Hello", font=("Segoe UI", 14), text_color=THEME["text_secondary"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(txt_frame, text="Driver", font=("Segoe UI", 24, "bold"), text_color="white", anchor="w").pack(anchor="w")
        
        # Headset Icon
        ctk.CTkButton(header, text="🎧", width=50, height=50, fg_color=THEME["card_bg"], corner_radius=25, 
                      command=lambda: self.show_view("ai_agent")).pack(side="right")

        # 2. Health Ring Card ("Today's workout points")
        health_card = ctk.CTkFrame(canvas, fg_color=THEME["card_bg"], corner_radius=30)
        health_card.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(health_card, text="Vehicle Health Score:", font=("Segoe UI", 14), text_color="white", anchor="w").pack(pady=(15,0), padx=20, anchor="w")
        
        # Ring + Stats Layout
        ring_frame = ctk.CTkFrame(health_card, fg_color="transparent")
        ring_frame.pack(fill="x", pady=10)
        
        self.health_ring = HealthRing(ring_frame, score=98)
        self.health_ring.pack(side="left", padx=20)
        
        stats = ctk.CTkFrame(ring_frame, fg_color="transparent")
        stats.pack(side="left", expand=True)
        
        def stat_item(l, v, c):
             f = ctk.CTkFrame(stats, fg_color="transparent")
             f.pack(anchor="w", pady=2)
             ctk.CTkLabel(f, text=l, font=("Segoe UI", 12), text_color="#aaa", width=80, anchor="w").pack(side="left")
             ctk.CTkLabel(f, text=v, font=("Segoe UI", 16, "bold"), text_color=c).pack(side="left")

        stat_item("DTCs", "0 Active", THEME["accent_gold"])
        stat_item("Monitors", "Ready", THEME["accent_secondary"])
        stat_item("Battery", "12.6 V", THEME["accent_primary"])

        # 3. Discover ("Discover today's personal meal options")
        ctk.CTkLabel(canvas, text="Quick Actions", font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=25, pady=(20, 10))
        
        discover_scroll = ctk.CTkScrollableFrame(canvas, orientation="horizontal", height=160, fg_color="transparent")
        discover_scroll.pack(fill="x", padx=10)
        
        def discover_card(title, subt, icon, color, target):
            c = ctk.CTkButton(discover_scroll, text="", width=200, height=130, fg_color=THEME["card_bg"], corner_radius=25,
                              command=lambda: self.show_view(target))
            c.pack(side="left", padx=10)
            c.configure(text=f"{icon}\n\n{title}\n{subt}", font=("Segoe UI", 16, "bold"))

        discover_card("Smart Scan", "Full Check", "🔍", THEME["accent_primary"], "intelligent_diagnose")
        discover_card("Marketplace", "Shop Parts", "🛒", THEME["accent_primary"], "marketplace")
        discover_card("Car Hire", "Assistance", "🚗", "green", "assistance")
        discover_card("Settings", "App Config", "⚙️", "gray", "settings")

        # 4. Main Diagnostics Grid ("The Workout List")
        ctk.CTkLabel(canvas, text="Diagnostic Hub", font=("Segoe UI", 18, "bold"), anchor="w").pack(fill="x", padx=25, pady=(20, 10))
        
        # Grid Container
        grid_frame = ctk.CTkFrame(canvas, fg_color="transparent")
        grid_frame.pack(fill="x", padx=15)
        # Configure grid for 3 columns
        grid_frame.grid_columnconfigure((0,1,2), weight=1)

        def grid_tile(row, col, title, icon, color, target, subtext=""):
             f = ctk.CTkButton(grid_frame, text="", height=120, fg_color=THEME["card_bg"], corner_radius=20,
                               command=lambda: self.show_view(target))
             f.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
             # Custom Layout inside text
             f.configure(text=f"{icon}\n{title}", font=("Segoe UI", 14, "bold"))
             
        # Row 0
        grid_tile(0, 0, "Smart Scan", "☁️", "#2980b9", "intelligent_diagnose")
        grid_tile(0, 1, "Local\nDiagnose", "🚘", "#c0392b", "local_diagnose")
        grid_tile(0, 2, "Service\nFunctions", "🔧", "#16a085", "service")
        
        # Row 1
        grid_tile(1, 0, "ADAS\nCalibration", "📡", "#8e44ad", "adas")
        grid_tile(1, 1, "TPMS", "⚠️", "#f39c12", "service") # Redirect to service for now or specific
        grid_tile(1, 2, "Diagnostic\nHistory", "📋", "#7f8c8d", "history")

        # Row 2
        grid_tile(2, 0, "Software\nUpdate", "⬆️", "#27ae60", "software_update")
        grid_tile(2, 1, "User\nInfo", "👤", "#f1c40f", "user_info")
        grid_tile(2, 2, "Other\nModules", "📦", "#2c3e50", "other_modules")
        
        # Row 3
        grid_tile(3, 0, "Info\nCenter", "ℹ️", "#d35400", "info_center")
        grid_tile(3, 1, "Vehicle\nVoltage", "⚡", "#e74c3c", "voltage")
        grid_tile(3, 2, "CarBugs\nForum", "🐞", "#34495e", "settings") # Placeholder link

        # Padding for bottom nav
        ctk.CTkLabel(canvas, text="", height=100).pack()

        self.views["home"] = view

    def init_marketplace_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        # Search Bar
        search_frame = ctk.CTkFrame(view, fg_color="transparent")
        search_frame.pack(fill="x", pady=10)
        ctk.CTkEntry(search_frame, placeholder_text="Search parts, tools, accessories...", height=40, font=("Segoe UI", 14)).pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(search_frame, text="SEARCH", width=100, height=40, fg_color=THEME["accent_cyan"]).pack(side="right")
        
        # Categories
        cat_scroll = ctk.CTkScrollableFrame(view, orientation="horizontal", height=60, fg_color="transparent")
        cat_scroll.pack(fill="x", pady=10)
        for cat in ["Performance", "Maintenance", "Electronics", "Interior", "External", "Tools"]:
            ctk.CTkButton(cat_scroll, text=cat, width=120, fg_color=THEME["card_bg"], border_width=1, border_color="#333").pack(side="left", padx=5)

        # Listings
        listings = ctk.CTkScrollableFrame(view, fg_color="transparent")
        listings.pack(fill="both", expand=True)
        
        items = [
            ("OBDII Pro Scanner", "$29.99", "⭐⭐⭐⭐⭐"),
            ("Synthetic Oil 5W-30", "$14.99", "⭐⭐⭐⭐"),
            ("Performance Air Filter", "$45.00", "⭐⭐⭐⭐⭐"),
            ("LED Headlight Kit", "$89.99", "⭐⭐⭐⭐"),
            ("Digital Torque Wrench", "$120.00", "⭐⭐⭐⭐⭐")
        ]
        
        for name, price, rating in items:
            card = ctk.CTkFrame(listings, fg_color=THEME["card_bg"])
            card.pack(fill="x", pady=5)
            ctk.CTkLabel(card, text="📦", font=("Arial", 30)).pack(side="left", padx=15)
            ctk.CTkLabel(card, text=f"{name}\n{rating}", font=("Segoe UI", 14), anchor="w").pack(side="left", padx=10)
            ctk.CTkButton(card, text=f"BUY {price}", width=100, fg_color=THEME["accent_green"]).pack(side="right", padx=10)
            
        self.views["marketplace"] = view

    def init_ai_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        ctk.CTkLabel(view, text="MotoAI ASSISTANT", font=("Impact", 24), text_color=THEME["accent_purple"]).pack(pady=10)
        
        self.chat_history = ctk.CTkTextbox(view, width=800, height=400, fg_color=THEME["card_bg"], text_color="#DDD", font=("Segoe UI", 14))
        self.chat_history.pack(fill="both", expand=True, pady=10)
        self.chat_history.insert("0.0", "MotoAI: Hello! I am your vehicle diagnostics assistant. Ask me about any trouble code or maintenance issue.\n\n")
        
        input_frame = ctk.CTkFrame(view, fg_color="transparent")
        input_frame.pack(fill="x")
        
        self.ai_entry = ctk.CTkEntry(input_frame, placeholder_text="Ask a question...", height=40)
        self.ai_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        
        ctk.CTkButton(input_frame, text="ASK", width=100, height=40, fg_color=THEME["accent_purple"], 
                      command=self.ask_ai).pack(side="right")
        
        self.views["ai_agent"] = view

    def ask_ai(self):
        q = self.ai_entry.get()
        if not q: return
        
        self.chat_history.insert("end", f"\nYou: {q}\n")
        self.chat_history.insert("end", "MotoAI: ...\n")
        self.ai_entry.delete(0, "end")
        
        # Simulated Response
        def reply():
            time.sleep(1)
            resp = "I can help with that. Based on common vehicle data, this issue often relates to sensor voltage irregularities. I recommend checking the O2 sensor connection first."
            if "P0" in q.upper():
                resp = f"That code ({q}) is a standard powertrain trouble code. It usually requires a scan tool reset after repair."
            
            self.chat_history.delete("end-2l", "end") # Remove "..."
            self.chat_history.insert("end", f"MotoAI: {resp}\n")
            self.chat_history.see("end")
            
        threading.Thread(target=reply, daemon=True).start()

    def init_tutorial_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        ctk.CTkLabel(view, text="LEARNING CENTER", font=("Impact", 24), text_color="#FFA500").pack(pady=10)
        
        videos = [
            ("How to user MotoSmart", "10:05"),
            ("Understanding DTC Codes", "05:30"),
            ("Changing Oil Guide", "15:20"),
            ("Live Data Explained", "08:45")
        ]
        
        grid = ctk.CTkScrollableFrame(view, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        
        for title, duration in videos:
            card = ctk.CTkFrame(grid, fg_color=THEME["card_bg"], border_width=1, border_color="#333")
            card.pack(fill="x", pady=10)
            
            ctk.CTkLabel(card, text="▶️", font=("Arial", 30)).pack(side="left", padx=20)
            ctk.CTkLabel(card, text=f"{title}\nDuration: {duration}", font=("Segoe UI", 16, "bold"), anchor="w").pack(side="left")
            ctk.CTkButton(card, text="WATCH NOW", fg_color="#FFA500", text_color="black").pack(side="right", padx=10, pady=20)
            
        self.views["tutorials"] = view

    def init_service_functions_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        ctk.CTkLabel(view, text="Service Functions", font=("Segoe UI", 24, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        
        grid = ctk.CTkScrollableFrame(view, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure((0,1), weight=1)
        
        services = [
            ("Oil Reset", "💧", THEME["card_bg"]), ("EPB Reset", "⭕", THEME["card_bg"]),
            ("Battery Match", "🔋", THEME["card_bg"]), ("SAS Reset", "🔄", THEME["card_bg"]),
            ("DPF Regen", "💨", THEME["card_bg"]), ("TPMS Reset", "⚠️", THEME["card_bg"]),
            ("ABS Bleed", "🩸", THEME["card_bg"]), ("Coolant Bleed", "🌡️", THEME["card_bg"])
        ]
        
        for i, (name, icon, color) in enumerate(services):
            row = i // 2
            col = i % 2
            # Enhanced Service Button
            btn = ctk.CTkButton(grid, text=f"{icon}\n{name}", fg_color=color, 
                                height=150, font=("Segoe UI", 18, "bold"), border_width=1, border_color="#333",
                                hover_color="#222",
                                command=lambda n=name: self.simulate_service_action(n))
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
            
        self.views["service"] = view

    def simulate_service_action(self, name):
        # Create a modal-like overlay
        dialog = ctk.CTkFrame(self, fg_color="#101010", border_width=2, border_color=THEME["accent_green"])
        dialog.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.5, relheight=0.3)
        
        ctk.CTkLabel(dialog, text=f"Performing {name}...", font=("Segoe UI", 18)).pack(expand=True)
        prog = ctk.CTkProgressBar(dialog, progress_color=THEME["accent_green"])
        prog.pack(fill="x", padx=40, pady=20)
        prog.set(0)
        
        def run_sim():
            for i in range(101):
                prog.set(i/100)
                time.sleep(0.02)
            
            ctk.CTkLabel(dialog, text="Success!", text_color=THEME["accent_green"], font=("Segoe UI", 16, "bold")).pack()
            self.after(1000, dialog.destroy)
            
        threading.Thread(target=run_sim, daemon=True).start()

    def init_vci_connection_view(self):
        # This will be overlaid or accessed via settings, but let's make it a full view
        # Accessed via a dedicated button or potentially replacing the "Connect" logic
        pass 

    def init_dashboard_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        view.grid_columnconfigure(0, weight=1)
        
        # Top: Connection Status / VCI
        top_bar = ctk.CTkFrame(view, fg_color="#0a0a1a", height=50)
        top_bar.pack(fill="x", pady=(0, 10))
        
        self.vci_status = ctk.CTkLabel(top_bar, text="NO VCI CONNECTED", text_color="red")
        self.vci_status.pack(side="left", padx=20)
        
        ctk.CTkButton(top_bar, text="CONNECT VCI", width=100, height=30, fg_color=THEME["accent_green"],
                      command=self.open_vci_modal).pack(side="right", padx=10)
        
        # Center: Big Tach
        gauge_container = ctk.CTkFrame(view, fg_color="transparent")
        gauge_container.pack(expand=True)
        
        self.gauge_rpm = CyberGauge(gauge_container, width=350, height=350, max_val=8000, title="RPM", unit="", color=THEME["accent_magenta"])
        self.gauge_rpm.pack(pady=10)
        
        # Bottom: Speed & Temp
        bottom_gauges = ctk.CTkFrame(view, fg_color="transparent")
        bottom_gauges.pack(fill="x", pady=20)
        
        self.gauge_speed = CyberGauge(bottom_gauges, width=180, height=180, max_val=220, title="SPEED", unit="km/h", color=THEME["accent_cyan"])
        self.gauge_speed.pack(side="left", padx=20, expand=True)
        
        self.stat_temp_gauge = CyberGauge(bottom_gauges, width=180, height=180, max_val=150, title="TEMP", unit="°C", color=THEME["accent_cyan"])
        self.stat_temp_gauge.pack(side="right", padx=20, expand=True)
        
        self.views["dashboard"] = view
        
        # We need to map the old update function to these new widgets
        # Update dummy objects for compatibility with existing update_ui
        self.stat_temp = ctk.CTkLabel(view, text="") # Dummy
        self.stat_fuel = ctk.CTkLabel(view, text="") # Dummy


    def open_vci_modal(self):
        modal = ctk.CTkFrame(self, fg_color="#080810", border_width=2, border_color="#333", corner_radius=20)
        modal.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.85) # Maximized size to fit content
        
        # Header (Compact)
        ctk.CTkLabel(modal, text="VCI CONNECTION v1.1", font=("Segoe UI", 20, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(modal, text="Select adapter interface type", font=("Segoe UI", 12), text_color="gray").pack()
        
        # Type Selection (Compact)
        type_frame = ctk.CTkFrame(modal, fg_color="transparent")
        type_frame.pack(pady=10)
        
        self.conn_type = tk.StringVar(value="bluetooth")
        self.selected_device = tk.StringVar(value="")
        
        btn_bt = ctk.CTkButton(type_frame, text="Bluetooth", width=120, height=40, corner_radius=10, 
                             font=("Segoe UI", 14, "bold"), fg_color="#2962FF", 
                             command=lambda: self.scan_devices("bluetooth"))
        btn_bt.pack(side="left", padx=10)
        
        btn_wifi = ctk.CTkButton(type_frame, text="Wi-Fi", width=120, height=40, corner_radius=10, 
                               font=("Segoe UI", 14, "bold"), fg_color="#333", hover_color="#444", 
                               command=lambda: self.scan_devices("wifi"))
        btn_wifi.pack(side="left", padx=10)
        
        # Device List Area (Reduced height)
        self.device_list_frame = ctk.CTkScrollableFrame(modal, fg_color="#111", height=150, label_text="Discovered Devices")
        self.device_list_frame.pack(fill="x", padx=20, pady=10)
        
        # Status Label
        self.scan_status = ctk.CTkLabel(self.device_list_frame, text="Select an interface above to scan", text_color="gray")
        self.scan_status.pack(pady=20)
        
        # Connect Button
        # Connect Button
        self.btn_connect = ctk.CTkButton(modal, text="CONNECT", width=200, height=50, fg_color=THEME["accent_green"], 
                      font=("Segoe UI", 18, "bold"), state="disabled",
                      command=lambda: self.perform_connection(modal))
        self.btn_connect.pack(side="bottom", pady=15)

    def scan_devices(self, mode):
        self.conn_type.set(mode)
        
        # Clear list
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
            
        self.scan_status = ctk.CTkLabel(self.device_list_frame, text=f"Scanning for {mode} devices...", text_color=THEME["accent_primary"])
        self.scan_status.pack(pady=20)
        
        def run_scan():
            time.sleep(1.5) # Simulate scan time
            
            devices = []
            if mode == "bluetooth":
                # Try to find real COM ports
                try:
                    import serial.tools.list_ports
                    ports = serial.tools.list_ports.comports()
                    for p in ports:
                        devices.append(f"{p.device} - {p.description}")
                except:
                    pass
                
                # Add Demo/Mock devices if none found or for testing
                if not devices:
                    devices.append("DEMO OBDII ADAPTER")
            else:
                devices.append("192.168.0.10:35000 (WiFi OBD)")
            
            # Update UI
            self.after(0, lambda: self.show_scan_results(devices))
            
        threading.Thread(target=run_scan, daemon=True).start()

    def show_scan_results(self, devices):
        for widget in self.device_list_frame.winfo_children():
            widget.destroy()
            
        if not devices:
            ctk.CTkLabel(self.device_list_frame, text="No devices found", text_color="red").pack(pady=10)
            ctk.CTkLabel(self.device_list_frame, text="💡 Tip: Pair your OBD adapter in Windows\nBluetooth Settings first!", text_color="gray", font=("Segoe UI", 12)).pack(pady=5)
            return

        for dev in devices:
            btn = ctk.CTkButton(self.device_list_frame, text=f"🔗 {dev}", height=40, fg_color="#333", anchor="w",
                                command=lambda d=dev: self.select_device(d))
            btn.pack(fill="x", pady=2, padx=5)

    def select_device(self, device_name):
        self.selected_device.set(device_name)
        # Highlight logic could go here (reset all buttons colors, highlight selected)
        self.btn_connect.configure(state="normal", text=f"CONNECT: {device_name.split(' - ')[0]}")

    def perform_connection(self, modal):
        device = self.selected_device.get()
        # Parse port from string "COM3 - USB Serial" -> "COM3"
        port = device.split(' - ')[0]
        if "DEMO" in port: port = "DEMO" # Explicitly trigger demo mode in backend
        if "WiFi" in port: port = None # Logic for wifi not implemented in backend yet, strictly speaking
        
        # Call Backend
        def connect_thread():
            try:
                import requests
                # Send port to backend
                requests.post("http://localhost:8000/connect", params={"port": port})
                self.after(0, lambda: [modal.destroy(), self.on_connect_success(device)])
            except Exception as e:
                print(f"Connection failed: {e}")
                
        threading.Thread(target=connect_thread, daemon=True).start()

    def on_connect_success(self, device_name):
        self.connected = True
        self.vci_status.configure(text=f"CONNECTED: {device_name}", text_color=THEME["accent_green"])
        # Redirect to Dashboard or Smart Scan
        self.show_view("intelligent_diagnose") # Optional auto-redirect


    def init_terminal_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        lbl = ctk.CTkLabel(view, text="UNIVERSAL TERMINAL (Direct Access)", font=("Segoe UI", 24, "bold"), text_color=THEME["accent_green"])
        lbl.pack(anchor="w", pady=(0, 20))
        
        # Console Output
        self.console = ctk.CTkTextbox(view, width=800, height=400, fg_color="#050510", text_color="#00ff00", font=("Consolas", 14), border_color="#333", border_width=1)
        self.console.pack(fill="both", expand=True)
        self.console.insert("0.0", "> CONNECTING TO UNIVERSAL INTERFACE...\n> READY FOR COMMANDS.\n")
        
        # Input
        input_frame = ctk.CTkFrame(view, fg_color="transparent")
        input_frame.pack(fill="x", pady=10)
        
        self.cmd_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter HEX Command (e.g. 01 0C)", font=("Consolas", 14), fg_color="#101020")
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        send_btn = ctk.CTkButton(input_frame, text="SEND", fg_color=THEME["accent_green"], width=100, command=self.send_terminal_command)
        send_btn.pack(side="right")
        
        self.views["terminal"] = view

    def init_settings_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        ctk.CTkLabel(view, text="GLOBAL SETTINGS", font=("Impact", 24), text_color="#FFF").pack(anchor="w", pady=20)
        
        # Language - Comprehensive Global List
        lang_frame = ctk.CTkFrame(view, fg_color=THEME["card_bg"])
        lang_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(lang_frame, text="Language / Region").pack(side="left", padx=20, pady=20)
        
        all_languages = [
            "English (US) 🇺🇸", "English (UK) 🇬🇧", "Español 🇪🇸", "Français 🇫🇷", "Deutsch 🇩🇪", 
            "中文 (Simplified) 🇨🇳", "中文 (Traditional) 🇹🇼", "日本語 🇯🇵", "한국어 🇰🇷", "Русский 🇷🇺",
            "Português (Brasil) 🇧🇷", "Português (Portugal) 🇵🇹", "Italiano 🇮🇹", "Nederlands 🇳🇱",
            "Polski 🇵🇱", "Türkçe 🇹🇷", "العربية 🇸🇦", "हिन्दी 🇮🇳", "বাংলা 🇧🇩", "اردو 🇵🇰",
            "Bahasa Indonesia 🇮🇩", "Bahasa Melayu 🇲🇾", "Tiếng Việt 🇻🇳", "ไทย 🇹🇭", "Ελληνικά 🇬🇷",
            "עברית 🇮🇱", "Svenska 🇸🇪", "Norsk 🇳🇴", "Dansk 🇩🇰", "Suomi 🇫🇮", "Čeština 🇨🇿",
            "Magyar 🇭🇺", "Română 🇷🇴", "Български 🇧🇬", "Српски 🇷🇸", "Hrvatski 🇭🇷", "Slovenčina 🇸🇰",
            "Lietuvių 🇱🇹", "Latviešu 🇱🇻", "Eesti 🇪🇪", "Українська 🇺🇦", "Kiswahili 🇰🇪", "Tagalog 🇵🇭"
        ]
        
        ctk.CTkComboBox(lang_frame, values=all_languages, width=250).pack(side="right", padx=20)
        
        # Appearance Theme (Visual Swatches)
        theme_frame = ctk.CTkFrame(view, fg_color=THEME["card_bg"])
        theme_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(theme_frame, text="Cyber Aesthetic").pack(side="left", padx=20, pady=20)
        
        swatches = ctk.CTkFrame(theme_frame, fg_color="transparent")
        swatches.pack(side="right", padx=20)
        
        ctk.CTkButton(swatches, text="", width=30, height=30, fg_color="#050510", corner_radius=15, border_width=2, border_color="#FFF", command=lambda: self.change_theme_fade("Dark")).pack(side="left", padx=5)
        ctk.CTkButton(swatches, text="", width=30, height=30, fg_color="#F0F0F0", corner_radius=15, command=lambda: self.change_theme_fade("Light")).pack(side="left", padx=5)

        # Connection
        conn_frame = ctk.CTkFrame(view, fg_color=THEME["card_bg"])
        conn_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(conn_frame, text="Universal Protocol Override").pack(side="left", padx=20, pady=20)
        ctk.CTkOptionMenu(conn_frame, values=["Auto", "ISO 15765-4 (CAN 11/500)", "ISO 9141-2 (Asian)", "SAE J1850 VPW (GM)"]).pack(side="right", padx=20)
        
        self.views["settings"] = view

    def init_assistance_view(self):
        # Only used if Shop View fails or as backup
        pass

    def change_theme_fade(self, mode):
        # 1. Fade Out
        for i in range(10, -1, -1):
            alpha = i / 10.0
            self.attributes("-alpha", alpha)
            self.update()
            time.sleep(0.02)
            
        # 2. Change Theme
        ctk.set_appearance_mode(mode)
        
        # 3. Fade In
        for i in range(0, 11):
            alpha = i / 10.0
            self.attributes("-alpha", alpha)
            self.update()
            # time.sleep(0.02) # Optional: Faster fade in


    def show_view(self, name):
        if self.current_view:
            self.current_view.pack_forget()
        self.current_view = self.views[name]
        self.current_view.pack(fill="both", expand=True)

    def toggle_hud(self):
        # Premium Feature: Mirror the UI for windshield reflection
        self.hud_mode = not self.hud_mode
        state = "ON" if self.hud_mode else "OFF"
        self.console.insert("end", f"\n> HUD MODE {state} (Visual Mirroring requires Restart in this Prototype)\n")
        self.console.see("end")

    def send_terminal_command(self):
        cmd = self.cmd_entry.get()
        if cmd:
            self.console.insert("end", f"\n> TX: {cmd}")
            self.console.insert("end", f"\n< RX: NO DATA (Demo Mode)")
            self.console.see("end")
            self.cmd_entry.delete(0, "end")

    # ==========================================
    # WEBSOCKET MANAGER
    # ==========================================
    def start_websocket(self):
        def on_message(ws, message):
            data = json.loads(message)
            self.after(0, self.update_ui, data)

        def on_error(ws, error):
            print(f"WS Error: {error}")
            # time.sleep(2) # Retry delay handled by run_forever loop usually, or we restart thread

        def on_close(ws, close_status_code, close_msg):
            print("WS Closed")

        def run():
            while True:
                try:
                    self.ws = websocket.WebSocketApp(
                        "ws://localhost:8000/ws/sensors",
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_close
                    )
                    self.ws.run_forever()
                    time.sleep(2) # Reconnect delay
                except Exception as e:
                    print(f"WS Connection Failed: {e}")
                    time.sleep(2)

        self.ws_thread = threading.Thread(target=run, daemon=True)
        self.ws_thread.start()

    def update_ui(self, data):
        try:
            # Update Dashboard Gauges
            if "rpm" in data:
                self.gauge_rpm.update_value(data["rpm"])
            if "speed" in data:
                self.gauge_speed.update_value(data["speed"])
            if "coolant_temp" in data:
                self.stat_temp_gauge.update_value(data["coolant_temp"])
            
            # Check for Demo Mode flag (Connection status update)
            if data.get("status") == "DEMO_MODE" and not self.connected:
                self.vci_status.configure(text="DEMO MODE ACTIVE", text_color="orange")
                self.connected = True
                
        except Exception as e:
            print(f"UI Update Error: {e}")

    # ==========================================
    # DIAGZONE MODULE IMPLEMENTATIONS
    # ==========================================

    def init_intelligent_diagnose_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        # Header
        ctk.CTkLabel(view, text="Smart Scan", font=("Segoe UI", 24, "bold"), text_color="white").pack(pady=20)
        
        # Button (Pack First to ensure visibility at bottom)
        btn = ctk.CTkButton(view, text="START SCAN", height=60, width=200, fg_color=THEME["accent_green"],
                            font=("Segoe UI", 20, "bold"),
                            command=self.run_intelligent_diagnose_anim)
        btn.pack(side="bottom", pady=40)

        # Animation Canvas (Pack last to fill remaining space)
        anim_frame = ctk.CTkFrame(view, fg_color="transparent")
        anim_frame.pack(expand=True)
        
        self.step_labels = []
        steps = ["Connecting VCI...", "Reading VIN...", "Decoding VIN...", "Vehicle Matched"]
        
        for step in steps:
            lbl = ctk.CTkLabel(anim_frame, text=step, font=("Segoe UI", 18), text_color="gray")
            lbl.pack(pady=10)
            self.step_labels.append(lbl)
            
        self.views["intelligent_diagnose"] = view



    def run_intelligent_diagnose_anim(self):
        # Disable button to prevent double click? (Optional)
        
        # Step 1: Animation Sequence handled safely on main thread via recursive after or pre-scheduled
        
        def update_step(step_index):
            if step_index > 0:
                 # Mark previous as done
                 self.step_labels[step_index-1].configure(text=self.step_labels[step_index-1].cget("text") + " ✔️", text_color=THEME["accent_green"])
            
            if step_index < len(self.step_labels):
                # Highlight current
                self.step_labels[step_index].configure(text_color="white")
                # Schedule next step
                self.after(800, lambda: update_step(step_index + 1))
            else:
                # Finished - Fetch and Show
                self.finish_diagnose()

        # Reset labels first
        steps = ["Connecting VCI...", "Reading VIN...", "Decoding VIN...", "Vehicle Matched"]
        for i, lbl in enumerate(self.step_labels):
            lbl.configure(text=steps[i], text_color="gray")

        # Start sequence
        update_step(0)

    def finish_diagnose(self):
         def fetch_and_show():
            try:
                import requests
                # requests is blocking, run in thread to avoid freeze, then callback to UI
                response = requests.get("http://localhost:8000/diagnostics/codes")
                codes = response.json().get("codes", [])
            except:
                codes = []
            
            # Update UI on main thread
            self.after(0, lambda: [self.populate_diagnostic_report(codes), self.show_view("diagnostic_report")])

         threading.Thread(target=fetch_and_show, daemon=True).start()
    def init_diagnostic_report_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        # Header
        header = ctk.CTkFrame(view, fg_color="transparent")
        header.pack(fill="x", pady=20)
        ctk.CTkButton(header, text="< Back", width=60, fg_color="transparent", command=lambda: self.show_view("home")).pack(side="left", padx=10)
        ctk.CTkLabel(header, text="Diagnostic Report", font=("Segoe UI", 24, "bold"), text_color="white").pack(side="left", padx=20)
        
        # Report Container
        self.report_frame = ctk.CTkScrollableFrame(view, fg_color="transparent")
        self.report_frame.pack(fill="both", expand=True, padx=20)
        
        # Controls
        controls = ctk.CTkFrame(view, fg_color="#101010", height=60)
        controls.pack(fill="x")
        
        ctk.CTkButton(controls, text="CLEAR CODES", width=150, fg_color="#c0392b", 
                      command=self.clear_codes_action).pack(side="right", padx=20, pady=10)
        ctk.CTkButton(controls, text="EMAIL REPORT", width=150, fg_color="#2980b9",
                      command=lambda: print("Email sent")).pack(side="right", padx=0, pady=10)
                      
        self.views["diagnostic_report"] = view

    def populate_diagnostic_report(self, codes):
        for widget in self.report_frame.winfo_children():
            widget.destroy()
            
        if not codes:
            ctk.CTkLabel(self.report_frame, text="✅ No Fault Codes Detected", font=("Segoe UI", 20), text_color=THEME["accent_green"]).pack(pady=50)
            return

        ctk.CTkLabel(self.report_frame, text=f"Found {len(codes)} Issues", font=("Segoe UI", 16, "bold"), text_color="#ff5555").pack(anchor="w", pady=10)
        
        for dtc in codes:
            card = ctk.CTkFrame(self.report_frame, fg_color=THEME["card_bg"], border_width=1, border_color="#ff5555" if dtc['severity'] == 'critical' else "#444")
            card.pack(fill="x", pady=5)
            
            # Icon
            color = "#ff5555" if dtc['severity'] == "critical" else "#f1c40f"
            ctk.CTkLabel(card, text="⚠️", text_color=color, font=("Arial", 24)).pack(side="left", padx=15)
            
            # Info
            info = ctk.CTkFrame(card, fg_color="transparent")
            info.pack(side="left", fill="x", expand=True, pady=10)
            ctk.CTkLabel(info, text=dtc['code'], font=("Segoe UI", 18, "bold"), text_color="white", anchor="w").pack(fill="x")
            ctk.CTkLabel(info, text=dtc['description'], font=("Segoe UI", 14), text_color="#ccc", anchor="w").pack(fill="x")
            
    def clear_codes_action(self):
        # Call backend to clear (simulated)
        import requests
        try:
           requests.post("http://localhost:8000/diagnostics/clear")
           self.populate_diagnostic_report([])
        except:
           pass




    def init_local_diagnose_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        
        ctk.CTkLabel(view, text="Local Diagnose", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        # Tabs
        tabs = ctk.CTkTabview(view, height=500, fg_color=THEME["card_bg"])
        tabs.pack(fill="both", expand=True, padx=20)
        
        for region in ["USA", "Europe", "Asia", "China"]:
            tabs.add(region)
            grid = ctk.CTkScrollableFrame(tabs.tab(region), fg_color="transparent")
            grid.pack(fill="both", expand=True)
            
            # Dummy brands
            brands = ["Ford", "GM", "Chrysler"] if region == "USA" else ["BMW", "Benz", "VW"] if region == "Europe" else ["Toyota", "Honda", "Nissan"]
            for brand in brands:
                ctk.CTkButton(grid, text=brand, height=80, fg_color="#333", command=lambda b=brand: print(f"Selected {b}")).pack(fill="x", pady=5)
                
        self.views["local_diagnose"] = view

    def init_voltage_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="Vehicle Voltage Monitor", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        # Graph Placeholders
        graph_area = ctk.CTkFrame(view, height=300, fg_color="#111")
        graph_area.pack(fill="x", padx=20, pady=20)
        
        self.volt_display = ctk.CTkLabel(view, text="12.6 V", font=("Impact", 60), text_color=THEME["accent_primary"])
        self.volt_display.pack()
        ctk.CTkLabel(view, text="Current Value", text_color="gray").pack()
        
        self.views["voltage"] = view

    def init_adas_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="ADAS Calibration", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        grid = ctk.CTkFrame(view, fg_color="transparent")
        grid.pack(expand=True)
        
        def item(row, col, title, icon):
             b = ctk.CTkButton(grid, text=f"{icon}\n{title}", height=150, width=150, fg_color=THEME["card_bg"], font=("Segoe UI", 16, "bold"))
             b.grid(row=row, column=col, padx=10, pady=10)
             
        item(0,0, "Passenger", "🚗")
        item(0,1, "Commercial", "🚛")
        item(1,0, "Manual", "📖")
        item(1,1, "Steps", "🪜")

        self.views["adas"] = view

    def init_other_modules_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="Toolbox & Modules", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        # Grid
        grid = ctk.CTkScrollableFrame(view, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        grid.grid_columnconfigure((0,1), weight=1)
        
        tools = [("Toolbox", "🧰"), ("Browser", "🌐"), ("Files", "📁"), ("Camera", "📷"), ("Remote", "📡")]
        for i, (name, icon) in enumerate(tools):
             ctk.CTkButton(grid, text=f"{icon}\n{name}", height=120, fg_color=THEME["card_bg"],
                           command=lambda n=name: self.open_tool(n)).grid(row=i//2, column=i%2, padx=10, pady=10, sticky="ew")

        self.views["other_modules"] = view

    def open_tool(self, name):
        if name == "Files":
            # Simulate Error as per screenshot
            tk.messagebox.showinfo("Error", "Files is not available, please download installation application!")
        elif name == "Browser":
             # Simulate Cloudflare check
             self.show_browser_check()
             
    def show_browser_check(self):
        win = ctk.CTkToplevel(self)
        win.geometry("400x500")
        win.title("Browser Check")
        ctk.CTkLabel(win, text="diagzone.com", font=("Arial", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(win, text="Verifying you are human...").pack()
        bar = ctk.CTkProgressBar(win)
        bar.pack(pady=20, padx=20)
        bar.set(0)
        
        def load():
            for i in range(101):
                bar.set(i/100)
                time.sleep(0.02)
            win.destroy()
            
        threading.Thread(target=load, daemon=True).start()

    def init_user_info_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="User Profile", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        menu = ctk.CTkScrollableFrame(view, fg_color="transparent")
        menu.pack(fill="both", expand=True)
        
        items = ["My Report", "VCI Management", "Firmware Fix", "Profile", "Change Password", "Log Out"]
        for it in items:
            ctk.CTkButton(menu, text=it, height=60, fg_color=THEME["card_bg"], anchor="w").pack(fill="x", pady=2)
            
        self.views["user_info"] = view
        
    def init_info_center_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="Info Center", font=("Segoe UI", 24, "bold")).pack(pady=20)
        tabs = ctk.CTkTabview(view)
        tabs.pack(fill="both", expand=True)
        tabs.add("Repair Info")
        tabs.add("General")
        
        # Repair info buttons
        grid = ctk.CTkFrame(tabs.tab("Repair Info"), fg_color="transparent")
        grid.pack(expand=True)
        ctk.CTkButton(grid, text="DTC Help", height=100, width=100, fg_color=THEME["card_bg"]).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkButton(grid, text="Tech Handbook", height=100, width=100, fg_color=THEME["card_bg"]).grid(row=0, column=1, padx=10, pady=10)
        
        self.views["info_center"] = view

    def init_history_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="Diagnostic History", font=("Segoe UI", 24, "bold")).pack(pady=20)
        ctk.CTkLabel(view, text="🔍 No Record", font=("Segoe UI", 20), text_color="gray").pack(expand=True)
        self.views["history"] = view

    def init_software_update_view(self):
        view = ctk.CTkFrame(self.view_container, fg_color="transparent")
        ctk.CTkLabel(view, text="Software Downloads", font=("Segoe UI", 24, "bold")).pack(pady=20)
        
        list_frame = ctk.CTkScrollableFrame(view, fg_color="transparent")
        list_frame.pack(fill="both", expand=True)
        
        sw = [("EOBD", "V22.53"), ("DEMO", "V15.90"), ("AutoSearch", "V10.02")]
        for s, v in sw:
            f = ctk.CTkFrame(list_frame, fg_color=THEME["card_bg"])
            f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=s, font=("bold", 16)).pack(side="left", padx=10)
            ctk.CTkLabel(f, text=v).pack(side="left", padx=10)
            ctk.CTkButton(f, text="Update", width=60, fg_color=THEME["accent_green"]).pack(side="right", padx=10)

        self.views["software_update"] = view

if __name__ == "__main__":
    app = MotoSmartApp()
    app.mainloop()
