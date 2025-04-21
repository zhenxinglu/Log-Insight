import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from datetime import datetime
import pyperclip
import os
import json
from typing import List, Pattern, Optional, Any, Dict

class LogInsight:
    # 配置文件路径
    CONFIG_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("LogInsight")
        self.root.geometry("1000x600")
        
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
        self.include_entry: ttk.Entry = ttk.Entry(self.filter_frame, textvariable=self.include_var, width=80)
        self.include_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        # 添加占位文本
        self.include_entry.insert(0, "keyword1 \"multiple words keywords\" keyword3")
        self.include_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.include_entry, self.include_var))
        self.include_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.include_entry, self.include_var, "keyword1 \"multiple words keywords\" keyword3"))
        # 设置占位文本样式
        self.set_placeholder_style(self.include_entry, True)
        
        # 包含关键字大小写敏感开关
        self.include_case_sensitive_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.include_case_sensitive_check: ttk.Checkbutton = ttk.Checkbutton(self.filter_frame, text="大小写敏感", variable=self.include_case_sensitive_var)
        self.include_case_sensitive_check.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 排除关键字
        ttk.Label(self.filter_frame, text="排除关键字:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_var: tk.StringVar = tk.StringVar()
        self.exclude_entry: ttk.Entry = ttk.Entry(self.filter_frame, textvariable=self.exclude_var, width=80)
        self.exclude_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        # 添加占位文本
        self.exclude_entry.insert(0, "keyword1 \"multiple words keywords\" keyword3")
        self.exclude_entry.bind("<FocusIn>", lambda event: self.clear_placeholder(event, self.exclude_entry, self.exclude_var))
        self.exclude_entry.bind("<FocusOut>", lambda event: self.restore_placeholder(event, self.exclude_entry, self.exclude_var, "keyword1 \"multiple words keywords\" keyword3"))
        # 设置占位文本样式
        self.set_placeholder_style(self.exclude_entry, True)
        
        # 排除关键字大小写敏感开关
        self.exclude_case_sensitive_var: tk.BooleanVar = tk.BooleanVar(value=False)
        self.exclude_case_sensitive_check: ttk.Checkbutton = ttk.Checkbutton(self.filter_frame, text="大小写敏感", variable=self.exclude_case_sensitive_var)
        self.exclude_case_sensitive_check.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
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
        
        # 结果显示区域
        self.result_frame: ttk.LabelFrame = ttk.LabelFrame(self.main_frame, text="搜索结果")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建文本框和滚动条
        self.result_text: tk.Text = tk.Text(self.result_frame, wrap=tk.WORD)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar: ttk.Scrollbar = ttk.Scrollbar(self.result_frame, command=self.result_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=self.scrollbar.set)
        
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
            "end_time": end_time
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
            if "exclude_keywords" in config and config["exclude_keywords"] and config["exclude_keywords"] != "keyword1 \"multiple words keywords\" keyword3":
                self.exclude_var.set(config["exclude_keywords"])
                self.set_placeholder_style(self.exclude_entry, False)  # 设置为正常样式
            else:
                self.set_placeholder_style(self.exclude_entry, True)  # 设置为占位文本样式
            if "exclude_case_sensitive" in config:
                self.exclude_case_sensitive_var.set(config["exclude_case_sensitive"])
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
    
    def on_closing(self) -> None:
        """窗口关闭时的处理"""
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