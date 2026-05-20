# %%
# %%
"""


Real-Time Interactive CPU Scheduling Simulator
Bahria University - CSL-320 Operating Systems
Complex Computing Problem (CCP) - BSCS 5A
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import threading
import time
import copy
import math
from collections import deque
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

# ─────────────────────────────────────────────────────────────
#  DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

COLORS = {
    'bg':        '#0F1117',
    'panel':     '#1A1D2E',
    'card':      '#242840',
    'accent1':   '#6C63FF',   # purple
    'accent2':   '#00D4FF',   # cyan
    'accent3':   '#FF6B6B',   # red
    'accent4':   '#4ECDC4',   # teal
    'accent5':   '#FFE66D',   # yellow
    'accent6':   '#A8E6CF',   # green
    'text':      '#E8E9F3',
    'subtext':   '#8B8FA8',
    'border':    '#2E3250',
    'running':   '#00FF88',
    'waiting':   '#FF6B6B',
    'completed': '#6C63FF',
    'idle':      '#3A3F5C',
}

PROCESS_COLORS = ['#6C63FF','#00D4FF','#FF6B6B','#4ECDC4',
                  '#FFE66D','#A8E6CF','#FF9F43','#EE5A24',
                  '#9980FA','#1289A7']

class Process:
    def __init__(self, pid, arrival, burst, priority=1, color=None):
        self.pid       = pid
        self.arrival   = arrival
        self.burst     = burst
        self.remaining = burst
        self.priority  = priority
        self.color     = color or PROCESS_COLORS[pid % len(PROCESS_COLORS)]
        self.start_time    = -1
        self.finish_time   = -1
        self.waiting_time  = 0
        self.response_time = -1
        self.state         = 'ready'   # ready / running / waiting / done

    def reset(self):
        self.remaining     = self.burst
        self.start_time    = -1
        self.finish_time   = -1
        self.waiting_time  = 0
        self.response_time = -1
        self.state         = 'ready'

    @property
    def turnaround(self):
        if self.finish_time < 0:
            return 0
        return self.finish_time - self.arrival

    @property
    def waiting(self):
        return max(0, self.turnaround - self.burst)

    def clone(self):
        p = Process(self.pid, self.arrival, self.burst, self.priority, self.color)
        p.remaining = self.remaining
        return p


# ─────────────────────────────────────────────────────────────
#  SCHEDULING ALGORITHMS  (pure computation, no UI)
# ─────────────────────────────────────────────────────────────

def run_fcfs(processes):
    procs = sorted([p.clone() for p in processes], key=lambda x: x.arrival)
    gantt, t = [], 0
    for p in procs:
        if t < p.arrival:
            gantt.append(('IDLE', t, p.arrival))
            t = p.arrival
        p.start_time    = t
        p.response_time = t - p.arrival
        t              += p.burst
        p.finish_time   = t
        p.remaining     = 0
        p.state         = 'done'
        gantt.append((p.pid, p.start_time, p.finish_time))
    return gantt, procs


def run_sjf(processes, preemptive=False):
    procs  = [p.clone() for p in processes]
    gantt  = []
    t      = 0
    done   = 0
    n      = len(procs)
    prev   = None

    while done < n:
        available = [p for p in procs if p.arrival <= t and p.state != 'done']
        if not available:
            next_arr = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, next_arr))
            t = next_arr
            continue
        if preemptive:
            chosen = min(available, key=lambda x: x.remaining)
        else:
            chosen = min(available, key=lambda x: x.burst)

        if chosen.start_time < 0:
            chosen.start_time    = t
            chosen.response_time = t - chosen.arrival

        if preemptive:
            chosen.state = 'running'
            if not gantt or gantt[-1][0] != chosen.pid:
                gantt.append((chosen.pid, t, t + 1))
            else:
                gantt[-1] = (gantt[-1][0], gantt[-1][1], t + 1)
            chosen.remaining -= 1
            t += 1
            if chosen.remaining == 0:
                chosen.finish_time = t
                chosen.state       = 'done'
                done              += 1
        else:
            chosen.state = 'running'
            gantt.append((chosen.pid, t, t + chosen.burst))
            t              += chosen.burst
            chosen.remaining = 0
            chosen.finish_time = t
            chosen.state       = 'done'
            done              += 1
    return gantt, procs


def run_priority(processes, preemptive=False):
    procs  = [p.clone() for p in processes]
    gantt  = []
    t      = 0
    done   = 0
    n      = len(procs)

    while done < n:
        available = [p for p in procs if p.arrival <= t and p.state != 'done']
        if not available:
            next_arr = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, next_arr))
            t = next_arr
            continue
        chosen = min(available, key=lambda x: x.priority)

        if chosen.start_time < 0:
            chosen.start_time    = t
            chosen.response_time = t - chosen.arrival

        if preemptive:
            chosen.state = 'running'
            if not gantt or gantt[-1][0] != chosen.pid:
                gantt.append((chosen.pid, t, t + 1))
            else:
                gantt[-1] = (gantt[-1][0], gantt[-1][1], t + 1)
            chosen.remaining -= 1
            t += 1
            if chosen.remaining == 0:
                chosen.finish_time = t
                chosen.state       = 'done'
                done              += 1
        else:
            chosen.state = 'running'
            gantt.append((chosen.pid, t, t + chosen.burst))
            t              += chosen.burst
            chosen.remaining = 0
            chosen.finish_time = t
            chosen.state       = 'done'
            done              += 1
    return gantt, procs


def run_rr(processes, quantum=2):
    procs = [p.clone() for p in processes]
    queue = deque()
    t     = 0
    gantt = []
    done  = 0
    n     = len(procs)
    added = set()

    # seed queue with arrivals at t=0
    for p in sorted(procs, key=lambda x: x.arrival):
        if p.arrival == 0:
            queue.append(p)
            added.add(p.pid)

    while done < n:
        if not queue:
            next_arr = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, next_arr))
            t = next_arr
            for p in sorted(procs, key=lambda x: x.arrival):
                if p.arrival <= t and p.pid not in added and p.state != 'done':
                    queue.append(p)
                    added.add(p.pid)
            continue

        p = queue.popleft()
        if p.state == 'done':
            continue

        if p.start_time < 0:
            p.start_time    = t
            p.response_time = t - p.arrival

        run_time = min(quantum, p.remaining)
        p.state  = 'running'
        gantt.append((p.pid, t, t + run_time))
        t              += run_time
        p.remaining    -= run_time

        # add newly arrived processes
        for proc in sorted(procs, key=lambda x: x.arrival):
            if proc.arrival <= t and proc.pid not in added and proc.state != 'done':
                queue.append(proc)
                added.add(proc.pid)

        if p.remaining == 0:
            p.finish_time = t
            p.state       = 'done'
            done         += 1
        else:
            queue.append(p)

    return gantt, procs


def run_mlfq(processes, quantums=None):
    if quantums is None:
        quantums = [2, 4, 8]
    n_queues = len(quantums)
    procs    = [p.clone() for p in processes]
    queues   = [deque() for _ in range(n_queues)]
    levels   = {p.pid: 0 for p in procs}
    t        = 0
    done     = 0
    n        = len(procs)
    added    = set()
    gantt    = []

    for p in sorted(procs, key=lambda x: x.arrival):
        if p.arrival == 0:
            queues[0].append(p)
            added.add(p.pid)

    while done < n:
        current = None
        level   = -1
        for i, q in enumerate(queues):
            if q:
                current = q.popleft()
                level   = i
                break

        if current is None:
            next_arr = min(p.arrival for p in procs if p.state != 'done')
            gantt.append(('IDLE', t, next_arr))
            t = next_arr
            for p in sorted(procs, key=lambda x: x.arrival):
                if p.arrival <= t and p.pid not in added and p.state != 'done':
                    queues[0].append(p)
                    added.add(p.pid)
            continue

        if current.state == 'done':
            continue

        if current.start_time < 0:
            current.start_time    = t
            current.response_time = t - current.arrival

        q_time   = quantums[level]
        run_time = min(q_time, current.remaining)
        current.state = 'running'
        gantt.append((current.pid, t, t + run_time))
        t               += run_time
        current.remaining -= run_time

        for p in sorted(procs, key=lambda x: x.arrival):
            if p.arrival <= t and p.pid not in added and p.state != 'done':
                queues[0].append(p)
                added.add(p.pid)

        if current.remaining == 0:
            current.finish_time = t
            current.state       = 'done'
            done               += 1
        else:
            next_level = min(level + 1, n_queues - 1)
            levels[current.pid] = next_level
            queues[next_level].append(current)

    return gantt, procs


def compute_metrics(procs, gantt):
    total_time = gantt[-1][2] if gantt else 1
    idle_time  = sum(e - s for lbl, s, e in gantt if lbl == 'IDLE')
    cpu_util   = ((total_time - idle_time) / total_time * 100) if total_time else 0
    n          = len(procs)
    awt        = sum(p.waiting     for p in procs) / n if n else 0
    att        = sum(p.turnaround  for p in procs) / n if n else 0
    art        = sum(p.response_time for p in procs if p.response_time >= 0) / n if n else 0
    throughput = n / total_time if total_time else 0
    return {
        'avg_waiting':    round(awt, 2),
        'avg_turnaround': round(att, 2),
        'avg_response':   round(art, 2),
        'cpu_utilization': round(cpu_util, 2),
        'throughput':     round(throughput, 4),
    }


def detect_starvation(procs, gantt, threshold=20):
    issues = []
    for p in procs:
        if p.waiting > threshold:
            issues.append(f"P{p.pid} starvation (wait={p.waiting})")
    return issues


def recommend_algorithm(procs, current_algo):
    bursts   = [p.burst for p in procs]
    variance = max(bursts) - min(bursts) if bursts else 0
    n        = len(procs)
    prios    = list(set(p.priority for p in procs))

    if variance < 3 and n <= 6:
        rec = "FCFS"
        reason = "Similar burst times — FCFS minimises overhead."
    elif variance > 6:
        rec = "SJF (Non-Preemptive)"
        reason = "High burst variance — SJF minimises average waiting."
    elif len(prios) > 2:
        rec = "Priority (Preemptive)"
        reason = "Distinct priorities detected — preemptive priority suits this."
    elif n > 6:
        rec = "Round Robin"
        reason = "Many processes — RR ensures fair time-sharing."
    else:
        rec = "MLFQ"
        reason = "Mixed workload — MLFQ adapts queue levels dynamically."

    if rec == current_algo:
        return f"✓ {current_algo} is already optimal for this workload."
    return f"Recommendation: Switch to {rec}. Reason: {reason}"


# ─────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────

class CPUSchedulerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CPU Scheduling Simulator — Bahria University CSL-320")
        self.root.geometry("1400x860")
        self.root.configure(bg=COLORS['bg'])
        self.root.minsize(1100, 700)

        self.processes   = []
        self.pid_counter = 0
        self.running     = False
        self.paused      = False
        self.sim_thread  = None
        self.gantt_data  = []
        self.result_procs = []
        self.quantum     = tk.IntVar(value=2)
        self.algo_var    = tk.StringVar(value="FCFS")
        self.speed_var   = tk.DoubleVar(value=1.0)
        self.mlfq_q1     = tk.IntVar(value=2)
        self.mlfq_q2     = tk.IntVar(value=4)
        self.mlfq_q3     = tk.IntVar(value=8)

        self._build_ui()
        self._add_sample_processes()

    # ── UI CONSTRUCTION ──────────────────────────────────────

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self.root, bg=COLORS['accent1'], height=50)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="⚡  CPU Scheduling Simulator",
                 bg=COLORS['accent1'], fg='white',
                 font=('Segoe UI', 16, 'bold')).pack(side='left', padx=16, pady=8)
        tk.Label(title_frame, text="Bahria University · CSL-320 Operating Systems",
                 bg=COLORS['accent1'], fg='#D0CCFF',
                 font=('Segoe UI', 10)).pack(side='right', padx=16)

        # Main paned layout
        main = tk.PanedWindow(self.root, orient='horizontal',
                              bg=COLORS['bg'], sashwidth=4,
                              sashrelief='flat', opaqueresize=True)
        main.pack(fill='both', expand=True, padx=8, pady=8)

        left  = self._build_left_panel(main)
        right = self._build_right_panel(main)
        main.add(left,  minsize=340, width=360)
        main.add(right, minsize=600)

    def _build_left_panel(self, parent):
        frame = tk.Frame(parent, bg=COLORS['bg'])

        # ── Algorithm selection ──
        alg_card = self._card(frame, "🧠  Algorithm")
        alg_card.pack(fill='x', pady=(0, 6))

        algos = ["FCFS", "SJF (Non-Preemptive)", "SJF (Preemptive / SRTF)",
                 "Priority (Non-Preemptive)", "Priority (Preemptive)",
                 "Round Robin", "MLFQ"]
        self.algo_menu = ttk.Combobox(alg_card, values=algos,
                                       textvariable=self.algo_var,
                                       state='readonly', font=('Segoe UI', 10))
        self._style_combo(self.algo_menu)
        self.algo_menu.pack(fill='x', padx=10, pady=(0, 8))
        self.algo_menu.bind('<<ComboboxSelected>>', self._on_algo_change)

        # RR quantum
        self.rr_frame = tk.Frame(alg_card, bg=COLORS['card'])
        self.rr_frame.pack(fill='x', padx=10, pady=(0, 6))
        tk.Label(self.rr_frame, text="Time Quantum:", bg=COLORS['card'],
                 fg=COLORS['subtext'], font=('Segoe UI', 9)).pack(side='left')
        tk.Spinbox(self.rr_frame, from_=1, to=20, textvariable=self.quantum,
                   width=5, bg=COLORS['panel'], fg=COLORS['text'],
                   buttonbackground=COLORS['accent1'],
                   relief='flat', font=('Segoe UI', 10)).pack(side='left', padx=6)

        # MLFQ quantums
        self.mlfq_frame = tk.Frame(alg_card, bg=COLORS['card'])
        for i, (var, label) in enumerate([(self.mlfq_q1,'Q1'), (self.mlfq_q2,'Q2'), (self.mlfq_q3,'Q3')]):
            tk.Label(self.mlfq_frame, text=f"{label}:", bg=COLORS['card'],
                     fg=COLORS['subtext'], font=('Segoe UI', 9)).grid(row=0, column=i*2, padx=(6,2))
            tk.Spinbox(self.mlfq_frame, from_=1, to=20, textvariable=var,
                       width=4, bg=COLORS['panel'], fg=COLORS['text'],
                       buttonbackground=COLORS['accent1'],
                       relief='flat', font=('Segoe UI', 9)).grid(row=0, column=i*2+1, padx=2)
        self.mlfq_frame.pack(fill='x', padx=10, pady=(0, 8))
        self.mlfq_frame.pack_forget()

        # Speed
        sp_row = tk.Frame(alg_card, bg=COLORS['card'])
        sp_row.pack(fill='x', padx=10, pady=(0, 8))
        tk.Label(sp_row, text="Sim Speed:", bg=COLORS['card'],
                 fg=COLORS['subtext'], font=('Segoe UI', 9)).pack(side='left')
        tk.Scale(sp_row, from_=0.2, to=5.0, resolution=0.2,
                 variable=self.speed_var, orient='horizontal',
                 bg=COLORS['card'], fg=COLORS['text'],
                 troughcolor=COLORS['panel'],
                 highlightthickness=0, length=140,
                 label='').pack(side='left', padx=6)

        # ── Process input ──
        proc_card = self._card(frame, "➕  Add Process")
        proc_card.pack(fill='x', pady=(0, 6))

        fields = [("Arrival Time", 'arrival_var', 0),
                  ("Burst Time",   'burst_var',   5),
                  ("Priority",     'priority_var', 1)]
        self.arrival_var  = tk.IntVar(value=0)
        self.burst_var    = tk.IntVar(value=5)
        self.priority_var = tk.IntVar(value=1)

        for label, attr, default in fields:
            row = tk.Frame(proc_card, bg=COLORS['card'])
            row.pack(fill='x', padx=10, pady=2)
            tk.Label(row, text=label + ":", bg=COLORS['card'],
                     fg=COLORS['subtext'], font=('Segoe UI', 9),
                     width=13, anchor='w').pack(side='left')
            tk.Spinbox(row, from_=0, to=999, textvariable=getattr(self, attr),
                       width=8, bg=COLORS['panel'], fg=COLORS['text'],
                       buttonbackground=COLORS['accent1'],
                       relief='flat', font=('Segoe UI', 10)).pack(side='left', padx=4)

        btn_row = tk.Frame(proc_card, bg=COLORS['card'])
        btn_row.pack(fill='x', padx=10, pady=(6, 8))
        self._btn(btn_row, "Add Process", self._add_process,
                  COLORS['accent1']).pack(side='left', padx=(0, 6))
        self._btn(btn_row, "Clear All",  self._clear_processes,
                  COLORS['accent3']).pack(side='left')

        # ── Process table ──
        tbl_card = self._card(frame, "📋  Process Queue")
        tbl_card.pack(fill='both', expand=True, pady=(0, 6))

        cols = ('PID', 'Arrival', 'Burst', 'Priority', 'State')
        self.tree = ttk.Treeview(tbl_card, columns=cols, show='headings', height=8)
        for c in cols:
            w = 50 if c not in ('State',) else 70
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor='center', minwidth=40)
        self._style_tree()
        vsb = ttk.Scrollbar(tbl_card, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        vsb.pack(side='right', fill='y', pady=6, padx=(0, 8))
        self.tree.bind('<Delete>', lambda e: self._remove_selected())

        # ── Control buttons ──
        ctrl_card = self._card(frame, "▶  Simulation Control")
        ctrl_card.pack(fill='x', pady=(0, 6))

        row1 = tk.Frame(ctrl_card, bg=COLORS['card'])
        row1.pack(fill='x', padx=10, pady=(4, 2))
        self.btn_run   = self._btn(row1, "▶ Run",    self._run_simulation,   COLORS['running'])
        self.btn_pause = self._btn(row1, "⏸ Pause",  self._pause_simulation, COLORS['accent5'])
        self.btn_reset = self._btn(row1, "⏹ Reset",  self._reset_simulation, COLORS['accent3'])
        for b in (self.btn_run, self.btn_pause, self.btn_reset):
            b.pack(side='left', padx=3)

        # Starvation / Feedback
        self.feedback_label = tk.Label(ctrl_card, text="",
                                       bg=COLORS['card'], fg=COLORS['accent2'],
                                       font=('Segoe UI', 8), wraplength=320,
                                       justify='left')
        self.feedback_label.pack(fill='x', padx=10, pady=(4, 8))

        return frame

    def _build_right_panel(self, parent):
        frame = tk.Frame(parent, bg=COLORS['bg'])

        # Gantt chart area
        gantt_card = self._card(frame, "📊  Gantt Chart (Live)")
        gantt_card.pack(fill='x', pady=(0, 6))

        self.gantt_canvas_frame = tk.Frame(gantt_card, bg=COLORS['card'],
                                           height=140)
        self.gantt_canvas_frame.pack(fill='x', padx=8, pady=6)
        self.gantt_canvas_frame.pack_propagate(False)

        self.gantt_cv = tk.Canvas(self.gantt_canvas_frame,
                                  bg=COLORS['panel'], highlightthickness=0)
        self.gantt_cv.pack(fill='both', expand=True)

        # Metrics panel
        metrics_card = self._card(frame, "📈  Performance Metrics")
        metrics_card.pack(fill='x', pady=(0, 6))

        metrics_inner = tk.Frame(metrics_card, bg=COLORS['card'])
        metrics_inner.pack(fill='x', padx=10, pady=8)

        metric_defs = [
            ("Avg Waiting",    'accent1', 'awt_label'),
            ("Avg Turnaround", 'accent2', 'att_label'),
            ("Avg Response",   'accent4', 'art_label'),
            ("CPU Util %",     'running', 'util_label'),
            ("Throughput",     'accent5', 'tput_label'),
        ]
        for i, (title, color, attr) in enumerate(metric_defs):
            cell = tk.Frame(metrics_inner, bg=COLORS['panel'],
                            relief='flat', bd=0)
            cell.grid(row=0, column=i, padx=4, pady=2, sticky='ew')
            metrics_inner.columnconfigure(i, weight=1)
            tk.Label(cell, text=title, bg=COLORS['panel'],
                     fg=COLORS['subtext'], font=('Segoe UI', 8)).pack(pady=(6, 0))
            lbl = tk.Label(cell, text="—", bg=COLORS['panel'],
                           fg=COLORS[color], font=('Segoe UI', 14, 'bold'))
            lbl.pack(pady=(2, 6))
            setattr(self, attr, lbl)

        # Process metrics table
        tbl2_card = self._card(frame, "📑  Per-Process Results")
        tbl2_card.pack(fill='x', pady=(0, 6))

        cols2 = ('PID', 'Arrival', 'Burst', 'Priority',
                 'Start', 'Finish', 'Waiting', 'Turnaround', 'Response')
        self.result_tree = ttk.Treeview(tbl2_card, columns=cols2,
                                        show='headings', height=6)
        for c in cols2:
            self.result_tree.heading(c, text=c)
            self.result_tree.column(c, width=72, anchor='center', minwidth=50)
        self._style_tree(self.result_tree)
        vsb2 = ttk.Scrollbar(tbl2_card, orient='vertical',
                              command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=vsb2.set)
        self.result_tree.pack(side='left', fill='x', expand=True, padx=(8, 0), pady=6)
        vsb2.pack(side='right', fill='y', pady=6, padx=(0, 8))

        # Ready queue visualisation
        rq_card = self._card(frame, "🔄  Ready Queue State")
        rq_card.pack(fill='both', expand=True, pady=(0, 0))

        self.rq_canvas = tk.Canvas(rq_card, bg=COLORS['panel'],
                                   height=70, highlightthickness=0)
        self.rq_canvas.pack(fill='x', padx=8, pady=6)

        return frame

    # ── HELPERS ─────────────────────────────────────────────

    def _card(self, parent, title):
        outer = tk.Frame(parent, bg=COLORS['border'], bd=1)
        header = tk.Frame(outer, bg=COLORS['accent1'], height=26)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text=title, bg=COLORS['accent1'],
                 fg='white', font=('Segoe UI', 9, 'bold'),
                 padx=10).pack(side='left', fill='y')
        inner = tk.Frame(outer, bg=COLORS['card'])
        inner.pack(fill='both', expand=True)
        return inner

    def _btn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd,
                         bg=color, fg='white' if color != COLORS['accent5'] else '#111',
                         font=('Segoe UI', 9, 'bold'),
                         relief='flat', bd=0, padx=10, pady=5,
                         activebackground=color, cursor='hand2')

    def _style_combo(self, widget):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TCombobox',
                        fieldbackground=COLORS['panel'],
                        background=COLORS['panel'],
                        foreground=COLORS['text'],
                        selectbackground=COLORS['accent1'],
                        selectforeground='white',
                        arrowcolor=COLORS['accent1'])

    def _style_tree(self, tree=None):
        if tree is None:
            tree = self.tree
        style = ttk.Style()
        style.configure('Treeview',
                        background=COLORS['panel'],
                        foreground=COLORS['text'],
                        rowheight=26,
                        fieldbackground=COLORS['panel'],
                        bordercolor=COLORS['border'],
                        font=('Segoe UI', 9))
        style.configure('Treeview.Heading',
                        background=COLORS['accent1'],
                        foreground='white',
                        font=('Segoe UI', 9, 'bold'),
                        relief='flat')
        style.map('Treeview',
                  background=[('selected', COLORS['accent1'])],
                  foreground=[('selected', 'white')])

    # ── PROCESS MANAGEMENT ───────────────────────────────────

    def _add_sample_processes(self):
        samples = [(0, 8, 3), (1, 4, 1), (2, 9, 2), (3, 5, 4), (3, 3, 5)]
        for arr, burst, pri in samples:
            self._add_process_data(arr, burst, pri)

    def _add_process_data(self, arrival, burst, priority):
        color = PROCESS_COLORS[self.pid_counter % len(PROCESS_COLORS)]
        p = Process(self.pid_counter, arrival, burst, priority, color)
        self.processes.append(p)
        self.tree.insert('', 'end', iid=str(self.pid_counter),
                         values=(f'P{p.pid}', p.arrival, p.burst,
                                 p.priority, p.state),
                         tags=(f'p{p.pid}',))
        self.tree.tag_configure(f'p{p.pid}', foreground=color)
        self.pid_counter += 1

    def _add_process(self):
        if self.running:
            self._show_feedback("⚠ Stop simulation before adding processes.")
            return
        try:
            arrival  = self.arrival_var.get()
            burst    = self.burst_var.get()
            priority = self.priority_var.get()
            if burst < 1:
                raise ValueError("Burst must be ≥ 1")
            self._add_process_data(arrival, burst, priority)
            self.arrival_var.set(arrival + 1)
        except Exception as e:
            messagebox.showerror("Input Error", str(e))

    def _remove_selected(self):
        sel = self.tree.selection()
        for iid in sel:
            pid = int(iid)
            self.processes = [p for p in self.processes if p.pid != pid]
            self.tree.delete(iid)

    def _clear_processes(self):
        if self.running:
            return
        self.processes.clear()
        self.tree.delete(*self.tree.get_children())
        self.pid_counter = 0
        self._clear_visuals()

    def _on_algo_change(self, event=None):
        algo = self.algo_var.get()
        if algo == "Round Robin":
            self.rr_frame.pack(fill='x', padx=10, pady=(0, 6))
            self.mlfq_frame.pack_forget()
        elif algo == "MLFQ":
            self.mlfq_frame.pack(fill='x', padx=10, pady=(0, 6))
            self.rr_frame.pack_forget()
        else:
            self.rr_frame.pack_forget()
            self.mlfq_frame.pack_forget()

    # ── SIMULATION ───────────────────────────────────────────

    def _run_simulation(self):
        if not self.processes:
            messagebox.showwarning("No Processes", "Add at least one process first.")
            return
        if self.running and not self.paused:
            return
        if self.paused:
            self.paused = False
            self._show_feedback("▶ Resumed")
            return

        self._clear_visuals()
        self.running = True
        self.paused  = False
        self.btn_run.config(text="▶ Running…", state='disabled')

        self.sim_thread = threading.Thread(target=self._simulate, daemon=True)
        self.sim_thread.start()

    def _pause_simulation(self):
        if self.running:
            self.paused = not self.paused
            label = "⏸ Paused" if self.paused else "▶ Resumed"
            self._show_feedback(label)
            if not self.paused:
                self.btn_run.config(text="▶ Running…", state='disabled')

    def _reset_simulation(self):
        self.running = False
        self.paused  = False
        for p in self.processes:
            p.reset()
        self._update_tree_states()
        self._clear_visuals()
        self.btn_run.config(text="▶ Run", state='normal')
        self._show_feedback("Reset. Ready to run.")

    def _simulate(self):
        algo = self.algo_var.get()
        try:
            if algo == "FCFS":
                gantt, procs = run_fcfs(self.processes)
            elif algo == "SJF (Non-Preemptive)":
                gantt, procs = run_sjf(self.processes, preemptive=False)
            elif algo == "SJF (Preemptive / SRTF)":
                gantt, procs = run_sjf(self.processes, preemptive=True)
            elif algo == "Priority (Non-Preemptive)":
                gantt, procs = run_priority(self.processes, preemptive=False)
            elif algo == "Priority (Preemptive)":
                gantt, procs = run_priority(self.processes, preemptive=True)
            elif algo == "Round Robin":
                gantt, procs = run_rr(self.processes, self.quantum.get())
            elif algo == "MLFQ":
                qs = [self.mlfq_q1.get(), self.mlfq_q2.get(), self.mlfq_q3.get()]
                gantt, procs = run_mlfq(self.processes, qs)
            else:
                gantt, procs = run_fcfs(self.processes)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Simulation Error", str(e)))
            self.running = False
            return

        self.gantt_data   = gantt
        self.result_procs = procs
        metrics = compute_metrics(procs, gantt)

        # Animate gantt step by step
        delay = 1.0 / max(self.speed_var.get(), 0.1)
        partial_gantt = []

        for step in gantt:
            while self.paused:
                time.sleep(0.1)
            if not self.running:
                break
            partial_gantt.append(step)
            snap = list(partial_gantt)
            p_snap = list(procs)
            self.root.after(0, lambda g=snap, p=p_snap: self._draw_gantt(g, p))
            self.root.after(0, lambda g=snap, p=p_snap: self._draw_ready_queue(g, p))
            time.sleep(delay)

        if self.running:
            self.root.after(0, lambda: self._show_metrics(metrics))
            self.root.after(0, lambda: self._populate_result_table(procs))
            issues = detect_starvation(procs, gantt)
            rec    = recommend_algorithm(procs, algo)
            msg    = rec
            if issues:
                msg += "\n⚠ " + " | ".join(issues)
            self.root.after(0, lambda m=msg: self._show_feedback(m))
            self.root.after(0, lambda: self.btn_run.config(text="▶ Run", state='normal'))
        self.running = False

    # ── DRAWING ──────────────────────────────────────────────

    def _draw_gantt(self, gantt, procs):
        cv = self.gantt_cv
        cv.delete('all')
        w  = cv.winfo_width()  or 800
        h  = cv.winfo_height() or 130

        if not gantt:
            return

        total = gantt[-1][2]
        if total == 0:
            return

        margin_l = 8
        margin_r = 8
        bar_y    = 30
        bar_h    = 50
        avail_w  = w - margin_l - margin_r

        pid_to_color = {}
        for p in procs:
            pid_to_color[p.pid] = p.color

        for (lbl, start, end) in gantt:
            x1 = margin_l + (start / total) * avail_w
            x2 = margin_l + (end   / total) * avail_w
            bw = max(x2 - x1, 2)

            if lbl == 'IDLE':
                fill = COLORS['idle']
                text = 'IDLE'
                fg   = COLORS['subtext']
            else:
                fill = pid_to_color.get(lbl, COLORS['accent1'])
                text = f'P{lbl}'
                fg   = 'white'

            cv.create_rectangle(x1, bar_y, x1 + bw, bar_y + bar_h,
                                 fill=fill, outline=COLORS['bg'], width=1)
            if bw > 20:
                cv.create_text(x1 + bw/2, bar_y + bar_h/2,
                               text=text, fill=fg,
                               font=('Segoe UI', 8, 'bold'))

        # Time markers
        step = max(1, total // 10)
        for t in range(0, total + 1, step):
            x = margin_l + (t / total) * avail_w
            cv.create_line(x, bar_y + bar_h, x, bar_y + bar_h + 8,
                           fill=COLORS['subtext'], width=1)
            cv.create_text(x, bar_y + bar_h + 18,
                           text=str(t), fill=COLORS['subtext'],
                           font=('Segoe UI', 7))

        cv.create_text(w - 50, 14, text=f"t = {total}",
                       fill=COLORS['accent2'], font=('Segoe UI', 8, 'bold'))

    def _draw_ready_queue(self, gantt, procs):
        cv = self.rq_canvas
        cv.delete('all')
        w = cv.winfo_width() or 800
        h = cv.winfo_height() or 70

        if not gantt:
            return

        current_time = gantt[-1][2]
        pid_to_color = {p.pid: p.color for p in procs}

        # determine states at current_time
        in_gantt_now = gantt[-1][0] if gantt else None
        done_pids = set()
        for p in procs:
            if p.finish_time >= 0 and p.finish_time <= current_time:
                done_pids.add(p.pid)

        ready = []
        for p in procs:
            if p.pid in done_pids:
                continue
            if p.arrival <= current_time and p.pid != in_gantt_now:
                ready.append(p)

        # Draw running
        x = 10
        if in_gantt_now and in_gantt_now != 'IDLE':
            color = pid_to_color.get(in_gantt_now, COLORS['running'])
            cv.create_rectangle(x, 12, x + 60, 56,
                                 fill=color, outline=COLORS['running'], width=2)
            cv.create_text(x + 30, 28, text=f'P{in_gantt_now}',
                           fill='white', font=('Segoe UI', 10, 'bold'))
            cv.create_text(x + 30, 46, text='Running',
                           fill=COLORS['running'], font=('Segoe UI', 7))
            x += 80

        # Arrow
        if ready:
            cv.create_text(x, 34, text="Queue →",
                           fill=COLORS['subtext'], font=('Segoe UI', 8))
            x += 60

        for p in ready[:10]:
            color = pid_to_color.get(p.pid, COLORS['accent1'])
            cv.create_rectangle(x, 16, x + 50, 52,
                                 fill=color, outline=COLORS['border'], width=1)
            cv.create_text(x + 25, 30, text=f'P{p.pid}',
                           fill='white', font=('Segoe UI', 9, 'bold'))
            cv.create_text(x + 25, 44, text=f'rem={p.remaining}',
                           fill='white', font=('Segoe UI', 7))
            x += 56

    def _show_metrics(self, m):
        self.awt_label.config(text=str(m['avg_waiting']))
        self.att_label.config(text=str(m['avg_turnaround']))
        self.art_label.config(text=str(m['avg_response']))
        self.util_label.config(text=f"{m['cpu_utilization']}%")
        self.tput_label.config(text=str(m['throughput']))

    def _populate_result_table(self, procs):
        self.result_tree.delete(*self.result_tree.get_children())
        for p in sorted(procs, key=lambda x: x.pid):
            self.result_tree.insert('', 'end',
                values=(f'P{p.pid}', p.arrival, p.burst, p.priority,
                        p.start_time, p.finish_time,
                        p.waiting, p.turnaround, p.response_time),
                tags=(f'rp{p.pid}',))
            self.result_tree.tag_configure(f'rp{p.pid}', foreground=p.color)

    def _update_tree_states(self):
        for p in self.processes:
            try:
                self.tree.item(str(p.pid), values=(
                    f'P{p.pid}', p.arrival, p.burst, p.priority, p.state))
            except Exception:
                pass

    def _clear_visuals(self):
        self.gantt_cv.delete('all')
        self.rq_canvas.delete('all')
        self.result_tree.delete(*self.result_tree.get_children())
        for lbl in (self.awt_label, self.att_label, self.art_label,
                    self.util_label, self.tput_label):
            lbl.config(text="—")
        self._show_feedback("")

    def _show_feedback(self, msg):
        self.feedback_label.config(text=msg)


# ─────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    root = tk.Tk()
    app  = CPUSchedulerApp(root)
    root.mainloop()
