"""图形界面（tkinter）。"""

from __future__ import annotations

import ctypes
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from . import audio, config as cfgmod, paths
from .config import LANGUAGES
from .hotkey import capture_once
from .service import VoiceService

ACCENT = "#e8112d"
STATUS_STYLE = {
    "idle": ("待命 · 按下快捷键说话", "#1f9d55"),
    "recording": ("● 正在录音…", "#d32f2f"),
    "busy": ("识别中…", "#c77700"),
}
FONT = ("Microsoft YaHei UI", 10)


class ScrollFrame(ttk.Frame):
    """可纵向滚动的容器。"""

    def __init__(self, master, **kw) -> None:
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.body = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vbar.pack(side="right", fill="y")
        self.body.bind("<Configure>", self._on_body)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.canvas.bind_all("<MouseWheel>", self._on_wheel, add="+")

    def _on_body(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, event) -> None:
        self.canvas.itemconfigure(self._win, width=event.width)

    def _on_wheel(self, event) -> None:
        try:
            if self.winfo_containing(event.x_root, event.y_root) is None:
                return
            self.canvas.yview_scroll(int(-event.delta / 120), "units")
        except Exception:
            pass


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = cfgmod.load()
        self.events: "queue.Queue" = queue.Queue()
        self.service = VoiceService(self.cfg, self.events)
        self.running_flag = False
        self._busy_loading = False
        self._record_btn_down = False

        root.title(paths.APP_NAME)
        root.geometry(self._centered_geometry(620, 660))
        root.minsize(560, 560)
        try:
            root.option_add("*Font", FONT)
        except Exception:
            pass
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self._poll)
        if self.cfg.always_on_top:
            root.attributes("-topmost", True)
        self.log("程序已启动，正在加载离线识别引擎…（约需 1~2 秒）")
        self.root.after(300, self.start_service)

    def _centered_geometry(self, width: int, height: int) -> str:
        try:
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = max(0, (screen_w - width) // 2)
            y = max(0, (screen_h - height) // 3)
            return f"{width}x{height}+{x}+{y}"
        except Exception:
            return f"{width}x{height}"

    # ------------------------------------------------------------------ 界面
    def _build(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except Exception:
            pass

        header = ttk.Frame(self.root, padding=(14, 12, 14, 6))
        header.pack(fill="x")
        self.dot = tk.Canvas(header, width=16, height=16, highlightthickness=0)
        self.dot_id = self.dot.create_oval(2, 2, 14, 14, fill="#1f9d55", outline="")
        self.dot.pack(side="left", padx=(0, 8), pady=4)
        self.status_var = tk.StringVar(value="待命")
        ttk.Label(
            header, textvariable=self.status_var, font=("Microsoft YaHei UI", 13, "bold")
        ).pack(side="left")
        self.hint_var = tk.StringVar(value="")
        ttk.Label(header, textvariable=self.hint_var, foreground="#666").pack(
            side="right"
        )

        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.tab_use = ttk.Frame(nb, padding=10)
        self.tab_set = ttk.Frame(nb, padding=(4, 4))
        nb.add(self.tab_use, text="  使用  ")
        nb.add(self.tab_set, text="  设置  ")
        self._build_use(self.tab_use)
        self._build_settings(self.tab_set)

    def _build_use(self, parent: ttk.Frame) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x")
        self.btn_toggle = ttk.Button(row, text="开始", width=12, command=self._toggle_service)
        self.btn_toggle.pack(side="left")
        self.btn_test = ttk.Button(row, text="录音 3 秒并识别", command=self._test_record)
        self.btn_test.pack(side="left", padx=8)
        self.btn_send = ttk.Button(row, text="把上次结果打到记事本", command=self._test_type)
        self.btn_send.pack(side="left")

        ttk.Label(parent, text="最近一次识别：", foreground="#444").pack(
            anchor="w", pady=(12, 2)
        )
        self.last_box = tk.Text(
            parent, height=3, wrap="word", relief="solid", borderwidth=1, font=FONT
        )
        self.last_box.pack(fill="x")
        self.last_box.configure(state="disabled")

        ttk.Label(parent, text="运行日志：", foreground="#444").pack(
            anchor="w", pady=(10, 2)
        )
        self.log_box = scrolledtext.ScrolledText(
            parent, height=12, wrap="word", font=("Consolas", 9)
        )
        self.log_box.pack(fill="both", expand=True)
        self.log_box.configure(state="disabled")

        tip = ttk.Label(
            parent,
            text="提示：游戏建议使用「无边框窗口」模式；说话时按住快捷键，松开后文字会自动进入聊天框。",
            foreground="#777",
            wraplength=560,
            justify="left",
        )
        tip.pack(anchor="w", pady=(8, 0))

    def _build_settings(self, parent: ttk.Frame) -> None:
        sf = ScrollFrame(parent)
        sf.pack(fill="both", expand=True)
        body = sf.body
        pad = {"padx": 10, "pady": 4}

        # --- 触发方式 ---
        box = ttk.LabelFrame(body, text=" 触发方式 ", padding=8)
        box.pack(fill="x", **pad)
        self.mode_var = tk.StringVar(value=self.cfg.trigger_mode)
        ttk.Radiobutton(
            box, text="按住说话（松开即识别）", value="hold", variable=self.mode_var
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            box, text="按一下开始，再按一下结束", value="toggle", variable=self.mode_var
        ).grid(row=0, column=1, sticky="w", padx=(18, 0))

        ttk.Label(box, text="快捷键：").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.hotkey_var = tk.StringVar(value=self.cfg.hotkey)
        ttk.Entry(box, textvariable=self.hotkey_var, width=18).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Button(box, text="录制按键", width=10, command=self._capture_hotkey).grid(
            row=1, column=1, sticky="e", pady=(8, 0)
        )
        ttk.Label(
            box, text="支持 F1~F12、单字母、鼠标侧键（mouse4/mouse5）、组合键（如 ctrl+alt+v）",
            foreground="#777",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # --- 麦克风 ---
        box = ttk.LabelFrame(body, text=" 麦克风与识别 ", padding=8)
        box.pack(fill="x", **pad)
        ttk.Label(box, text="输入设备：").grid(row=0, column=0, sticky="w")
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(box, textvariable=self.mic_var, width=38, state="readonly")
        self.mic_combo.grid(row=0, column=1, sticky="w", padx=(4, 4))
        ttk.Button(box, text="刷新", width=6, command=self._refresh_mics).grid(
            row=0, column=2, sticky="w"
        )
        self._refresh_mics()

        ttk.Label(box, text="识别语言：").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.lang_label = tk.StringVar(
            value=LANGUAGES.get(self.cfg.language, LANGUAGES["zh"])
        )
        cb = ttk.Combobox(
            box,
            textvariable=self.lang_label,
            values=list(LANGUAGES.values()),
            width=16,
            state="readonly",
        )
        cb.grid(row=1, column=1, sticky="w", padx=(4, 4), pady=(6, 0))
        self.lang_combo = cb

        self.itn_var = tk.BooleanVar(value=self.cfg.use_itn)
        ttk.Checkbutton(box, text="数字/日期规范化（如 一 转 1）", variable=self.itn_var).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(6, 0)
        )

        # --- 引擎 ---
        box = ttk.LabelFrame(body, text=" 识别引擎 ", padding=8)
        box.pack(fill="x", **pad)
        self.engine_var = tk.StringVar(value=self.cfg.engine)
        ttk.Radiobutton(
            box, text="本地离线（免费、无需联网）", value="local", variable=self.engine_var,
            command=self._sync_engine,
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(
            box, text="云端接口（需要 API Key）", value="api", variable=self.engine_var,
            command=self._sync_engine,
        ).grid(row=1, column=0, columnspan=2, sticky="w")

        self.api_widgets: list[tk.Widget] = []
        ttk.Label(box, text="接口地址：").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.api_base_var = tk.StringVar(value=self.cfg.api_base)
        e1 = ttk.Entry(box, textvariable=self.api_base_var, width=44)
        e1.grid(row=2, column=1, sticky="w", padx=(4, 0), pady=(4, 0))
        ttk.Label(box, text="API Key：").grid(row=3, column=0, sticky="w", pady=(4, 0))
        self.api_key_var = tk.StringVar(value=self.cfg.api_key)
        e2 = ttk.Entry(box, textvariable=self.api_key_var, width=44, show="*")
        e2.grid(row=3, column=1, sticky="w", padx=(4, 0), pady=(4, 0))
        ttk.Label(box, text="模型名：").grid(row=4, column=0, sticky="w", pady=(4, 0))
        self.api_model_var = tk.StringVar(value=self.cfg.api_model)
        e3 = ttk.Entry(box, textvariable=self.api_model_var, width=44)
        e3.grid(row=4, column=1, sticky="w", padx=(4, 0), pady=(4, 0))
        self.api_widgets = [e1, e2, e3]

        # --- 输入行为 ---
        box = ttk.LabelFrame(body, text=" 输入到游戏 ", padding=8)
        box.pack(fill="x", **pad)
        self.auto_chat_var = tk.BooleanVar(value=self.cfg.auto_enter_chat)
        self.auto_send_var = tk.BooleanVar(value=self.cfg.auto_send)
        self.only_game_var = tk.BooleanVar(value=self.cfg.only_when_game)
        self.clip_var = tk.BooleanVar(value=self.cfg.only_clipboard)
        self.strip_var = tk.BooleanVar(value=self.cfg.strip_punct)
        ttk.Checkbutton(
            box, text="自动按回车打开聊天框", variable=self.auto_chat_var
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            box, text="打完字再按回车发送（取消则留在输入框里可编辑）",
            variable=self.auto_send_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(
            box, text="仅在游戏窗口激活时输入（否则只复制到剪贴板）",
            variable=self.only_game_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(box, text="只复制到剪贴板，不模拟按键", variable=self.clip_var).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(box, text="去掉句末标点", variable=self.strip_var).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )

        ttk.Label(box, text="游戏进程名：").grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.game_proc_var = tk.StringVar(value=self.cfg.game_process)
        ttk.Entry(box, textvariable=self.game_proc_var, width=38).grid(
            row=5, column=1, sticky="w", padx=(4, 0), pady=(6, 0)
        )

        ttk.Label(box, text="开聊天延迟(秒)：").grid(row=6, column=0, sticky="w", pady=(4, 0))
        self.chat_delay_var = tk.StringVar(value=str(self.cfg.chat_open_delay))
        ttk.Entry(box, textvariable=self.chat_delay_var, width=8).grid(
            row=6, column=1, sticky="w", padx=(4, 0), pady=(4, 0)
        )
        ttk.Label(box, text="字间停顿(秒)：").grid(row=7, column=0, sticky="w", pady=(4, 0))
        self.char_delay_var = tk.StringVar(value=str(self.cfg.char_delay))
        ttk.Entry(box, textvariable=self.char_delay_var, width=8).grid(
            row=7, column=1, sticky="w", padx=(4, 0), pady=(4, 0)
        )

        # --- 修正与杂项 ---
        box = ttk.LabelFrame(body, text=" 修正词与其它 ", padding=8)
        box.pack(fill="x", **pad)
        self.prefix_var = tk.StringVar(value=self.cfg.prefix)
        ttk.Label(box, text="前缀（可留空）：").grid(row=0, column=0, sticky="w")
        ttk.Entry(box, textvariable=self.prefix_var, width=24).grid(
            row=0, column=1, sticky="w", padx=(4, 0)
        )
        self.beep_var = tk.BooleanVar(value=self.cfg.beep)
        ttk.Checkbutton(box, text="提示音", variable=self.beep_var).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        self.top_var = tk.BooleanVar(value=self.cfg.always_on_top)
        ttk.Checkbutton(
            box, text="窗口置顶", variable=self.top_var, command=self._apply_topmost
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(
            box,
            text="识别修正（每行一条，格式：错误=正确；例如 a大=A大）",
            foreground="#777",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.repl_box = tk.Text(box, height=4, width=52, font=("Consolas", 9))
        self.repl_box.grid(row=3, column=0, columnspan=2, sticky="we")
        self.repl_box.insert(
            "1.0", "\n".join(f"{k}={v}" for k, v in (self.cfg.replacements or {}).items())
        )

        bar = ttk.Frame(body)
        bar.pack(fill="x", padx=10, pady=(6, 14))
        ttk.Button(bar, text="打开配置文件夹", command=self._open_data_dir).pack(side="left")
        ttk.Button(bar, text="保存并应用", command=self._save).pack(side="right")
        ttk.Label(
            bar, text="修改后点这里生效", foreground="#777"
        ).pack(side="right", padx=8)

        self._sync_engine()

    # ------------------------------------------------------------------ 小工具
    def _refresh_mics(self) -> None:
        names = ["系统默认"] + [name for _, name in audio.list_input_devices()]
        self.mic_combo.configure(values=names)
        current = self.cfg.device
        picked = "系统默认"
        if current:
            for name in names:
                if current.lower() in name.lower():
                    picked = name
                    break
        self.mic_var.set(picked)
        self._mic_names = names

    def _apply_topmost(self) -> None:
        try:
            self.root.attributes("-topmost", bool(self.top_var.get()))
        except Exception:
            pass

    def _open_data_dir(self) -> None:
        try:
            folder = paths.ensure_data_root()
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("打不开文件夹", str(exc))

    def _sync_engine(self) -> None:
        state = "normal" if self.engine_var.get() == "api" else "disabled"
        for widget in self.api_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def log(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{stamp}] {message}\n")
        lines = int(self.log_box.index("end-1c").split(".")[0])
        if lines > 600:
            self.log_box.delete("1.0", f"{lines - 500}.0")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_last(self, text: str) -> None:
        self.last_box.configure(state="normal")
        self.last_box.delete("1.0", "end")
        self.last_box.insert("1.0", text)
        self.last_box.configure(state="disabled")

    def _set_status(self, state: str) -> None:
        text, color = STATUS_STYLE.get(state, STATUS_STYLE["idle"])
        self.status_var.set(text)
        self.dot.itemconfigure(self.dot_id, fill=color)

    # ------------------------------------------------------------------ 服务
    def start_service(self) -> None:
        if self.running_flag or self._busy_loading:
            return
        self._busy_loading = True
        self.btn_toggle.configure(state="disabled", text="启动中…")

        def run() -> None:
            try:
                self.service.start()
            finally:
                self._busy_loading = False
                self.root.after(0, self._after_start)

        threading.Thread(target=run, daemon=True).start()

    def _after_start(self) -> None:
        ready = self.service.ready
        self.running_flag = ready
        self.btn_toggle.configure(state="normal", text="停止" if ready else "开始")
        if ready:
            self._set_status("idle")
        else:
            self.status_var.set("未启动")
            self.dot.itemconfigure(self.dot_id, fill="#999999")
        self._update_hint()

    def _stop_service(self) -> None:
        if not self.service.ready and not self.running_flag:
            return
        self.service.stop()
        self.running_flag = False
        self.btn_toggle.configure(state="normal", text="开始")
        self._set_status("idle")
        self.status_var.set("已停止")
        self.dot.itemconfigure(self.dot_id, fill="#999999")
        self._update_hint()

    def _toggle_service(self) -> None:
        if self.running_flag or self.service.ready:
            self._stop_service()
        else:
            self.start_service()

    def _update_hint(self) -> None:
        key = (self.service.cfg.hotkey or "").upper()
        if self.running_flag:
            self.hint_var.set(f"快捷键：{key}")
        else:
            self.hint_var.set("未启动")

    # ------------------------------------------------------------------ 测试
    def _test_record(self) -> None:
        if not self.running_flag:
            messagebox.showinfo("提示", "请先点击“开始”，等状态变成“待命”后再测试。")
            return
        self.btn_test.configure(state="disabled", text="录音中…")
        self._set_status("recording")

        def run() -> None:
            try:
                samples = self.service.record_test(3.0)
                self.root.after(0, lambda: self.btn_test.configure(text="识别中…"))
                text = self.service.preview(samples)
                self.root.after(0, lambda: self._test_done(text))
            except Exception as exc:
                self.root.after(0, lambda: self._test_done("", str(exc)))

        threading.Thread(target=run, daemon=True).start()

    def _test_done(self, text: str, error: str = "") -> None:
        self.btn_test.configure(state="normal", text="录音 3 秒并识别")
        self._set_status("idle")
        if error:
            self.log(f"测试失败：{error}")
            messagebox.showerror("测试失败", error)
            return
        if text:
            self._set_last(text)
            self.log(f"测试识别：{text}")
        else:
            self.log("测试没有识别到内容，请检查麦克风与音量")

    def _test_type(self) -> None:
        text = self.last_box.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("提示", "还没有识别结果。先按住快捷键说一句话吧。")
            return
        from .winapi import set_clipboard, tap_key, type_text

        set_clipboard(text)
        self.log("已复制到剪贴板；2 秒后把文字打到当前窗口，请先点开记事本/输入框…")

        def run() -> None:
            time.sleep(2.0)
            try:
                type_text(text, 0.004)
            except Exception as exc:
                self.root.after(0, lambda: self.log(f"模拟打字失败：{exc}"))

        threading.Thread(target=run, daemon=True).start()

    def _capture_hotkey(self) -> None:
        top = tk.Toplevel(self.root)
        top.title("设置快捷键")
        top.geometry("360x140")
        top.transient(self.root)
        top.grab_set()
        ttk.Label(
            top, text="请按下想使用的按键（键盘或鼠标侧键）…", font=FONT
        ).pack(pady=(24, 8))
        tip = ttk.Label(top, text="组合键请直接手动填写，例如 ctrl+alt+v", foreground="#777")
        tip.pack()

        def worker() -> None:
            name = capture_once(12)
            self.root.after(0, lambda: done(name))

        def done(name: str) -> None:
            if name:
                name = {"x1": "mouse4", "x2": "mouse5"}.get(name, name)
                if not name.startswith("vk"):
                    self.hotkey_var.set(name)
                    self.log(f"快捷键已设为 {name.upper()}")
            try:
                top.grab_release()
                top.destroy()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------ 保存
    def _save(self) -> None:
        cfg = self.cfg
        try:
            cfg.chat_open_delay = max(0.0, float(self.chat_delay_var.get()))
            cfg.char_delay = max(0.0, float(self.char_delay_var.get()))
        except ValueError:
            messagebox.showerror("格式错误", "延迟必须是数字，例如 0.25")
            return

        cfg.trigger_mode = self.mode_var.get()
        cfg.hotkey = (self.hotkey_var.get() or "f8").strip().lower()
        cfg.engine = self.engine_var.get()
        cfg.api_base = self.api_base_var.get().strip()
        cfg.api_key = self.api_key_var.get().strip()
        cfg.api_model = self.api_model_var.get().strip()
        cfg.use_itn = bool(self.itn_var.get())
        cfg.auto_enter_chat = bool(self.auto_chat_var.get())
        cfg.auto_send = bool(self.auto_send_var.get())
        cfg.only_when_game = bool(self.only_game_var.get())
        cfg.only_clipboard = bool(self.clip_var.get())
        cfg.strip_punct = bool(self.strip_var.get())
        cfg.game_process = self.game_proc_var.get().strip() or "VALORANT"
        cfg.prefix = self.prefix_var.get()
        cfg.beep = bool(self.beep_var.get())
        cfg.always_on_top = bool(self.top_var.get())
        cfg.device = "" if self.mic_var.get() == "系统默认" else self.mic_var.get()

        lang_map = {v: k for k, v in LANGUAGES.items()}
        cfg.language = lang_map.get(self.lang_label.get(), "zh")

        repl: dict[str, str] = {}
        for line in self.repl_box.get("1.0", "end").splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            old, new = line.split("=", 1)
            if old.strip():
                repl[old.strip()] = new.strip()
        cfg.replacements = repl

        try:
            cfgmod.save(cfg)
        except Exception as exc:
            messagebox.showerror("保存失败", f"无法写入配置文件：\n{exc}")
            return
        self.log("设置已保存")
        self._apply_topmost()

        if self.running_flag:
            self._stop_service()
            self.root.after(200, self.start_service)

    # ------------------------------------------------------------------ 轮询
    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "state":
                    self._set_status(payload)
                elif kind == "text":
                    self._set_last(payload)
                elif kind == "error":
                    self.log(f"错误：{payload}")
                    self._set_status("idle")
                elif kind == "ready":
                    self._after_start()
        except queue.Empty:
            pass
        self.root.after(120, self._poll)

    def _on_close(self) -> None:
        try:
            self.service.stop()
        except Exception:
            pass
        self.root.destroy()


def _apply_app_identity(root: tk.Tk) -> None:
    """让任务栏显示自己的图标/名称，而不是 Python 的。"""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "ValorantVoiceInput.Desktop.1"
        )
    except Exception:
        pass
    icon = paths.icon_path()
    if icon.exists():
        try:
            root.iconbitmap(default=str(icon))
        except Exception:
            pass


def _enable_dpi_awareness() -> None:
    """高分屏下避免界面发虚（必须在创建 Tk 之前调用）。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def run() -> None:
    _enable_dpi_awareness()
    root = tk.Tk()
    _apply_app_identity(root)

    def report_exception(exc_type, exc, tb) -> None:
        try:
            import traceback

            paths.log_dir().mkdir(parents=True, exist_ok=True)
            with (paths.log_dir() / "crash.log").open("a", encoding="utf-8") as fh:
                fh.write("\n===== " + time.strftime("%Y-%m-%d %H:%M:%S") + " =====\n")
                traceback.print_exception(exc_type, exc, tb, file=fh)
        except Exception:
            pass
        try:
            app.log(f"界面异常：{exc}")
        except Exception:
            pass

    root.report_callback_exception = report_exception
    app = App(root)
    root.mainloop()


def main() -> None:
    run()
