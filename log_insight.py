import sys
import re
import os
import json
import time
from datetime import datetime
from typing import List, Pattern, Optional, Tuple

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QFrame, QGroupBox,
                             QPushButton, QFileDialog, QMessageBox, QMenu,
                             QGridLayout, QDialog, QToolButton)
from PyQt6.QtGui import (QFont, QWheelEvent, QIcon,
                         QDragEnterEvent, QDropEvent, QTextCursor, QTextCharFormat, QKeySequence,
                         QShortcut)
from PyQt6.QtCore import Qt, QTimer, QSize, QFileSystemWatcher, QThread, pyqtSignal

class FilterWorker(QThread):
    """Worker thread for filtering log content"""
    # Signal to emit when filtering is complete
    filteringComplete = pyqtSignal(str, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_lines = []
        self.include_terms = []
        self.exclude_terms = []
        self.include_case_sensitive = False
        self.exclude_case_sensitive = False
        self.start_time = ""
        self.end_time = ""
        self.include_patterns = []
        self.exclude_patterns = []
        
    def setup(self, log_lines, include_terms, exclude_terms, 
              include_case_sensitive, exclude_case_sensitive,
              start_time, end_time):
        """Set up the worker with filtering parameters"""
        self.log_lines = log_lines
        self.include_terms = include_terms
        self.exclude_terms = exclude_terms
        self.include_case_sensitive = include_case_sensitive
        self.exclude_case_sensitive = exclude_case_sensitive
        self.start_time = start_time
        self.end_time = end_time
        
        # Pre-compile patterns for better performance
        self.include_patterns = []
        for term in self.include_terms:
            escaped_term = re.escape(term)
            if self.include_case_sensitive:
                self.include_patterns.append(re.compile(escaped_term))
            else:
                self.include_patterns.append(re.compile(escaped_term, re.IGNORECASE))
        
        self.exclude_patterns = []
        for term in self.exclude_terms:
            escaped_term = re.escape(term)
            if self.exclude_case_sensitive:
                self.exclude_patterns.append(re.compile(escaped_term))
            else:
                self.exclude_patterns.append(re.compile(escaped_term, re.IGNORECASE))
    
    def run(self):
        """Run the filtering process in background thread"""
        time_format = "%H:%M:%S.%f"
        use_time_filter = False
        start_datetime = None
        end_datetime = None
        
        # Process time filters
        if self.start_time:
            try:
                start_datetime = datetime.strptime(self.start_time, time_format)
                use_time_filter = True
            except ValueError:
                # Invalid time format, will be handled in the main thread
                pass
                
        if self.end_time:
            try:
                end_datetime = datetime.strptime(self.end_time, time_format)
                use_time_filter = True
            except ValueError:
                # Invalid time format, will be handled in the main thread
                pass
        
        # Time regex pattern (matches HH:MM:SS.XXX at line start)
        time_pattern = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3})')
        
        match_count = 0
        result_lines = []
        
        for line in self.log_lines:
            # Check for any exclude keywords (high priority)
            if self.exclude_patterns and any(pattern.search(line) for pattern in self.exclude_patterns):
                continue
            
            # Check for at least one include keyword
            if self.include_patterns and not any(pattern.search(line) for pattern in self.include_patterns):
                continue
            
            # Time filtering
            if use_time_filter:
                time_match = time_pattern.search(line)
                if time_match:
                    line_time_str = time_match.group(1)
                    try:
                        line_time = datetime.strptime(line_time_str, time_format)
                        
                        # Check time range
                        if start_datetime and line_time < start_datetime:
                            continue
                        if end_datetime and line_time > end_datetime:
                            continue
                    except ValueError:
                        # Skip time filtering if time parsing fails
                        pass
            
            # Add matching line to results list
            result_lines.append(line)
            match_count += 1
        
        # Join the collected lines into a single string for better performance
        result_text = "".join(result_lines)
        
        # Emit signal with results
        self.filteringComplete.emit(result_text, match_count)

class LogInsight(QMainWindow):
    # Configuration file path
    CONFIG_FILE: str = os.path.join(os.path.expanduser('~'), "logInsight.json")
    
    # Base path for icons
    ICONS_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    
    ICON_NAMES = {
        'CASE_SENSITIVE_ON': "case_sensitive_on.svg",
        'CASE_SENSITIVE_OFF': "case_sensitive_off.svg",
        'APP_LOGO': "logo.svg",
        'ARROW_UP': "arrow_up.svg",
        'ARROW_DOWN': "arrow_down.svg",
        'THEME_LIGHT': "theme_light.svg",
        'THEME_DARK': "theme_dark.svg",
        'WORD_WRAP_ON': "word_wrap_on.svg",
        'WORD_WRAP_OFF': "word_wrap_off.svg",
        'TAIL_LOG_ON': "tail_log_on.svg",
        'TAIL_LOG_OFF': "tail_log_off.svg",
        'HELP': "help.svg"
    }
    
    @classmethod
    def get_icon_path(cls, icon_name: str) -> str:
        """Get the full path for an icon based on its name
        
        Args:
            icon_name: Name of the icon from ICON_NAMES
            
        Returns:
            Full path to the icon file
        """
        return os.path.join(cls.ICONS_DIR, cls.ICON_NAMES.get(icon_name, icon_name))

    # Track the last file position for tail mode
    last_file_position: int = 0
    
    def __init__(self) -> None:
        super().__init__()
        
        self.setWindowTitle("Log Insight")
        
        # Set application icon
        app_icon = QIcon(self.get_icon_path('APP_LOGO'))
        self.setWindowIcon(app_icon)
        
        self.log_content: List[str] = []
        self.current_file: Optional[str] = None
        self.current_font_size: int = 10
        
        # Default prompt text when no file is loaded
        self.default_prompt_text = "Click \"Open Log File\" to open file or drag file here."
        
        self.prompt_text_color = "#0066cc"  
        self.prompt_text_size = 16  
        
        # Initialize file watcher variables
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.on_file_changed)
        
        self.filter_collapsed: bool = False
        self.button_collapsed: bool = False
        
        # Initialize search-related variables
        self.search_dialog = None
        self.search_matches: List[int] = []
        self.current_match_index: int = -1
        self.search_highlight_format = QTextCharFormat()
        self.search_highlight_format.setBackground(Qt.GlobalColor.yellow)
        self.search_highlight_format.setForeground(Qt.GlobalColor.black)
        
        self.case_sensitive_on_icon = QIcon(self.get_icon_path('CASE_SENSITIVE_ON'))
        self.case_sensitive_off_icon = QIcon(self.get_icon_path('CASE_SENSITIVE_OFF'))
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.setup_ui()
        self.load_config()
        self.setAcceptDrops(True)
        self.setup_shortcuts()
        
        # Create worker thread for filtering
        self.filter_worker = FilterWorker(self)
        self.filter_worker.filteringComplete.connect(self.on_filtering_complete)
    
    def setup_ui(self) -> None:
        self.control_group = QGroupBox()
        self.main_layout.addWidget(self.control_group)
        
        self.control_layout = QVBoxLayout(self.control_group)
        self.control_layout.setContentsMargins(5, 5, 5, 5)
        
        self.title_widget = QWidget()
        self.title_layout = QHBoxLayout(self.title_widget)
        self.title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.control_title = QLabel("Control Panel")
        self.control_title.setStyleSheet("font-weight: bold;")
        self.title_layout.addWidget(self.control_title)
        
        self.title_layout.addStretch()
        
        # Add collapse/expand button
        self.control_toggle_btn = QPushButton("▼")
        self.control_toggle_btn.setToolTip("Collapse/Expand Control Panel")
        self.control_toggle_btn.setFixedSize(20, 20)  # Set button size
        self.control_toggle_btn.clicked.connect(self.toggle_control_panel)
        self.title_layout.addWidget(self.control_toggle_btn)
        
        # Add title bar to control panel layout
        self.control_layout.addWidget(self.title_widget)
        
        # Create control panel content area
        self.control_content_widget = QWidget()
        self.control_content_layout = QVBoxLayout(self.control_content_widget)
        self.control_content_layout.setContentsMargins(0, 0, 0, 0)
        self.control_content_layout.setSpacing(5)  # Reduce vertical spacing
        self.control_layout.addWidget(self.control_content_widget)
        
        # Create filter section
        self.filter_widget = QWidget()
        self.filter_layout = QGridLayout(self.filter_widget)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.setVerticalSpacing(3)  # Reduce vertical spacing
        
        # Add filter title
        self.filter_title = QLabel("<b>Filters</b>")
        self.filter_layout.addWidget(self.filter_title, 0, 0, 1, 3)
        
        # Include keywords
        self.filter_layout.addWidget(QLabel("Include Keywords:"), 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.include_entry = QLineEdit()
        self.include_entry.setPlaceholderText("keyword1 \"multiple words keywords\" keyword3")
        # Add enter key event handler
        self.include_entry.returnPressed.connect(self.search_log)
        self.filter_layout.addWidget(self.include_entry, 1, 1)
        
        # Include keywords case sensitive toggle
        self.include_case_frame = QWidget()
        self.include_case_layout = QHBoxLayout(self.include_case_frame)
        self.include_case_layout.setContentsMargins(0, 0, 0, 0)
        
        self.include_case_sensitive = QToolButton()
        self.include_case_sensitive.setCheckable(True)
        self.include_case_sensitive.setToolTip("Case Sensitive")
        self.include_case_sensitive.setIcon(self.case_sensitive_off_icon)
        self.include_case_sensitive.setIconSize(QToolButton().sizeHint())
        self.include_case_sensitive.toggled.connect(self.toggle_include_case_sensitive)
        
        self.include_case_layout.addWidget(self.include_case_sensitive)
        self.filter_layout.addWidget(self.include_case_frame, 1, 2)
        
        # Exclude keywords
        self.filter_layout.addWidget(QLabel("Exclude Keywords:"), 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.exclude_entry = QLineEdit()
        self.exclude_entry.setPlaceholderText("keyword1 \"multiple words keywords\" keyword3")
        # Add enter key event handler
        self.exclude_entry.returnPressed.connect(self.search_log)
        self.filter_layout.addWidget(self.exclude_entry, 2, 1)
        
        # Exclude keywords case sensitive toggle
        self.exclude_case_frame = QWidget()
        self.exclude_case_layout = QHBoxLayout(self.exclude_case_frame)
        self.exclude_case_layout.setContentsMargins(0, 0, 0, 0)
        
        self.exclude_case_sensitive = QToolButton()
        self.exclude_case_sensitive.setCheckable(True)
        self.exclude_case_sensitive.setToolTip("Case Sensitive")
        self.exclude_case_sensitive.setIcon(self.case_sensitive_off_icon)
        self.exclude_case_sensitive.setIconSize(QToolButton().sizeHint())
        self.exclude_case_sensitive.toggled.connect(self.toggle_exclude_case_sensitive)
        
        self.exclude_case_layout.addWidget(self.exclude_case_sensitive)
        self.filter_layout.addWidget(self.exclude_case_frame, 2, 2)
        
        # Time range
        self.filter_layout.addWidget(QLabel("Time Range:"), 3, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        
        self.time_frame = QWidget()
        self.time_layout = QHBoxLayout(self.time_frame)
        self.time_layout.setContentsMargins(0, 0, 0, 0)
        self.time_layout.setSpacing(5)  # Set fixed spacing between widgets
        
        self.start_time_entry = QLineEdit()
        self.start_time_entry.setPlaceholderText("00:00:00.000")
        # Set fixed width to prevent the input box from being too wide
        self.start_time_entry.setFixedWidth(100)
        # Set placeholder style to make it more visible
        self.start_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
        # Add enter key event handler
        self.start_time_entry.returnPressed.connect(self.search_log)
        # Add text changed handler for real-time validation
        self.start_time_entry.textChanged.connect(self.validate_start_time)
        self.time_layout.addWidget(self.start_time_entry)
        
        # Use a fixed width label for the "to" text
        self.time_separator_label = QLabel("to")
        self.time_separator_label.setFixedWidth(20)  # Set fixed width for the label
        self.time_separator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the text
        self.time_layout.addWidget(self.time_separator_label)
        
        self.end_time_entry = QLineEdit()
        self.end_time_entry.setPlaceholderText("23:59:59.999")
        # Set fixed width to prevent the input box from being too wide
        self.end_time_entry.setFixedWidth(100)
        # Set placeholder style to make it more visible
        self.end_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
        # Add enter key event handler
        self.end_time_entry.returnPressed.connect(self.search_log)
        # Add text changed handler for real-time validation
        self.end_time_entry.textChanged.connect(self.validate_end_time)
        self.time_layout.addWidget(self.end_time_entry)
        
        # Add stretch at the end to push everything to the left
        self.time_layout.addStretch()
        
        self.filter_layout.addWidget(self.time_frame, 3, 1)
        
        # Add filter section to control panel
        self.control_content_layout.addWidget(self.filter_widget)
        
        # Add separator
        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.control_content_layout.addWidget(self.separator)
        
        # Create operations section
        self.button_widget = QWidget()
        self.button_layout = QVBoxLayout(self.button_widget)
        self.button_layout.setContentsMargins(0, 0, 0, 0)
        self.button_layout.setSpacing(3)  # Reduce vertical spacing
        
        # Add operations title
        self.button_title = QLabel("<b>Operations</b>")
        self.button_layout.addWidget(self.button_title)
        
        # Create button content area
        self.button_frame = QWidget()
        self.buttons_layout = QHBoxLayout(self.button_frame)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_button = QPushButton("Filter Log")
        self.search_button.clicked.connect(self.search_log)
        self.buttons_layout.addWidget(self.search_button)
        
        self.tail_log_btn = QToolButton()
        self.tail_log_btn.setToolTip("Tail Log")
        self.tail_log_btn.setCheckable(True)
        self.tail_log_btn.setIcon(QIcon(self.get_icon_path('TAIL_LOG_OFF')))
        self.tail_log_btn.setIconSize(QSize(20, 20))
        self.tail_log_btn.toggled.connect(self.toggle_tail_log)
        self.buttons_layout.addWidget(self.tail_log_btn)
        
        self.word_wrap_btn = QToolButton()
        self.word_wrap_btn.setToolTip("Word Wrap")
        self.word_wrap_btn.setCheckable(True)
        self.word_wrap_btn.setChecked(True)
        self.word_wrap_btn.setIcon(QIcon(self.get_icon_path('WORD_WRAP_ON')))
        self.word_wrap_btn.setIconSize(QSize(20, 20))
        self.word_wrap_btn.toggled.connect(self.toggle_word_wrap)
        self.buttons_layout.addWidget(self.word_wrap_btn)
        
        # Add theme toggle button with icon
        self.theme_toggle_btn = QToolButton()
        self.theme_toggle_btn.setCheckable(True)
        self.theme_toggle_btn.setIcon(QIcon(self.get_icon_path('THEME_LIGHT')))
        self.theme_toggle_btn.setIconSize(QSize(20, 20))
        self.theme_toggle_btn.toggled.connect(self.toggle_theme)
        self.buttons_layout.addWidget(self.theme_toggle_btn)
        
        self.buttons_layout.addStretch()
        
        self.open_button = QPushButton("Open Log File")
        self.open_button.clicked.connect(self.open_log_file)
        self.buttons_layout.addWidget(self.open_button)
        
        self.button_layout.addWidget(self.button_frame)
        
        # Add operations section to control panel
        self.control_content_layout.addWidget(self.button_widget)
        
        # Results display area
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth) 
        self.result_text.setFont(QFont("Consolas", self.current_font_size))
        self.result_text.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.result_text.customContextMenuRequested.connect(self.show_context_menu)
        self.result_text.wheelEvent = self.on_mouse_wheel  # Override wheel event
        
        # Set default prompt text
        if not self.current_file:
            self.result_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.apply_styled_prompt_text()
        
        self.main_layout.addWidget(self.result_text, 1)  # Add stretch factor to make results area occupy more space
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Add help button to status bar
        self.help_btn = QToolButton()
        self.help_btn.setIcon(QIcon(self.get_icon_path('HELP')))
        self.help_btn.setIconSize(QSize(16, 16))
        self.help_btn.setToolTip("Help")
        self.help_btn.clicked.connect(self.show_help_dialog)
        
        # Add permanent widget to right side of status bar
        self.statusBar().addPermanentWidget(self.help_btn)
    
    # Collapse/Expand control panel
    def toggle_control_panel(self) -> None:
        """Collapse or expand control panel (including filters and operations)
        """
        # Use existing collapse state variable for compatibility
        self.filter_collapsed = not self.filter_collapsed
        self.button_collapsed = self.filter_collapsed  # Keep states synchronized
        
        # Update button text
        self.control_toggle_btn.setText("▶" if self.filter_collapsed else "▼")
        
        # Hide or show control panel content
        self.control_content_widget.setVisible(not self.filter_collapsed)
        
    
    # Toggle include keywords case sensitive icon
    def toggle_include_case_sensitive(self, checked: bool) -> None:
        """Toggle include keywords case sensitive icon
        
        Args:
            checked: Whether the button is checked
        """
        if checked:
            self.include_case_sensitive.setIcon(self.case_sensitive_on_icon)
        else:
            self.include_case_sensitive.setIcon(self.case_sensitive_off_icon)
    
    # Toggle exclude keywords case sensitive icon
    def toggle_exclude_case_sensitive(self, checked: bool) -> None:
        """Toggle exclude keywords case sensitive icon
        
        Args:
            checked: Whether the button is checked
        """
        if checked:
            self.exclude_case_sensitive.setIcon(self.case_sensitive_on_icon)
        else:
            self.exclude_case_sensitive.setIcon(self.case_sensitive_off_icon)
    
    # Add theme toggle method
    def toggle_theme(self, checked: bool) -> None:
        """Toggle theme mode
        
        Args:
            checked: Whether the button is checked
        """
        if checked:
            # Dark mode
            self.theme_toggle_btn.setIcon(QIcon(self.get_icon_path('THEME_DARK')))
            self.theme_toggle_btn.setToolTip("switch to light theme")
            self.result_text.setStyleSheet("background-color: black; color: white;")
        else:
            # Light mode
            self.theme_toggle_btn.setIcon(QIcon(self.get_icon_path('THEME_LIGHT')))
            self.theme_toggle_btn.setToolTip("switch to dark theme")
            self.result_text.setStyleSheet("background-color: white; color: black;")
    
    def apply_styled_prompt_text(self) -> None:
        """Apply styled HTML format to the default prompt text
        """
        # Create HTML with the configured style properties
        prompt_html = f'<div style="font-size: {self.prompt_text_size}pt; color: {self.prompt_text_color}; font-weight: bold;">{self.default_prompt_text}</div>'
        self.result_text.setHtml(prompt_html)
    
    
    def validate_time_format(self, time_str: str) -> bool:
        """Validate if the time string matches the required format
        
        Args:
            time_str: Time string to validate
            
        Returns:
            True if the format is valid, False otherwise
        """
        if not time_str.strip():
            return True  # Empty string is valid (no filter)
            
        time_format = "%H:%M:%S.%f"
        try:
            datetime.strptime(time_str, time_format)
            return True
        except ValueError:
            return False
    
    def validate_start_time(self) -> None:
        """Validate start time format and provide visual feedback"""
        time_str = self.start_time_entry.text().strip()
        if self.validate_time_format(time_str):
            # Valid format - reset to normal style
            self.start_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.start_time_entry.setToolTip("")
        else:
            # Invalid format - highlight with red background
            self.start_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; background-color: #FFDDDD; border: 1px solid #FF0000; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.start_time_entry.setToolTip("Invalid time format! Please use format: HH:MM:SS.mmm")
    
    def validate_end_time(self) -> None:
        """Validate end time format and provide visual feedback"""
        time_str = self.end_time_entry.text().strip()
        if self.validate_time_format(time_str):
            # Valid format - reset to normal style
            self.end_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.end_time_entry.setToolTip("")
        else:
            # Invalid format - highlight with red background
            self.end_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; background-color: #FFDDDD; border: 1px solid #FF0000; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.end_time_entry.setToolTip("Invalid time format! Please use format: HH:MM:SS.mmm")
    
    def open_log_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Log File",
            "",
            "Log Files (*.log);;Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    self.log_content = file.readlines()
                
                # Remove previous file from watcher if exists
                if self.current_file and self.current_file in self.file_watcher.files():
                    self.file_watcher.removePath(self.current_file)
                
                self.current_file = file_path
                # Reset file position tracker when opening a new file
                self.last_file_position = 0
                
                self.statusBar().showMessage(f"File loaded: {os.path.basename(file_path)} - {len(self.log_content)} lines")
                # Update window title to show file path
                self.setWindowTitle(f"Log Insight - {file_path}")
                
                # Display log content in results area
                self.result_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self.result_text.setText("".join(self.log_content))
                
                # Add file to watcher if tail mode is active
                if self.tail_log_btn.isChecked():
                    self.file_watcher.addPath(self.current_file)
                
                # Save current configuration
                self.save_config()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot open file: {str(e)}")
    
    def filter_log_content(self, log_lines: List[str]) -> Tuple[str, int]:
        """
        Filter log content based on filter conditions
        
        Args:
            log_lines: List of log lines to filter
            
        Returns:
            Tuple of filtered text content and number of matches
        """
        # parse include keywords
        include_input: str = self.include_entry.text().strip()
        include_terms: List[str] = self.parse_keywords(include_input)
        
        # parse exclude keywords
        exclude_input: str = self.exclude_entry.text().strip()
        exclude_terms: List[str] = self.parse_keywords(exclude_input)
        
        start_time: str = self.start_time_entry.text().strip()
        end_time: str = self.end_time_entry.text().strip()
        
        include_case_sensitive: bool = self.include_case_sensitive.isChecked()
        exclude_case_sensitive: bool = self.exclude_case_sensitive.isChecked()
        
        include_patterns: List[Pattern] = []
        for term in include_terms:
            # consider it as normal string, rather than regular expression 
            escaped_term = re.escape(term)
            if include_case_sensitive:
                include_patterns.append(re.compile(escaped_term))
            else:
                include_patterns.append(re.compile(escaped_term, re.IGNORECASE))
        
        exclude_patterns: List[Pattern] = []
        for term in exclude_terms:
            # consider it as normal string, rather than regular expression 
            escaped_term = re.escape(term)
            if exclude_case_sensitive:
                exclude_patterns.append(re.compile(escaped_term))
            else:
                exclude_patterns.append(re.compile(escaped_term, re.IGNORECASE))
        
        
        time_format: str = "%H:%M:%S.%f"
        use_time_filter: bool = False
        start_datetime: Optional[datetime] = None
        end_datetime: Optional[datetime] = None
        
        # Validate start time format
        if start_time and not self.validate_time_format(start_time):
            # Highlight the input field with error style
            self.start_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; background-color: #FFDDDD; border: 1px solid #FF0000; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.start_time_entry.setToolTip("Invalid time format! Please use format: HH:MM:SS.mmm")
            return "Invalid start time format, please use format: " + time_format, 0
        elif start_time:
            start_datetime = datetime.strptime(start_time, time_format)
            use_time_filter = True
        
        # Validate end time format
        if end_time and not self.validate_time_format(end_time):
            # Highlight the input field with error style
            self.end_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; background-color: #FFDDDD; border: 1px solid #FF0000; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.end_time_entry.setToolTip("Invalid time format! Please use format: HH:MM:SS.mmm")
            return "Invalid end time format, please use format: " + time_format, 0
        elif end_time:
            end_datetime = datetime.strptime(end_time, time_format)
            use_time_filter = True
        
        # Time regex pattern (matches HH:MM:SS.XXX at line start)
        time_pattern: Pattern = re.compile(r'^(\d{2}:\d{2}:\d{2}\.\d{3})')
        
        match_count: int = 0
        # Use a list to collect matching lines instead of string concatenation
        result_lines: List[str] = []
        
        for line in log_lines:
            # Check for any exclude keywords (high priority)
            if exclude_patterns and any(pattern.search(line) for pattern in exclude_patterns):
                continue
            
            # Check for at least one include keyword
            if include_patterns and not any(pattern.search(line) for pattern in include_patterns):
                continue
            
            # Time filtering
            if use_time_filter:
                time_match = time_pattern.search(line)
                if time_match:
                    line_time_str = time_match.group(1)
                    try:
                        line_time = datetime.strptime(line_time_str, time_format)
                        
                        # Check time range
                        if start_datetime and line_time < start_datetime:
                            continue
                        if end_datetime and line_time > end_datetime:
                            continue
                    except ValueError:
                        # Skip time filtering if time parsing fails
                        pass
                # elif start_datetime or end_datetime:
                #     # Skip line if time filtering is needed but no time found
                #     continue
            
            # Add matching line to results list
            result_lines.append(line)
            match_count += 1
        
        # Join the collected lines into a single string for better performance
        result_text = "".join(result_lines)
        return result_text, match_count
    
    def search_log(self) -> None:
        if not self.log_content:
            QMessageBox.warning(self, "Warning", "Please open a log file first")
            return
        
        # Save current search conditions
        self.save_config()
        self.clear_results()
        
        # Apply filter conditions
        result_text, match_count = self.filter_log_content(self.log_content)
        
        # Reset time input styles if search was successful
        if isinstance(result_text, str) and not result_text.startswith("Invalid"):
            # Reset start time input style
            self.start_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.start_time_entry.setToolTip("")
            
            # Reset end time input style
            self.end_time_entry.setStyleSheet("QLineEdit { padding: 2px 4px; } QLineEdit::placeholder { color: #888; font-style: italic; }")
            self.end_time_entry.setToolTip("")
        
        if match_count == 0:
            self.result_text.setText("No matching results found.\n")
        else:
            self.result_text.setText(result_text)
        
        self.statusBar().showMessage(f"Found {match_count} matches")
    
    def clear_results(self) -> None:
        self.result_text.clear()
        
        # Show default prompt text if no file is loaded
        if not self.current_file:
            self.result_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            prompt_html = f'<div style="font-size: 16pt; font-weight: bold; color: #0066cc;">{self.default_prompt_text}</div>'
            self.result_text.setHtml(prompt_html)
        else:
            self.result_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
    
    def show_context_menu(self, position) -> None:
        context_menu = QMenu()
        copy_action = context_menu.addAction("Copy")
        select_all_action = context_menu.addAction("Select All")
        copy_all_action = context_menu.addAction("Copy All")
        
        action = context_menu.exec(self.result_text.mapToGlobal(position))
        
        if action == copy_action:
            self.copy_selection()
        elif action == select_all_action:
            self.select_all()
        elif action == copy_all_action:
            self.copy_all()
    
    def copy_selection(self) -> None:
        self.result_text.copy()
        self.statusBar().showMessage("Selected content copied to clipboard")
    
    def select_all(self) -> None:
        self.result_text.selectAll()
    
    def copy_all(self) -> None:
        cursor = self.result_text.textCursor()
        cursor.select(cursor.SelectionType.Document)
        self.result_text.setTextCursor(cursor)
        self.result_text.copy()
        self.statusBar().showMessage("All content copied to clipboard")
    
    def setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts"""
        # Set up Ctrl+F shortcut
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.show_search_dialog)
        
        # Set up F1 shortcut for help
        self.help_shortcut = QShortcut(QKeySequence("F1"), self)
        self.help_shortcut.activated.connect(self.show_help_dialog)
    
    def show_search_dialog(self) -> None:
        """Show search dialog"""
        # If dialog already exists, just show it
        if self.search_dialog is not None and self.search_dialog.isVisible():
            self.search_dialog.activateWindow()
            return
        
        # Create search dialog
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
                margin: 0;
                min-height: 24px;
                min-width: 24px;
            }
            QToolButton:hover {
                background-color: #e0e0e0;
                border-radius: 2px;
            }
            QToolButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # Create layout
        layout = QHBoxLayout(self.search_dialog)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)  # Increase spacing
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # Vertical center alignment
        
        # Create search box
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("search...")
        self.search_entry.textChanged.connect(self.search_text_changed)
        # F3 shortcut will be used instead of Enter
        layout.addWidget(self.search_entry)
        
        # Create previous button
        self.prev_button = QToolButton()
        self.prev_button.setIcon(QIcon(self.get_icon_path('ARROW_UP')))
        self.prev_button.setIconSize(QSize(16, 16))  # Fixed icon size
        self.prev_button.setToolTip("Previous Match (Shift+F3)")
        self.prev_button.clicked.connect(lambda: self.navigate_search(-1))
        self.prev_button.setFixedSize(24, 24)  # Fixed button size
        layout.addWidget(self.prev_button)
        
        # Create next button
        self.next_button = QToolButton()
        self.next_button.setIcon(QIcon(self.get_icon_path('ARROW_DOWN')))
        self.next_button.setIconSize(QSize(16, 16))  # Fixed icon size
        self.next_button.setToolTip("Next Match (F3)")
        self.next_button.clicked.connect(lambda: self.navigate_search(1))
        self.next_button.setFixedSize(24, 24)  # Fixed button size
        layout.addWidget(self.next_button)
        
        # Create close button
        self.close_button = QToolButton()
        self.close_button.setText("x")
        self.close_button.setToolTip("Close (Esc)")
        self.close_button.clicked.connect(self.close_search_dialog)
        layout.addWidget(self.close_button)
        
        # set the dialog position - at the top right corner of the result area
        result_rect = self.result_text.geometry()
        dialog_pos = self.result_text.mapToGlobal(result_rect.topRight())
        dialog_pos.setX(dialog_pos.x() - self.search_dialog.sizeHint().width() - 10) 
        dialog_pos.setY(dialog_pos.y() + 10)  
        self.search_dialog.move(dialog_pos)
        
        self.search_dialog.show()
        self.search_entry.setFocus()
        
        # Press ESC键 to clase dialog
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self.search_dialog)
        self.esc_shortcut.activated.connect(self.close_search_dialog)
        
        # Add F3 shortcut to find next match
        self.next_shortcut = QShortcut(QKeySequence("F3"), self.search_dialog)
        self.next_shortcut.activated.connect(lambda: self.navigate_search(1))
        
        # Add Shift+F3 shortcut to find previous match
        self.prev_shortcut = QShortcut(QKeySequence("Shift+F3"), self.search_dialog)
        self.prev_shortcut.activated.connect(lambda: self.navigate_search(-1))
    
    def close_search_dialog(self) -> None:
        """Close search dialog"""
        if self.search_dialog:
            self.search_dialog.close()
            self.clear_highlights()
    
    def search_text_changed(self) -> None:
        """Triggered when search text changes"""
        search_text = self.search_entry.text()
        if not search_text:
            self.clear_highlights()
            self.search_matches = []
            self.current_match_index = -1
            return
        
        self.find_all_matches(search_text)
        
        # No need to update status bar here as find_all_matches already does it
    
    def find_all_matches(self, search_text: str) -> None:
        """Find all matching positions using batch processing to avoid UI freezing"""

        self.clear_highlights()
        
        # Reset match list
        self.search_matches = []
        self.current_match_index = -1
        
        if not search_text:
            return
        
        # Get text content
        document = self.result_text.document()
        cursor = QTextCursor(document)
        
        # Set batch processing parameters
        batch_size = 1000  # Maximum matches per batch
        max_matches = 10000  # Maximum total matches limit
        current_batch = 0
        
        # Create progress indicator
        self.statusBar().showMessage("Searching for matches...")
        QApplication.processEvents()  # Ensure UI updates
        
        # Find matches (batch processing)
        while len(self.search_matches) < max_matches:
            # Process current batch
            batch_count = 0
            batch_start_time = time.time()
            
            while batch_count < batch_size and len(self.search_matches) < max_matches:
                cursor = document.find(search_text, cursor)
                if cursor.isNull():
                    break
                
                # Save match position
                match_position = cursor.position() - len(search_text)
                self.search_matches.append(match_position)
                batch_count += 1
                
                # Ensure cursor moves forward to avoid infinite loop
                cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 1)
            
            # Exit loop if no more matches found or max matches reached
            if batch_count == 0 or len(self.search_matches) >= max_matches:
                break
            
            # Update status bar with progress
            current_batch += 1
            self.statusBar().showMessage(f"Found {len(self.search_matches)} matches...")
            QApplication.processEvents()  # Ensure UI updates
            
            # If batch processing is too fast (less than 50ms), increase batch size for efficiency
            batch_time = time.time() - batch_start_time
            if batch_time < 0.05 and batch_size < 5000:
                batch_size = min(batch_size * 2, 5000)
            # If batch processing is too slow (more than 200ms), decrease batch size for responsiveness
            elif batch_time > 0.2 and batch_size > 100:
                batch_size = max(batch_size // 2, 100)
        
        # Highlight matches (only highlight matches near visible area)
        self.highlight_visible_matches()
        
        # If matches found, select the first one
        if self.search_matches:
            self.current_match_index = 0
            self.scroll_to_match(self.current_match_index)
            
            # Show message if max matches limit reached
            if len(self.search_matches) >= max_matches:
                self.statusBar().showMessage(f"Found over {max_matches} matches, showing first {max_matches} only")
            else:
                self.statusBar().showMessage(f"Found {len(self.search_matches)} matches")
        else:
            self.statusBar().showMessage("No matches found")
    
    def navigate_search(self, direction: int) -> None:
        """Navigate to next or previous match
        
        Args:
            direction: Navigation direction, 1 for next, -1 for previous
        """
        if not self.search_matches:
            return
        
        # Update current match index
        self.current_match_index = (self.current_match_index + direction) % len(self.search_matches)
        
        # Scroll to current match
        self.scroll_to_match(self.current_match_index)
        
        # Update status bar
        self.statusBar().showMessage(f"Match {self.current_match_index + 1}/{len(self.search_matches)}")
    
    def scroll_to_match(self, index: int) -> None:
        """Scroll to match at specified index
        
        Args:
            index: Match index
        """
        if 0 <= index < len(self.search_matches):
            # Get match position
            position = self.search_matches[index]
            
            # Create cursor and move to match position
            cursor = QTextCursor(self.result_text.document())
            cursor.setPosition(position)
            cursor.setPosition(position + len(self.search_entry.text()), QTextCursor.MoveMode.KeepAnchor)
            
            # Set text cursor and scroll to visible area
            self.result_text.setTextCursor(cursor)
            self.result_text.ensureCursorVisible()
            
            # Rehighlight matches in visible area after scrolling
            # Delay slightly to ensure scrolling completes
            QTimer.singleShot(50, self.highlight_visible_matches)
    
    def highlight_visible_matches(self) -> None:
        """Only highlight matches near the current visible area
        
        This lazy loading approach significantly improves performance with many matches
        """
        if not self.search_matches or not self.search_entry:
            return
            
        # Get current visible area
        visible_cursor = self.result_text.cursorForPosition(self.result_text.viewport().rect().center())
        visible_position = visible_cursor.position()
        
        # Calculate range before and after visible area (about 1000 characters each)
        visible_range = 1000
        start_pos = max(0, visible_position - visible_range)
        end_pos = min(self.result_text.document().characterCount(), visible_position + visible_range)
        
        # Find matches within visible range
        search_text = self.search_entry.text()
        document = self.result_text.document()
        
        # Limit to 100 highlights to avoid performance issues
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
        cursor = QTextCursor(self.result_text.document())
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()
    
    def on_mouse_wheel(self, event: QWheelEvent) -> None:
        # check if Ctrl is pressed
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                # increase font size
                self.current_font_size = min(36, self.current_font_size + 1)  # set maximum font size to 36
            else:
                # decrease font size
                self.current_font_size = max(6, self.current_font_size - 1)  # Set minimum font size to 6
            
            # Update text box font
            font = self.result_text.font()
            font.setPointSize(self.current_font_size)
            self.result_text.setFont(font)
            
            self.statusBar().showMessage(f"Font size: {self.current_font_size}")
            
            # Handle event
            event.accept()
        else:
            # If Ctrl is not pressed, pass the event to QTextEdit's native wheelEvent for normal scrolling
            # Note: Cannot use super().wheelEvent(event) because current class is a subclass of QMainWindow
            # Need to pass the event to QTextEdit's native method
            QTextEdit.wheelEvent(self.result_text, event)
            
            # Update highlights after scrolling (use timer to delay execution, avoid frequent updates)
            if self.search_matches and hasattr(self, 'search_entry') and self.search_entry:
                if hasattr(self, 'scroll_timer'):
                    self.scroll_timer.stop()
                else:
                    self.scroll_timer = QTimer()
                    self.scroll_timer.setSingleShot(True)
                    self.scroll_timer.timeout.connect(self.highlight_visible_matches)
                
                self.scroll_timer.start(100)  # 100ms delay to avoid frequent updates while scrolling
    
    def keyPressEvent(self, event) -> None:
        """Handle keyboard events, support Ctrl+Home and Ctrl+End shortcuts for navigation
        
        Args:
            event: Keyboard event object
        """
        # Check if Ctrl+Home combination is pressed (navigate to first line)
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier and 
                event.key() == Qt.Key.Key_Home):
            # Move text cursor to document start
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            self.result_text.setTextCursor(cursor)
            # Ensure view scrolls to top
            self.result_text.ensureCursorVisible()
            self.statusBar().showMessage("Navigated to first line")
            event.accept()
        # Check if Ctrl+End combination is pressed (navigate to last line)
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier and 
                event.key() == Qt.Key.Key_End):
            # Move text cursor to document end
            cursor = self.result_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.result_text.setTextCursor(cursor)
            # Ensure view scrolls to bottom
            self.result_text.ensureCursorVisible()
            self.statusBar().showMessage("Navigated to last line")
            event.accept()
        else:
            # For other keys, call parent class handler
            super().keyPressEvent(event)
    
    def toggle_word_wrap(self, checked: bool) -> None:
        """Toggle word wrap
        
        Args:
            checked: Button checked state
        """
        if checked:
            self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            self.word_wrap_btn.setIcon(QIcon(self.get_icon_path('WORD_WRAP_ON')))
        else:
            self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            self.word_wrap_btn.setIcon(QIcon(self.get_icon_path('WORD_WRAP_OFF')))
    
    def toggle_tail_log(self, checked: bool) -> None:
        """Toggle log tail mode using QFileSystemWatcher
        
        Args:
            checked: Whether the button is checked
        """
        if checked:
            # Update icon to ON state
            self.tail_log_btn.setIcon(QIcon(self.get_icon_path('TAIL_LOG_ON')))
            
            if self.current_file and os.path.exists(self.current_file):
                # Update last file position to current file size to only read new content
                self.last_file_position = os.path.getsize(self.current_file)
                # Add file to watcher if not already watching
                if self.current_file not in self.file_watcher.files():
                    self.file_watcher.addPath(self.current_file)
                self.statusBar().showMessage("Log tail mode started")
            else:
                self.tail_log_btn.setChecked(False)
                QMessageBox.warning(self, "Warning", "Please open a log file first")
        else:
            # Update icon to OFF state
            self.tail_log_btn.setIcon(QIcon(self.get_icon_path('TAIL_LOG_OFF')))
            
            # Remove file from watcher
            if self.current_file and self.current_file in self.file_watcher.files():
                self.file_watcher.removePath(self.current_file)
            self.statusBar().showMessage("Log tail mode stopped")
    
    def on_file_changed(self, path: str) -> None:
        """Handle file change events from QFileSystemWatcher
        
        Args:
            path: Path to the changed file
        """
        # Quick exit if not tailing or not the current file
        if not self.tail_log_btn.isChecked() or path != self.current_file:
            return
            
        if not os.path.exists(path):
            return

        # Get current file size
        current_size = os.path.getsize(path)

        # Read only new content
        with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                # If file is smaller than last position (file was truncated), read from beginning
            if current_size < self.last_file_position:
                    file.seek(0)
                    self.last_file_position = 0
            else:
                    # Otherwise, read only new content from last position
                    file.seek(self.last_file_position)

            new_content = file.read()
            # Update last position for next read
            self.last_file_position = current_size

        # Process new content in background thread if there's content
        if new_content:
            new_lines = new_content.splitlines(True)  # Keep line breaks

            if new_lines:
                    # Parse filter parameters
                include_input = self.include_entry.text().strip()
                include_terms = self.parse_keywords(include_input)

                exclude_input = self.exclude_entry.text().strip()
                exclude_terms = self.parse_keywords(exclude_input)

                start_time = self.start_time_entry.text().strip()
                end_time = self.end_time_entry.text().strip()

                include_case_sensitive = self.include_case_sensitive.isChecked()
                exclude_case_sensitive = self.exclude_case_sensitive.isChecked()

                self.filter_worker.setup(
                        new_lines,
                        include_terms,
                        exclude_terms,
                        include_case_sensitive,
                        exclude_case_sensitive,
                        start_time,
                        end_time
                )

                # Start the worker thread if it's not already running
                if not self.filter_worker.isRunning():
                    self.filter_worker.start()

        # Re-add the file to the watcher if it was removed
        if path not in self.file_watcher.files() and self.tail_log_btn.isChecked():
                self.file_watcher.addPath(path)
                

    def on_filtering_complete(self, filtered_content: str, match_count: int) -> None:
        """Handle completion of background filtering
        
        Args:
            filtered_content: The filtered text content
            match_count: Number of matching lines
        """
        if filtered_content:
            # Append filtered content to results text box
            self.result_text.append(filtered_content)
            # Scroll to bottom
            self.result_text.verticalScrollBar().setValue(self.result_text.verticalScrollBar().maximum())
            
            self.statusBar().showMessage(f"Appended {match_count} matching log lines")
    
    def parse_keywords(self, input_str: str) -> List[str]:
        """parse keywords, support space separation and keywords with spaces inside quotes
        Args:
            input_str: Input keyword string

        Returns:
            Parsed keyword list
        """
        
        if not input_str:
            return []
            
        keywords: List[str] = []
        # regular expression matching: content inside quotes as a keyword, or non-space character sequence as a keyword
        pattern: Pattern = re.compile(r'"([^"]*)"|\S+')
        
        matches = pattern.finditer(input_str)
        for match in matches:
            # if it's inside quotes, group(1) will have a value
            if match.group(1) is not None:
                keywords.append(match.group(1))
            else:
                # otherwise, use the full match
                keywords.append(match.group(0))
                
        return [keyword.strip() for keyword in keywords if keyword.strip()]
    
    def load_config(self) -> None:
        if not os.path.exists(self.CONFIG_FILE):
            return
            
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # restore search conditions
            if "include_keywords" in config and config["include_keywords"]:
                self.include_entry.setText(config["include_keywords"])
                
            if "exclude_keywords" in config and config["exclude_keywords"]:
                self.exclude_entry.setText(config["exclude_keywords"])
                
            if "start_time" in config and config["start_time"]:
                self.start_time_entry.setText(config["start_time"])
                
            if "end_time" in config and config["end_time"]:
                self.end_time_entry.setText(config["end_time"])
                
            # restore case sensitive settings
            if "include_case_sensitive" in config:
                self.include_case_sensitive.setChecked(config["include_case_sensitive"])
                
            if "exclude_case_sensitive" in config:
                self.exclude_case_sensitive.setChecked(config["exclude_case_sensitive"])
                
            # restore word wrap setting
            if "word_wrap" in config:
                self.word_wrap_btn.setChecked(config["word_wrap"])
                # toggle_word_wrap will be called by the toggled signal
                
            # restore font size
            if "font_size" in config:
                self.current_font_size = config["font_size"]
                font = self.result_text.font()
                font.setPointSize(self.current_font_size)
                self.result_text.setFont(font)
                
            # restore theme setting
            if "theme" in config:
                self.theme_toggle_btn.setChecked(config["theme"])
                self.toggle_theme(config["theme"])
                
            # restore filter_collapsed setting
            if "filter_collapsed" in config:
                self.filter_collapsed = config["filter_collapsed"]
                self.button_collapsed = self.filter_collapsed  # synchronize two states
                
                # update control panel
                if self.filter_collapsed:
                    self.control_toggle_btn.setText("▶")
                    self.control_content_widget.setVisible(False)
                
            # restore last open file
            if "last_file" in config and config["last_file"] and os.path.exists(config["last_file"]):
                self.current_file = config["last_file"]
                with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as file:
                    self.log_content = file.readlines()
                
                self.statusBar().showMessage(f"File loaded: {os.path.basename(self.current_file)} - {len(self.log_content)} lines")
                self.setWindowTitle(f"LogInsight - {self.current_file}")
                self.result_text.setText("".join(self.log_content))
                
                # add file to watcher if tail mode is enabled
                if self.tail_log_btn.isChecked():
                    self.file_watcher.addPath(self.current_file)
                
        except Exception as e:
            self.statusBar().showMessage(f"Failed to load configuration: {str(e)}")
    
    def save_config(self) -> None:
        """Save current configuration to config file"""
        config = {
            "include_keywords": self.include_entry.text(),
            "exclude_keywords": self.exclude_entry.text(),
            "start_time": self.start_time_entry.text(),
            "end_time": self.end_time_entry.text(),
            "include_case_sensitive": self.include_case_sensitive.isChecked(),
            "exclude_case_sensitive": self.exclude_case_sensitive.isChecked(),
            "word_wrap": self.word_wrap_btn.isChecked(),
            "font_size": self.current_font_size,
            "last_file": self.current_file if self.current_file else "",
            "theme": self.theme_toggle_btn.isChecked(),  # Add theme configuration
            "filter_collapsed": self.filter_collapsed,  # Save filter collapse state
            "button_collapsed": self.button_collapsed  # Save button area collapse state
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.statusBar().showMessage(f"Failed to save configuration: {str(e)}")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event, accept file drops
        
        Args:
            event: Drag enter event object
        """
        # Check if contains file URLs
        if event.mimeData().hasUrls():
            # Only accept file URLs
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop event, open dropped file
        
        Args:
            event: Drop event object
        """
        # Get list of dropped file URLs
        urls = event.mimeData().urls()
        
        # If files were dropped
        if urls:
            # Get local path of first file (only process first file)
            file_path = urls[0].toLocalFile()
            
            # If it's a valid file path, open the file
            if file_path and os.path.isfile(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        self.log_content = file.readlines()
                    
                    # Remove previous file from watcher if exists
                    if self.current_file and self.current_file in self.file_watcher.files():
                        self.file_watcher.removePath(self.current_file)
                    
                    self.current_file = file_path
                    self.statusBar().showMessage(f"File loaded: {os.path.basename(file_path)} - {len(self.log_content)} lines")
                    self.clear_results()
                    self.setWindowTitle(f"LogInsight - {file_path}")
                    
                    # Display log content in results area
                    self.result_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
                    self.result_text.setText("".join(self.log_content))
                    
                    # Add file to watcher if tail mode is active
                    if self.tail_log_btn.isChecked():
                        self.file_watcher.addPath(self.current_file)
                    
                    # Save current configuration
                    self.save_config()
                except Exception as e:
                    self.current_file = None
                    self.clear_results()
                    QMessageBox.critical(self, "Error", f"Cannot open file: {str(e)}")


    def show_help_dialog(self) -> None:
        """Show help dialog with application features and shortcuts"""
        from help_content import get_help_content
        
        help_dialog = QDialog(self)
        help_dialog.setWindowTitle("Log Insight Help")
        help_dialog.setWindowIcon(QIcon(self.get_icon_path('HELP')))
        help_dialog.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(help_dialog)
        
        # Create a QTextEdit to display help content
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        
        # Get help content from the help_content module
        help_content = get_help_content()
        
        help_text.setHtml(help_content)
        layout.addWidget(help_text)
        
        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(help_dialog.accept)
        layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignRight)
        
        help_dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LogInsight()
    window.showMaximized()  
    sys.exit(app.exec())