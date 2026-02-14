# one_gui_modern.py
# Requirements: pip install pymongo pandas matplotlib python-dateutil customtkinter

import re
import warnings
from datetime import datetime, date, timedelta
from dateutil import tz
import tkinter as tk
from tkinter import ttk, messagebox

import pandas as pd
from pymongo import MongoClient

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- NEW LIBRARY FOR UI ---
import customtkinter as ctk

warnings.filterwarnings("ignore", category=FutureWarning)

# ===================== CONFIG =====================
MONGO_URI = "mongodb://localhost:27017"
CODES = ["mg", "tp", "yn", "cb"]
COSTS_DB = "costs"
COSTS_COLLECTION = "campaigns"
COSTS_DATE_FIELD = "campaign_date"
DEFAULT_COSTS_TEXT_FIELD = "campaign_name"
METRIX_DB = "metrix_revenue"
DEFAULT_METRIX_TIME_FIELD = "miladi_time"
TZ_NAME = "Asia/Tehran"
LOCAL_TZ = tz.gettz(TZ_NAME)

# --- THEME SETTINGS ---
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "green", "dark-blue"

# Colors for Charts to match Dark Theme
CHART_BG = "#2b2b2b"  # Match CTk frames
CHART_FG = "#ffffff"
ACCENT_COLOR = "#1f6aa5" 

# ===================== LOGIC (UNCHANGED) =====================
def parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()

def daterange(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)

def day_start_utc(d: date) -> datetime:
    start_local = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=LOCAL_TZ)
    return start_local.astimezone(tz.UTC)

def next_day_start_utc(d: date) -> datetime:
    return day_start_utc(d + timedelta(days=1))

def costs_campaigns_daily(client: MongoClient, start_day: date, end_day: date, text_field: str) -> pd.DataFrame:
    db = client[COSTS_DB]
    col = db[COSTS_COLLECTION]
    start_s = start_day.isoformat()
    end_s = end_day.isoformat()
    any_code_regex = re.compile(r"(mg|tp|yn|cb)", re.IGNORECASE)

    pipeline = [
        {"$match": {
            COSTS_DATE_FIELD: {"$gte": start_s, "$lte": end_s},
            text_field: {"$regex": any_code_regex}
        }},
        {"$addFields": {
            "__code": {
                "$switch": {
                    "branches": [
                        {"case": {"$regexMatch": {"input": f"${text_field}", "regex": "mg", "options": "i"}}, "then": "mg"},
                        {"case": {"$regexMatch": {"input": f"${text_field}", "regex": "tp", "options": "i"}}, "then": "tp"},
                        {"case": {"$regexMatch": {"input": f"${text_field}", "regex": "yn", "options": "i"}}, "then": "yn"},
                        {"case": {"$regexMatch": {"input": f"${text_field}", "regex": "cb", "options": "i"}}, "then": "cb"},
                    ],
                    "default": "other"
                }
            }
        }},
        {"$match": {"__code": {"$in": CODES}}},
        {"$group": {
            "_id": {"day": f"${COSTS_DATE_FIELD}", "code": "$__code"},
            "count": {"$sum": 1}
        }},
        {"$project": {"_id": 0, "day": "$_id.day", "code": "$_id.code", "count": 1}}
    ]

    data = list(col.aggregate(pipeline, allowDiskUse=True))
    df = pd.DataFrame(data)
    all_days = pd.DataFrame({"day": [d.isoformat() for d in daterange(start_day, end_day)]})
    all_days["day"] = pd.to_datetime(all_days["day"])

    if df.empty:
        out = all_days.copy()
        for c in CODES: out[c] = 0
        out["total"] = 0
        return out.sort_values("day")

    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df = df.dropna(subset=["day"])
    pivot = (df.pivot_table(index="day", columns="code", values="count", aggfunc="sum")
             .fillna(0).astype(int).reset_index())

    for c in CODES:
        if c not in pivot.columns: pivot[c] = 0

    pivot["total"] = pivot[CODES].sum(axis=1)
    out = all_days.merge(pivot[["day"] + CODES + ["total"]], on="day", how="left").fillna(0)
    for c in CODES + ["total"]: out[c] = out[c].astype(int)
    return out.sort_values("day")

def metrix_revenue_daily(client: MongoClient, start_day: date, end_day: date, time_field: str) -> pd.DataFrame:
    db = client[METRIX_DB]
    start_utc = day_start_utc(start_day)
    end_utc = next_day_start_utc(end_day)
    rows = []
    collections = [c for c in db.list_collection_names() if not c.startswith("system.")]

    for cname in collections:
        col = db[cname]
        pipeline = [
            {"$addFields": {
                "__t": {
                    "$cond": [
                        {"$eq": [{"$type": f"${time_field}"}, "date"]},
                        f"${time_field}",
                        {"$dateFromString": {"dateString": f"${time_field}", "onError": None, "onNull": None}}
                    ]
                }
            }},
            {"$match": {"__t": {"$ne": None, "$gte": start_utc, "$lt": end_utc}}},
            {"$group": {
                "_id": {"day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$__t"}}},
                "count": {"$sum": 1}
            }},
            {"$project": {"_id": 0, "day": "$_id.day", "count": 1}}
        ]
        try:
            agg = list(col.aggregate(pipeline, allowDiskUse=True))
        except Exception:
            agg = []
        for r in agg:
            rows.append({"day": r["day"], "collection": cname, "count": int(r["count"])})

    df = pd.DataFrame(rows)
    if df.empty: return pd.DataFrame(columns=["day", "collection", "count"])
    df["day"] = pd.to_datetime(df["day"], errors="coerce")
    df = df.dropna(subset=["day"])
    df["count"] = df["count"].astype(int)
    return df.sort_values(["day", "collection"])


# ===================== MODERN UI APP =====================
class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Analytics Dashboard | MongoDB Monitor")
        self.geometry("1400x900")
        self.minsize(1280, 800)

        # Config Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.client = None
        self._df_metrix_long = pd.DataFrame(columns=["day", "collection", "count"])
        self._metrix_collections_all = ["TOTAL"]

        self._init_style()
        self._build_sidebar()
        self._build_main_area()

    def _init_style(self):
        # Customizing the legacy Treeview to match Modern Dark Theme
        style = ttk.Style()
        style.theme_use("clam")
        
        # Colors
        bg_color = "#2b2b2b" # Match CTk Surface
        fg_color = "white"
        header_bg = "#343638"
        select_bg = "#1f6aa5"

        style.configure("Treeview", 
                        background=bg_color, 
                        foreground=fg_color, 
                        fieldbackground=bg_color, 
                        borderwidth=0, 
                        rowheight=30,
                        font=("Roboto", 11))
        
        style.configure("Treeview.Heading", 
                        background=header_bg, 
                        foreground="white", 
                        relief="flat", 
                        font=("Roboto", 11, "bold"))
        
        style.map("Treeview", background=[("selected", select_bg)])

    # ---------- LEFT SIDEBAR ----------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        # Title
        ctk.CTkLabel(self.sidebar, text="DASHBOARD", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20, padx=20)

        # Dates
        self._add_sidebar_label("Start Date (YYYY-MM-DD):")
        today = datetime.now(LOCAL_TZ).date()
        self.start_var = ctk.StringVar(value=(today - timedelta(days=14)).isoformat())
        ctk.CTkEntry(self.sidebar, textvariable=self.start_var).pack(pady=5, padx=20, fill="x")

        self._add_sidebar_label("End Date (YYYY-MM-DD):")
        self.end_var = ctk.StringVar(value=today.isoformat())
        ctk.CTkEntry(self.sidebar, textvariable=self.end_var).pack(pady=5, padx=20, fill="x")

        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=15)

        # Config
        self._add_sidebar_label("Costs Field (regex):")
        self.costs_field_var = ctk.StringVar(value=DEFAULT_COSTS_TEXT_FIELD)
        ctk.CTkEntry(self.sidebar, textvariable=self.costs_field_var).pack(pady=5, padx=20, fill="x")

        self._add_sidebar_label("Metrix Time Field:")
        self.metrix_field_var = ctk.StringVar(value=DEFAULT_METRIX_TIME_FIELD)
        ctk.CTkEntry(self.sidebar, textvariable=self.metrix_field_var).pack(pady=5, padx=20, fill="x")

        # Run Button
        self.run_btn = ctk.CTkButton(self.sidebar, text="LOAD DATA", command=self.on_run, height=40, font=ctk.CTkFont(weight="bold"))
        self.run_btn.pack(pady=30, padx=20, fill="x")

        # Status
        self.status_label = ctk.CTkLabel(self.sidebar, text="Ready", text_color="gray")
        self.status_label.pack(side="bottom", pady=10)

    def _add_sidebar_label(self, text):
        ctk.CTkLabel(self.sidebar, text=text, anchor="w").pack(pady=(10, 0), padx=20, fill="x")

    # ---------- MAIN AREA ----------
    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(2, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. KPI Cards Row
        self.kpi_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.kpi_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.kpi_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.kpis = {}
        self.kpis["costs_total"] = self._create_kpi_card(self.kpi_frame, 0, "Costs Total", "0")
        self.kpis["costs_days"] = self._create_kpi_card(self.kpi_frame, 1, "Active Days", "0")
        self.kpis["metrix_total"] = self._create_kpi_card(self.kpi_frame, 2, "Revenue Writes", "0")
        self.kpis["metrix_cols"] = self._create_kpi_card(self.kpi_frame, 3, "Collections", "0")

        # 2. Tabs
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.grid(row=2, column=0, sticky="nsew")
        self.tabview.add("Costs Analysis")
        self.tabview.add("Metrix Analysis")

        self._build_costs_tab(self.tabview.tab("Costs Analysis"))
        self._build_metrix_tab(self.tabview.tab("Metrix Analysis"))

    def _create_kpi_card(self, parent, col, title, value):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, sticky="ew", padx=5)
        
        ctk.CTkLabel(card, text=title, font=("Arial", 12), text_color="gray90").pack(anchor="w", padx=15, pady=(10, 0))
        val_lbl = ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold"), text_color="#64B5F6")
        val_lbl.pack(anchor="w", padx=15, pady=(0, 10))
        return val_lbl

    # ---------- TABS IMPLEMENTATION ----------
    def _build_costs_tab(self, parent):
        parent.grid_columnconfigure(0, weight=3) # Chart bigger
        parent.grid_columnconfigure(1, weight=1) # Table smaller
        parent.grid_rowconfigure(0, weight=1)

        # Chart Frame
        chart_frame = ctk.CTkFrame(parent)
        chart_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        self.fig_costs = Figure(figsize=(5, 4), dpi=100, facecolor=CHART_BG)
        self.ax_costs = self.fig_costs.add_subplot(111)
        self.ax_costs.set_facecolor(CHART_BG)
        self._style_axis(self.ax_costs)
        
        self.canvas_costs = FigureCanvasTkAgg(self.fig_costs, master=chart_frame)
        self.canvas_costs.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Table Frame
        table_frame = ctk.CTkFrame(parent)
        table_frame.grid(row=0, column=1, sticky="nsew", pady=10)
        
        cols = ["day", "mg", "tp", "yn", "cb", "total"]
        self.tree_costs = ttk.Treeview(table_frame, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree_costs.heading(c, text=c.upper())
            self.tree_costs.column(c, width=60, anchor="center")
        
        # Scrollbar for tree
        sb = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree_costs.yview)
        self.tree_costs.configure(yscrollcommand=sb.set)
        
        self.tree_costs.pack(side="left", fill="both", expand=True, padx=(2,0), pady=2)
        sb.pack(side="right", fill="y", padx=2, pady=2)

    def _build_metrix_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1) # List
        parent.grid_columnconfigure(1, weight=3) # Chart
        parent.grid_columnconfigure(2, weight=1) # Table
        parent.grid_rowconfigure(0, weight=1)

        # 1. Selection List
        list_frame = ctk.CTkFrame(parent)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        ctk.CTkLabel(list_frame, text="Search Collection:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self.metrix_search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(list_frame, textvariable=self.metrix_search_var, placeholder_text="Type to filter...")
        search_entry.pack(fill="x", padx=10, pady=5)
        search_entry.bind("<KeyRelease>", lambda e: self._refresh_metrix_listbox())

        # Using standard Listbox because CTk doesn't have a simple listbox yet, styled best we can
        self.metrix_list = tk.Listbox(list_frame, bg="#343638", fg="white", borderwidth=0, highlightthickness=0, selectbackground=ACCENT_COLOR)
        self.metrix_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.metrix_list.bind("<<ListboxSelect>>", lambda e: self._on_metrix_select())

        # 2. Chart
        chart_frame = ctk.CTkFrame(parent)
        chart_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        
        self.metrix_title_lbl = ctk.CTkLabel(chart_frame, text="Revenue: TOTAL", font=("Arial", 14, "bold"))
        self.metrix_title_lbl.pack(pady=10)

        self.fig_metrix = Figure(figsize=(5, 4), dpi=100, facecolor=CHART_BG)
        self.ax_metrix = self.fig_metrix.add_subplot(111)
        self.ax_metrix.set_facecolor(CHART_BG)
        self._style_axis(self.ax_metrix)

        self.canvas_metrix = FigureCanvasTkAgg(self.fig_metrix, master=chart_frame)
        self.canvas_metrix.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # 3. Table
        table_frame = ctk.CTkFrame(parent)
        table_frame.grid(row=0, column=2, sticky="nsew", pady=10)

        self.tree_metrix = ttk.Treeview(table_frame, columns=["day", "count"], show="headings", height=15)
        self.tree_metrix.heading("day", text="DATE")
        self.tree_metrix.heading("count", text="COUNT")
        self.tree_metrix.column("day", width=90, anchor="center")
        self.tree_metrix.column("count", width=70, anchor="center")

        sb = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.tree_metrix.yview)
        self.tree_metrix.configure(yscrollcommand=sb.set)
        
        self.tree_metrix.pack(side="left", fill="both", expand=True, padx=(2,0), pady=2)
        sb.pack(side="right", fill="y", padx=2, pady=2)

    # ---------- HELPERS ----------
    def _style_axis(self, ax):
        ax.tick_params(colors='white', which='both')
        ax.spines['bottom'].set_color('gray')
        ax.spines['left'].set_color('gray')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.label.set_color('white')
        ax.xaxis.label.set_color('white')
        ax.title.set_color('white')

    def _clear_tree(self, tree):
        for item in tree.get_children(): tree.delete(item)

    def _connect(self):
        if self.client is None:
            self.client = MongoClient(MONGO_URI)

    # ---------- EVENT HANDLERS (LOGIC LINKING) ----------
    def on_run(self):
        try:
            self.status_label.configure(text="Querying MongoDB...", text_color="yellow")
            self.run_btn.configure(state="disabled")
            self.update_idletasks()

            start_day = parse_date(self.start_var.get())
            end_day = parse_date(self.end_var.get())
            if start_day > end_day: raise ValueError("Start Date > End Date")

            self._connect()

            # Data Loading
            df_costs = costs_campaigns_daily(self.client, start_day, end_day, self.costs_field_var.get().strip())
            df_metrix = metrix_revenue_daily(self.client, start_day, end_day, self.metrix_field_var.get().strip())
            self._df_metrix_long = df_metrix.copy()

            # Update KPIs
            self._update_kpis(df_costs, df_metrix)

            # Update Costs Tab
            self._fill_costs_table(df_costs)
            self._draw_costs_chart(df_costs)

            # Update Metrix Tab
            cols = ["TOTAL"] + sorted(df_metrix["collection"].unique().tolist()) if not df_metrix.empty else ["TOTAL"]
            self._metrix_collections_all = cols
            self._refresh_metrix_listbox()
            self._update_metrix_views("TOTAL")

            self.status_label.configure(text="Data Loaded Successfully", text_color="#66bb6a") # Green

        except Exception as e:
            self.status_label.configure(text="Error Occurred", text_color="#ef5350")
            messagebox.showerror("Error", str(e))
        finally:
            self.run_btn.configure(state="normal")

    def _update_kpis(self, df_costs, df_metrix):
        # Costs
        c_tot = int(df_costs['total'].sum()) if not df_costs.empty else 0
        c_days = df_costs['day'].nunique() if not df_costs.empty else 0
        self.kpis["costs_total"].configure(text=f"{c_tot:,}")
        self.kpis["costs_days"].configure(text=f"{c_days}")

        # Metrix
        m_tot = int(df_metrix['count'].sum()) if not df_metrix.empty else 0
        m_cols = df_metrix['collection'].nunique() if not df_metrix.empty else 0
        self.kpis["metrix_total"].configure(text=f"{m_tot:,}")
        self.kpis["metrix_cols"].configure(text=f"{m_cols}")

    def _fill_costs_table(self, df):
        self._clear_tree(self.tree_costs)
        if df.empty: return
        for _, r in df.iterrows():
            d_str = r["day"].strftime("%Y-%m-%d")
            self.tree_costs.insert("", "end", values=[d_str, r["mg"], r["tp"], r["yn"], r["cb"], r["total"]])

    def _draw_costs_chart(self, df):
        self.ax_costs.clear()
        if not df.empty:
            x = df["day"]
            for c in CODES:
                self.ax_costs.plot(x, df[c], marker="o", linewidth=2, label=c.upper())
            self.ax_costs.plot(x, df["total"], marker="o", linestyle="--", color="white", alpha=0.5, label="TOTAL")
            self.ax_costs.legend(facecolor=CHART_BG, labelcolor="white", frameon=False)
        else:
            self.ax_costs.text(0.5, 0.5, "No Data", color="white", ha="center")
        
        self.ax_costs.set_title("Campaigns Daily Trend", color="white", pad=10)
        self.fig_costs.autofmt_xdate()
        self.canvas_costs.draw()

    # --- Metrix Specific ---
    def _refresh_metrix_listbox(self):
        q = self.metrix_search_var.get().lower()
        items = [x for x in self._metrix_collections_all if q in x.lower()]
        
        self.metrix_list.delete(0, "end")
        for it in items:
            self.metrix_list.insert("end", it)
        if items:
            self.metrix_list.selection_set(0)

    def _on_metrix_select(self):
        sel = self.metrix_list.curselection()
        if not sel: return
        picked = self.metrix_list.get(sel[0])
        self._update_metrix_views(picked)






    def _update_metrix_views(self, picked):
            self.metrix_title_lbl.configure(text=f"Revenue: {picked}")
            
            # 1. ساختن یک دیتافریم کامل از تمام روزهای بازه (Backbone)
            try:
                s_date = parse_date(self.start_var.get())
                e_date = parse_date(self.end_var.get())
                # ایجاد لیستی از تمام تاریخ‌ها
                all_dates = [d for d in daterange(s_date, e_date)]
                series = pd.DataFrame({"day": pd.to_datetime(all_dates)})
            except Exception:
                # در صورتی که تاریخ‌ها اشتباه باشند یا ست نشده باشند
                series = pd.DataFrame(columns=["day"])
    
            # 2. آماده‌سازی داده‌های موجود در دیتابیس
            df = self._df_metrix_long.copy()
            
            if not df.empty:
                # مطمئن می‌شویم فرمت تاریخ برای Merge یکی باشد
                df["day"] = pd.to_datetime(df["day"])
                
                if picked == "TOTAL":
                    data = df.groupby("day", as_index=False)["count"].sum()
                else:
                    data = df[df["collection"] == picked].groupby("day", as_index=False)["count"].sum()
            else:
                data = pd.DataFrame(columns=["day", "count"])
    
            # 3. ترکیب (Merge) بازه کامل با داده‌های موجود
            # how='left' باعث می‌شود تمام روزهای series حفظ شوند
            if not series.empty:
                series = series.merge(data, on="day", how="left")
                # پر کردن مقادیر NaN با صفر
                series["count"] = series["count"].fillna(0).astype(int)
            else:
                series["count"] = 0
    
            series = series.sort_values("day")
            
            # --- رسم نمودار (Chart) ---
            self.ax_metrix.clear()
            if not series.empty:
                # رسم بار چارت
                self.ax_metrix.bar(series["day"], series["count"], color="#42a5f5", alpha=0.8, width=0.6)
                
                # اگر تعداد روزها کم است، تاریخ‌ها را کامل نشان بده
                if len(series) < 15:
                    self.ax_metrix.set_xticks(series["day"])
                    
            else:
                self.ax_metrix.text(0.5, 0.5, "No Data", color="white", ha="center")
            
            self.fig_metrix.autofmt_xdate()
            self.canvas_metrix.draw()
    
            # --- پر کردن جدول (Table) ---
            self._clear_tree(self.tree_metrix)
            for _, r in series.iterrows():
                 # فرمت‌دهی تاریخ برای نمایش زیباتر
                 d_str = r["day"].strftime("%Y-%m-%d")
                 # نمایش عدد با جداکننده هزارگان
                 count_str = f"{int(r['count']):,}"
                 self.tree_metrix.insert("", "end", values=[d_str, count_str])
    






if __name__ == "__main__":
    app = ModernApp()
    app.mainloop()