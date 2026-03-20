#!/usr/bin/env python3
"""
Embedded Programming Calculator
A modern calculator designed for embedded systems / firmware development.
Supports hex/dec/oct/bin entry, bitwise ops, shift operations, and a
visual bit-field editor.
"""

import tkinter as tk
from tkinter import ttk
import struct
import math

# ─── Color Palette (GitHub-dark inspired) ────────────────────────────────────
C_BG       = "#0d1117"
C_SURFACE  = "#161b22"
C_SURFACE2 = "#1c2128"
C_BORDER   = "#30363d"
C_TEXT     = "#e6edf3"
C_DIM      = "#6e7681"
C_DIM2     = "#8b949e"

C_HEX      = "#79c0ff"   # blue
C_DEC      = "#56d364"   # green
C_OCT      = "#e3b341"   # yellow
C_BIN      = "#f78166"   # orange-red
C_FLOAT    = "#d2a8ff"   # purple

C_BTN      = "#21262d"
C_BTN_HOV  = "#30363d"
C_BTN_OP   = "#1c2b3a"
C_BTN_LOG  = "#271b3a"
C_BTN_SHF  = "#1a2f3f"
C_BTN_DEL  = "#3d1a1a"

C_GREEN    = "#2ea043"
C_GREEN_HI = "#56d364"
C_BLUE_HI  = "#388bfd"
C_RED      = "#da3633"
C_AMBER    = "#e3b341"
C_PURPLE   = "#8957e5"
C_TEAL     = "#2d6a4f"

C_BIT_0    = "#1c2128"
C_BIT_1    = "#2ea043"
C_BIT_SEL0 = "#1f3a5f"
C_BIT_SEL1 = "#2d6a3f"
C_BIT_OUT  = C_BORDER
C_BIT_SOUT = "#79c0ff"


class EmbeddedCalc:
    # ═══════════════════════════════════════════════════════════════════════════
    # INITIALISATION
    # ═══════════════════════════════════════════════════════════════════════════

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Embedded Calculator")
        self.root.configure(bg=C_BG)
        self.root.minsize(860, 680)

        # ── Core state ────────────────────────────────────────────────────────
        self._value      = 0        # current value (Python arbitrary-precision int)
        self.bit_size    = 32
        self._updating   = False    # guard against recursive trace callbacks

        # ── Calculator state ──────────────────────────────────────────────────
        self.operand1       = None
        self.pending_op     = None
        self.new_entry      = True
        self._drag_moved    = False
        self._pending_gt_id = None   # timer id for > vs >> disambiguation

        # ── Bit-field selection ───────────────────────────────────────────────
        # field_ranges: list of (lo, hi) tuples, one per marked field
        self.field_ranges    = []
        self.active_range_idx = -1   # index into field_ranges currently shown in panel
        self.drag_start_bit     = None
        self._drag_ctrl         = False
        self._pending_new_range = False

        # ── Tk variables ──────────────────────────────────────────────────────
        self.bit_size_var    = tk.StringVar(value="32")
        self.signed_var      = tk.BooleanVar(value=False)
        self.float_enabled   = tk.BooleanVar(value=False)
        self.double_enabled  = tk.BooleanVar(value=False)
        self.input_base_var  = tk.StringVar(value="hex")
        self.expr_var        = tk.StringVar(value="")
        self.field_info_var  = tk.StringVar(value="No selection — click/drag bits below")
        self.field_hex_var   = tk.StringVar()
        self.field_dec_var   = tk.StringVar()

        self.entry_vars    = {}   # base_key -> StringVar
        self.entry_widgets = {}   # base_key -> tk.Entry
        self.entry_colors  = {}   # base_key -> color string
        self.digit_buttons = {}   # char  -> tk.Button

        # Dynamic field-row widgets in the bit-view panel
        self.field_row_vars   = []   # list of (hex_var, dec_var) per range
        self.field_rows_frame = None

        self._build_ui()
        self.root.after(50, self._init_display)

    def _init_display(self):
        self._update_button_states()   # also calls _apply_active_entry_highlight
        self.update_displays()

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_top_bar()
        self._build_entry_fields()
        tk.Frame(self.root, bg=C_BORDER, height=1).pack(fill=tk.X, padx=0)
        self._build_notebook()
        self._bind_keys()

    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_top_bar(self):
        bar = tk.Frame(self.root, bg=C_SURFACE, padx=14, pady=7)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="⬡ EMBEDDED CALC", bg=C_SURFACE, fg=C_DIM2,
                 font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=(0, 18))

        tk.Label(bar, text="WIDTH", bg=C_SURFACE, fg=C_DIM,
                 font=("Consolas", 9)).pack(side=tk.LEFT, padx=(0, 6))

        self._size_btns = {}
        for size in ("8", "16", "32", "64", "128"):
            btn = tk.Radiobutton(
                bar, text=size, variable=self.bit_size_var, value=size,
                bg=C_SURFACE, fg=C_TEXT, selectcolor=C_BLUE_HI,
                activebackground=C_SURFACE, activeforeground=C_TEXT,
                font=("Consolas", 10, "bold"), indicatoron=False,
                relief=tk.FLAT, padx=9, pady=3, cursor="hand2",
                command=self._on_bit_size_change
            )
            btn.pack(side=tk.LEFT, padx=1)
            self._size_btns[size] = btn

        self._vsep(bar)

        tk.Checkbutton(bar, text="Signed", variable=self.signed_var,
                       bg=C_SURFACE, fg=C_TEXT, selectcolor=C_BG,
                       activebackground=C_SURFACE, font=("Consolas", 10),
                       cursor="hand2", command=self.update_displays
                       ).pack(side=tk.LEFT, padx=6)

        self._vsep(bar)

        tk.Checkbutton(bar, text="Float", variable=self.float_enabled,
                       bg=C_SURFACE, fg=C_FLOAT, selectcolor=C_BG,
                       activebackground=C_SURFACE, font=("Consolas", 10),
                       cursor="hand2", command=self._on_float_toggle
                       ).pack(side=tk.LEFT, padx=4)

        tk.Checkbutton(bar, text="Double", variable=self.double_enabled,
                       bg=C_SURFACE, fg=C_FLOAT, selectcolor=C_BG,
                       activebackground=C_SURFACE, font=("Consolas", 10),
                       cursor="hand2", command=self._on_double_toggle
                       ).pack(side=tk.LEFT, padx=4)

    def _vsep(self, parent):
        tk.Frame(parent, bg=C_BORDER, width=1, height=18).pack(
            side=tk.LEFT, fill=tk.Y, padx=10)

    # ── Entry fields ──────────────────────────────────────────────────────────

    def _build_entry_fields(self):
        outer = tk.Frame(self.root, bg=C_BG)
        outer.pack(fill=tk.X, padx=10, pady=6)

        self._entry_container = outer

        bases = [
            ("HEX", "hex",    C_HEX,   set("0123456789ABCDEFabcdef")),
            ("DEC", "dec",    C_DEC,   set("0123456789-")),
            ("OCT", "oct",    C_OCT,   set("01234567")),
            ("BIN", "bin",    C_BIN,   set("01")),
        ]
        for label, key, color, allowed in bases:
            self._make_entry_row(outer, label, key, color, allowed)

        # Optional float / double rows (hidden until checkbox ticked)
        self.float_row = tk.Frame(outer, bg=C_BG)
        self._make_entry_row(self.float_row, "FLT", "float", C_FLOAT,
                             set("0123456789.-+eEnNaAiIfF"))

        self.double_row = tk.Frame(outer, bg=C_BG)
        self._make_entry_row(self.double_row, "DBL", "double", C_FLOAT,
                             set("0123456789.-+eEnNaAiIfF"))

    def _make_entry_row(self, container, label, key, color, allowed):
        row = tk.Frame(container, bg=C_BG)
        row.pack(fill=tk.X, pady=2)

        tk.Label(row, text=label, bg=C_BG, fg=color,
                 font=("Consolas", 11, "bold"), width=5, anchor='w'
                 ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Frame(row, bg=color, width=3).pack(
            side=tk.LEFT, fill=tk.Y, padx=(4, 8), pady=2)

        var = tk.StringVar()
        vcmd = (self.root.register(
            lambda s, a=allowed, k=key: self._validate(s, a, k)
        ), '%P')

        entry = tk.Entry(
            row, textvariable=var, bg=C_SURFACE, fg=color,
            insertbackground=color, relief=tk.FLAT,
            font=("Consolas", 12), bd=0,
            highlightthickness=1,
            highlightbackground=C_BORDER, highlightcolor=color,
            validate='key', validatecommand=vcmd
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 4))

        self.entry_vars[key]    = var
        self.entry_widgets[key] = entry
        self.entry_colors[key]  = color

        var.trace_add('write', lambda *_, k=key: self._on_entry_change(k))
        entry.bind('<FocusIn>',  lambda _, k=key: self._on_entry_focus(k))
        entry.bind('<FocusOut>', lambda _: self._apply_active_entry_highlight())

    # ── Notebook ──────────────────────────────────────────────────────────────

    def _build_notebook(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure('E.TNotebook', background=C_BG, borderwidth=0, tabmargins=0)
        style.configure('E.TNotebook.Tab', background=C_BTN, foreground=C_DIM2,
                        padding=[18, 7], font=("Consolas", 10, "bold"), borderwidth=0)
        style.map('E.TNotebook.Tab',
                  background=[('selected', C_SURFACE)],
                  foreground=[('selected', C_TEXT)])

        nb = ttk.Notebook(self.root, style='E.TNotebook')
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=(4, 10))

        calc_frame = tk.Frame(nb, bg=C_BG)
        nb.add(calc_frame, text="  Calculator  ")
        self._build_calculator(calc_frame)

        bit_frame = tk.Frame(nb, bg=C_BG)
        nb.add(bit_frame, text="  Bit View  ")
        self._build_bit_view(bit_frame)

    # ── Calculator tab ────────────────────────────────────────────────────────

    def _build_calculator(self, parent):
        # Expression / history strip
        expr_strip = tk.Frame(parent, bg=C_SURFACE2, padx=12, pady=5)
        expr_strip.pack(fill=tk.X, padx=8, pady=(8, 2))
        tk.Label(expr_strip, textvariable=self.expr_var, bg=C_SURFACE2,
                 fg=C_DIM2, font=("Consolas", 10), anchor='e'
                 ).pack(fill=tk.X)

        # Input-base selector
        base_bar = tk.Frame(parent, bg=C_BG, padx=8, pady=5)
        base_bar.pack(fill=tk.X)
        tk.Label(base_bar, text="Input base:", bg=C_BG, fg=C_DIM,
                 font=("Consolas", 9)).pack(side=tk.LEFT, padx=(0, 8))
        for b, c in (("hex", C_HEX), ("dec", C_DEC), ("oct", C_OCT), ("bin", C_BIN)):
            tk.Radiobutton(base_bar, text=b.upper(), variable=self.input_base_var,
                           value=b, bg=C_BG, fg=c, selectcolor=C_SURFACE,
                           activebackground=C_BG, font=("Consolas", 10, "bold"),
                           cursor="hand2", command=self._update_button_states
                           ).pack(side=tk.LEFT, padx=8)

        # Button area
        area = tk.Frame(parent, bg=C_BG)
        area.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left  = tk.Frame(area, bg=C_BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = tk.Frame(area, bg=C_BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH)

        self._build_digit_panel(left)
        self._build_op_panel(right)

    def _build_digit_panel(self, parent):
        layout = [
            ["A", "B", "C", "DEL"],
            ["D", "E", "F", "CLR"],
            ["7", "8", "9", "00" ],
            ["4", "5", "6", "FF" ],
            ["1", "2", "3", "NEG"],
            ["0", "00","FF", "="  ],
        ]
        # Deduplicate last row collision — just use clean layout:
        layout = [
            ["A",   "B",   "C",   "DEL"],
            ["D",   "E",   "F",   "CLR"],
            ["7",   "8",   "9",   "00" ],
            ["4",   "5",   "6",   "FF" ],
            ["1",   "2",   "3",   "NEG"],
            ["0",   "0",   "0",   "="  ],
        ]
        layout = [
            ["A",  "B",  "C",  "DEL"],
            ["D",  "E",  "F",  "CLR"],
            ["7",  "8",  "9",  "00" ],
            ["4",  "5",  "6",  "FF" ],
            ["1",  "2",  "3",  "NEG"],
            ["0",  "00", "FF", "="  ],
        ]

        for r, row in enumerate(layout):
            for c, t in enumerate(row):
                is_hex  = t in "ABCDEF"
                is_ctrl = t in ("DEL", "CLR")
                is_sp   = t in ("FF", "NEG", "00")
                is_eq   = t == "="

                if is_ctrl:   bg = C_BTN_DEL
                elif is_eq:   bg = C_GREEN
                elif is_sp:   bg = C_TEAL
                elif is_hex:  bg = C_BTN_OP
                else:         bg = C_BTN

                btn = tk.Button(
                    parent, text=t, bg=bg, fg=C_TEXT,
                    activebackground=C_BTN_HOV, activeforeground=C_TEXT,
                    relief=tk.FLAT, font=("Consolas", 11, "bold"),
                    cursor="hand2", bd=0, highlightthickness=0,
                    command=lambda v=t: self._on_calc(v)
                )
                btn.grid(row=r, column=c, padx=2, pady=2, sticky='nsew', ipady=7)
                parent.grid_columnconfigure(c, weight=1)
                parent.grid_rowconfigure(r, weight=1)

                if len(t) == 1 and t in "0123456789ABCDEF":
                    self.digit_buttons[t] = btn

    def _build_op_panel(self, parent):
        #   (display_text, op_token, bg_color)
        OPS = [
            [("+",      "+",    C_BTN_OP),  ("-",    "-",    C_BTN_OP),
             ("×",      "*",    C_BTN_OP),  ("÷",    "/",    C_BTN_OP)],
            [("%",      "%",    C_BTN_OP),  ("AND",  "AND",  C_BTN_LOG),
             ("OR",     "OR",   C_BTN_LOG), ("XOR",  "XOR",  C_BTN_LOG)],
            [("NOT",    "NOT",  C_BTN_LOG), ("~",    "NOT",  C_BTN_LOG),
             ("NEG",    "NEG",  C_BTN_OP),  ("ABS",  "ABS",  C_BTN_OP)],
            [("LSL ←",  "<<",   C_BTN_SHF), ("LSR →",">>",   C_BTN_SHF),
             ("ASR →",  ">>>",  C_BTN_SHF), ("ROL",  "ROL",  C_BTN_SHF)],
            [("ROR",    "ROR",  C_BTN_SHF), ("<<1",  "<<1",  C_BTN_SHF),
             (">>1",    ">>1",  C_BTN_SHF), ("=",    "=",    C_GREEN)],
        ]

        for r, row in enumerate(OPS):
            for c, (disp, op, bg) in enumerate(row):
                btn = tk.Button(
                    parent, text=disp, bg=bg, fg=C_TEXT,
                    activebackground=C_BTN_HOV, activeforeground=C_TEXT,
                    relief=tk.FLAT, font=("Consolas", 10, "bold"),
                    cursor="hand2", bd=0, highlightthickness=0,
                    width=7, command=lambda o=op: self._on_calc(o)
                )
                btn.grid(row=r, column=c, padx=2, pady=2, sticky='nsew', ipady=7)
                parent.grid_columnconfigure(c, weight=1)
                parent.grid_rowconfigure(r, weight=1)

    # ── Bit view tab ──────────────────────────────────────────────────────────

    def _build_bit_view(self, parent):
        info_bar = tk.Frame(parent, bg=C_BG, padx=8, pady=5)
        info_bar.pack(fill=tk.X)
        tk.Label(info_bar,
                 text="Click: toggle bit   |   Drag: select field   |   Ctrl+drag: add field",
                 bg=C_BG, fg=C_DIM, font=("Consolas", 9)
                 ).pack(side=tk.LEFT)
        tk.Button(info_bar, text="Clear Selection", bg=C_BTN, fg=C_DIM2,
                  relief=tk.FLAT, font=("Consolas", 9), cursor="hand2",
                  command=self._clear_field_selection
                  ).pack(side=tk.RIGHT)

        # ── Vertical paned window (drag sash to resize) ────────────────────
        sash_style = ttk.Style()
        sash_style.configure('Bit.TPanedwindow', background=C_BORDER)
        sash_style.configure('Bit.Sash', sashthickness=6, sashpad=2,
                             background=C_BORDER, relief='flat')

        paned = ttk.PanedWindow(parent, orient=tk.VERTICAL, style='Bit.TPanedwindow')
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # ── Top pane: bit canvas ───────────────────────────────────────────
        c_wrap = tk.Frame(paned, bg=C_BG)

        self.bit_canvas = tk.Canvas(c_wrap, bg=C_SURFACE,
                                    highlightthickness=1,
                                    highlightbackground=C_BORDER)
        vsb = tk.Scrollbar(c_wrap, orient=tk.VERTICAL,
                           command=self.bit_canvas.yview)
        self.bit_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.bit_canvas.pack(fill=tk.BOTH, expand=True)

        self.bit_canvas.bind('<Configure>',         lambda _: self._redraw_bits())
        self.bit_canvas.bind('<Button-1>',          self._on_bit_press)
        self.bit_canvas.bind('<B1-Motion>',         self._on_bit_drag)
        self.bit_canvas.bind('<ButtonRelease-1>',   self._on_bit_release)
        self.bit_canvas.bind('<MouseWheel>',
            lambda e: self.bit_canvas.yview_scroll(int(-e.delta / 120), "units"))

        paned.add(c_wrap, weight=3)

        # ── Bottom pane: multi-field panel ─────────────────────────────────
        fp_outer = tk.Frame(paned, bg=C_SURFACE2)

        # Header
        hdr = tk.Frame(fp_outer, bg=C_SURFACE2, padx=10, pady=4)
        hdr.pack(fill=tk.X)
        for col_txt, width_ch in (("●", 2), ("FIELD", 18), ("HEX", 16), ("", 4),
                                   ("DEC", 14), ("", 4), ("", 4)):
            tk.Label(hdr, text=col_txt, bg=C_SURFACE2, fg=C_DIM,
                     font=("Consolas", 8, "bold"), width=width_ch, anchor='w'
                     ).pack(side=tk.LEFT)

        # Scrollable rows area — fills all remaining space in the bottom pane
        rows_canvas = tk.Canvas(fp_outer, bg=C_SURFACE2, highlightthickness=0)
        rows_sb = tk.Scrollbar(fp_outer, orient=tk.VERTICAL,
                               command=rows_canvas.yview)
        rows_canvas.configure(yscrollcommand=rows_sb.set)
        rows_sb.pack(side=tk.RIGHT, fill=tk.Y)
        rows_canvas.pack(fill=tk.BOTH, expand=True)

        self.field_rows_frame = tk.Frame(rows_canvas, bg=C_SURFACE2)
        self._rows_canvas_win = rows_canvas.create_window(
            (0, 0), window=self.field_rows_frame, anchor='nw')

        def _on_rows_configure(e):
            rows_canvas.configure(scrollregion=rows_canvas.bbox('all'))
            rows_canvas.itemconfig(self._rows_canvas_win, width=rows_canvas.winfo_width())
        self.field_rows_frame.bind('<Configure>', _on_rows_configure)
        rows_canvas.bind('<Configure>',
            lambda e: rows_canvas.itemconfig(self._rows_canvas_win, width=e.width))

        self._rows_canvas = rows_canvas

        paned.add(fp_outer, weight=1)

        # "No selection" placeholder label
        self.no_sel_label = tk.Label(
            self.field_rows_frame,
            text="No field selected — drag on bits above to mark a field",
            bg=C_SURFACE2, fg=C_DIM, font=("Consolas", 9), pady=8
        )
        self.no_sel_label.pack()

    # ═══════════════════════════════════════════════════════════════════════════
    # VALUE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def mask(self):
        return (1 << self.bit_size) - 1

    def _clip(self, v):
        return int(v) & self.mask

    def _to_signed(self, v):
        if self.signed_var.get() and v >= (1 << (self.bit_size - 1)):
            return v - (1 << self.bit_size)
        return v

    def set_value(self, v):
        self._value = self._clip(v)
        self.update_displays()

    # ═══════════════════════════════════════════════════════════════════════════
    # DISPLAY / REDRAW
    # ═══════════════════════════════════════════════════════════════════════════

    def update_displays(self):
        if self._updating:
            return
        self._updating = True
        try:
            v  = self._value

            self.entry_vars['hex'].set(format(v, 'X') if v else '0')
            self.entry_vars['dec'].set(str(self._to_signed(v)))
            self.entry_vars['oct'].set(format(v, 'o') if v else '0')
            self.entry_vars['bin'].set(format(v, 'b') if v else '0')

            if self.float_enabled.get():
                self.entry_vars['float'].set(self._as_float(v))
            if self.double_enabled.get():
                self.entry_vars['double'].set(self._as_double(v))

            self._redraw_bits()
        finally:
            self._updating = False

    def _as_float(self, v):
        if self.bit_size < 32:
            return "(needs ≥32 bits)"
        try:
            return repr(struct.unpack('f', struct.pack('I', v & 0xFFFFFFFF))[0])
        except Exception:
            return "—"

    def _as_double(self, v):
        if self.bit_size < 64:
            return "(needs ≥64 bits)"
        try:
            return repr(struct.unpack('d', struct.pack('Q', v & 0xFFFFFFFFFFFFFFFF))[0])
        except Exception:
            return "—"

    # ── Bit canvas ────────────────────────────────────────────────────────────

    # Per-range color palette: (outline, fill_0, fill_1)
    RANGE_COLORS = [
        ("#79c0ff", "#1a3a5c", "#2d5f8a"),   # blue   (range 0)
        ("#ff9f43", "#3f2a10", "#8a5020"),   # orange (range 1)
        ("#d2a8ff", "#2f1f4a", "#6a3a9a"),   # purple (range 2)
        ("#f78166", "#4a1a15", "#8a3020"),   # red    (range 3)
        ("#56d364", "#1a3a25", "#2d8a50"),   # green  (range 4)
        ("#e3b341", "#3a2e10", "#8a6e20"),   # amber  (range 5)
    ]

    def _redraw_bits(self):
        if not hasattr(self, 'bit_canvas'):
            return
        canvas = self.bit_canvas
        canvas.delete('all')
        w = canvas.winfo_width()
        if w < 60:
            return

        n = self.bit_size
        if n <= 8:
            bpr = 8
        elif n <= 16:
            bpr = 16
        else:
            bpr = 32

        n_rows = n // bpr

        PAD_X   = 10
        PAD_Y   = 10
        LABEL_W = 52
        NIB_GAP = 5
        IDX_H   = 16
        BIT_H   = 34
        ROW_GAP = 14

        nibs_per_row  = bpr // 4
        avail_w       = w - PAD_X * 2 - LABEL_W - (nibs_per_row - 1) * NIB_GAP
        bit_w         = avail_w / bpr
        row_h         = IDX_H + BIT_H

        # Build bit → (range_idx, is_active) lookup
        bit_to_range = {}
        for ri, (lo, hi) in enumerate(self.field_ranges):
            is_active = (ri == self.active_range_idx)
            for b in range(lo, hi + 1):
                bit_to_range[b] = (ri, is_active)

        for row in range(n_rows):
            ry = PAD_Y + row * (row_h + ROW_GAP)
            msb = n - 1 - row * bpr
            lsb = msb - bpr + 1

            canvas.create_text(
                PAD_X + LABEL_W - 6, ry + IDX_H + BIT_H // 2,
                text=f"[{msb}:{lsb}]", fill=C_DIM,
                font=("Consolas", 8), anchor='e'
            )

            for col in range(bpr):
                bit_idx = msb - col
                nib_off = (col // 4) * NIB_GAP
                bx = PAD_X + LABEL_W + col * bit_w + nib_off

                if bpr <= 16 or col % 4 == 0 or bit_idx == 0 or bit_idx == n - 1:
                    canvas.create_text(
                        bx + bit_w / 2, ry + IDX_H / 2,
                        text=str(bit_idx), fill=C_DIM,
                        font=("Consolas", 7)
                    )

                bv      = (self._value >> bit_idx) & 1
                ri_info = bit_to_range.get(bit_idx)

                if ri_info is not None:
                    ri, is_active = ri_info
                    rc      = self.RANGE_COLORS[ri % len(self.RANGE_COLORS)]
                    outline = rc[0]
                    fill    = rc[2] if bv else rc[1]
                    lw      = 2 if is_active else 1
                else:
                    fill    = C_BIT_1 if bv else C_BIT_0
                    outline = C_BIT_OUT
                    lw      = 1

                x1 = bx + 1
                y1 = ry + IDX_H
                x2 = bx + bit_w - 2
                y2 = ry + IDX_H + BIT_H

                canvas.create_rectangle(x1, y1, x2, y2,
                                        fill=fill, outline=outline, width=lw,
                                        tags=f"bit_{bit_idx}")
                canvas.create_text(
                    (x1 + x2) / 2, (y1 + y2) / 2,
                    text=str(bv), fill=C_TEXT,
                    font=("Consolas", 10, "bold"),
                    tags=f"bv_{bit_idx}"
                )

        total_h = PAD_Y * 2 + n_rows * (row_h + ROW_GAP)
        canvas.configure(scrollregion=(0, 0, w, max(total_h, canvas.winfo_height())))
        self._update_field_panel()

    def _update_field_panel(self):
        """Rebuild field rows whenever field_ranges changes, then refresh values."""
        if self.field_rows_frame is None:
            return

        # ── Determine if structure changed ─────────────────────────────────
        n_fields = len(self.field_ranges)
        if n_fields != len(self.field_row_vars):
            self._rebuild_field_rows()
        else:
            self._refresh_field_values()

    def _rebuild_field_rows(self):
        """Destroy and recreate all rows in the field panel."""
        if self.field_rows_frame is None:
            return
        for w in self.field_rows_frame.winfo_children():
            w.destroy()
        self.field_row_vars = []

        n_fields = len(self.field_ranges)
        if n_fields == 0:
            self.no_sel_label = tk.Label(
                self.field_rows_frame,
                text="No field selected — Ctrl+drag on bits above to mark a field",
                bg=C_SURFACE2, fg=C_DIM, font=("Consolas", 9), pady=8
            )
            self.no_sel_label.pack()
            return

        for ri, (lo, hi) in enumerate(self.field_ranges):
            rc      = self.RANGE_COLORS[ri % len(self.RANGE_COLORS)]
            color   = rc[0]
            width   = hi - lo + 1
            fmask   = ((1 << width) - 1) << lo
            fval    = (self._value & fmask) >> lo
            max_val = (1 << width) - 1

            hex_var = tk.StringVar(value=format(fval, 'X'))
            dec_var = tk.StringVar(value=str(fval))
            self.field_row_vars.append((hex_var, dec_var))

            row = tk.Frame(self.field_rows_frame, bg=C_SURFACE2, pady=3)
            row.pack(fill=tk.X, padx=6)

            # Color dot
            tk.Label(row, text="●", bg=C_SURFACE2, fg=color,
                     font=("Consolas", 11)).pack(side=tk.LEFT, padx=(2, 4))

            # Bit range label
            lbl_text = f"bits[{hi}:{lo}]  ({width}b)"
            tk.Label(row, text=lbl_text, bg=C_SURFACE2, fg=color,
                     font=("Consolas", 9, "bold"), width=18, anchor='w'
                     ).pack(side=tk.LEFT)

            # ── HEX entry + Apply ──────────────────────────────────────────
            def _make_hex_vcmd(max_v):
                def _validate_hex(s):
                    if not s:
                        return True
                    try:
                        return all(c in '0123456789ABCDEFabcdef' for c in s) \
                               and int(s, 16) <= max_v
                    except ValueError:
                        return False
                return (self.root.register(_validate_hex), '%P')

            def _make_dec_vcmd(max_v):
                def _validate_dec(s):
                    if not s:
                        return True
                    try:
                        return s.isdigit() and int(s) <= max_v
                    except ValueError:
                        return False
                return (self.root.register(_validate_dec), '%P')

            hex_vcmd = _make_hex_vcmd(max_val)
            dec_vcmd = _make_dec_vcmd(max_val)

            tk.Label(row, text="HEX", bg=C_SURFACE2, fg=C_DIM,
                     font=("Consolas", 8)).pack(side=tk.LEFT, padx=(4, 2))
            hex_ent = tk.Entry(row, textvariable=hex_var, bg=C_BG, fg=color,
                               insertbackground=color, relief=tk.FLAT,
                               font=("Consolas", 10), width=12,
                               highlightthickness=1, highlightbackground=C_BORDER,
                               highlightcolor=color,
                               validate='key', validatecommand=hex_vcmd)
            hex_ent.pack(side=tk.LEFT, ipady=2)
            tk.Button(row, text="↵", bg=C_BTN, fg=color, relief=tk.FLAT,
                      font=("Consolas", 9, "bold"), cursor="hand2", padx=3,
                      command=lambda i=ri, v=hex_var: self._apply_field_row(i, v, 16)
                      ).pack(side=tk.LEFT, padx=(1, 8))

            # ── DEC entry + Apply ──────────────────────────────────────────
            tk.Label(row, text="DEC", bg=C_SURFACE2, fg=C_DIM,
                     font=("Consolas", 8)).pack(side=tk.LEFT, padx=(0, 2))
            dec_ent = tk.Entry(row, textvariable=dec_var, bg=C_BG, fg=color,
                               insertbackground=color, relief=tk.FLAT,
                               font=("Consolas", 10), width=12,
                               highlightthickness=1, highlightbackground=C_BORDER,
                               highlightcolor=color,
                               validate='key', validatecommand=dec_vcmd)
            dec_ent.pack(side=tk.LEFT, ipady=2)
            tk.Button(row, text="↵", bg=C_BTN, fg=color, relief=tk.FLAT,
                      font=("Consolas", 9, "bold"), cursor="hand2", padx=3,
                      command=lambda i=ri, v=dec_var: self._apply_field_row(i, v, 10)
                      ).pack(side=tk.LEFT, padx=(1, 4))

            # ── Enter applies value; Escape removes focus ──────────────────
            hex_ent.bind('<Return>',
                lambda _, i=ri, v=hex_var: (self._apply_field_row(i, v, 16), 'break')[-1])
            dec_ent.bind('<Return>',
                lambda _, i=ri, v=dec_var: (self._apply_field_row(i, v, 10), 'break')[-1])

            hex_ent.bind('<Escape>', lambda e: (self.root.focus_set(), 'break')[-1])
            dec_ent.bind('<Escape>', lambda e: (self.root.focus_set(), 'break')[-1])

            # Separator
            tk.Frame(row.master, bg=C_BORDER, height=1).pack(fill=tk.X, padx=6)

    def _refresh_field_values(self):
        """Update only the values in existing field rows (no structural rebuild)."""
        for ri, (lo, hi) in enumerate(self.field_ranges):
            if ri >= len(self.field_row_vars):
                break
            width  = hi - lo + 1
            fmask  = ((1 << width) - 1) << lo
            fval   = (self._value & fmask) >> lo
            hex_v, dec_v = self.field_row_vars[ri]
            hex_v.set(format(fval, 'X'))
            dec_v.set(str(fval))

    def _apply_field_row(self, ri, var, radix):
        """Write a field-row entry value back into the main register."""
        if ri >= len(self.field_ranges):
            return
        try:
            fv = int(var.get().strip(), radix)
        except ValueError:
            return
        lo, hi = self.field_ranges[ri]
        width   = hi - lo + 1
        fmask   = ((1 << width) - 1) << lo
        placed  = (fv & ((1 << width) - 1)) << lo
        self.active_range_idx = ri
        self.set_value((self._value & ~fmask) | placed)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS – ENTRY FIELDS
    # ═══════════════════════════════════════════════════════════════════════════

    def _apply_active_entry_highlight(self):
        """Always show which base entry is active regardless of OS focus."""
        active = self.input_base_var.get()
        for key, entry in self.entry_widgets.items():
            if key not in ('hex', 'dec', 'oct', 'bin'):
                continue
            is_active = (key == active)
            color = self.entry_colors.get(key, C_BORDER)
            entry.configure(
                highlightbackground=color if is_active else C_BORDER,
                highlightthickness=2 if is_active else 1,
            )

    def _validate(self, new_text, allowed, key):
        if not new_text:
            return True
        if key in ('dec', 'float', 'double') and new_text == '-':
            return True
        return all(c in allowed for c in new_text)

    def _on_entry_focus(self, key):
        if key in ('hex', 'dec', 'oct', 'bin'):
            self.input_base_var.set(key)
            self._update_button_states()
            self._apply_active_entry_highlight()

    def _on_entry_change(self, base):
        if self._updating:
            return
        s = self.entry_vars[base].get().strip()
        if not s or s in ('-', '.', '+'):
            return

        try:
            if base == 'hex':
                v = int(s, 16)
            elif base == 'dec':
                v = int(s, 10)
                if v < 0:
                    v &= self.mask
            elif base == 'oct':
                v = int(s, 8)
            elif base == 'bin':
                v = int(s, 2)
            elif base == 'float':
                fv = float(s)
                v = struct.unpack('I', struct.pack('f', fv))[0]
            elif base == 'double':
                dv = float(s)
                v = struct.unpack('Q', struct.pack('d', dv))[0]
            else:
                return
        except (ValueError, struct.error, OverflowError):
            return

        self._value = self._clip(v)

        self._updating = True
        try:
            val = self._value
            sv  = self._to_signed(val)

            if base != 'hex':    self.entry_vars['hex'].set(format(val, 'X') if val else '0')
            if base != 'dec':    self.entry_vars['dec'].set(str(sv))
            if base != 'oct':    self.entry_vars['oct'].set(format(val, 'o') if val else '0')
            if base != 'bin':    self.entry_vars['bin'].set(format(val, 'b') if val else '0')
            if base != 'float'   and self.float_enabled.get():
                self.entry_vars['float'].set(self._as_float(val))
            if base != 'double'  and self.double_enabled.get():
                self.entry_vars['double'].set(self._as_double(val))

            self._redraw_bits()
        finally:
            self._updating = False

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS – CALCULATOR BUTTONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_button_states(self):
        base = self.input_base_var.get()
        ok = {
            'hex': set("0123456789ABCDEF"),
            'dec': set("0123456789"),
            'oct': set("01234567"),
            'bin': set("01"),
        }.get(base, set())
        for ch, btn in self.digit_buttons.items():
            if ch in ok:
                btn.configure(state=tk.NORMAL,   fg=C_TEXT, bg=C_BTN)
            else:
                btn.configure(state=tk.DISABLED, fg=C_DIM,  bg=C_BG)
        self._apply_active_entry_highlight()

    def _on_calc(self, token):
        base = self.input_base_var.get()
        ok = {
            'hex': "0123456789ABCDEF",
            'dec': "0123456789",
            'oct': "01234567",
            'bin': "01",
        }.get(base, "0123456789ABCDEF")

        # ── Single hex/digit character ─────────────────────────────────────
        if len(token) == 1 and token in ok:
            self._append_digit(token, base)

        # ── Double-zero shortcut ───────────────────────────────────────────
        elif token == '00':
            if '0' in ok:
                self._append_digit('0', base)
                self._append_digit('0', base)

        # ── Fill shortcuts ─────────────────────────────────────────────────
        elif token == 'FF':
            self.new_entry = True
            self.set_value(self.mask)
            self.new_entry = True

        # ── Clear / delete ─────────────────────────────────────────────────
        elif token == 'CLR':
            self._value      = 0
            self.operand1    = None
            self.pending_op  = None
            self.new_entry   = True
            self.expr_var.set("")
            self.update_displays()

        elif token == 'DEL':
            s = self.entry_vars[base].get()
            new_s = s[:-1] if len(s) > 1 else '0'
            try:
                nv = int(new_s, {'hex': 16, 'dec': 10, 'oct': 8, 'bin': 2}[base])
                self.set_value(nv)
            except ValueError:
                self.set_value(0)

        # ── Unary / immediate ops ──────────────────────────────────────────
        elif token == 'NOT':
            self.set_value(~self._value & self.mask)
            self.new_entry = True

        elif token == 'NEG':
            self.set_value((-self._value) & self.mask)
            self.new_entry = True

        elif token == 'ABS':
            sv = self._to_signed(self._value)
            self.set_value(abs(sv))
            self.new_entry = True

        elif token == '<<1':
            self.set_value((self._value << 1) & self.mask)
            self.new_entry = True

        elif token == '>>1':
            self.set_value(self._value >> 1)
            self.new_entry = True

        # ── Binary operators ───────────────────────────────────────────────
        elif token in ('+', '-', '*', '/', '%',
                       'AND', 'OR', 'XOR',
                       '<<', '>>', '>>>', 'ROL', 'ROR'):
            self.operand1   = self._value
            self.pending_op = token
            self.expr_var.set(f"{self._fmt(self._value)}  {token}")
            self.new_entry  = True

        # ── Equals ────────────────────────────────────────────────────────
        elif token == '=':
            if self.operand1 is not None and self.pending_op is not None:
                result = self._exec_op(self.operand1, self._value, self.pending_op)
                self.expr_var.set(
                    f"{self._fmt(self.operand1)}  {self.pending_op}  "
                    f"{self._fmt(self._value)}  ="
                )
                self.operand1   = None
                self.pending_op = None
                self.new_entry  = True
                self.set_value(result)

    def _append_digit(self, ch, base):
        radix = {'hex': 16, 'dec': 10, 'oct': 8, 'bin': 2}[base]
        if self.new_entry:
            s = ch
            self.new_entry = False
        else:
            s = (self.entry_vars[base].get().lstrip('0') or '0') + ch
        try:
            self.set_value(int(s, radix))
        except ValueError:
            pass

    def _exec_op(self, a, b, op):
        m   = self.mask
        bs  = self.bit_size
        sh  = int(b) % bs if b else 0

        if op == '+':    return (a + b) & m
        if op == '-':    return (a - b) & m
        if op == '*':    return (a * b) & m
        if op == '/':
            if b == 0: return 0
            if self.signed_var.get():
                sa = a if a < (1 << (bs-1)) else a - (1 << bs)
                sb = b if b < (1 << (bs-1)) else b - (1 << bs)
                return int(sa / sb) & m
            return (a // b) & m
        if op == '%':
            if b == 0: return 0
            return (a % b) & m
        if op == 'AND':  return a & b
        if op == 'OR':   return a | b
        if op == 'XOR':  return a ^ b
        if op == '<<':   return (a << sh) & m           # LSL
        if op == '>>':   return (a >> sh) & m           # LSR
        if op == '>>>':                                  # ASR
            if self.signed_var.get() and a >= (1 << (bs - 1)):
                return (a - (1 << bs)) >> sh & m
            return (a >> sh) & m
        if op == 'ROL':
            s2 = sh % bs
            return ((a << s2) | (a >> (bs - s2))) & m
        if op == 'ROR':
            s2 = sh % bs
            return ((a >> s2) | (a << (bs - s2))) & m
        return a

    def _fmt(self, v):
        base = self.input_base_var.get()
        n  = self.bit_size
        nb = (n + 3) // 4
        if base == 'hex': return f"0x{format(v, f'0{nb}X')}"
        if base == 'dec': return str(self._to_signed(v))
        if base == 'oct': return f"0o{format(v, 'o')}"
        if base == 'bin': return f"0b{format(v, f'0{n}b')}"
        return str(v)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS – BIT CANVAS
    # ═══════════════════════════════════════════════════════════════════════════

    def _bit_at(self, x, y):
        """Return the bit index under canvas coordinate (x, y), or None."""
        canvas = self.bit_canvas
        w = canvas.winfo_width()
        n = self.bit_size

        if n <= 8:      bpr = 8
        elif n <= 16:   bpr = 16
        else:           bpr = 32

        PAD_X   = 10
        PAD_Y   = 10
        LABEL_W = 52
        NIB_GAP = 5
        IDX_H   = 16
        BIT_H   = 34
        ROW_GAP = 14

        nibs    = bpr // 4
        avail   = w - PAD_X * 2 - LABEL_W - (nibs - 1) * NIB_GAP
        bit_w   = avail / bpr
        row_h   = IDX_H + BIT_H
        cy      = canvas.canvasy(y)
        n_rows  = n // bpr

        for row in range(n_rows):
            ry  = PAD_Y + row * (row_h + ROW_GAP)
            y1  = ry + IDX_H
            y2  = y1 + BIT_H
            if not (y1 <= cy <= y2):
                continue
            msb = n - 1 - row * bpr
            for col in range(bpr):
                nib_off = (col // 4) * NIB_GAP
                bx      = PAD_X + LABEL_W + col * bit_w + nib_off
                if bx <= x <= bx + bit_w:
                    bit_idx = msb - col
                    if 0 <= bit_idx < n:
                        return bit_idx
        return None

    def _on_bit_press(self, e):
        bit = self._bit_at(e.x, e.y)
        if bit is None:
            return
        self._drag_ctrl         = bool(e.state & 0x0004)
        self.drag_start_bit     = bit
        self._drag_moved        = False
        self._pending_new_range = False

        if self._drag_ctrl:
            # Ctrl held: start a brand-new field range
            self.field_ranges.append((bit, bit))
            self.active_range_idx = len(self.field_ranges) - 1
            self._rebuild_field_rows()
            self._redraw_bits()
        else:
            # Plain click: activate an existing range if the bit is inside one,
            # but do NOT modify field_ranges at all.
            for ri, (lo, hi) in enumerate(self.field_ranges):
                if lo <= bit <= hi:
                    self.active_range_idx = ri
                    self._redraw_bits()
                    return
            # Bit is outside all ranges → mark for potential toggle on release
            self._pending_new_range = True

    def _on_bit_drag(self, e):
        if self.drag_start_bit is None:
            return
        bit = self._bit_at(e.x, e.y)
        if bit is None:
            return
        if bit != self.drag_start_bit:
            self._drag_moved = True

        if self._drag_ctrl and self.field_ranges and self.active_range_idx >= 0:
            # Resize the active (Ctrl-created) range as the mouse moves
            lo = min(self.drag_start_bit, bit)
            hi = max(self.drag_start_bit, bit)
            self.field_ranges[self.active_range_idx] = (lo, hi)
            self._rebuild_field_rows()
            self._redraw_bits()
        # Plain drag: do nothing to ranges

    def _on_bit_release(self, e):
        if self.drag_start_bit is None:
            return
        bit = self._bit_at(e.x, e.y)

        if self._pending_new_range and not self._drag_moved and bit is not None:
            # Pure plain click on a bit outside any range → toggle the bit value
            self._value ^= (1 << bit)
            self._value &= self.mask
            self.update_displays()

        self.drag_start_bit     = None
        self._drag_moved        = False
        self._drag_ctrl         = False
        self._pending_new_range = False

    def _clear_field_selection(self):
        self.field_ranges     = []
        self.active_range_idx = -1
        self.field_row_vars   = []
        self._rebuild_field_rows()
        self._redraw_bits()




    # ═══════════════════════════════════════════════════════════════════════════
    # GLOBAL KEYBOARD BINDINGS
    # ═══════════════════════════════════════════════════════════════════════════

    def _bind_keys(self):
        """Attach a single root-level KeyPress listener for all calc shortcuts."""
        self.root.bind('<KeyPress>', self._on_root_key, add=True)

    def _on_root_key(self, event):
        keysym  = event.keysym
        char    = event.char
        focused = self.root.focus_get()

        # Classify focus location
        in_main_entry  = focused in self.entry_widgets.values()
        in_field_entry = (focused is not None and
                          isinstance(focused, tk.Entry) and
                          not in_main_entry)

        # ── Field-panel entry is focused ───────────────────────────────────
        # Let the entry handle its own character input.
        # Only intercept Escape (defocus) and Enter (apply, handled by widget binding).
        if in_field_entry:
            if keysym in ('Escape',):
                self.root.focus_set()
                return 'break'
            # Enter is handled by the per-entry widget binding; swallow here
            # so it never reaches the '=' handler below.
            if keysym in ('Return', 'KP_Enter'):
                return 'break'
            # All other keys (digits, backspace, etc.) → let the entry handle them
            return

        # ── From here on: focus is on a main entry, a button, or nowhere ──
        # ALL calc keys are routed through _on_calc so that new_entry logic,
        # operand stashing, and display updates all go through one code path.
        # We always return 'break' to prevent double-processing by entry widgets.

        base = self.input_base_var.get()
        valid_digits = {
            'hex': set('0123456789ABCDEFabcdef'),
            'dec': set('0123456789'),
            'oct': set('01234567'),
            'bin': set('01'),
        }.get(base, set())

        if char and char.upper() in valid_digits:
            self._on_calc(char.upper())
            return 'break'

        if keysym in ('Return', 'KP_Enter'):
            self._on_calc('=')
            return 'break'

        if keysym == 'Escape':
            self._on_calc('CLR')
            return 'break'

        if keysym == 'plus':
            self._on_calc('+');   return 'break'

        if keysym == 'minus':
            self._on_calc('-');   return 'break'

        if keysym == 'asterisk':
            self._on_calc('*');   return 'break'

        if keysym == 'slash':
            self._on_calc('/');   return 'break'

        if keysym == 'percent':
            self._on_calc('%');   return 'break'

        # '<' → logical shift left
        if keysym == 'less':
            self._on_calc('<<');  return 'break'

        # '>' once → logical shift right (LSR)
        # '>' twice quickly → arithmetic shift right (ASR)
        if keysym == 'greater':
            if self._pending_gt_id is not None:
                self.root.after_cancel(self._pending_gt_id)
                self._pending_gt_id = None
                self._on_calc('>>>')      # ASR on double-tap
            else:
                self._pending_gt_id = self.root.after(350, self._fire_lsr)
            return 'break'

        if keysym == 'BackSpace':
            self._on_calc('DEL');  return 'break'

    def _fire_lsr(self):
        """Delayed dispatch for a lone '>' keypress → logical shift right."""
        self._pending_gt_id = None
        self._on_calc('>>')   # LSR

    # ═══════════════════════════════════════════════════════════════════════════
    # SETTINGS CHANGES
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_bit_size_change(self):
        self.bit_size         = int(self.bit_size_var.get())
        self._value           = self._clip(self._value)
        self.field_ranges     = []
        self.active_range_idx = -1
        self.field_row_vars   = []
        self.update_displays()

    def _on_float_toggle(self):
        if self.float_enabled.get():
            self.float_row.pack(fill=tk.X)
        else:
            self.float_row.pack_forget()
        self.update_displays()

    def _on_double_toggle(self):
        if self.double_enabled.get():
            self.double_row.pack(fill=tk.X)
        else:
            self.double_row.pack_forget()
        self.update_displays()

    # ═══════════════════════════════════════════════════════════════════════════
    # RUN
    # ═══════════════════════════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    EmbeddedCalc().run()
