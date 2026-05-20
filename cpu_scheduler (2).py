"""
Real-Time Interactive CPU Scheduling Simulator
Bahria University - CSL-320 Operating Systems
Complex Computing Problem (CCP) - BSCS 5A
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from collections import deque

# ─── COLOURS ────────────────────────────────────────────────
BG      = '#0F1117'
PANEL   = '#1A1D2E'
CARD    = '#242840'
PURPLE  = '#6C63FF'
CYAN    = '#00D4FF'
RED     = '#FF6B6B'
TEAL    = '#4ECDC4'
YELLOW  = '#FFE66D'
GREEN   = '#00FF88'
IDLE_C  = '#3A3F5C'
TEXT    = '#E8E9F3'
SUBTEXT = '#8B8FA8'
BORDER  = '#2E3250'

PROC_COLORS = ['#6C63FF','#00D4FF','#FF6B6B','#4ECDC4',
               '#FFE66D','#A8E6CF','#FF9F43','#EE5A24','#9980FA','#1289A7']

# ─── DATA MODEL ─────────────────────────────────────────────
class Process:
    def __init__(self, pid, arrival, burst, priority=1, color=None):
        self.pid       = pid
        self.arrival   = arrival
        self.burst     = burst
        self.priority  = priority
        self.color     = color or PROC_COLORS[pid % len(PROC_COLORS)]
        self.remaining = burst
        self.start_time    = -1
        self.finish_time   = -1
        self.response_time = -1
        self.state         = 'ready'

    def reset(self):
        self.remaining = self.burst
        self.start_time = self.finish_time = self.response_time = -1
        self.state = 'ready'

    @property
    def turnaround(self):
        return max(0, self.finish_time - self.arrival) if self.finish_time >= 0 else 0

    @property
    def waiting(self):
        return max(0, self.turnaround - self.burst)

    def clone(self):
        p = Process(self.pid, self.arrival, self.burst, self.priority, self.color)
        p.remaining = self.remaining
        return p

# ─── ALGORITHMS ─────────────────────────────────────────────
def run_fcfs(processes):
    procs = sorted([p.clone() for p in processes], key=lambda x: x.arrival)
    gantt, t = [], 0
    for p in procs:
        if t < p.arrival:
            gantt.append(('IDLE', t, p.arrival))
            t = p.arrival
        p.start_time = t
        p.response_time = t - p.arrival
        gantt.append((p.pid, t, t + p.burst))
        t += p.burst
        p.finish_time = t
        p.remaining = 0
        p.state = 'done'
    return gantt, procs

def run_sjf(processes, preemptive=False):
    procs = [p.clone() for p in processes]
    gantt, t, done = [], 0, 0
    n = len(procs)
    while done < n:
        avail = [p for p in procs if p.arrival <= t and p.state != 'done']
        if not avail:
            nxt = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, nxt)); t = nxt; continue
        chosen = min(avail, key=lambda x: x.remaining if preemptive else x.burst)
        if chosen.start_time < 0:
            chosen.start_time = t
            chosen.response_time = t - chosen.arrival
        if preemptive:
            if gantt and gantt[-1][0] == chosen.pid:
                gantt[-1] = (gantt[-1][0], gantt[-1][1], t + 1)
            else:
                gantt.append((chosen.pid, t, t + 1))
            chosen.remaining -= 1; t += 1
            if chosen.remaining == 0:
                chosen.finish_time = t; chosen.state = 'done'; done += 1
        else:
            gantt.append((chosen.pid, t, t + chosen.burst))
            t += chosen.burst
            chosen.remaining = 0; chosen.finish_time = t
            chosen.state = 'done'; done += 1
    return gantt, procs

def run_priority(processes, preemptive=False):
    procs = [p.clone() for p in processes]
    gantt, t, done = [], 0, 0
    n = len(procs)
    while done < n:
        avail = [p for p in procs if p.arrival <= t and p.state != 'done']
        if not avail:
            nxt = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, nxt)); t = nxt; continue
        chosen = min(avail, key=lambda x: x.priority)
        if chosen.start_time < 0:
            chosen.start_time = t
            chosen.response_time = t - chosen.arrival
        if preemptive:
            if gantt and gantt[-1][0] == chosen.pid:
                gantt[-1] = (gantt[-1][0], gantt[-1][1], t + 1)
            else:
                gantt.append((chosen.pid, t, t + 1))
            chosen.remaining -= 1; t += 1
            if chosen.remaining == 0:
                chosen.finish_time = t; chosen.state = 'done'; done += 1
        else:
            gantt.append((chosen.pid, t, t + chosen.burst))
            t += chosen.burst
            chosen.remaining = 0; chosen.finish_time = t
            chosen.state = 'done'; done += 1
    return gantt, procs

def run_rr(processes, quantum=2):
    procs = [p.clone() for p in processes]
    queue, added = deque(), set()
    gantt, t, done = [], 0, 0
    n = len(procs)
    for p in sorted(procs, key=lambda x: x.arrival):
        if p.arrival <= 0:
            queue.append(p); added.add(p.pid)
    while done < n:
        if not queue:
            remaining = [p for p in procs if p.pid not in added and p.state != 'done']
            if not remaining: break
            nxt = min(p.arrival for p in remaining)
            gantt.append(('IDLE', t, nxt)); t = nxt
            for p in sorted(procs, key=lambda x: x.arrival):
                if p.arrival <= t and p.pid not in added and p.state != 'done':
                    queue.append(p); added.add(p.pid)
            continue
        p = queue.popleft()
        if p.state == 'done': continue
        if p.start_time < 0:
            p.start_time = t; p.response_time = t - p.arrival
        run_t = min(quantum, p.remaining)
        gantt.append((p.pid, t, t + run_t))
        t += run_t; p.remaining -= run_t
        for proc in sorted(procs, key=lambda x: x.arrival):
            if proc.arrival <= t and proc.pid not in added and proc.state != 'done':
                queue.append(proc); added.add(proc.pid)
        if p.remaining == 0:
            p.finish_time = t; p.state = 'done'; done += 1
        else:
            queue.append(p)
    return gantt, procs

def run_mlfq(processes, quantums=None):
    if quantums is None: quantums = [2, 4, 8]
    procs = [p.clone() for p in processes]
    queues = [deque() for _ in quantums]
    added = set()
    gantt, t, done = [], 0, 0
    n = len(procs)
    for p in sorted(procs, key=lambda x: x.arrival):
        if p.arrival <= 0:
            queues[0].append(p); added.add(p.pid)
    while done < n:
        current = level = None
        for i, q in enumerate(queues):
            if q: current = q.popleft(); level = i; break
        if current is None:
            remaining = [p for p in procs if p.pid not in added and p.state != 'done']
            if not remaining: break
            nxt = min(p.arrival for p in remaining)
            gantt.append(('IDLE', t, nxt)); t = nxt
            for p in sorted(procs, key=lambda x: x.arrival):
                if p.arrival <= t and p.pid not in added and p.state != 'done':
                    queues[0].append(p); added.add(p.pid)
            continue
        if current.state == 'done': continue
        if current.start_time < 0:
            current.start_time = t
            current.response_time = t - current.arrival
        run_t = min(quantums[level], current.remaining)
        gantt.append((current.pid, t, t + run_t))
        t += run_t; current.remaining -= run_t
        for p in sorted(procs, key=lambda x: x.arrival):
            if p.arrival <= t and p.pid not in added and p.state != 'done':
                queues[0].append(p); added.add(p.pid)
        if current.remaining == 0:
            current.finish_time = t; current.state = 'done'; done += 1
        else:
            queues[min(level + 1, len(quantums) - 1)].append(current)
    return gantt, procs

def compute_metrics(procs, gantt):
    if not gantt or not procs: return {}
    total = max(1, gantt[-1][2])
    idle  = sum(e - s for lbl, s, e in gantt if lbl == 'IDLE')
    n = len(procs)
    return {
        'awt': round(sum(p.waiting for p in procs) / n, 2),
        'att': round(sum(p.turnaround for p in procs) / n, 2),
        'art': round(sum(max(0,p.response_time) for p in procs) / n, 2),
        'cpu': round((total - idle) / total * 100, 1),
        'tpt': round(n / total, 4),
    }

def get_feedback(procs, algo):
    bursts   = [p.burst for p in procs]
    variance = max(bursts) - min(bursts) if bursts else 0
    n        = len(procs)
    prios    = set(p.priority for p in procs)
    if variance < 3 and n <= 6:    rec, why = "FCFS",                  "burst times are similar"
    elif variance > 6:             rec, why = "SJF (Non-Preemptive)",  "high burst variance favours SJF"
    elif len(prios) > 2:           rec, why = "Priority (Preemptive)", "multiple priority levels detected"
    elif n > 6:                    rec, why = "Round Robin",           "many processes need fair sharing"
    else:                          rec, why = "MLFQ",                  "mixed workload suits MLFQ"
    starved = [f"P{p.pid}(wait={p.waiting})" for p in procs if p.waiting > 20]
    msg = (f"✓ {algo} is already optimal." if rec == algo
           else f"💡 Consider {rec} — {why}.")
    if starved:
        msg += f"\n⚠ Starvation: {', '.join(starved)}"
    return msg

# ─── MAIN APP ───────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Scheduling Simulator — Bahria University CSL-320")
        self.root.configure(bg=BG)
        self.root.geometry("1380x830")
        self.root.minsize(1000, 650)

        self.processes   = []
        self.pid_counter = 0
        self.running     = False
        self.paused      = False

        self.v_algo    = tk.StringVar(value="FCFS")
        self.v_quantum = tk.IntVar(value=2)
        self.v_speed   = tk.DoubleVar(value=1.0)
        self.v_arrival = tk.IntVar(value=0)
        self.v_burst   = tk.IntVar(value=5)
        self.v_prio    = tk.IntVar(value=1)
        self.v_mq1     = tk.IntVar(value=2)
        self.v_mq2     = tk.IntVar(value=4)
        self.v_mq3     = tk.IntVar(value=8)

        self._styles()
        self._build()
        self._samples()

    # ── STYLES ───────────────────────────────────────────────
    def _styles(self):
        s = ttk.Style()
        s.theme_use('clam')
        s.configure('TCombobox',
                    fieldbackground=PANEL, background=PANEL,
                    foreground=TEXT, selectbackground=PURPLE,
                    selectforeground='white', arrowcolor=PURPLE)
        s.configure('Treeview',
                    background=PANEL, foreground=TEXT,
                    rowheight=24, fieldbackground=PANEL,
                    font=('Consolas', 9))
        s.configure('Treeview.Heading',
                    background=PURPLE, foreground='white',
                    font=('Segoe UI', 9, 'bold'), relief='flat')
        s.map('Treeview',
              background=[('selected', PURPLE)],
              foreground=[('selected', 'white')])

    # ── WIDGET HELPERS ───────────────────────────────────────
    def _card(self, parent, title):
        """Returns the inner content frame of a titled card."""
        wrap = tk.Frame(parent, bg=PURPLE, pady=1, padx=1)
        hdr  = tk.Frame(wrap, bg=PURPLE)
        hdr.pack(fill='x')
        tk.Label(hdr, text=title, bg=PURPLE, fg='white',
                 font=('Segoe UI', 9, 'bold'), padx=8, pady=3).pack(side='left')
        inner = tk.Frame(wrap, bg=CARD)
        inner.pack(fill='both', expand=True)
        return wrap, inner   # caller packs `wrap`, puts widgets in `inner`

    def _btn(self, parent, text, cmd, bg):
        fg = '#111' if bg == YELLOW else 'white'
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, relief='flat', bd=0,
                         font=('Segoe UI', 9, 'bold'),
                         padx=12, pady=6, cursor='hand2',
                         activebackground=bg, activeforeground=fg)

    def _spinbox(self, parent, var, lo=0, hi=999, w=6):
        return tk.Spinbox(parent, from_=lo, to=hi, textvariable=var,
                          width=w, bg=PANEL, fg=TEXT, relief='flat',
                          buttonbackground=PURPLE, insertbackground=TEXT,
                          font=('Segoe UI', 10))

    def _label(self, parent, text, fg=SUBTEXT, font_=('Segoe UI', 9)):
        return tk.Label(parent, text=text, bg=CARD, fg=fg, font=font_)

    # ── BUILD ────────────────────────────────────────────────
    def _build(self):
        # ── title bar ──
        bar = tk.Frame(self.root, bg=PURPLE, height=46)
        bar.pack(side='top', fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text="⚡  CPU Scheduling Simulator",
                 bg=PURPLE, fg='white',
                 font=('Segoe UI', 15, 'bold')).pack(side='left', padx=16, pady=4)
        tk.Label(bar, text="Bahria University · CSL-320",
                 bg=PURPLE, fg='#D0CCFF',
                 font=('Segoe UI', 9)).pack(side='right', padx=16)

        # ── two-column body ──
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill='both', expand=True, padx=10, pady=10)
        body.columnconfigure(0, weight=0, minsize=340)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left  = tk.Frame(body, bg=BG)
        right = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky='nsew', padx=(0,8))
        right.grid(row=0, column=1, sticky='nsew')

        self._build_left(left)
        self._build_right(right)

    # ── LEFT ─────────────────────────────────────────────────
    def _build_left(self, col):
        # ── Algorithm card ──
        wrap, inner = self._card(col, "🧠  Algorithm & Parameters")
        wrap.pack(fill='x', pady=(0,8))

        algos = ["FCFS","SJF (Non-Preemptive)","SJF (Preemptive / SRTF)",
                 "Priority (Non-Preemptive)","Priority (Preemptive)",
                 "Round Robin","MLFQ"]
        cb = ttk.Combobox(inner, values=algos, textvariable=self.v_algo,
                          state='readonly', font=('Segoe UI', 10))
        cb.pack(fill='x', padx=10, pady=(8,6))
        cb.bind('<<ComboboxSelected>>', self._on_algo)

        # RR quantum (hidden by default)
        self.rr_row = tk.Frame(inner, bg=CARD)
        tk.Label(self.rr_row, text="Time Quantum:", bg=CARD, fg=SUBTEXT,
                 font=('Segoe UI', 9)).pack(side='left', padx=(10,6))
        self._spinbox(self.rr_row, self.v_quantum, 1, 20, 5).pack(side='left')

        # MLFQ quantums (hidden by default)
        self.mq_row = tk.Frame(inner, bg=CARD)
        for lbl, var in [("Q1:", self.v_mq1),("Q2:", self.v_mq2),("Q3:", self.v_mq3)]:
            tk.Label(self.mq_row, text=lbl, bg=CARD, fg=SUBTEXT,
                     font=('Segoe UI', 9)).pack(side='left', padx=(8,2))
            self._spinbox(self.mq_row, var, 1, 20, 4).pack(side='left', padx=(0,4))

        # Speed
        sp_row = tk.Frame(inner, bg=CARD)
        sp_row.pack(fill='x', padx=10, pady=(4,10))
        tk.Label(sp_row, text="Speed:", bg=CARD, fg=SUBTEXT,
                 font=('Segoe UI', 9)).pack(side='left', padx=(0,6))
        tk.Scale(sp_row, from_=0.5, to=10.0, resolution=0.5,
                 variable=self.v_speed, orient='horizontal',
                 bg=CARD, fg=TEXT, troughcolor=PANEL,
                 highlightthickness=0, length=200,
                 showvalue=True).pack(side='left')

        # ── Add process card ──
        wrap2, inner2 = self._card(col, "➕  Add Process")
        wrap2.pack(fill='x', pady=(0,8))

        for lbl_text, var in [("Arrival Time", self.v_arrival),
                               ("Burst Time",   self.v_burst),
                               ("Priority (1=high)", self.v_prio)]:
            row = tk.Frame(inner2, bg=CARD)
            row.pack(fill='x', padx=10, pady=4)
            tk.Label(row, text=lbl_text, bg=CARD, fg=SUBTEXT,
                     font=('Segoe UI', 9), width=17, anchor='w').pack(side='left')
            self._spinbox(row, var, 0, 999, 7).pack(side='left', padx=6)

        btn_row = tk.Frame(inner2, bg=CARD)
        btn_row.pack(fill='x', padx=10, pady=(4,10))
        self._btn(btn_row, "Add Process", self._add_proc, PURPLE).pack(side='left', padx=(0,8))
        self._btn(btn_row, "Clear All",   self._clear,    RED  ).pack(side='left')

        # ── Queue card ──
        wrap3, inner3 = self._card(col, "📋  Process Queue   [Del] to remove")
        wrap3.pack(fill='both', expand=True, pady=(0,8))

        cols = ('PID','Arrival','Burst','Priority')
        self.tree = ttk.Treeview(inner3, columns=cols, show='headings', height=9)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=70, anchor='center', minwidth=50)
        vsb = ttk.Scrollbar(inner3, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=(8,0), pady=6)
        vsb.pack(side='right', fill='y', pady=6, padx=(0,6))
        self.tree.bind('<Delete>', lambda e: self._del_selected())

        # ── Controls card ──
        wrap4, inner4 = self._card(col, "▶  Simulation Controls")
        wrap4.pack(fill='x')

        btn_row2 = tk.Frame(inner4, bg=CARD)
        btn_row2.pack(fill='x', padx=10, pady=(8,4))
        self.btn_run   = self._btn(btn_row2, "▶  Run",   self._run,   GREEN)
        self.btn_pause = self._btn(btn_row2, "⏸ Pause",  self._pause, YELLOW)
        self.btn_reset = self._btn(btn_row2, "⏹ Reset",  self._reset, RED)
        for b in (self.btn_run, self.btn_pause, self.btn_reset):
            b.pack(side='left', padx=(0,6))

        self.lbl_fb = tk.Label(inner4, text="", bg=CARD, fg=CYAN,
                               font=('Segoe UI', 8), wraplength=310,
                               justify='left', anchor='w')
        self.lbl_fb.pack(fill='x', padx=10, pady=(2,10))

    # ── RIGHT ────────────────────────────────────────────────
    def _build_right(self, col):
        # ── Gantt ──
        wrap, inner = self._card(col, "📊  Gantt Chart  (live)")
        wrap.pack(fill='x', pady=(0,8))
        self.gantt_cv = tk.Canvas(inner, bg=PANEL, height=130, highlightthickness=0)
        self.gantt_cv.pack(fill='x', padx=8, pady=8)

        # ── Metrics ──
        wrap2, inner2 = self._card(col, "📈  Performance Metrics")
        wrap2.pack(fill='x', pady=(0,8))
        mrow = tk.Frame(inner2, bg=CARD)
        mrow.pack(fill='x', padx=10, pady=10)
        self.mlbls = {}
        for i, (title, color, key) in enumerate([
                ("Avg Waiting",    PURPLE, 'awt'),
                ("Avg Turnaround", CYAN,   'att'),
                ("Avg Response",   TEAL,   'art'),
                ("CPU Util %",     GREEN,  'cpu'),
                ("Throughput",     YELLOW, 'tpt')]):
            cell = tk.Frame(mrow, bg=PANEL, padx=10, pady=8)
            cell.grid(row=0, column=i, sticky='ew', padx=4)
            mrow.columnconfigure(i, weight=1)
            tk.Label(cell, text=title, bg=PANEL, fg=SUBTEXT,
                     font=('Segoe UI', 8)).pack()
            lbl = tk.Label(cell, text="—", bg=PANEL, fg=color,
                           font=('Segoe UI', 16, 'bold'))
            lbl.pack()
            self.mlbls[key] = lbl

        # ── Results table ──
        wrap3, inner3 = self._card(col, "📑  Per-Process Results")
        wrap3.pack(fill='x', pady=(0,8))
        rcols = ('PID','Arrival','Burst','Priority','Start','Finish','Waiting','Turnaround','Response')
        self.rtree = ttk.Treeview(inner3, columns=rcols, show='headings', height=5)
        for c in rcols:
            self.rtree.heading(c, text=c)
            self.rtree.column(c, width=80, anchor='center', minwidth=55)
        vsb2 = ttk.Scrollbar(inner3, orient='vertical', command=self.rtree.yview)
        self.rtree.configure(yscrollcommand=vsb2.set)
        self.rtree.pack(side='left', fill='x', expand=True, padx=(8,0), pady=6)
        vsb2.pack(side='right', fill='y', pady=6, padx=(0,6))

        # ── Ready queue ──
        wrap4, inner4 = self._card(col, "🔄  Ready Queue State")
        wrap4.pack(fill='both', expand=True)
        self.rq_cv = tk.Canvas(inner4, bg=PANEL, height=90, highlightthickness=0)
        self.rq_cv.pack(fill='x', padx=8, pady=8)

    # ── ALGO TOGGLE ──────────────────────────────────────────
    def _on_algo(self, _=None):
        algo = self.v_algo.get()
        self.rr_row.pack_forget()
        self.mq_row.pack_forget()
        if algo == "Round Robin":
            self.rr_row.pack(fill='x', padx=10, pady=(0,6))
        elif algo == "MLFQ":
            self.mq_row.pack(fill='x', padx=10, pady=(0,6))

    # ── PROCESS MANAGEMENT ───────────────────────────────────
    def _samples(self):
        for arr, burst, pri in [(0,8,3),(1,4,1),(2,9,2),(3,5,4),(3,3,5)]:
            self._add_raw(arr, burst, pri)

    def _add_raw(self, arrival, burst, priority):
        color = PROC_COLORS[self.pid_counter % len(PROC_COLORS)]
        p = Process(self.pid_counter, arrival, burst, priority, color)
        self.processes.append(p)
        iid = str(self.pid_counter)
        self.tree.insert('', 'end', iid=iid,
                         values=(f'P{p.pid}', p.arrival, p.burst, p.priority),
                         tags=(iid,))
        self.tree.tag_configure(iid, foreground=color)
        self.pid_counter += 1

    def _add_proc(self):
        if self.running:
            self._fb("⚠ Stop simulation first."); return
        try:
            arr, burst, prio = self.v_arrival.get(), self.v_burst.get(), self.v_prio.get()
            if burst < 1: raise ValueError("Burst ≥ 1 required")
            self._add_raw(arr, burst, prio)
            self.v_arrival.set(arr + 1)
        except Exception as e:
            messagebox.showerror("Input Error", str(e))

    def _del_selected(self):
        for iid in self.tree.selection():
            self.processes = [p for p in self.processes if p.pid != int(iid)]
            self.tree.delete(iid)

    def _clear(self):
        if self.running: return
        self.processes.clear()
        self.tree.delete(*self.tree.get_children())
        self.pid_counter = 0
        self._clear_right()

    # ── SIMULATION ───────────────────────────────────────────
    def _run(self):
        if not self.processes:
            messagebox.showwarning("Empty", "Add at least one process."); return
        if self.paused:
            self.paused = False; self._fb("▶ Resumed"); return
        if self.running: return
        self._clear_right()
        self.running = True
        self.btn_run.config(text="Running…", state='disabled')
        threading.Thread(target=self._simulate, daemon=True).start()

    def _pause(self):
        if not self.running: return
        self.paused = not self.paused
        self._fb("⏸ Paused — click Run to resume" if self.paused else "▶ Resumed")

    def _reset(self):
        self.running = self.paused = False
        for p in self.processes: p.reset()
        self._clear_right()
        self.btn_run.config(text="▶  Run", state='normal')
        self._fb("Reset — ready.")

    def _simulate(self):
        algo = self.v_algo.get()
        try:
            if   algo == "FCFS":                      g, ps = run_fcfs(self.processes)
            elif algo == "SJF (Non-Preemptive)":      g, ps = run_sjf(self.processes, False)
            elif algo == "SJF (Preemptive / SRTF)":   g, ps = run_sjf(self.processes, True)
            elif algo == "Priority (Non-Preemptive)":  g, ps = run_priority(self.processes, False)
            elif algo == "Priority (Preemptive)":      g, ps = run_priority(self.processes, True)
            elif algo == "Round Robin":                g, ps = run_rr(self.processes, self.v_quantum.get())
            elif algo == "MLFQ":                       g, ps = run_mlfq(self.processes,
                                                           [self.v_mq1.get(),self.v_mq2.get(),self.v_mq3.get()])
            else:                                      g, ps = run_fcfs(self.processes)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Simulation Error", str(e)))
            self.running = False
            self.root.after(0, lambda: self.btn_run.config(text="▶  Run", state='normal'))
            return

        delay = 1.0 / max(self.v_speed.get(), 0.1)
        partial = []
        for step in g:
            while self.paused: time.sleep(0.05)
            if not self.running: break
            partial.append(step)
            snap_g, snap_p = list(partial), list(ps)
            self.root.after(0, lambda sg=snap_g, sp=snap_p: self._draw_gantt(sg, sp))
            self.root.after(0, lambda sg=snap_g, sp=snap_p: self._draw_rq(sg, sp))
            time.sleep(delay)

        if self.running:
            m = compute_metrics(ps, g)
            self.root.after(0, lambda: self._show_metrics(m))
            self.root.after(0, lambda: self._fill_results(ps))
            fb = get_feedback(ps, algo)
            self.root.after(0, lambda f=fb: self._fb(f))
        self.running = False
        self.root.after(0, lambda: self.btn_run.config(text="▶  Run", state='normal'))

    # ── DRAWING ──────────────────────────────────────────────
    def _draw_gantt(self, gantt, procs):
        cv = self.gantt_cv
        cv.delete('all')
        W = cv.winfo_width()
        H = cv.winfo_height()
        if W < 20 or not gantt: return

        total = max(1, gantt[-1][2])
        ML, MR = 8, 8
        BY, BH = 20, 60
        AW = W - ML - MR
        pc = {p.pid: p.color for p in procs}

        for lbl, s, e in gantt:
            x1 = ML + s / total * AW
            x2 = ML + e / total * AW
            bw = max(x2 - x1, 2)
            fill = IDLE_C if lbl == 'IDLE' else pc.get(lbl, PURPLE)
            fg   = SUBTEXT if lbl == 'IDLE' else 'white'
            txt  = 'IDLE' if lbl == 'IDLE' else f'P{lbl}'
            cv.create_rectangle(x1, BY, x1+bw, BY+BH,
                                 fill=fill, outline=BG, width=1)
            if bw > 16:
                cv.create_text(x1+bw/2, BY+BH/2, text=txt,
                               fill=fg, font=('Segoe UI', 8, 'bold'))

        step = max(1, total // 12)
        for t in range(0, total+1, step):
            x = ML + t/total * AW
            cv.create_line(x, BY+BH, x, BY+BH+7, fill=SUBTEXT)
            cv.create_text(x, BY+BH+17, text=str(t),
                           fill=SUBTEXT, font=('Segoe UI', 7))
        cv.create_text(W-36, 12, text=f"t={total}",
                       fill=CYAN, font=('Segoe UI', 8, 'bold'))

    def _draw_rq(self, gantt, procs):
        cv = self.rq_cv
        cv.delete('all')
        if not gantt: return
        now     = gantt[-1][2]
        running = gantt[-1][0]
        pc      = {p.pid: p.color for p in procs}
        done    = {p.pid for p in procs if p.finish_time >= 0 and p.finish_time <= now}
        ready   = [p for p in procs if p.pid not in done and p.arrival <= now and p.pid != running]

        x = 10
        if running != 'IDLE':
            col = pc.get(running, PURPLE)
            cv.create_rectangle(x, 12, x+64, 62, fill=col, outline=GREEN, width=2)
            cv.create_text(x+32, 30, text=f'P{running}', fill='white', font=('Segoe UI', 11, 'bold'))
            cv.create_text(x+32, 50, text='RUNNING', fill=GREEN, font=('Segoe UI', 7, 'bold'))
            x += 80

        if ready:
            cv.create_text(x+28, 37, text="Queue →", fill=SUBTEXT, font=('Segoe UI', 9))
            x += 64

        for p in ready[:11]:
            col = pc.get(p.pid, PURPLE)
            cv.create_rectangle(x, 16, x+54, 60, fill=col, outline=BORDER, width=1)
            cv.create_text(x+27, 32, text=f'P{p.pid}', fill='white', font=('Segoe UI', 9, 'bold'))
            cv.create_text(x+27, 48, text=f'rem={p.remaining}', fill='white', font=('Segoe UI', 7))
            x += 60

    def _show_metrics(self, m):
        for key, lbl in self.mlbls.items():
            val = m.get(key, '—')
            lbl.config(text=f"{val}%" if key == 'cpu' else str(val))

    def _fill_results(self, procs):
        self.rtree.delete(*self.rtree.get_children())
        for p in sorted(procs, key=lambda x: x.pid):
            tag = f'r{p.pid}'
            self.rtree.insert('', 'end', tags=(tag,),
                              values=(f'P{p.pid}', p.arrival, p.burst, p.priority,
                                      p.start_time, p.finish_time,
                                      p.waiting, p.turnaround, p.response_time))
            self.rtree.tag_configure(tag, foreground=p.color)

    def _clear_right(self):
        self.gantt_cv.delete('all')
        self.rq_cv.delete('all')
        self.rtree.delete(*self.rtree.get_children())
        for lbl in self.mlbls.values(): lbl.config(text='—')
        self._fb('')

    def _fb(self, msg):
        self.lbl_fb.config(text=msg)

# ─── ENTRY POINT ────────────────────────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app  = App(root)
    root.mainloop()
