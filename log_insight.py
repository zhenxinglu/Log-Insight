import sys
import re
import os
import json
import time
import pyperclip
from datetime import datetime
from typing import List, Pattern, Optional, Any, Dict, Tuple, Union
from threading import Thread, Event
from PIL import Image, ImageDraw

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QScrollBar, QFrame, QGroupBox,
                             QPushButton, QCheckBox, QFileDialog, QMessageBox, QMenu,
                             QGridLayout, QSizePolicy, QDialog, QToolButton)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent, QObject, QTimer
from PyQt6.QtGui import (QFont, QAction, QWheelEvent, QIcon, QImage, QContextMenuEvent,
                         QDragEnterEvent, QDropEvent, QTextCursor, QTextCharFormat, QKeySequence,
                         QShortcut)


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
        
        # 初始化搜索相关变量
        self.search_dialog = None
        self.search_matches: List[int] = []
        self.current_match_index: int = -1
        self.search_highlight_format = QTextCharFormat()
        self.search_highlight_format.setBackground(Qt.GlobalColor.yellow)
        self.search_highlight_format.setForeground(Qt.GlobalColor.black)
        
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
        
        # 启用拖放功能
        self.setAcceptDrops(True)
        
        # 设置快捷键
        self.setup_shortcuts()
    
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
        
        # 新增主题切换按钮
        self.theme_toggle_check = QCheckBox("切换主题")
        self.theme_toggle_check.stateChanged.connect(self.toggle_theme)
        self.button_layout.addWidget(self.theme_toggle_check)
        
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
    
    # 新增主题切换方法
    def toggle_theme(self, state: int) -> None:
        """切换主题模式
        
        Args:
            state: 复选框状态
        """
        if state == Qt.CheckState.Checked.value:
            # 普通模式（白底黑字）
            self.result_text.setStyleSheet("background-color: white; color: black;")
        else:
            # 暗黑模式（黑底白字）
            self.result_text.setStyleSheet("background-color: black; color: white;")
    
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
    
    def filter_log_content(self, log_lines: List[str]) -> Tuple[str, int]:
        """
        根据过滤条件过滤日志内容
        
        Args:
            log_lines: 要过滤的日志行列表
            
        Returns:
            过滤后的文本内容和匹配行数的元组
        """
        # 解析包含关键字
        include_input: str = self.include_entry.text().strip()
        include_terms: List[str] = self.parse_keywords(include_input)
        
        # 解析排除关键字
        exclude_input: str = self.exclude_entry.text().strip()
        exclude_terms: List[str] = self.parse_keywords(exclude_input)
        
        start_time: str = self.start_time_entry.text().strip()
        end_time: str = self.end_time_entry.text().strip()
        
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
                return "开始时间格式无效，请使用格式: " + time_format, 0
        
        if end_time:
            try:
                end_datetime = datetime.strptime(end_time, time_format)
                use_time_filter = True
            except ValueError:
                return "结束时间格式无效，请使用格式: " + time_format, 0
        
        # 时间正则表达式 (匹配行首 HH:MM:SS.XXX)
        time_pattern: Pattern = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3})')
        
        match_count: int = 0
        result_text = ""
        
        for line in log_lines:
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
        
        return result_text, match_count
    
    def search_log(self) -> None:
        if not self.log_content:
            QMessageBox.warning(self, "警告", "请先打开日志文件")
            return
        
        # 保存当前搜索条件
        self.save_config()
        self.clear_results()
        
        # 应用过滤条件
        result_text, match_count = self.filter_log_content(self.log_content)
        
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
    
    def setup_shortcuts(self) -> None:
        """设置快捷键"""
        # 设置Ctrl+F快捷键
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.show_search_dialog)
    
    def show_search_dialog(self) -> None:
        """显示搜索对话框"""
        # 如果对话框已存在，则直接显示
        if self.search_dialog is not None and self.search_dialog.isVisible():
            self.search_dialog.activateWindow()
            return
        
        # 创建搜索对话框
        self.search_dialog = QDialog(self)
        self.search_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.search_dialog.setStyleSheet("""
            QDialog {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QLineEdit {
                border: 1px solid #cccccc;
                border-radius: 2px;
                padding: 2px 4px;
                background-color: white;
                selection-background-color: #0078d7;
            }
            QToolButton {
                border: none;
                background-color: transparent;
                padding: 2px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
                border-radius: 2px;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # 创建布局
        layout = QHBoxLayout(self.search_dialog)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 创建搜索框
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("搜索...")
        self.search_entry.textChanged.connect(self.search_text_changed)
        self.search_entry.returnPressed.connect(lambda: self.navigate_search(1))  # 按回车键查找下一个
        layout.addWidget(self.search_entry)
        
        # 创建上一个按钮
        self.prev_button = QToolButton()
        self.prev_button.setText("^")
        self.prev_button.setToolTip("上一个匹配 (Shift+Enter)")
        self.prev_button.clicked.connect(lambda: self.navigate_search(-1))
        layout.addWidget(self.prev_button)
        
        # 创建下一个按钮
        self.next_button = QToolButton()
        self.next_button.setText("v")
        self.next_button.setToolTip("下一个匹配 (Enter)")
        self.next_button.clicked.connect(lambda: self.navigate_search(1))
        layout.addWidget(self.next_button)
        
        # 创建关闭按钮
        self.close_button = QToolButton()
        self.close_button.setText("x")
        self.close_button.setToolTip("关闭 (Esc)")
        self.close_button.clicked.connect(self.close_search_dialog)
        layout.addWidget(self.close_button)
        
        # 设置对话框位置 - 在结果区域的右上角
        result_rect = self.result_group.geometry()
        dialog_pos = self.result_group.mapToGlobal(result_rect.topRight())
        dialog_pos.setX(dialog_pos.x() - self.search_dialog.sizeHint().width() - 10)  # 向左偏移
        dialog_pos.setY(dialog_pos.y() + 10)  # 向下偏移
        self.search_dialog.move(dialog_pos)
        
        # 显示对话框并设置焦点
        self.search_dialog.show()
        self.search_entry.setFocus()
        
        # 添加ESC键关闭对话框
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self.search_dialog)
        self.esc_shortcut.activated.connect(self.close_search_dialog)
        
        # 添加Shift+Enter快捷键查找上一个
        self.prev_shortcut = QShortcut(QKeySequence("Shift+Return"), self.search_dialog)
        self.prev_shortcut.activated.connect(lambda: self.navigate_search(-1))
    
    def close_search_dialog(self) -> None:
        """关闭搜索对话框"""
        if self.search_dialog:
            self.search_dialog.close()
            # 清除所有高亮
            self.clear_highlights()
    
    def search_text_changed(self) -> None:
        """搜索文本变化时触发"""
        search_text = self.search_entry.text()
        if not search_text:
            self.clear_highlights()
            self.search_matches = []
            self.current_match_index = -1
            return
        
        # 查找所有匹配
        self.find_all_matches(search_text)
        
        # 不需要在这里更新状态栏，因为find_all_matches已经更新了
    
    def find_all_matches(self, search_text: str) -> None:
        """查找所有匹配的位置，使用分批处理避免UI卡死"""
        # 清除之前的高亮
        self.clear_highlights()
        
        # 重置匹配列表
        self.search_matches = []
        self.current_match_index = -1
        
        if not search_text:
            return
        
        # 获取文本内容
        document = self.result_text.document()
        cursor = QTextCursor(document)
        
        # 设置批处理参数
        batch_size = 1000  # 每批处理的最大匹配数
        max_matches = 10000  # 最大匹配数限制
        current_batch = 0
        
        # 创建进度指示器
        self.statusBar().showMessage("正在搜索匹配项...")
        QApplication.processEvents()  # 确保UI更新
        
        # 查找匹配（分批处理）
        while len(self.search_matches) < max_matches:
            # 处理当前批次
            batch_count = 0
            batch_start_time = time.time()
            
            while batch_count < batch_size and len(self.search_matches) < max_matches:
                cursor = document.find(search_text, cursor)
                if cursor.isNull():
                    break
                
                # 保存匹配位置
                match_position = cursor.position() - len(search_text)
                self.search_matches.append(match_position)
                batch_count += 1
                
                # 确保光标向前移动，避免无限循环
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 1)
            
            # 如果没有找到更多匹配或已达到最大匹配数，退出循环
            if batch_count == 0 or len(self.search_matches) >= max_matches:
                break
            
            # 更新状态栏显示进度
            current_batch += 1
            self.statusBar().showMessage(f"已找到 {len(self.search_matches)} 个匹配项...")
            QApplication.processEvents()  # 确保UI更新
            
            # 如果批处理太快（小于50ms），增加批处理大小以提高效率
            batch_time = time.time() - batch_start_time
            if batch_time < 0.05 and batch_size < 5000:
                batch_size = min(batch_size * 2, 5000)
            # 如果批处理太慢（大于200ms），减小批处理大小以保持响应性
            elif batch_time > 0.2 and batch_size > 100:
                batch_size = max(batch_size // 2, 100)
        
        # 高亮显示（仅高亮可见区域附近的匹配项）
        self.highlight_visible_matches()
        
        # 如果有匹配，选择第一个
        if self.search_matches:
            self.current_match_index = 0
            self.scroll_to_match(self.current_match_index)
            
            # 如果达到最大匹配数限制，显示提示
            if len(self.search_matches) >= max_matches:
                self.statusBar().showMessage(f"找到超过 {max_matches} 个匹配项，仅显示前 {max_matches} 个")
            else:
                self.statusBar().showMessage(f"找到 {len(self.search_matches)} 个匹配项")
        else:
            self.statusBar().showMessage("没有找到匹配项")
    
    def navigate_search(self, direction: int) -> None:
        """导航到下一个或上一个匹配
        
        Args:
            direction: 导航方向，1表示下一个，-1表示上一个
        """
        if not self.search_matches:
            return
        
        # 更新当前匹配索引
        self.current_match_index = (self.current_match_index + direction) % len(self.search_matches)
        
        # 滚动到当前匹配
        self.scroll_to_match(self.current_match_index)
        
        # 更新状态栏
        self.statusBar().showMessage(f"匹配 {self.current_match_index + 1}/{len(self.search_matches)}")
    
    def scroll_to_match(self, index: int) -> None:
        """滚动到指定索引的匹配
        
        Args:
            index: 匹配索引
        """
        if 0 <= index < len(self.search_matches):
            # 获取匹配位置
            position = self.search_matches[index]
            
            # 创建光标并移动到匹配位置
            cursor = QTextCursor(self.result_text.document())
            cursor.setPosition(position)
            cursor.setPosition(position + len(self.search_entry.text()), QTextCursor.MoveMode.KeepAnchor)
            
            # 设置文本光标并滚动到可见区域
            self.result_text.setTextCursor(cursor)
            self.result_text.ensureCursorVisible()
            
            # 滚动后重新高亮可见区域的匹配项
            # 延迟一小段时间确保滚动完成
            QTimer.singleShot(50, self.highlight_visible_matches)
    
    def highlight_visible_matches(self) -> None:
        """只高亮当前可见区域附近的匹配项
        
        这种懒加载方式可以显著提高大量匹配项时的性能
        """
        if not self.search_matches or not self.search_entry:
            return
            
        # 获取当前可见区域
        visible_cursor = self.result_text.cursorForPosition(self.result_text.viewport().rect().center())
        visible_position = visible_cursor.position()
        
        # 计算可见区域前后的范围（大约前后各1000个字符）
        visible_range = 1000
        start_pos = max(0, visible_position - visible_range)
        end_pos = min(self.result_text.document().characterCount(), visible_position + visible_range)
        
        # 查找在可见范围内的匹配项
        search_text = self.search_entry.text()
        document = self.result_text.document()
        
        # 最多高亮100个匹配项，避免性能问题
        highlight_count = 0
        max_highlights = 100
        
        for pos in self.search_matches:
            if start_pos <= pos <= end_pos and highlight_count < max_highlights:
                # 高亮匹配文本
                cursor_highlight = QTextCursor(document)
                cursor_highlight.setPosition(pos)
                cursor_highlight.setPosition(pos + len(search_text), QTextCursor.MoveMode.KeepAnchor)
                cursor_highlight.setCharFormat(self.search_highlight_format)
                highlight_count += 1
    
    def clear_highlights(self) -> None:
        """清除所有高亮"""
        # 重置文档格式
        cursor = QTextCursor(self.result_text.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()
    
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
            
            # 处理事件
            event.accept()
        else:
            # 如果没有按下Ctrl键，则调用原生的wheelEvent方法处理正常滚动
            super().wheelEvent(event)
            
            # 滚动后更新高亮（使用计时器延迟执行，避免频繁更新）
            if self.search_matches and hasattr(self, 'search_entry') and self.search_entry:
                if hasattr(self, 'scroll_timer'):
                    self.scroll_timer.stop()
                else:
                    self.scroll_timer = QTimer()
                    self.scroll_timer.setSingleShot(True)
                    self.scroll_timer.timeout.connect(self.highlight_visible_matches)
                
                self.scroll_timer.start(100)  # 100ms延迟，避免滚动时频繁更新
            else:
                self.scroll_timer = QTimer()
                self.scroll_timer.setSingleShot(True)
                self.scroll_timer.timeout.connect(self.highlight_visible_matches)
            
            self.scroll_timer.start(100)  # 100ms延迟，避免滚动时频繁更新
            
            # 更新状态栏
            self.statusBar().showMessage(f"字体大小: {self.current_font_size}")
            
            # 阻止事件继续传播
            event.accept()
            
            # 滚动后更新高亮（使用计时器延迟执行，避免频繁更新）
            if hasattr(self, 'scroll_timer'):
                self.scroll_timer.stop()
            else:
                self.scroll_timer = QTimer()
                self.scroll_timer.setSingleShot(True)
                self.scroll_timer.timeout.connect(self.highlight_visible_matches)
            
            self.scroll_timer.start(100)  # 100ms延迟，避免滚动时频繁更新
    
    def keyPressEvent(self, event) -> None:
        """处理键盘按键事件，支持Ctrl+Home和Ctrl+End快捷键导航
        
        Args:
            event: 键盘事件对象
        """
        # 检查是否按下了Ctrl+Home组合键（导航到首行）
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier and 
                event.key() == Qt.Key.Key_Home):
            # 将文本光标移动到文档开始位置
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.result_text.setTextCursor(cursor)
            # 确保视图滚动到顶部
            self.result_text.ensureCursorVisible()
            self.statusBar().showMessage("已导航到首行")
            event.accept()
        # 检查是否按下了Ctrl+End组合键（导航到末行）
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier and 
                event.key() == Qt.Key.Key_End):
            # 将文本光标移动到文档结束位置
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.result_text.setTextCursor(cursor)
            # 确保视图滚动到底部
            self.result_text.ensureCursorVisible()
            self.statusBar().showMessage("已导航到末行")
            event.accept()
        else:
            # 对于其他按键，调用父类的处理方法
            super().keyPressEvent(event)
    
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
                
            # 恢复主题设置
            if "theme" in config:
                self.theme_toggle_check.setChecked(config["theme"])
                self.toggle_theme(Qt.CheckState.Checked.value if config["theme"] else Qt.CheckState.Unchecked.value)
                
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
            "last_file": self.current_file if self.current_file else "",
            "theme": self.theme_toggle_check.isChecked()  # 新增主题配置
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.statusBar().showMessage(f"保存配置失败: {str(e)}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """处理拖拽进入事件，接受文件拖放
        
        Args:
            event: 拖拽进入事件对象
        """
        # 检查是否包含文件URL
        if event.mimeData().hasUrls():
            # 只接受文件URL
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """处理拖放事件，打开拖放的文件
        
        Args:
            event: 拖放事件对象
        """
        # 获取拖放的文件URL列表
        urls = event.mimeData().urls()
        
        # 如果有文件被拖放
        if urls:
            # 获取第一个文件的本地路径（只处理第一个文件）
            file_path = urls[0].toLocalFile()
            
            # 如果是有效的文件路径，则打开该文件
            if file_path and os.path.isfile(file_path):
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


# 自定义事件类型，用于在线程间通信
class TailLogEvent(QEvent):
    EVENT_TYPE = QEvent.Type(QEvent.registerEventType())
    
    def __init__(self, content: str):
        super().__init__(self.EVENT_TYPE)
        self.content = content


# 重写事件处理方法，处理自定义事件
def event(self, event: QEvent) -> bool:
    if event.type() == TailLogEvent.EVENT_TYPE:
        # 获取新内容
        new_content = event.content
        
        # 将新内容按行分割
        new_lines = new_content.splitlines(True)  # 保留换行符
        
        if new_lines:
            # 应用过滤条件
            filtered_content, match_count = self.filter_log_content(new_lines)
            
            if filtered_content:
                # 追加过滤后的内容到结果文本框
                self.result_text.append(filtered_content)
                # 滚动到底部
                self.result_text.verticalScrollBar().setValue(self.result_text.verticalScrollBar().maximum())
                
                # 更新状态栏
                self.statusBar().showMessage(f"追加了 {match_count} 行匹配的日志")
        
        return True
    return super(LogInsight, self).event(event)


# 添加事件处理方法到类
LogInsight.event = event


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogInsight()
    window.showMaximized()  
    sys.exit(app.exec())