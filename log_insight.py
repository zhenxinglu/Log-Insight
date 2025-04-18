import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
from datetime import datetime
import pyperclip
import os

class LogInsight:
    def __init__(self, root):
        self.root = root
        self.root.title("LogInsight")
        self.root.geometry("1000x600")
        
        # 创建菜单栏
        self.menu_bar = tk.Menu(root)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="打开日志文件", command=self.open_log_file)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        root.config(menu=self.menu_bar)
        
        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 文件路径变量（用于标题栏显示）
        self.file_path_var = tk.StringVar()
        
        # 搜索框架
        self.search_frame = ttk.LabelFrame(self.main_frame, text="搜索")
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 过滤器框架
        self.filter_frame = ttk.LabelFrame(self.main_frame, text="过滤器")
        self.filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 包含关键字
        ttk.Label(self.filter_frame, text="包含关键字:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.include_var = tk.StringVar()
        self.include_entry = ttk.Entry(self.filter_frame, textvariable=self.include_var, width=80)
        self.include_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 包含关键字大小写敏感开关
        self.include_case_sensitive_var = tk.BooleanVar(value=False)
        self.include_case_sensitive_check = ttk.Checkbutton(self.filter_frame, text="大小写敏感", variable=self.include_case_sensitive_var)
        self.include_case_sensitive_check.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 排除关键字
        ttk.Label(self.filter_frame, text="排除关键字:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.exclude_var = tk.StringVar()
        self.exclude_entry = ttk.Entry(self.filter_frame, textvariable=self.exclude_var, width=80)
        self.exclude_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 排除关键字大小写敏感开关
        self.exclude_case_sensitive_var = tk.BooleanVar(value=False)
        self.exclude_case_sensitive_check = ttk.Checkbutton(self.filter_frame, text="大小写敏感", variable=self.exclude_case_sensitive_var)
        self.exclude_case_sensitive_check.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # 时间范围
        ttk.Label(self.filter_frame, text="时间范围:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.time_frame = ttk.Frame(self.filter_frame)
        self.time_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.start_time_var = tk.StringVar()
        self.start_time_entry = ttk.Entry(self.time_frame, textvariable=self.start_time_var, width=20)
        self.start_time_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(self.time_frame, text="至").pack(side=tk.LEFT, padx=5)
        
        self.end_time_var = tk.StringVar()
        self.end_time_entry = ttk.Entry(self.time_frame, textvariable=self.end_time_var, width=20)
        self.end_time_entry.pack(side=tk.LEFT, padx=5)
        
        # 按钮框架
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.open_button = ttk.Button(self.button_frame, text="打开日志文件", command=self.open_log_file)
        self.open_button.pack(side=tk.RIGHT, padx=5)
        
        self.search_button = ttk.Button(self.button_frame, text="搜索日志文件", command=self.search_log)
        self.search_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = ttk.Button(self.button_frame, text="清除结果", command=self.clear_results)
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # 结果显示区域
        self.result_frame = ttk.LabelFrame(self.main_frame, text="搜索结果")
        self.result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建文本框和滚动条
        self.result_text = tk.Text(self.result_frame, wrap=tk.WORD)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.scrollbar = ttk.Scrollbar(self.result_frame, command=self.result_text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=self.scrollbar.set)
        
        # 右键菜单
        self.context_menu = tk.Menu(self.result_text, tearoff=0)
        self.context_menu.add_command(label="复制", command=self.copy_selection)
        self.context_menu.add_command(label="全选", command=self.select_all)
        self.context_menu.add_command(label="复制全部", command=self.copy_all)
        
        self.result_text.bind("<Button-3>", self.show_context_menu)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 初始化变量
        self.log_content = []
        self.current_file = None
    
    def open_log_file(self):
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
            except Exception as e:
                messagebox.showerror("错误", f"无法打开文件: {str(e)}")
    
    def search_log(self):
        if not self.log_content:
            messagebox.showwarning("警告", "请先打开日志文件")
            return
        
        include_terms = [term.strip() for term in self.include_var.get().split(',') if term.strip()]
        exclude_terms = [term.strip() for term in self.exclude_var.get().split(',') if term.strip()]
        start_time = self.start_time_var.get().strip()
        end_time = self.end_time_var.get().strip()
        
        self.clear_results()
        
        # 根据大小写敏感设置编译正则表达式
        include_case_sensitive = self.include_case_sensitive_var.get()
        exclude_case_sensitive = self.exclude_case_sensitive_var.get()
        
        include_patterns = []
        for term in include_terms:
            if include_case_sensitive:
                include_patterns.append(re.compile(term))
            else:
                include_patterns.append(re.compile(term, re.IGNORECASE))
        
        exclude_patterns = []
        for term in exclude_terms:
            if exclude_case_sensitive:
                exclude_patterns.append(re.compile(term))
            else:
                exclude_patterns.append(re.compile(term, re.IGNORECASE))
        
        # 时间格式检查
        time_format = "%Y-%m-%d %H:%M:%S"
        use_time_filter = False
        start_datetime = None
        end_datetime = None
        
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
        
        # 时间正则表达式
        time_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
        
        match_count = 0
        for line in self.log_content:
            
            # 检查是否包含所有包含关键字
            if include_patterns and not all(pattern.search(line) for pattern in include_patterns):
                continue
            
            # 检查是否包含任何排除关键字
            if exclude_patterns and any(pattern.search(line) for pattern in exclude_patterns):
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
    
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
    
    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)
    
    def copy_selection(self):
        try:
            selected_text = self.result_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.status_var.set("已复制选中内容到剪贴板")
        except tk.TclError:
            # 没有选中文本
            pass
    
    def select_all(self):
        self.result_text.tag_add(tk.SEL, "1.0", tk.END)
        self.result_text.mark_set(tk.INSERT, "1.0")
        self.result_text.see(tk.INSERT)
        return 'break'
    
    def copy_all(self):
        all_text = self.result_text.get(1.0, tk.END)
        pyperclip.copy(all_text)
        self.status_var.set("已复制全部内容到剪贴板")

def main():
    root = tk.Tk()
    app = LogInsight(root)
    root.mainloop()

if __name__ == "__main__":
    main()