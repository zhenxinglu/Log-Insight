import sys
import re
import os
import json
import time
import pyperclip
import io
from datetime import datetime
from typing import List, Pattern, Optional, Any, Dict, Tuple, Union
from threading import Thread, Event
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QScrollBar, QFrame, QGroupBox,
                             QPushButton, QCheckBox, QFileDialog, QMessageBox, QMenu,
                             QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent, QObject, QTimer
from PyQt6.QtGui import QFont, QAction, QWheelEvent, QIcon, QPixmap, QImage, QContextMenuEvent


class LogInsight(QMainWindow):
    # 配置文件路径
    CONFIG_FILE: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    def __init__(self) -> None:
        super().__init__()
        
        # 设置窗口标题和大小
        self.setWindowTitle("Log Insight")
        
        # 初始化变量
        self.log_content: List[str] = []
        self.current_file: Optional[str] = None
        self.last_file_size: int = 0
        self.tail_stop_event: Event = Event()
        self.tail_thread: Optional[Thread] = None
        self.current_font_size: int = 10
        
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建UI组件
        self.setup_ui()
        
        # 加载上次的配置
        self.load_config()
    
    def setup_ui(self) -> None:
        # 创建过滤器框架
        self.filter_group = QGroupBox("过滤器")
        self.main_layout.addWidget(self.filter_group)
        
        self.filter_layout = QGridLayout(self.filter_group)
        
        # 包含关键字
        self.filter_layout.addWidget(QLabel("包含关键字:"), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.include_entry = QLineEdit()
        self.include_entry.setPlaceholderText("keyword1 \"multiple words keywords\" keyword3")
        self.filter_layout.addWidget(self.include_entry, 0, 1)
        
        # 包含关键字大小写敏感开关
        self.include_case_frame = QWidget()
        self.include_case_layout = QHBoxLayout(self.include_case_frame)
        self.include_case_layout.setContentsMargins(0, 0, 0, 0)
        
        self.include_case_sensitive = QCheckBox("大小写敏感")
        self.include_case_layout.addWidget(self.include_case_sensitive)
        self.filter_layout.addWidget(self.include_case_frame, 0, 2)
        
        # 排除关键字
        self.filter_layout.addWidget(QLabel("排除关键字:"), 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.exclude_entry = QLineEdit()
        self.exclude_entry.setPlaceholderText("keyword1 \"multiple words keywords\" keyword3")
        self.filter_layout.addWidget(self.exclude_entry, 1, 1)
        
        # 排除关键字大小写敏感开关
        self.exclude_case_frame = QWidget()
        self.exclude_case_layout = QHBoxLayout(self.exclude_case_frame)
        self.exclude_case_layout.setContentsMargins(0, 0, 0, 0)
        
        self.exclude_case_sensitive = QCheckBox("大小写敏感")
        self.exclude_case_layout.addWidget(self.exclude_case_sensitive)
        self.filter_layout.addWidget(self.exclude_case_frame, 1, 2)
        
        # 时间范围
        self.filter_layout.addWidget(QLabel("时间范围:"), 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.time_frame = QWidget()
        self.time_layout = QHBoxLayout(self.time_frame)
        self.time_layout.setContentsMargins(0, 0, 0, 0)
        
        self.start_time_entry = QLineEdit()
        self.start_time_entry.setPlaceholderText("00:00:00.000")
        self.time_layout.addWidget(self.start_time_entry)
        
        self.time_layout.addWidget(QLabel("至"))
        
        self.end_time_entry = QLineEdit()
        self.end_time_entry.setPlaceholderText("23:59:59.999")
        self.time_layout.addWidget(self.end_time_entry)
        
        self.filter_layout.addWidget(self.time_frame, 2, 1)
        
        # 按钮框架
        self.button_frame = QWidget()
        self.button_layout = QHBoxLayout(self.button_frame)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_button = QPushButton("过滤日志")
        self.search_button.clicked.connect(self.search_log)
        self.button_layout.addWidget(self.search_button)
        
        self.tail_log_check = QCheckBox("Tail Log")
        self.tail_log_check.stateChanged.connect(self.toggle_tail_log)
        self.button_layout.addWidget(self.tail_log_check)
        
        self.word_wrap_check = QCheckBox("Word Wrap")
        self.word_wrap_check.setChecked(True)
        self.word_wrap_check.stateChanged.connect(self.toggle_word_wrap)
        self.button_layout.addWidget(self.word_wrap_check)
        
        self.button_layout.addStretch()
        
        self.open_button = QPushButton("打开日志文件")
        self.open_button.clicked.connect(self.open_log_file)
        self.button_layout.addWidget(self.open_button)
        
        self.main_layout.addWidget(self.button_frame)
        
        # 结果显示区域
        self.result_group = QGroupBox("搜索结果")
        self.result_layout = QVBoxLayout(self.result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 默认启用自动换行
        self.result_text.setFont(QFont("Consolas", self.current_font_size))
        self.result_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_text.customContextMenuRequested.connect(self.show_context_menu)
        self.result_text.wheelEvent = self.on_mouse_wheel  # 重写滚轮事件
        
        self.result_layout.addWidget(self.result_text)
        self.main_layout.addWidget(self.result_group, 1)  # 添加拉伸因子，使结果区域占据更多空间
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def open_log_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择日志文件",
            "",
            "日志文件 (*.log);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    self.log_content = file.readlines()
                
                self.current_file = file_path
                self.statusBar().showMessage(f"已加载文件: {os.path.basename(file_path)} - {len(self.log_content)} 行")
                self.clear_results()
                # 更新窗口标题显示文件路径
                self.setWindowTitle(f"LogInsight - {file_path}")
                
                # 在结果区域显示日志内容
                self.result_text.setText("".join(self.log_content))
                
                # 保存当前配置
                self.save_config()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
    
    def search_log(self) -> None:
        if not self.log_content:
            QMessageBox.warning(self, "警告", "请先打开日志文件")
            return
        
        # 解析包含关键字
        include_input: str = self.include_entry.text().strip()
        include_terms: List[str] = self.parse_keywords(include_input)
        
        # 解析排除关键字
        exclude_input: str = self.exclude_entry.text().strip()
        exclude_terms: List[str] = self.parse_keywords(exclude_input)
        
        start_time: str = self.start_time_entry.text().strip()
        end_time: str = self.end_time_entry.text().strip()
        
        # 保存当前搜索条件
        self.save_config()
        self.clear_results()
        
        # 根据大小写敏感设置编译正则表达式
        include_case_sensitive: bool = self.include_case_sensitive.isChecked()
        exclude_case_sensitive: bool = self.exclude_case_sensitive.isChecked()
        
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
                QMessageBox.warning(self, "警告", f"开始时间格式无效，请使用格式: {time_format}")
                return
        
        if end_time:
            try:
                end_datetime = datetime.strptime(end_time, time_format)
                use_time_filter = True
            except ValueError:
                QMessageBox.warning(self, "警告", f"结束时间格式无效，请使用格式: {time_format}")
                return
        
        # 时间正则表达式 (匹配行首 HH:MM:SS.XXX)
        time_pattern: Pattern = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3})')
        
        match_count: int = 0
        result_text = ""
        
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
            result_text += line
            match_count += 1
        
        if match_count == 0:
            self.result_text.setText("没有找到匹配的结果。\n")
        else:
            self.result_text.setText(result_text)
        
        self.statusBar().showMessage(f"找到 {match_count} 个匹配结果")
    
    def clear_results(self) -> None:
        self.result_text.clear()
    
    def show_context_menu(self, position) -> None:
        context_menu = QMenu()
        copy_action = context_menu.addAction("复制")
        select_all_action = context_menu.addAction("全选")
        copy_all_action = context_menu.addAction("复制全部")
        
        action = context_menu.exec(self.result_text.mapToGlobal(position))
        
        if action == copy_action:
            self.copy_selection()
        elif action == select_all_action:
            self.select_all()
        elif action == copy_all_action:
            self.copy_all()
    
    def copy_selection(self) -> None:
        self.result_text.copy()
        self.statusBar().showMessage("已复制选中内容到剪贴板")
    
    def select_all(self) -> None:
        self.result_text.selectAll()
    
    def copy_all(self) -> None:
        cursor = self.result_text.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.result_text.setTextCursor(cursor)
        self.result_text.copy()
        self.statusBar().showMessage("已复制全部内容到剪贴板")
    
    def on_mouse_wheel(self, event: QWheelEvent) -> None:
        """处理鼠标滚轮事件，支持Ctrl+滚轮调整字体大小和普通滚轮滚动文本
        
        Args:
            event: 鼠标事件对象
        """
        # 检查是否按下了Ctrl键
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                # 增大字体
                self.current_font_size = min(36, self.current_font_size + 1)  # 设置最大字体大小为36
            else:
                # 减小字体
                self.current_font_size = max(6, self.current_font_size - 1)  # 设置最小字体大小为6
            
            # 更新文本框字体
            font = self.result_text.font()
            font.setPointSize(self.current_font_size)
            self.result_text.setFont(font)
            
            # 更新状态栏
            self.statusBar().showMessage(f"字体大小: {self.current_font_size}")
            
            # 阻止事件继续传播
            event.accept()
        else:
            # 如果没有按下Ctrl键，则调用QTextEdit原生的wheelEvent方法处理正常滚动
            QTextEdit.wheelEvent(self.result_text, event)
    
    def toggle_word_wrap(self, state: int) -> None:
        """切换自动换行
        
        Args:
            state: 复选框状态
        """
        if state == Qt.CheckState.Checked.value:
            self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        else:
            self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    
    def toggle_tail_log(self, state: int) -> None:
        """切换日志跟踪模式
        
        Args:
            state: 复选框状态
        """
        if state == Qt.CheckState.Checked.value:
            if self.current_file and os.path.exists(self.current_file):
                self.tail_stop_event.clear()
                self.tail_thread = Thread(target=self.tail_file, daemon=True)
                self.tail_thread.start()
                self.statusBar().showMessage("已启动日志跟踪模式")
            else:
                self.tail_log_check.setChecked(False)
                QMessageBox.warning(self, "警告", "请先打开日志文件")
        else:
            if self.tail_thread and self.tail_thread.is_alive():
                self.tail_stop_event.set()
                self.tail_thread.join(1.0)  # 等待线程结束，最多等待1秒
                self.statusBar().showMessage("已停止日志跟踪模式")
    
    def tail_file(self) -> None:
        """跟踪日志文件变化"""
        if not self.current_file:
            return
            
        try:
            self.last_file_size = os.path.getsize(self.current_file)
            
            while not self.tail_stop_event.is_set():
                if os.path.exists(self.current_file):
                    current_size = os.path.getsize(self.current_file)
                    
                    if current_size > self.last_file_size:
                        with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as file:
                            file.seek(self.last_file_size)
                            new_content = file.read()
                            
                        self.last_file_size = current_size
                        
                        # 更新UI（在主线程中）
                        QApplication.instance().postEvent(self, TailLogEvent(new_content))
                
                time.sleep(1.0)  # 每秒检查一次文件变化
        except Exception as e:
            print(f"Tail log error: {str(e)}")
    
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
        config = {
            "include_keywords": self.include_entry.text(),
            "exclude_keywords": self.exclude_entry.text(),
            "start_time": self.start_time_entry.text(),
            "end_time": self.end_time_entry.text(),
            "include_case_sensitive": self.include_case_sensitive.isChecked(),
            "exclude_case_sensitive": self.exclude_case_sensitive.isChecked(),
            "word_wrap": self.word_wrap_check.isChecked(),
            "font_size": self.current_font_size,
            "last_file": self.current_file if self.current_file else ""
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.statusBar().showMessage(f"保存配置失败: {str(e)}")
    
    def load_config(self) -> None:
        """从配置文件加载配置"""
        if not os.path.exists(self.CONFIG_FILE):
            return
            
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # 恢复搜索条件
            if "include_keywords" in config and config["include_keywords"]:
                self.include_entry.setText(config["include_keywords"])
                
            if "exclude_keywords" in config and config["exclude_keywords"]:
                self.exclude_entry.setText(config["exclude_keywords"])
                
            if "start_time" in config and config["start_time"]:
                self.start_time_entry.setText(config["start_time"])
                
            if "end_time" in config and config["end_time"]:
                self.end_time_entry.setText(config["end_time"])
                
            # 恢复大小写敏感设置
            if "include_case_sensitive" in config:
                self.include_case_sensitive.setChecked(config["include_case_sensitive"])
                
            if "exclude_case_sensitive" in config:
                self.exclude_case_sensitive.setChecked(config["exclude_case_sensitive"])
                
            # 恢复自动换行设置
            if "word_wrap" in config:
                self.word_wrap_check.setChecked(config["word_wrap"])
                self.toggle_word_wrap(Qt.CheckState.Checked.value if config["word_wrap"] else Qt.CheckState.Unchecked.value)
                
            # 恢复字体大小
            if "font_size" in config:
                self.current_font_size = config["font_size"]
                font = self.result_text.font()
                font.setPointSize(self.current_font_size)
                self.result_text.setFont(font)
                
            # 恢复上次打开的文件
            if "last_file" in config and config["last_file"] and os.path.exists(config["last_file"]):
                self.current_file = config["last_file"]
                with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as file:
                    self.log_content = file.readlines()
                
                self.statusBar().showMessage(f"已加载文件: {os.path.basename(self.current_file)} - {len(self.log_content)} 行")
                self.setWindowTitle(f"LogInsight - {self.current_file}")
                self.result_text.setText("".join(self.log_content))
                
        except Exception as e:
            self.statusBar().showMessage(f"加载配置失败: {str(e)}")


# 自定义事件类型，用于在线程间通信
class TailLogEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, content: str):
        super().__init__(self.EVENT_TYPE)
        self.content = content


# 重写事件处理方法，处理自定义事件
def event(self, event: QEvent) -> bool:
    if event.type() == TailLogEvent.EVENT_TYPE:
        # 追加新内容到结果文本框
        self.result_text.append(event.content)
        # 滚动到底部
        self.result_text.verticalScrollBar().setValue(self.result_text.verticalScrollBar().maximum())
        return True
    return super(LogInsight, self).event(event)


# 添加事件处理方法到类
LogInsight.event = event


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogInsight()
    window.show()  # 先显示窗口
    window.showMaximized()  # 然后最大化窗口
    sys.exit(app.exec())