import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from datetime import datetime
import pyperclip
import os
import json
from typing import List, Pattern, Optional, Any, Dict, Tuple, Union
import time
from threading import Thread, Event
from PIL import Image, ImageTk, ImageDraw
import io

class LogInsight:
    # 配置文件路径
    CONFIG_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Log Insight")
        # self.root.geometry("1000x600")
        # 设置窗口最大化
        self.root.state("zoomed")
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 创建主框架
        self.main_frame: ttk.Frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 文件路径变量（用于标题栏显示）
        self.file_path_var: tk.StringVar = tk.StringVar()
        
        # 搜索框架
        self.search_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text="搜索")
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 过滤器框架
        self.filter_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text="过滤器")
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 包含关键字
        ttk.Label(self.filter_frame, text="包含关键字:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.include_var: tk.StringVar = tk.StringVar()
        self.include_entry: ttk.Entry = ttk.Entry(self.filter_frame, textvariable=self.include_var, width=100)
        self.include_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        # 添加占位文本
        self.include_entry.insert(0, "keyword1 \"multiple words keywords\" keyword3")
        self.include_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.include_entry, self.include_var))
        self.include_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.include_entry, self.include_var, "keyword1 \"multiple words keywords\" keyword3"))
        # 设置占位文本样式
        self.set_placeholder_style(self.include_entry, True)
        
        # 包含关键字大小写敏感开关 - SVG图标按钮
        self.include_case_sensitive_var: tk.BooleanVar = tk.BooleanVar(value=False)
        
        # 创建图标按钮框架
        self.include_case_frame: ttk.Frame = ttk.Frame(self.filter_frame)
        self.include_case_frame.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 加载SVG图标
        self.case_icons: Dict[str, Tuple[ImageTk.PhotoImage, ImageTk.PhotoImage]] = self.load_case_icons()
        
        # 不显示"大小写敏感"文本标签
        
        # 创建图标按钮
        self.include_case_btn: ttk.Label = ttk.Label(self.include_case_frame, cursor="hand2")
        self.include_case_btn.pack(side=tk.LEFT)
        
        # 设置初始图标
        self.update_case_icon(self.include_case_btn, self.include_case_sensitive_var.get())
        
        # 绑定点击事件 - 使用after方法确保事件处理在UI线程中完成
        self.include_case_btn.bind("<Button-1>", lambda event: self.root.after(10, lambda: self.toggle_case_sensitivity(event, self.include_case_sensitive_var, self.include_case_btn)))
        
        # 排除关键字
        ttk.Label(self.filter_frame, text="排除关键字:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_var: tk.StringVar = tk.StringVar()
        self.exclude_entry: ttk.Entry = ttk.Entry(self.filter_frame, textvariable=self.exclude_var, width=100)
        self.exclude_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        # 添加占位文本
        self.exclude_entry.insert(0, "keyword1 \"multiple words keywords\" keyword3")
        self.exclude_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.exclude_entry, self.exclude_var))
        self.exclude_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.exclude_entry, self.exclude_var, "keyword1 \"multiple words keywords\" keyword3"))
        # 设置占位文本样式
        self.set_placeholder_style(self.exclude_entry, True)
        
        # 排除关键字大小写敏感开关 - SVG图标按钮
        self.exclude_case_sensitive_var: tk.BooleanVar = tk.BooleanVar(value=False)
        
        # 创建图标按钮框架
        self.exclude_case_frame: ttk.Frame = ttk.Frame(self.filter_frame)
        self.exclude_case_frame.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 不显示"大小写敏感"文本标签
        
        # 创建图标按钮
        self.exclude_case_btn: tk.Label = ttk.Label(self.exclude_case_frame, cursor="hand2")
        self.exclude_case_btn.pack(side=tk.LEFT)
        
        # 设置初始图标
        self.update_case_icon(self.exclude_case_btn, self.exclude_case_sensitive_var.get())
        
        # 绑定点击事件 - 使用after方法确保事件处理在UI线程中完成
        self.exclude_case_btn.bind("<Button-1>", lambda event: self.root.after(10, lambda: self.toggle_case_sensitivity(event, self.exclude_case_sensitive_var, self.exclude_case_btn)))
        
        # 时间范围
        ttk.Label(self.filter_frame, text="时间范围:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.time_frame: ttk.Frame = ttk.Frame(self.filter_frame)
        self.time_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.start_time_var: tk.StringVar = tk.StringVar()
        self.start_time_entry: ttk.Entry = ttk.Entry(self.time_frame, textvariable=self.start_time_var, width=20)
        self.start_time_entry.pack(side=tk.LEFT, padx=5)
        # 添加占位文本
        self.start_time_entry.insert(0, "00:00:00.000")
        self.start_time_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.start_time_entry, self.start_time_var))
        self.start_time_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.start_time_entry, self.start_time_var, "00:00:00.000"))
        # 设置占位文本样式
        self.set_placeholder_style(self.start_time_entry, True)
        
        ttk.Label(self.time_frame, text="至").pack(side=tk.LEFT, padx=5)
        
        self.end_time_var: tk.StringVar = tk.StringVar()
        self.end_time_entry: ttk.Entry = ttk.Entry(self.time_frame, textvariable=self.end_time_var, width=20)
        self.end_time_entry.pack(side=tk.LEFT, padx=5)
        # 添加占位文本
        self.end_time_entry.insert(0, "23:59:59.999")
        self.end_time_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.end_time_entry, self.end_time_var))
        self.end_time_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.end_time_entry, self.end_time_var, "23:59:59.999"))
        # 设置占位文本样式
        self.set_placeholder_style(self.end_time_entry, True)
        
        # 按钮框架
        self.button_frame: ttk.Frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.open_button: ttk.Button = ttk.Button(self.button_frame, text="打开日志文件", command=self.open_log_file)
        self.open_button.pack(side=tk.RIGHT, padx=5)
        
        self.search_button: ttk.Button = ttk.Button(self.button_frame, text="过滤日志", command=self.search_log)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        # Tail Log 复选框
        self.tail_log_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.tail_log_check: ttk.Checkbutton = ttk.Checkbutton(
            self.button_frame,
            text="Tail Log",
            variable=self.tail_log_var,
            command=self.toggle_tail_log
        )
        self.tail_log_check.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text="搜索结果")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建文本框和滚动条
        self.result_text: tk.Text = tk.Text(self.result_frame, wrap=tk.WORD)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar: ttk.Scrollbar = ttk.Scrollbar(self.result_frame, command=self.result_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=self.scrollbar.set)
        
        # 初始化字体大小
        self.current_font_size: int = 10
        self.result_text.configure(font=("TkDefaultFont", self.current_font_size))
        
        # 绑定Ctrl+鼠标滚轮事件用于缩放字体
        self.result_text.bind("<Control-MouseWheel>", self.on_mouse_wheel)
        
        # 右键菜单
        self.context_menu: tk.Menu = tk.Menu(self.result_text, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_selection)
        self.context_menu.add_command(label="全选", command=self.select_all)
        self.context_menu.add_command(label="复制全部", command=self.copy_all)
        
        self.result_text.bind("<Button-3>", self.show_context_menu)
        
        # 状态栏
        self.status_var: tk.StringVar = tk.StringVar()
        self.status_var.set("就绪")
        self.status_bar: ttk.Label = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化变量
        self.log_content: List[str] = []
        self.current_file: Optional[str] = None
        self.last_file_size: int = 0
        self.tail_stop_event: Event = Event()
        self.tail_thread: Optional[Thread] = None
        
        # 加载上次的配置
        self.load_config()
    
    def open_log_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择日志文件",
            filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    self.log_content = file.readlines()
                
                self.current_file = file_path
                self.file_path_var.set(file_path)
                self.status_var.set(f"已加载文件: {os.path.basename(file_path)} - {len(self.log_content)} 行")
                self.clear_results()
                # 更新窗口标题显示文件路径
                self.root.title(f"LogInsight - {file_path}")
                
                # 在结果区域显示日志内容
                for line in self.log_content:
                    self.result_text.insert(tk.END, line)
                
                # 保存当前配置
                self.save_config()
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def search_log(self) -> None:
        if not self.log_content:
            messagebox.showwarning("警告", "请先打开日志文件")
            return
        # 解析包含关键字（使用空格分隔，支持引号包含空格的关键字）
        include_input: str = self.include_var.get().strip()
        # 检查是否是占位文本
        if include_input == "keyword1 \"multiple words keywords\" keyword3":
            include_input = ""
        include_terms: List[str] = self.parse_keywords(include_input)
        # 解析排除关键字（使用空格分隔，支持引号包含空格的关键字）
        exclude_input: str = self.exclude_var.get().strip()
        # 检查是否是占位文本
        if exclude_input == "keyword1 \"multiple words keywords\" keyword3":
            exclude_input = ""
        exclude_terms: List[str] = self.parse_keywords(exclude_input)
        start_time: str = self.start_time_var.get().strip()
        # 检查是否是占位文本
        if start_time == "00:00:00.000":
            start_time = ""
        end_time: str = self.end_time_var.get().strip()
        # 检查是否是占位文本
        if end_time == "23:59:59.999":
            end_time = ""
        # 保存当前搜索条件
        self.save_config()
        self.clear_results()
        # 根据大小写敏感设置编译正则表达式
        include_case_sensitive: bool = self.include_case_sensitive_var.get()
        exclude_case_sensitive: bool = self.exclude_case_sensitive_var.get()
        
        include_patterns: List[Pattern] = []
        for term in include_terms:
            # 将关键字作为普通字符串处理，而不是正则表达式
            escaped_term = re.escape(term)
            if include_case_sensitive:
                include_patterns.append(re.compile(escaped_term))
            else:
                include_patterns.append(re.compile(escaped_term, re.IGNORECASE))
        
        exclude_patterns: List[Pattern] = []
        for term in exclude_terms:
            # 将关键字作为普通字符串处理，而不是正则表达式
            escaped_term = re.escape(term)
            if exclude_case_sensitive:
                exclude_patterns.append(re.compile(escaped_term))
            else:
                exclude_patterns.append(re.compile(escaped_term, re.IGNORECASE))
        
        # 时间格式检查
        time_format: str = "%H:%M:%S.%f"
        use_time_filter: bool = False
        start_datetime: Optional[datetime] = None
        end_datetime: Optional[datetime] = None
        
        if start_time:
            try:
                start_datetime = datetime.strptime(start_time, time_format)
                use_time_filter = True
            except ValueError:
                messagebox.showwarning("警告", f"开始时间格式无效，请使用格式: {time_format}")
                return
        
        if end_time:
            try:
                end_datetime = datetime.strptime(end_time, time_format)
                use_time_filter = True
            except ValueError:
                messagebox.showwarning("警告", f"结束时间格式无效，请使用格式: {time_format}")
                return
        
        # 时间正则表达式 (匹配行首 HH:MM:SS.XXX)
        time_pattern: Pattern = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3})')
        
        match_count: int = 0
        for line in self.log_content:
            
            # 检查是否包含任何排除关键字（优先级高）
            if exclude_patterns and any(pattern.search(line) for pattern in exclude_patterns):
                continue
            
            # 检查是否包含至少一个包含关键字
            if include_patterns and not any(pattern.search(line) for pattern in include_patterns):
                continue
            
            # 时间过滤
            if use_time_filter:
                time_match = time_pattern.search(line)
                if time_match:
                    line_time_str = time_match.group(1)
                    try:
                        line_time = datetime.strptime(line_time_str, time_format)
                        
                        # 检查时间范围
                        if start_datetime and line_time < start_datetime:
                            continue
                        if end_datetime and line_time > end_datetime:
                            continue
                    except ValueError:
                        # 如果时间解析失败，跳过时间过滤
                        pass
                elif start_datetime or end_datetime:
                    # 如果需要时间过滤但找不到时间，则跳过该行
                    continue
            
            # 添加匹配行到结果
            self.result_text.insert(tk.END, line)
            match_count += 1
        
        if match_count == 0:
            self.result_text.insert(tk.END, "没有找到匹配的结果。\n")
        
        self.status_var.set(f"找到 {match_count} 个匹配结果")
    
    def clear_results(self) -> None:
        self.result_text.delete(1.0, tk.END)
    
    def show_context_menu(self, event: tk.Event) -> None:
        self.context_menu.post(event.x_root, event.y_root)
    
    def copy_selection(self) -> None:
        try:
            selected_text: str = self.result_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_var.set("已复制选中内容到剪贴板")
        except tk.TclError:
            # 没有选中文本
            pass
    
    def select_all(self) -> str:
        self.result_text.tag_add(tk.SEL, "1.0", tk.END)
        self.result_text.mark_set(tk.INSERT, "1.0")
        self.result_text.see(tk.INSERT)
        return 'break'
    
    def copy_all(self) -> None:
        all_text: str = self.result_text.get(1.0, tk.END)
        pyperclip.copy(all_text)
        self.status_var.set("已复制全部内容到剪贴板")
        
    def on_mouse_wheel(self, event: tk.Event) -> None:
        """处理Ctrl+鼠标滚轮事件，调整字体大小
        
        Args:
            event: 鼠标事件对象
        """
        # 在Windows上，event.delta为正表示向上滚动，为负表示向下滚动
        # 向上滚动增大字体，向下滚动减小字体
        if event.delta > 0:
            # 增大字体
            self.current_font_size = min(36, self.current_font_size + 1)  # 设置最大字体大小为36
        else:
            # 减小字体
            self.current_font_size = max(6, self.current_font_size - 1)  # 设置最小字体大小为6
        
        # 更新文本框字体
        self.result_text.configure(font=("TkDefaultFont", self.current_font_size))
        
        # 更新状态栏
        self.status_var.set(f"字体大小: {self.current_font_size}")
        
        # 阻止事件继续传播（防止默认的滚动行为）
        return "break"
        
    def parse_keywords(self, input_str: str) -> List[str]:
        """解析关键字，支持空格分隔和引号包含空格的关键字
        
        Args:
            input_str: 输入的关键字字符串
            
        Returns:
            解析后的关键字列表
        """
        if not input_str:
            return []
            
        keywords: List[str] = []
        # 正则表达式匹配：引号内的内容作为一个关键字，或者非空格字符序列作为关键字
        pattern: Pattern = re.compile(r'"([^"]*)"|\S+')
        
        matches = pattern.finditer(input_str)
        for match in matches:
            # 如果是引号内的内容，group(1)会有值
            if match.group(1) is not None:
                keywords.append(match.group(1))
            else:
                # 否则使用完整匹配
                keywords.append(match.group(0))
                
        return [keyword.strip() for keyword in keywords if keyword.strip()]

    def save_config(self) -> None:
        """保存当前配置到配置文件"""
        # 获取当前值，但不保存占位文本
        include_keywords = self.include_var.get()
        if include_keywords == "keyword1 \"multiple words keywords\" keyword3":
            include_keywords = ""
            
        exclude_keywords = self.exclude_var.get()
        if exclude_keywords == "keyword1 \"multiple words keywords\" keyword3":
            exclude_keywords = ""
            
        start_time = self.start_time_var.get()
        if start_time == "2023-01-01 00:00:00":
            start_time = ""
            
        end_time = self.end_time_var.get()
        if end_time == "2023-12-31 23:59:59":
            end_time = ""
        
        config: Dict[str, Any] = {
            "current_file": self.current_file,
            "include_keywords": include_keywords,
            "include_case_sensitive": self.include_case_sensitive_var.get(),
            "exclude_keywords": exclude_keywords,
            "exclude_case_sensitive": self.exclude_case_sensitive_var.get(),
            "start_time": start_time,
            "end_time": end_time,
            "font_size": self.current_font_size
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            self.status_var.set("配置已保存")
        except Exception as e:
            self.status_var.set(f"保存配置失败: {str(e)}")
    
    def load_config(self) -> None:
        """从配置文件加载上次的配置"""
        if not os.path.exists(self.CONFIG_FILE):
            self.status_var.set("没有找到配置文件，使用默认设置")
            return
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 恢复上次的设置
            if "include_keywords" in config and config["include_keywords"] and config["include_keywords"] != "keyword1 \"multiple words keywords\" keyword3":
                self.include_var.set(config["include_keywords"])
                self.set_placeholder_style(self.include_entry, False)  # 设置为正常样式
            else:
                self.set_placeholder_style(self.include_entry, True)  # 设置为占位文本样式
            if "include_case_sensitive" in config:
                self.include_case_sensitive_var.set(config["include_case_sensitive"])
                # 更新包含关键字大小写敏感图标状态
                self.update_case_icon(self.include_case_btn, self.include_case_sensitive_var.get())
            if "exclude_keywords" in config and config["exclude_keywords"] and config["exclude_keywords"] != "keyword1 \"multiple words keywords\" keyword3":
                self.exclude_var.set(config["exclude_keywords"])
                self.set_placeholder_style(self.exclude_entry, False)  # 设置为正常样式
            else:
                self.set_placeholder_style(self.exclude_entry, True)  # 设置为占位文本样式
            if "exclude_case_sensitive" in config:
                self.exclude_case_sensitive_var.set(config["exclude_case_sensitive"])
                # 更新排除关键字大小写敏感图标状态
                self.update_case_icon(self.exclude_case_btn, self.exclude_case_sensitive_var.get())
            if "start_time" in config and config["start_time"] and config["start_time"] != "2023-01-01 00:00:00":
                self.start_time_var.set(config["start_time"])
                self.set_placeholder_style(self.start_time_entry, False)  # 设置为正常样式
            else:
                self.set_placeholder_style(self.start_time_entry, True)  # 设置为占位文本样式
            if "end_time" in config and config["end_time"] and config["end_time"] != "2023-12-31 23:59:59":
                self.end_time_var.set(config["end_time"])
                self.set_placeholder_style(self.end_time_entry, False)  # 设置为正常样式
            else:
                self.set_placeholder_style(self.end_time_entry, True)  # 设置为占位文本样式
            
            # 加载字体大小设置
            if "font_size" in config and isinstance(config["font_size"], int):
                self.current_font_size = config["font_size"]
                self.result_text.configure(font=("TkDefaultFont", self.current_font_size))
            
            # 如果有上次打开的文件，自动打开它
            if "current_file" in config and config["current_file"] and os.path.exists(config["current_file"]):
                self.current_file = config["current_file"]
                try:
                    with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as file:
                        self.log_content = file.readlines()
                    
                    self.file_path_var.set(self.current_file)
                    self.status_var.set(f"已加载文件: {os.path.basename(self.current_file)} - {len(self.log_content)} 行")
                    self.clear_results()
                    # 更新窗口标题显示文件路径
                    self.root.title(f"LogInsight - {self.current_file}")
                    
                    # 在结果区域显示日志内容
                    for line in self.log_content:
                        self.result_text.insert(tk.END, line)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开上次的文件: {str(e)}")
            
            self.status_var.set("已加载上次的配置")
        except Exception as e:
            self.status_var.set(f"加载配置失败: {str(e)}")
    
    def set_placeholder_style(self, entry: ttk.Entry, is_placeholder: bool) -> None:
        """设置占位文本的样式
        
        Args:
            entry: 输入框对象
            is_placeholder: 是否是占位文本
        """
        style = ttk.Style()
        if is_placeholder:
            # 设置为灰色斜体
            style.configure("Placeholder.TEntry", foreground="gray", font=("", 9, "italic"))
            entry.configure(style="Placeholder.TEntry")
        else:
            # 恢复正常样式
            style.configure("TEntry", foreground="black", font=("", 9, "normal"))
            entry.configure(style="TEntry")
    
    def load_case_icons(self) -> Dict[str, Tuple[ImageTk.PhotoImage, ImageTk.PhotoImage]]:
        """加载大小写敏感图标
        
        Returns:
            包含图标的字典
        """
        icons = {}
        
        # 定义图标的标准大小 - 增加图标尺寸以便更容易看到
        icon_size = (24, 24)  # 从16x16增加到24x24
        
        try:
            # 从文件系统加载JPG图像
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "case_sensitive_icon.jpg")
            if os.path.exists(icon_path):
                # 加载图像
                img = Image.open(icon_path)
                
                # 调整图像大小到标准尺寸
                img = img.resize(icon_size, Image.LANCZOS)
                
                # 创建两个图标 - 一个用于关闭状态，一个用于激活状态
                # 为了区分状态，我们可以调整亮度或颜色
                img_off = img.copy()
                img_on = img.copy().convert('RGBA')
                
                # 为激活状态添加更深的蓝色色调，增加透明度以提高对比度
                overlay = Image.new('RGBA', img_on.size, (0, 80, 180, 120))  # 更深的蓝色，更高的透明度
                img_on = Image.alpha_composite(img_on, overlay)
                
                # 转换为PhotoImage
                off_image = ImageTk.PhotoImage(img_off)
                on_image = ImageTk.PhotoImage(img_on)
                
                icons["case"] = (off_image, on_image)
            else:
                raise FileNotFoundError(f"图标文件不存在: {icon_path}")
            
        except Exception as e:
            print(f"加载图标失败: {str(e)}")
            # 创建一个空白图标作为最后的备用
            try:
                # 尝试使用PIL创建空白图标
                img_off = Image.new('RGBA', icon_size, (240, 240, 240, 0))
                img_on = Image.new('RGBA', icon_size, (240, 240, 240, 0))
                
                # 在空白图标上添加简单文本
                draw_off = ImageDraw.Draw(img_off)
                draw_on = ImageDraw.Draw(img_on)
                
                # 调整文本位置以适应较大的图标，并增加字体大小
                draw_off.text((5, 5), "aa", fill=(100, 100, 100))
                draw_on.text((5, 5), "Aa", fill=(0, 80, 180))  # 使用更深的蓝色
                
                icons["case"] = (ImageTk.PhotoImage(img_off), ImageTk.PhotoImage(img_on))
            except Exception:
                # 如果PIL也失败，使用最基本的tkinter图标
                blank = tk.PhotoImage(width=icon_size[0], height=icon_size[1])
                icons["case"] = (blank, blank)
        
        return icons
    
    
    def update_case_icon(self, label: Union[tk.Label, ttk.Label], is_active: bool) -> None:
        """更新大小写敏感图标
        
        Args:
            label: 标签对象
            is_active: 是否激活
        """
        if is_active:
            label.configure(image=self.case_icons["case"][1])
        else:
            label.configure(image=self.case_icons["case"][0])
    
    def toggle_case_sensitivity(self, event: tk.Event, var: tk.BooleanVar, label: Union[tk.Label, ttk.Label]) -> None:
        """切换大小写敏感状态
        
        Args:
            event: 事件对象
            var: 布尔变量
            label: 标签对象
        """
        try:
            print(f"Toggle case sensitivity: {label}, {event}")
            # 获取当前值并切换状态
            current_value = var.get()
            new_value = not current_value
            var.set(new_value)
            
            # 确保图标更新
            if isinstance(label, ttk.Label):
                # 对于ttk.Label，需要特别处理
                if new_value:
                    label.configure(image=self.case_icons["case"][1])
                else:
                    label.configure(image=self.case_icons["case"][0])
            else:
                # 使用通用方法更新图标
                self.update_case_icon(label, new_value)
            
            # 强制更新UI
            label.update()
            self.root.update_idletasks()
            
            # 更新状态栏提示
            self.status_var.set(f"大小写敏感: {'开启' if new_value else '关闭'}")
            
            # 打印调试信息
            print(f"Toggle case sensitivity: {current_value} -> {new_value}, Widget: {label}")
        except Exception as e:
            print(f"Error in toggle_case_sensitivity: {str(e)}")
            # 确保异常不会影响用户体验
            self.status_var.set(f"切换大小写敏感状态时出错: {str(e)}")
    
    def clear_placeholder(self, event: tk.Event, entry: ttk.Entry, var: tk.StringVar) -> None:
        """当输入框获得焦点时清除占位文本
        
        Args:
            event: 事件对象
            entry: 输入框对象
            var: 输入框关联的变量
        """
        current_value = var.get()
        if not current_value or current_value in ["keyword1 \"multiple words keywords\" keyword3", "2023-01-01 00:00:00", "2023-12-31 23:59:59"]:
            var.set("")
            # 恢复正常样式
            self.set_placeholder_style(entry, False)
            
    def restore_placeholder(self, event: tk.Event, entry: ttk.Entry, var: tk.StringVar, placeholder: str) -> None:
        """当输入框失去焦点且为空时恢复占位文本
        
        Args:
            event: 事件对象
            entry: 输入框对象
            var: 输入框关联的变量
            placeholder: 占位文本
        """
        current_value = var.get().strip()
        if not current_value:
            var.set(placeholder)
            # 设置为占位文本样式（灰色斜体）
            self.set_placeholder_style(entry, True)
    
    def extract_time(self, line: str) -> Optional[str]:
        # 匹配格式为 HH:mm:ss.XXX 的时间
        match = re.search(r"(\d{2}:\d{2}:\d{2}\.\d{3})", line)
        if match:
            return match.group(1)
        return None
    
    def time_in_range(self, time_str: str, start: str, end: str) -> bool:
        # 只比较 HH:mm:ss.XXX
        try:
            time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")
            if start:
                start_obj = datetime.strptime(start, "%H:%M:%S.%f")
                if time_obj < start_obj:
                    return False
            if end:
                end_obj = datetime.strptime(end, "%H:%M:%S.%f")
                if time_obj > end_obj:
                    return False
            return True
        except Exception:
            return False
    
    def toggle_tail_log(self) -> None:
        """切换Tail Log状态"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开日志文件")
            self.tail_log_var.set(False)
            return
            
        if self.tail_log_var.get():
            # 启动文件监控
            self.tail_stop_event.clear()
            self.tail_thread = Thread(target=self.monitor_file, daemon=True)
            self.tail_thread.start()
            self.status_var.set("Tail Log 已启动")
        else:
            # 停止文件监控
            if self.tail_thread and self.tail_thread.is_alive():
                self.tail_stop_event.set()
                self.tail_thread.join()
            self.status_var.set("Tail Log 已停止")
    
    def monitor_file(self) -> None:
        """监控文件变化"""
        try:
            self.last_file_size = os.path.getsize(self.current_file)
            
            while not self.tail_stop_event.is_set():
                try:
                    current_size = os.path.getsize(self.current_file)
                    
                    if current_size > self.last_file_size:
                        # 读取新增的内容
                        with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as file:
                            file.seek(self.last_file_size)
                            new_content = file.readlines()
                            
                        # 在主线程中更新UI
                        self.root.after(0, self.update_content, new_content)
                        self.last_file_size = current_size
                    
                    time.sleep(1)  # 每秒检查一次文件变化
                    
                except FileNotFoundError:
                    self.root.after(0, self.handle_file_error, "文件已被删除或移动")
                    break
                except PermissionError:
                    self.root.after(0, self.handle_file_error, "无法访问文件")
                    break
                except Exception as e:
                    self.root.after(0, self.handle_file_error, f"监控文件时出错: {str(e)}")
                    break
                    
        except Exception as e:
            self.root.after(0, self.handle_file_error, f"启动文件监控时出错: {str(e)}")
    
    def update_content(self, new_content: List[str]) -> None:
        """更新显示内容"""
        # 应用当前的过滤条件
        for line in new_content:
            # 检查是否包含任何排除关键字（优先级高）
            if any(pattern.search(line) for pattern in self.get_exclude_patterns()):
                continue
            
            # 检查是否包含至少一个包含关键字
            include_patterns = self.get_include_patterns()
            if include_patterns and not any(pattern.search(line) for pattern in include_patterns):
                continue
            
            # 检查时间范围
            if not self.check_time_range(line):
                continue
            
            # 添加匹配的行
            self.result_text.insert(tk.END, line)
            self.result_text.see(tk.END)  # 滚动到最新内容
    
    def get_include_patterns(self) -> List[Pattern]:
        """获取包含关键字的正则表达式模式"""
        include_input = self.include_var.get().strip()
        if include_input == "keyword1 \"multiple words keywords\" keyword3":
            return []
        
        include_terms = self.parse_keywords(include_input)
        include_case_sensitive = self.include_case_sensitive_var.get()
        
        patterns = []
        for term in include_terms:
            escaped_term = re.escape(term)
            if include_case_sensitive:
                patterns.append(re.compile(escaped_term))
            else:
                patterns.append(re.compile(escaped_term, re.IGNORECASE))
        return patterns
    
    def get_exclude_patterns(self) -> List[Pattern]:
        """获取排除关键字的正则表达式模式"""
        exclude_input = self.exclude_var.get().strip()
        if exclude_input == "keyword1 \"multiple words keywords\" keyword3":
            return []
        
        exclude_terms = self.parse_keywords(exclude_input)
        exclude_case_sensitive = self.exclude_case_sensitive_var.get()
        
        patterns = []
        for term in exclude_terms:
            escaped_term = re.escape(term)
            if exclude_case_sensitive:
                patterns.append(re.compile(escaped_term))
            else:
                patterns.append(re.compile(escaped_term, re.IGNORECASE))
        return patterns
    
    def check_time_range(self, line: str) -> bool:
        """检查行是否在指定的时间范围内"""
        start_time = self.start_time_var.get().strip()
        if start_time == "00:00:00.000":
            start_time = ""
            
        end_time = self.end_time_var.get().strip()
        if end_time == "23:59:59.999":
            end_time = ""
        
        if not (start_time or end_time):
            return True
        
        time_match = re.search(r'^(\d{2}:\d{2}:\d{2}\.\d{3})', line)
        if not time_match:
            return False
            
        try:
            line_time = datetime.strptime(time_match.group(1), "%H:%M:%S.%f")
            
            if start_time:
                start_datetime = datetime.strptime(start_time, "%H:%M:%S.%f")
                if line_time < start_datetime:
                    return False
                    
            if end_time:
                end_datetime = datetime.strptime(end_time, "%H:%M:%S.%f")
                if line_time > end_datetime:
                    return False
                    
            return True
        except ValueError:
            return False
    
    def handle_file_error(self, error_message: str) -> None:
        """处理文件监控错误"""
        self.tail_log_var.set(False)
        self.status_var.set(error_message)
        messagebox.showerror("错误", error_message)
    
    def on_closing(self) -> None:
        """窗口关闭时的处理"""
        # 停止文件监控
        self.tail_log_var.set(False)
        self.toggle_tail_log()
        
        # 保存当前配置
        self.save_config()
        # 关闭窗口
        self.root.destroy()

def main() -> None:
    root: tk.Tk = tk.Tk()
    app: LogInsight = LogInsight(root)
    root.mainloop()

if __name__ == "__main__":
    main()