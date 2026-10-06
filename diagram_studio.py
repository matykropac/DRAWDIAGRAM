
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, colorchooser
import json
import os
import io
import contextlib
import traceback

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("TkAgg")

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


ANTENNA_COLUMNS = [
    "Elevation_deg",
    "Azimuth_deg",
    "Abs_Grlz_dB",
    "Abs_Cross_dB",
    "Phase_Cross_deg",
    "Abs_Copol_dB",
    "Phase_Copol_deg",
    "Ax_Ratio_dB",
]


class Curve:
    def __init__(self, name="Curve"):
        self.name = name
        self.x = []
        self.y = []
        self.color = None
        self.linestyle = "-"
        self.linewidth = 1.8
        self.marker = "None"
        self.markersize = 5.0
        self.alpha = 1.0
        self.visible = True

    def to_dict(self):
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "color": self.color,
            "linestyle": self.linestyle,
            "linewidth": self.linewidth,
            "marker": self.marker,
            "markersize": self.markersize,
            "alpha": self.alpha,
            "visible": self.visible,
        }

    @staticmethod
    def from_dict(data):
        c = Curve(data.get("name", "Curve"))
        c.x = data.get("x", [])
        c.y = data.get("y", [])
        c.color = data.get("color")
        c.linestyle = data.get("linestyle", "-")
        c.linewidth = data.get("linewidth", 1.8)
        c.marker = data.get("marker", "None")
        c.markersize = data.get("markersize", 5.0)
        c.alpha = data.get("alpha", 1.0)
        c.visible = data.get("visible", True)
        return c


class DiagramStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Engineering Diagram Studio")
        self.geometry("1550x920")
        self.minsize(1150, 720)

        self.curves = []
        self.current_curve_index = None
        self.console_extra_artists = []

        self.create_variables()
        self.create_layout()
        self.add_curve()
        self.redraw()

    def create_variables(self):
        self.title_var = tk.StringVar(value="")
        self.xlabel_var = tk.StringVar(value="X")
        self.ylabel_var = tk.StringVar(value="Y")

        self.xmin_var = tk.StringVar(value="")
        self.xmax_var = tk.StringVar(value="")
        self.ymin_var = tk.StringVar(value="")
        self.ymax_var = tk.StringVar(value="")

        self.xscale_var = tk.StringVar(value="Linear")
        self.yscale_var = tk.StringVar(value="Linear")

        self.plot_mode_var = tk.StringVar(value="Cartesian")
        self.polar_db_min_var = tk.StringVar(value="-60")

        self.grid_var = tk.BooleanVar(value=True)
        self.minor_grid_var = tk.BooleanVar(value=True)
        self.legend_var = tk.BooleanVar(value=True)

        self.curve_name_var = tk.StringVar()
        self.line_style_var = tk.StringVar(value="Solid")
        self.line_width_var = tk.DoubleVar(value=1.8)
        self.marker_var = tk.StringVar(value="None")
        self.marker_size_var = tk.DoubleVar(value=5.0)
        self.alpha_var = tk.DoubleVar(value=1.0)
        self.visible_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value="Ready")

    def create_layout(self):
        self.create_menu()

        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(main, width=410)
        right = ttk.Frame(main)
        main.add(left, weight=0)
        main.add(right, weight=1)

        self.create_left_panel(left)
        self.create_plot_area(right)

        status = ttk.Label(self, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def create_menu(self):
        menu = tk.Menu(self)
        file_menu = tk.Menu(menu, tearoff=0)
        file_menu.add_command(label="New project", command=self.new_project)
        file_menu.add_command(label="Open project...", command=self.open_project)
        file_menu.add_command(label="Save project...", command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Import data...", command=self.import_data)
        file_menu.add_command(label="Export image...", command=self.export_figure)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menu.add_cascade(label="File", menu=file_menu)
        self.config(menu=menu)

    def create_left_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        plot_tab = ttk.Frame(notebook)
        curves_tab = ttk.Frame(notebook)
        data_tab = ttk.Frame(notebook)
        console_tab = ttk.Frame(notebook)

        notebook.add(plot_tab, text="Plot")
        notebook.add(curves_tab, text="Curves")
        notebook.add(data_tab, text="Data")
        notebook.add(console_tab, text="Console")

        self.create_plot_settings(plot_tab)
        self.create_curve_settings(curves_tab)
        self.create_data_editor(data_tab)
        self.create_console(console_tab)

    def create_plot_settings(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        row = 0

        def add_label_entry(label, var):
            nonlocal row
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            ttk.Entry(frame, textvariable=var).grid(row=row, column=1, sticky="ew", padx=5, pady=3)
            row += 1

        ttk.Label(frame, text="Plot type").grid(row=row, column=0, sticky="w")
        combo = ttk.Combobox(
            frame,
            textvariable=self.plot_mode_var,
            values=["Cartesian", "Polar"],
            state="readonly",
        )
        combo.grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        combo.bind("<<ComboboxSelected>>", lambda e: self.redraw())
        row += 1

        add_label_entry("Polar dB floor", self.polar_db_min_var)

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        add_label_entry("Title", self.title_var)
        add_label_entry("X axis", self.xlabel_var)
        add_label_entry("Y axis", self.ylabel_var)

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        add_label_entry("X min", self.xmin_var)
        add_label_entry("X max", self.xmax_var)
        add_label_entry("Y min", self.ymin_var)
        add_label_entry("Y max", self.ymax_var)

        ttk.Label(frame, text="X scale").grid(row=row, column=0, sticky="w")
        ttk.Combobox(
            frame, textvariable=self.xscale_var,
            values=["Linear", "Log"], state="readonly"
        ).grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1

        ttk.Label(frame, text="Y scale").grid(row=row, column=0, sticky="w")
        ttk.Combobox(
            frame, textvariable=self.yscale_var,
            values=["Linear", "Log"], state="readonly"
        ).grid(row=row, column=1, sticky="ew", padx=5, pady=3)
        row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        ttk.Checkbutton(frame, text="Major grid", variable=self.grid_var, command=self.redraw).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        ttk.Checkbutton(frame, text="Minor grid", variable=self.minor_grid_var, command=self.redraw).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        ttk.Checkbutton(frame, text="Legend", variable=self.legend_var, command=self.redraw).grid(
            row=row, column=0, columnspan=2, sticky="w"
        )
        row += 1

        ttk.Button(frame, text="APPLY", command=self.redraw).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(15, 5)
        )
        row += 1

        ttk.Button(frame, text="Auto scale axes", command=self.auto_scale).grid(
            row=row, column=0, columnspan=2, sticky="ew"
        )

        frame.columnconfigure(1, weight=1)

    def create_curve_settings(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        self.curve_list = tk.Listbox(frame, height=10)
        self.curve_list.pack(fill=tk.X, pady=(0, 5))
        self.curve_list.bind("<<ListboxSelect>>", self.select_curve)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)

        ttk.Button(buttons, text="+ Add", command=self.add_curve).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Delete", command=self.delete_curve).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Duplicate", command=self.duplicate_curve).pack(side=tk.LEFT, expand=True, fill=tk.X)

        props = ttk.LabelFrame(frame, text="Curve properties")
        props.pack(fill=tk.X, pady=12)

        rows = [
            ("Name", ttk.Entry(props, textvariable=self.curve_name_var)),
            ("Line", ttk.Combobox(
                props, textvariable=self.line_style_var,
                values=["Solid", "Dashed", "Dotted", "Dash-dot", "None"], state="readonly"
            )),
            ("Width", ttk.Spinbox(
                props, from_=0.2, to=10, increment=0.2, textvariable=self.line_width_var
            )),
            ("Marker", ttk.Combobox(
                props, textvariable=self.marker_var,
                values=["None", "Circle", "Square", "Triangle", "Diamond", "Plus", "Cross", "Point"],
                state="readonly"
            )),
            ("Marker size", ttk.Spinbox(
                props, from_=1, to=30, increment=1, textvariable=self.marker_size_var
            )),
            ("Opacity", ttk.Spinbox(
                props, from_=0.1, to=1.0, increment=0.1, textvariable=self.alpha_var
            )),
        ]

        for i, (label, widget) in enumerate(rows):
            ttk.Label(props, text=label).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            widget.grid(row=i, column=1, sticky="ew", padx=5, pady=4)

        ttk.Checkbutton(props, text="Visible", variable=self.visible_var).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=5, pady=4
        )

        ttk.Button(props, text="Choose color", command=self.choose_curve_color).grid(
            row=7, column=0, columnspan=2, sticky="ew", padx=5, pady=5
        )

        ttk.Button(props, text="Apply curve settings", command=self.apply_curve_settings).grid(
            row=8, column=0, columnspan=2, sticky="ew", padx=5, pady=8
        )

        ttk.Button(
            frame,
            text="IMPORT DATA / ANTENNA PATTERN",
            command=self.import_data
        ).pack(fill=tk.X, pady=10)

        props.columnconfigure(1, weight=1)

    def create_data_editor(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        ttk.Label(frame, text="Points of selected curve").pack(anchor="w")

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.data_tree = ttk.Treeview(
            table_frame,
            columns=("x", "y"),
            show="headings",
            selectmode="extended"
        )

        self.data_tree.heading("x", text="X")
        self.data_tree.heading("y", text="Y")
        self.data_tree.column("x", width=120, anchor="center")
        self.data_tree.column("y", width=120, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)

        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_tree.bind("<Double-1>", self.edit_tree_cell)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X)

        ttk.Button(buttons, text="+ Point", command=self.add_point).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Delete", command=self.delete_points).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Sort X", command=self.sort_points).pack(side=tk.LEFT, expand=True, fill=tk.X)

        paste_frame = ttk.LabelFrame(frame, text="Paste X / Y data")
        paste_frame.pack(fill=tk.X, pady=10)

        self.paste_text = tk.Text(paste_frame, height=8, wrap="none")
        self.paste_text.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            paste_frame,
            text="Replace curve with pasted data",
            command=self.replace_with_pasted_data
        ).pack(fill=tk.X, padx=5, pady=5)

    def create_console(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        info = (
            "Python console for the current Matplotlib axes.\n\n"
            "Available names:\n"
            "  ax       current Matplotlib axes\n"
            "  fig      current Figure\n"
            "  np       NumPy\n"
            "  pd       Pandas\n"
            "  curves   list of Curve objects\n"
            "  current  selected Curve (or None)\n\n"
            "Examples:\n"
            "  ax.axhline(0)\n"
            "  ax.set_xlim(0, 900)\n"
            "  ax.plot([0,100,200],[0,50,100], '--')\n"
            "  x=np.linspace(0.5,30,500)\n"
            "  y=20*np.log10(np.sin(np.deg2rad(5))/np.sin(np.deg2rad(x)))\n"
            "  ax.plot(x,y,label='cosecant')\n"
            "  ax.legend()\n\n"
            "Note: this is a full local Python console. Run only code you trust."
        )
        ttk.Label(frame, text=info, justify="left", wraplength=370).pack(anchor="w", pady=(0, 8))

        self.console_input = tk.Text(frame, height=14, wrap="none")
        self.console_input.pack(fill=tk.BOTH, expand=True)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=5)

        ttk.Button(buttons, text="RUN", command=self.run_console).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Clear input", command=lambda: self.console_input.delete("1.0", tk.END)).pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )
        ttk.Button(buttons, text="Redraw base plot", command=self.redraw).pack(
            side=tk.LEFT, expand=True, fill=tk.X
        )

        ttk.Label(frame, text="Output / errors").pack(anchor="w", pady=(8, 2))

        self.console_output = tk.Text(frame, height=9, wrap="word", state="disabled")
        self.console_output.pack(fill=tk.BOTH, expand=True)

    def create_plot_area(self, parent):
        self.figure = Figure(figsize=(10, 7), dpi=100)
        self.ax = self.figure.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar_frame = ttk.Frame(parent)
        toolbar_frame.pack(fill=tk.X)

        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

    # ------------------------- curve handling -------------------------

    def add_curve(self):
        curve = Curve(f"Curve {len(self.curves) + 1}")
        self.curves.append(curve)
        self.current_curve_index = len(self.curves) - 1
        self.refresh_curve_list()
        self.curve_list.selection_clear(0, tk.END)
        self.curve_list.selection_set(self.current_curve_index)
        self.load_curve_settings()
        self.refresh_data_table()
        self.redraw()

    def delete_curve(self):
        if self.current_curve_index is None:
            return
        if len(self.curves) <= 1:
            messagebox.showinfo("Delete curve", "At least one curve must remain.")
            return

        del self.curves[self.current_curve_index]
        self.current_curve_index = max(0, self.current_curve_index - 1)
        self.refresh_curve_list()
        self.curve_list.selection_set(self.current_curve_index)
        self.load_curve_settings()
        self.refresh_data_table()
        self.redraw()

    def duplicate_curve(self):
        if self.current_curve_index is None:
            return

        source = self.curves[self.current_curve_index]
        clone = Curve(source.name + " copy")
        clone.x = list(source.x)
        clone.y = list(source.y)
        clone.color = source.color
        clone.linestyle = source.linestyle
        clone.linewidth = source.linewidth
        clone.marker = source.marker
        clone.markersize = source.markersize
        clone.alpha = source.alpha
        clone.visible = source.visible

        self.curves.append(clone)
        self.current_curve_index = len(self.curves) - 1
        self.refresh_curve_list()
        self.curve_list.selection_set(self.current_curve_index)
        self.load_curve_settings()
        self.refresh_data_table()
        self.redraw()

    def refresh_curve_list(self):
        self.curve_list.delete(0, tk.END)
        for curve in self.curves:
            prefix = "✓ " if curve.visible else "✗ "
            self.curve_list.insert(tk.END, prefix + curve.name)

    def select_curve(self, event=None):
        selection = self.curve_list.curselection()
        if not selection:
            return
        self.current_curve_index = selection[0]
        self.load_curve_settings()
        self.refresh_data_table()

    def load_curve_settings(self):
        if self.current_curve_index is None:
            return

        curve = self.curves[self.current_curve_index]

        self.curve_name_var.set(curve.name)

        styles = {
            "-": "Solid",
            "--": "Dashed",
            ":": "Dotted",
            "-.": "Dash-dot",
            "None": "None"
        }
        markers = {
            "None": "None",
            "o": "Circle",
            "s": "Square",
            "^": "Triangle",
            "D": "Diamond",
            "+": "Plus",
            "x": "Cross",
            ".": "Point"
        }

        self.line_style_var.set(styles.get(curve.linestyle, "Solid"))
        self.line_width_var.set(curve.linewidth)
        self.marker_var.set(markers.get(curve.marker, "None"))
        self.marker_size_var.set(curve.markersize)
        self.alpha_var.set(curve.alpha)
        self.visible_var.set(curve.visible)

    def apply_curve_settings(self):
        if self.current_curve_index is None:
            return

        curve = self.curves[self.current_curve_index]
        curve.name = self.curve_name_var.get().strip() or "Curve"

        styles = {
            "Solid": "-",
            "Dashed": "--",
            "Dotted": ":",
            "Dash-dot": "-.",
            "None": "None"
        }
        markers = {
            "None": "None",
            "Circle": "o",
            "Square": "s",
            "Triangle": "^",
            "Diamond": "D",
            "Plus": "+",
            "Cross": "x",
            "Point": "."
        }

        curve.linestyle = styles.get(self.line_style_var.get(), "-")
        curve.marker = markers.get(self.marker_var.get(), "None")
        curve.linewidth = float(self.line_width_var.get())
        curve.markersize = float(self.marker_size_var.get())
        curve.alpha = float(self.alpha_var.get())
        curve.visible = self.visible_var.get()

        self.refresh_curve_list()
        self.redraw()

    def choose_curve_color(self):
        if self.current_curve_index is None:
            return

        curve = self.curves[self.current_curve_index]
        result = colorchooser.askcolor(color=curve.color or "#1f77b4")
        if result[1]:
            curve.color = result[1]
            self.redraw()

    # ------------------------- data editing -------------------------

    def refresh_data_table(self):
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        if self.current_curve_index is None:
            return

        curve = self.curves[self.current_curve_index]
        for x, y in zip(curve.x, curve.y):
            self.data_tree.insert("", tk.END, values=(x, y))

    def add_point(self):
        if self.current_curve_index is None:
            return

        x = simpledialog.askfloat("X", "X value:")
        if x is None:
            return

        y = simpledialog.askfloat("Y", "Y value:")
        if y is None:
            return

        curve = self.curves[self.current_curve_index]
        curve.x.append(x)
        curve.y.append(y)

        self.refresh_data_table()
        self.redraw()

    def delete_points(self):
        selected = self.data_tree.selection()
        if not selected:
            return

        curve = self.curves[self.current_curve_index]
        indices = sorted(
            [self.data_tree.index(i) for i in selected],
            reverse=True
        )

        for i in indices:
            del curve.x[i]
            del curve.y[i]

        self.refresh_data_table()
        self.redraw()

    def sort_points(self):
        if self.current_curve_index is None:
            return

        curve = self.curves[self.current_curve_index]
        points = sorted(zip(curve.x, curve.y), key=lambda p: p[0])

        if points:
            curve.x = [p[0] for p in points]
            curve.y = [p[1] for p in points]

        self.refresh_data_table()
        self.redraw()

    def edit_tree_cell(self, event):
        region = self.data_tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.data_tree.identify_row(event.y)
        column = self.data_tree.identify_column(event.x)

        if not row_id:
            return

        column_index = int(column.replace("#", "")) - 1
        bbox = self.data_tree.bbox(row_id, column)
        if not bbox:
            return

        x0, y0, width, height = bbox
        old_value = self.data_tree.item(row_id, "values")[column_index]

        editor = ttk.Entry(self.data_tree)
        editor.place(x=x0, y=y0, width=width, height=height)
        editor.insert(0, old_value)
        editor.select_range(0, tk.END)
        editor.focus()

        def save(event=None):
            try:
                value = float(editor.get().replace(",", "."))
            except ValueError:
                editor.destroy()
                return

            row_index = self.data_tree.index(row_id)
            curve = self.curves[self.current_curve_index]

            if column_index == 0:
                curve.x[row_index] = value
            else:
                curve.y[row_index] = value

            editor.destroy()
            self.refresh_data_table()
            self.redraw()

        editor.bind("<Return>", save)
        editor.bind("<FocusOut>", save)

    def parse_pasted_points(self):
        text = self.paste_text.get("1.0", tk.END).strip()
        points = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            if "\t" in line:
                parts = line.split("\t")
            elif ";" in line:
                parts = line.split(";")
            else:
                parts = line.split()

            if len(parts) < 2:
                continue

            try:
                x = float(parts[0].replace(",", "."))
                y = float(parts[1].replace(",", "."))
                points.append((x, y))
            except ValueError:
                continue

        return points

    def replace_with_pasted_data(self):
        points = self.parse_pasted_points()

        if not points:
            messagebox.showwarning("Data", "No valid X/Y pairs found.")
            return

        curve = self.curves[self.current_curve_index]
        curve.x = [p[0] for p in points]
        curve.y = [p[1] for p in points]

        self.refresh_data_table()
        self.redraw()

    # ------------------------- file import -------------------------

    def import_data(self):
        filename = filedialog.askopenfilename(
            title="Import data",
            filetypes=[
                ("Data files", "*.txt *.csv *.xlsx *.xls"),
                ("Text files", "*.txt"),
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )

        if not filename:
            return

        try:
            df, detected_type = self.read_data_file(filename)
            self.choose_import_columns(df, filename, detected_type)
        except Exception as exc:
            messagebox.showerror("Import error", str(exc))

    def read_data_file(self, filename):
        extension = os.path.splitext(filename)[1].lower()

        if extension in [".xlsx", ".xls"]:
            return pd.read_excel(filename), "general"

        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()

        if "Elev." in first_line and "Azim." in first_line:
            df = pd.read_csv(
                filename,
                sep=r"\s+",
                skiprows=2,
                header=None,
                names=ANTENNA_COLUMNS,
                engine="python"
            )

            for column in ANTENNA_COLUMNS:
                df[column] = pd.to_numeric(df[column], errors="coerce")

            df = df.dropna(subset=["Elevation_deg", "Azimuth_deg"])
            return df, "antenna"

        try:
            df = pd.read_csv(filename, sep=None, engine="python")
            if df.shape[1] >= 2:
                return df, "general"
        except Exception:
            pass

        df = pd.read_csv(filename, sep=r"\s+", engine="python")
        return df, "general"

    def choose_import_columns(self, df, filename, detected_type):
        dialog = tk.Toplevel(self)
        dialog.title("Import data")
        dialog.geometry("550x610")
        dialog.transient(self)
        dialog.grab_set()

        columns = [str(c) for c in df.columns]

        preset_var = tk.StringVar(value="General X/Y data")
        x_var = tk.StringVar(value=columns[0])
        y_var = tk.StringVar(value=columns[1] if len(columns) > 1 else columns[0])
        filter_var = tk.StringVar(value="(none)")
        filter_value_var = tk.StringVar(value="0")
        normalize_var = tk.BooleanVar(value=False)
        name_var = tk.StringVar(value="Imported curve")

        ttk.Label(
            dialog,
            text=os.path.basename(filename),
            font=("TkDefaultFont", 10, "bold")
        ).pack(padx=10, pady=(12, 3))

        if detected_type == "antenna":
            ttk.Label(dialog, text="Antenna-pattern format detected").pack(pady=(0, 10))

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        row = 0

        ttk.Label(frame, text="Preset").grid(row=row, column=0, sticky="w", pady=5)
        preset_combo = ttk.Combobox(
            frame,
            textvariable=preset_var,
            values=[
                "General X/Y data",
                "Vertical antenna pattern",
                "Horizontal antenna pattern"
            ],
            state="readonly"
        )
        preset_combo.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        for label, var in [
            ("X column", x_var),
            ("Y column", y_var)
        ]:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Combobox(frame, textvariable=var, values=columns, state="readonly").grid(
                row=row, column=1, sticky="ew"
            )
            row += 1

        ttk.Separator(frame).grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1

        ttk.Label(frame, text="Filter column").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Combobox(
            frame,
            textvariable=filter_var,
            values=["(none)"] + columns,
            state="readonly"
        ).grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Filter value").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=filter_value_var).grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Label(frame, text="Curve name").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=name_var).grid(row=row, column=1, sticky="ew")
        row += 1

        ttk.Checkbutton(
            frame,
            text="Normalize Y maximum to 0 dB",
            variable=normalize_var
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=10)
        row += 1

        info_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=info_var, wraplength=470).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=8
        )

        frame.columnconfigure(1, weight=1)

        def apply_preset(event=None):
            preset = preset_var.get()

            if preset == "Vertical antenna pattern":
                if "Elevation_deg" in columns:
                    x_var.set("Elevation_deg")
                if "Abs_Copol_dB" in columns:
                    y_var.set("Abs_Copol_dB")
                if "Azimuth_deg" in columns:
                    filter_var.set("Azimuth_deg")

                filter_value_var.set("0")
                normalize_var.set(True)
                name_var.set("Vertical pattern")
                info_var.set("Vertical cut: gain versus elevation at selected azimuth.")

            elif preset == "Horizontal antenna pattern":
                if "Azimuth_deg" in columns:
                    x_var.set("Azimuth_deg")
                if "Abs_Copol_dB" in columns:
                    y_var.set("Abs_Copol_dB")
                if "Elevation_deg" in columns:
                    filter_var.set("Elevation_deg")

                filter_value_var.set("0")
                normalize_var.set(True)
                name_var.set("Horizontal pattern")
                info_var.set("Horizontal cut: gain versus azimuth at selected elevation.")

            else:
                filter_var.set("(none)")
                normalize_var.set(False)
                info_var.set("General X/Y import.")

        preset_combo.bind("<<ComboboxSelected>>", apply_preset)

        if detected_type == "antenna":
            preset_var.set("Vertical antenna pattern")
            apply_preset()

        def import_selected():
            try:
                work = df.copy()
                filter_column = filter_var.get()
                actual_filter_value = None

                if filter_column != "(none)":
                    numeric_filter = pd.to_numeric(work[filter_column], errors="coerce")
                    requested = float(filter_value_var.get().replace(",", "."))

                    available = np.asarray(
                        sorted(numeric_filter.dropna().unique()),
                        dtype=float
                    )

                    if len(available) == 0:
                        raise ValueError("Filter column contains no numeric values.")

                    actual_filter_value = available[
                        np.argmin(np.abs(available - requested))
                    ]

                    mask = np.isclose(
                        numeric_filter,
                        actual_filter_value,
                        rtol=0,
                        atol=1e-8
                    )
                    work = work.loc[mask].copy()

                x_series = pd.to_numeric(work[x_var.get()], errors="coerce")
                y_series = pd.to_numeric(work[y_var.get()], errors="coerce")

                valid = x_series.notna() & y_series.notna()

                x_data = x_series[valid].to_numpy(dtype=float)
                y_data = y_series[valid].to_numpy(dtype=float)

                if len(x_data) == 0:
                    raise ValueError("No valid X/Y data after filtering.")

                order = np.argsort(x_data)
                x_data = x_data[order]
                y_data = y_data[order]

                if normalize_var.get():
                    y_data = y_data - np.nanmax(y_data)

                curve_name = name_var.get().strip() or y_var.get()

                if actual_filter_value is not None:
                    curve_name += f" ({filter_column}={actual_filter_value:g}°)"

                curve = Curve(curve_name)
                curve.x = x_data.tolist()
                curve.y = y_data.tolist()

                self.curves.append(curve)
                self.current_curve_index = len(self.curves) - 1

                self.refresh_curve_list()
                self.curve_list.selection_clear(0, tk.END)
                self.curve_list.selection_set(self.current_curve_index)
                self.load_curve_settings()
                self.refresh_data_table()

                if x_var.get() == "Elevation_deg":
                    self.xlabel_var.set("Elevation [deg]")
                elif x_var.get() == "Azimuth_deg":
                    self.xlabel_var.set("Azimuth [deg]")
                else:
                    self.xlabel_var.set(x_var.get())

                if "_dB" in y_var.get():
                    self.ylabel_var.set(
                        "Relative Gain [dB]" if normalize_var.get()
                        else "Gain [dB]"
                    )
                else:
                    self.ylabel_var.set(y_var.get())

                if "_dB" in y_var.get() and normalize_var.get():
                    self.ymin_var.set("-60")
                    self.ymax_var.set("1")

                self.redraw()
                self.status_var.set(f"Imported {len(x_data)} points")
                dialog.destroy()

            except Exception as exc:
                messagebox.showerror(
                    "Import error",
                    str(exc),
                    parent=dialog
                )

        ttk.Button(
            dialog,
            text="IMPORT CURVE",
            command=import_selected
        ).pack(fill=tk.X, padx=15, pady=15)

    # ------------------------- plotting -------------------------

    def redraw(self):
        if not hasattr(self, "figure"):
            return

        self.figure.clear()

        if self.plot_mode_var.get() == "Polar":
            self.ax = self.figure.add_subplot(111, projection="polar")

            try:
                db_floor = float(self.polar_db_min_var.get().replace(",", "."))
            except Exception:
                db_floor = -60.0

            if db_floor >= 0:
                db_floor = -60.0

            for curve in self.curves:
                if not curve.visible or len(curve.x) == 0 or len(curve.y) == 0:
                    continue

                angle_deg = np.asarray(curve.x, dtype=float)
                gain_db = np.asarray(curve.y, dtype=float)

                valid = np.isfinite(angle_deg) & np.isfinite(gain_db)
                angle_deg = angle_deg[valid]
                gain_db = gain_db[valid]

                if len(angle_deg) == 0:
                    continue

                angle_deg = np.mod(angle_deg, 360.0)
                order = np.argsort(angle_deg)
                angle_deg = angle_deg[order]
                gain_db = gain_db[order]

                gain_clipped = np.clip(gain_db, db_floor, 0.0)
                radius = gain_clipped - db_floor
                theta = np.deg2rad(angle_deg)

                if len(theta) > 1:
                    theta = np.append(theta, theta[0] + 2 * np.pi)
                    radius = np.append(radius, radius[0])

                kwargs = {
                    "label": curve.name,
                    "linestyle": curve.linestyle,
                    "linewidth": curve.linewidth,
                    "marker": curve.marker,
                    "markersize": curve.markersize,
                    "alpha": curve.alpha,
                }

                if curve.color:
                    kwargs["color"] = curve.color

                self.ax.plot(theta, radius, **kwargs)

            self.ax.set_theta_zero_location("N")
            self.ax.set_theta_direction(-1)
            self.ax.set_thetagrids(np.arange(0, 360, 15))

            radial_max = abs(db_floor)
            self.ax.set_ylim(0, radial_max)

            possible_ticks = np.array([-60, -50, -40, -30, -20, -10, 0], dtype=float)
            db_ticks = possible_ticks[possible_ticks >= db_floor]

            if db_floor not in db_ticks:
                db_ticks = np.insert(db_ticks, 0, db_floor)

            db_ticks = np.unique(db_ticks)
            radial_ticks = db_ticks - db_floor

            self.ax.set_yticks(radial_ticks)
            self.ax.set_yticklabels([f"{v:g} dB" for v in db_ticks])
            self.ax.set_rlabel_position(135)
            self.ax.grid(True, which="major", alpha=0.45)
            self.ax.set_title(self.title_var.get(), pad=25, fontsize=14)

        else:
            self.ax = self.figure.add_subplot(111)

            self.ax.set_xscale("log" if self.xscale_var.get() == "Log" else "linear")
            self.ax.set_yscale("log" if self.yscale_var.get() == "Log" else "linear")

            for curve in self.curves:
                if not curve.visible or len(curve.x) == 0 or len(curve.y) == 0:
                    continue

                kwargs = {
                    "label": curve.name,
                    "linestyle": curve.linestyle,
                    "linewidth": curve.linewidth,
                    "marker": curve.marker,
                    "markersize": curve.markersize,
                    "alpha": curve.alpha,
                }

                if curve.color:
                    kwargs["color"] = curve.color

                self.ax.plot(curve.x, curve.y, **kwargs)

            self.ax.set_title(self.title_var.get(), fontsize=14)
            self.ax.set_xlabel(self.xlabel_var.get())
            self.ax.set_ylabel(self.ylabel_var.get())

            xmin = self.parse_optional_float(self.xmin_var.get())
            xmax = self.parse_optional_float(self.xmax_var.get())
            ymin = self.parse_optional_float(self.ymin_var.get())
            ymax = self.parse_optional_float(self.ymax_var.get())

            if xmin is not None or xmax is not None:
                self.ax.set_xlim(left=xmin, right=xmax)

            if ymin is not None or ymax is not None:
                self.ax.set_ylim(bottom=ymin, top=ymax)

            if self.minor_grid_var.get():
                self.ax.minorticks_on()
            else:
                self.ax.minorticks_off()

            if self.grid_var.get():
                self.ax.grid(True, which="major", alpha=0.35, linewidth=0.8)

            if self.minor_grid_var.get():
                self.ax.grid(True, which="minor", alpha=0.15, linewidth=0.5)

        if self.legend_var.get():
            handles, labels = self.ax.get_legend_handles_labels()
            if handles:
                self.ax.legend()

        self.figure.tight_layout()
        self.canvas.draw_idle()

    # ------------------------- console -------------------------

    def append_console_output(self, text):
        self.console_output.configure(state="normal")
        self.console_output.insert(tk.END, text)
        if not text.endswith("\n"):
            self.console_output.insert(tk.END, "\n")
        self.console_output.see(tk.END)
        self.console_output.configure(state="disabled")

    def run_console(self):
        code = self.console_input.get("1.0", tk.END).strip()
        if not code:
            return

        current = None
        if self.current_curve_index is not None and 0 <= self.current_curve_index < len(self.curves):
            current = self.curves[self.current_curve_index]

        namespace = {
            "__builtins__": __builtins__,
            "np": np,
            "pd": pd,
            "ax": self.ax,
            "fig": self.figure,
            "curves": self.curves,
            "current": current,
        }

        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, namespace, namespace)

            printed = stdout.getvalue()
            if printed:
                self.append_console_output(printed)

            self.canvas.draw_idle()
            self.status_var.set("Console command executed")

        except Exception:
            self.append_console_output(traceback.format_exc())
            self.status_var.set("Console error")

    # ------------------------- misc -------------------------

    @staticmethod
    def parse_optional_float(value):
        value = value.strip()
        if not value:
            return None
        return float(value.replace(",", "."))

    def auto_scale(self):
        self.xmin_var.set("")
        self.xmax_var.set("")
        self.ymin_var.set("")
        self.ymax_var.set("")
        self.redraw()

    def export_figure(self):
        filename = filedialog.asksaveasfilename(
            title="Export diagram",
            defaultextension=".png",
            filetypes=[
                ("PNG", "*.png"),
                ("PDF", "*.pdf"),
                ("SVG", "*.svg"),
                ("JPEG", "*.jpg"),
                ("TIFF", "*.tif")
            ]
        )

        if not filename:
            return

        extension = os.path.splitext(filename)[1].lower()

        try:
            if extension in [".png", ".jpg", ".jpeg", ".tif", ".tiff"]:
                self.figure.savefig(filename, dpi=300, bbox_inches="tight")
            else:
                self.figure.savefig(filename, bbox_inches="tight")

            self.status_var.set(f"Exported: {filename}")

        except Exception as exc:
            messagebox.showerror("Export error", str(exc))

    def save_project(self):
        filename = filedialog.asksaveasfilename(
            title="Save project",
            defaultextension=".diagram.json",
            filetypes=[
                ("Diagram project", "*.diagram.json"),
                ("JSON", "*.json")
            ]
        )

        if not filename:
            return

        data = {
            "plot": {
                "title": self.title_var.get(),
                "xlabel": self.xlabel_var.get(),
                "ylabel": self.ylabel_var.get(),
                "xmin": self.xmin_var.get(),
                "xmax": self.xmax_var.get(),
                "ymin": self.ymin_var.get(),
                "ymax": self.ymax_var.get(),
                "xscale": self.xscale_var.get(),
                "yscale": self.yscale_var.get(),
                "plot_mode": self.plot_mode_var.get(),
                "polar_db_min": self.polar_db_min_var.get(),
                "grid": self.grid_var.get(),
                "minor_grid": self.minor_grid_var.get(),
                "legend": self.legend_var.get(),
            },
            "curves": [curve.to_dict() for curve in self.curves]
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.status_var.set(f"Saved: {filename}")

        except Exception as exc:
            messagebox.showerror("Save error", str(exc))

    def open_project(self):
        filename = filedialog.askopenfilename(
            title="Open project",
            filetypes=[
                ("Diagram project", "*.diagram.json"),
                ("JSON", "*.json")
            ]
        )

        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            plot = data.get("plot", {})

            self.title_var.set(plot.get("title", ""))
            self.xlabel_var.set(plot.get("xlabel", "X"))
            self.ylabel_var.set(plot.get("ylabel", "Y"))
            self.xmin_var.set(plot.get("xmin", ""))
            self.xmax_var.set(plot.get("xmax", ""))
            self.ymin_var.set(plot.get("ymin", ""))
            self.ymax_var.set(plot.get("ymax", ""))
            self.xscale_var.set(plot.get("xscale", "Linear"))
            self.yscale_var.set(plot.get("yscale", "Linear"))
            self.plot_mode_var.set(plot.get("plot_mode", "Cartesian"))
            self.polar_db_min_var.set(plot.get("polar_db_min", "-60"))
            self.grid_var.set(plot.get("grid", True))
            self.minor_grid_var.set(plot.get("minor_grid", True))
            self.legend_var.set(plot.get("legend", True))

            self.curves = [
                Curve.from_dict(c)
                for c in data.get("curves", [])
            ]

            if not self.curves:
                self.curves = [Curve("Curve 1")]

            self.current_curve_index = 0

            self.refresh_curve_list()
            self.curve_list.selection_set(0)
            self.load_curve_settings()
            self.refresh_data_table()
            self.redraw()

        except Exception as exc:
            messagebox.showerror("Open error", str(exc))

    def new_project(self):
        if not messagebox.askyesno("New project", "Clear current project?"):
            return

        self.curves = [Curve("Curve 1")]
        self.current_curve_index = 0

        self.title_var.set("")
        self.xlabel_var.set("X")
        self.ylabel_var.set("Y")

        self.xmin_var.set("")
        self.xmax_var.set("")
        self.ymin_var.set("")
        self.ymax_var.set("")

        self.xscale_var.set("Linear")
        self.yscale_var.set("Linear")
        self.plot_mode_var.set("Cartesian")
        self.polar_db_min_var.set("-60")

        self.refresh_curve_list()
        self.curve_list.selection_set(0)
        self.load_curve_settings()
        self.refresh_data_table()
        self.redraw()


if __name__ == "__main__":
    app = DiagramStudio()
    app.mainloop()
