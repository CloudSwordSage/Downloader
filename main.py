from tkinter.ttk import Style
from PyQt6.QtWidgets import (
    QApplication, 
    QWidget,
    QLabel, 
    QVBoxLayout, 
    QScrollArea,
    QHBoxLayout,
    QFrame,
    QDialog,
    QButtonGroup,
    QPushButton,
    QMessageBox,
    QSpinBox,
    QLineEdit,
    QFileDialog,
    QTextEdit
    )
from PyQt6.QtGui import (
    QIcon, 
    QFont, 
    QPixmap, 
    QMovie, 
    QPalette, 
    QPen, 
    QColor,
    QPainter,
    QTextOption
    )
from PyQt6.QtCore import (
    Qt,
    QEvent,
    pyqtSignal,
    QTimer,
    QPropertyAnimation,
    pyqtSlot
    )

import os
import re
import sys
import time
import copy
import requests
import multiprocessing

from ctypes import c_ulonglong as unsigned_long_long

from data import Database
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)


def get_file_size(url, session, headers) -> int:
    head = session.head(url, headers=headers)
    head.raise_for_status()
    file_size = head.headers['Content-Length']
    return int(file_size)

def init_file(filepath):
    with open(filepath, 'wb') as fp:
        pass

def get_file_name(url):
    filename = re.findall(r"/([^/?]*)(?:\?.*)?$", url)[0]
    return filename


def partition(file_size, threads):
    part_size = file_size // threads
    # parts = []
    for i in range(threads):
        start = i * part_size
        if i == threads - 1:
            end = file_size - 1
        else:
            end = (i + 1) * part_size - 1
        yield start, end
    #     parts.append((start, end))
    # return parts

def download(url, headers, filepath, threads, retry):
    @retry(tries=retry)
    def download_parts(url, session, lock, start, end, total):
        headers = copy.deepcopy(headers)
        headers['Range'] = f'bytes={start}-{end}'
        response = session.get(
            url, headers=headers, stream=True)
        response.raise_for_status()
        chunks = []
        for chunk in response.iter_content(chunk_size=128):
            chunks.append(chunk)
            lock.acquire()
            total.value += len(chunk)
            lock.release()

        lock.acquire()
        f = open(filepath, 'r+b')
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        f.close()
        lock.release()
    
    session = requests.Session()
    lock = multiprocessing.Lock()
    total = multiprocessing.Value(unsigned_long_long, 0)
    file_size = get_file_size(url, session, headers)
    processes = []
    for start, end in partition(file_size, threads):
        p = multiprocessing.Process(target=download_parts, args=(url, session, lock, start, end, total))
        processes.append(p)
        p.daemon = True
        p.start()
    for process in processes:
        process.join()

class DownloadHistory(QWidget):
    clicked = pyqtSignal()
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.id = self.data['id']
        self.border_color = 'red' if self.data['status'].upper() == 'ERROR' else 'green'
        self.background_color = 'rgb(255,69,0)' if self.data['status'].upper() == 'ERROR' else 'rgb(124,252,0)'
        self.initUI()

    def initUI(self):
        self.setFixedHeight(150)

        main_layout = QVBoxLayout(self)

        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)

        layout = QVBoxLayout(frame)
        top_layout = QHBoxLayout()
        
        info = self.data['status'].upper()
        status_label = QLabel(f"状态: {info}", self)
        status_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(status_label)

        time_label = QLabel(f"时间: {self.data['start_time']}  -  {self.data['end_time']}", self)
        time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(time_label)

        layout.addLayout(top_layout)

        download_label = QLabel(
            f"文件名: {self.data['filename']} \t|\t 文件大小: {self.data['size']}", self)
        download_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(download_label)

        main_layout.addWidget(frame)

        self.setLayout(main_layout)

        style = f"""
                QFrame {{
                    background-color: {self.background_color};
                    border: 5px solid {self.border_color};
                    border-radius: 15px;
                }}
                QLabel {{
                            font-family: Arial;
                            color: black;
                            font-size: 20px;
                            background-color: transparent;
                            border: none;
                        }}
                """

        self.setStyleSheet(style)

        self.clicked.connect(self.on_clicked)
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def on_clicked(self):
        self.download_info = self.DownloadInfo(self.data, self)
        self.download_info.exec()
    
    
    class DownloadInfo(QDialog):
        def __init__(self, data, parent=None):
            super().__init__(parent)
            self.data = data
            self.background_color = 'rgb(255,69,0)' if self.data['status'].upper() == 'ERROR' else 'rgb(124,252,0)'
            self.setWindowTitle("下载信息")
            self.setFixedSize(800, 600)
            self.initUI()
        
        def initUI(self):
            self.setStyleSheet(f"background-color: {self.background_color};")
            layout = QVBoxLayout(self)

            title_label = QLabel(f"下载信息: {self.data['filename']}", self)
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)

            id_label = QLabel(f"内部记录ID: {self.data['id']}", self)
            id_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(id_label)

            status_label = QLabel(f"状态: {self.data['status']}", self)
            status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(status_label)

            filename_label = QLabel(f"文件名: {self.data['filename']}", self)
            filename_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(filename_label)

            url_label = QLabel(f"URL: {self.data['url']}", self)
            url_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            url_label.setWordWrap(True)
            layout.addWidget(url_label)

            stime_label = QLabel(f"开始下载时间: {self.data['start_time']}", self)
            stime_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(stime_label)

            etime_label = QLabel(f"结束下载时间: {self.data['end_time']}", self)
            etime_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(etime_label)

            size_label = QLabel(f"文件大小: {self.data['size']}", self)
            size_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            layout.addWidget(size_label)

            inner_layout = QHBoxLayout()

            style = f"""
                        background-color: #ffa500;
                        color: white;
                        padding: 10px 20px;
                        margin: 0 10px;
                        border-radius: 5px;
                        font-weight: bold;
                        text-align: center;
                        font-size: 20px;
                    """

            self.removeHistoryAction = QPushButton("删除记录", self)
            self.removeHistoryAction.clicked.connect(self.remove_history)
            self.removeHistoryAction.setStyleSheet(style)
            inner_layout.addWidget(self.removeHistoryAction)

            self.closeAction = QPushButton("关闭", self)
            self.closeAction.clicked.connect(self.close)
            self.closeAction.setStyleSheet(style)
            inner_layout.addWidget(self.closeAction)

            self.retryAction = QPushButton(
                "重新下载" if self.data['status'].upper() == 'OK' else '重试', self)
            self.retryAction.clicked.connect(self.retry)
            self.retryAction.setStyleSheet(style)
            inner_layout.addWidget(self.retryAction)

            layout.addLayout(inner_layout)

            layout.addStretch(1)

            self.setLayout(layout)
            style = f"""
                    QPushButton {{
                        background-color: #ffa500;
                        color: white;
                        padding: 10px 20px;
                        margin: 0 10px;
                        border-radius: 5px;
                        font-weight: bold;
                        text-align: center;
                    }}
                    """
            self.setStyleSheet(style)
        
        def remove_history(self):
            d = Database(is_Develop)
            d.delete_history(self.data['id'])
            parent_layout = self.parent().parentWidget().layout()
            parent_layout.removeWidget(self.parent())
            self.deleteLater()
        
        def retry(self):
            pass
        
        def showEvent(self, event) -> None:
            super().showEvent(event)
            self.fadeIn()
        
        def fadeIn(self):
            animation = QPropertyAnimation(self, b"windowOpacity", self)
            animation.setDuration(200)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.start()


class Setting(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.database = Database(is_Develop)
        self.threads, self.download_dir, self.retry, self.user_agent = self.database.return_config()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("设置")
        self.setFixedSize(800, 600)
        self.setModal(True)
        self.setStyleSheet("background-color: rgb(135,206,250);")
        self.main_layout = QVBoxLayout(self)

        self.threads_layout = QHBoxLayout()
        self.threads_label = QLabel("下载线程数: ", self)
        self.threads_label.setStyleSheet("font-size: 25px;")
        self.threads_layout.addWidget(self.threads_label)

        self.threads_spinbox = QSpinBox(self)
        self.threads_spinbox.setStyleSheet("font-size: 25px;")
        self.threads_spinbox.setFixedWidth(100)
        self.threads_spinbox.setRange(1, multiprocessing.cpu_count())
        self.threads_spinbox.setValue(self.threads)
        self.threads_layout.addWidget(self.threads_spinbox)

        self.threads_layout.addStretch(1)

        self.main_layout.addLayout(self.threads_layout)

        self.download_dir_layout = QHBoxLayout()

        self.download_dir_label = QLabel("下载目录: ", self)
        self.download_dir_label.setStyleSheet("font-size: 25px;")
        self.download_dir_layout.addWidget(self.download_dir_label)

        self.download_dir_edit = QLineEdit(self)
        self.download_dir_edit.setStyleSheet("font-size: 25px;")
        self.download_dir_edit.setText(self.download_dir)
        self.download_dir_layout.addWidget(self.download_dir_edit)

        self.browse_button = QPushButton("浏览", self)
        self.browse_button.setStyleSheet("font-size: 25px;")
        self.browse_button.clicked.connect(self.browse_directory)
        self.download_dir_layout.addWidget(self.browse_button)

        self.main_layout.addLayout(self.download_dir_layout)

        self.retry_layout = QHBoxLayout()

        self.retry_label = QLabel("重试次数: ", self)
        self.retry_label.setStyleSheet("font-size: 25px;")
        self.retry_layout.addWidget(self.retry_label)

        self.retry_spinbox = QSpinBox(self)
        self.retry_spinbox.setValue(self.retry)
        self.retry_spinbox.setStyleSheet("font-size: 25px;")
        self.retry_spinbox.setFixedWidth(100)
        self.retry_spinbox.setRange(1, 10)

        self.retry_layout.addWidget(self.retry_spinbox)

        self.retry_layout.addStretch(1)

        self.main_layout.addLayout(self.retry_layout)

        self.user_agent_layout = QHBoxLayout()

        self.user_agent_label = QLabel("User-Agent: ", self)
        self.user_agent_label.setStyleSheet("font-size: 25px;")
        self.user_agent_layout.addWidget(self.user_agent_label)

        self.user_agent_edit = QTextEdit(self)
        self.user_agent_edit.setStyleSheet("font-size: 25px;")
        self.user_agent_edit.setText(self.user_agent)
        self.user_agent_edit.setFixedHeight(100)
        self.user_agent_layout.addWidget(self.user_agent_edit)

        self.main_layout.addLayout(self.user_agent_layout)

        for _ in range(2):
            temp = QHBoxLayout()
            temp.addWidget(QLabel(""))
            self.main_layout.addLayout(temp)

        self.button_layout = QHBoxLayout()
        
        style = f"""
                        background-color: #ffa500;
                        color: white;
                        padding: 10px 20px;
                        margin: 0 10px;
                        border-radius: 5px;
                        font-weight: bold;
                        text-align: center;
                        font-size: 20px;
                    """

        self.save_button = QPushButton("保存", self)
        self.save_button.setStyleSheet(style)
        self.save_button.clicked.connect(self.save_setting)
        self.button_layout.addWidget(self.save_button)

        self.reset_button = QPushButton("重置", self)
        self.reset_button.setStyleSheet(style)
        self.reset_button.clicked.connect(self.reset_setting)
        self.button_layout.addWidget(self.reset_button)

        self.close_button = QPushButton("关闭", self)
        self.close_button.setStyleSheet(style)
        self.close_button.clicked.connect(self.close)
        self.button_layout.addWidget(self.close_button)

        self.main_layout.addLayout(self.button_layout)

        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)

    def browse_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "选择下载目录", self.download_dir)
        if directory:
            self.download_dir_edit.setText(directory)
    
    def save_setting(self):
        if not os.path.exists(self.download_dir_edit.text()):
            QMessageBox.warning(self, "警告", "请输入正确的下载目录！", QMessageBox.StandardButton.Ok)
            return
        result = QMessageBox.question(self, "确认", "是否保存全局设置？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.No:
            return
        self.database.update_config(
            threads=self.threads_spinbox.value(),
            download_dir=self.download_dir_edit.text(),
            retry=self.retry_spinbox.value(),
            user_agent=self.user_agent_edit.toPlainText()
        )
        QMessageBox.question(self, "提示", "已保存全局设置.", QMessageBox.StandardButton.Ok)

    def reset_setting(self):
        result = QMessageBox.question(self, "确认", "是否重置全局设置？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.database.reset_config()
            self.threads, self.download_dir, self.retry, self.user_agent = self.database.return_config()
            self.threads_spinbox.setValue(self.threads)
            self.download_dir_edit.setText(self.download_dir)
            self.retry_spinbox.setValue(self.retry)
            self.user_agent_edit.setText(self.user_agent)


class StartDownload(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.database = Database(is_Develop)
        self.threads, self.download_dir, self.retry, self.user_agent = self.database.return_config()
        self.initUI()

    def initUI(self):
        pass


class Window(QWidget):
    def __init__(self):
        super(Window, self).__init__()
        self.database = Database(is_Develop)
        self.pages = self.database.get_pages()
        self.count = 1
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Multi-process Downloader")
        self.setGeometry(200, 200, 800, 600)
        self.setFixedSize(800, 600)
        self.setWindowIcon(QIcon('./assets/app_icon.ico'))
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(135, 206, 250))
        self.setPalette(palette)

        self.main_layout = QVBoxLayout()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setStyleSheet("background-color: rgb(135,206,250);")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(5)
        self.scroll_area.setWidget(self.scroll_content)

        self.main_layout.addWidget(self.scroll_area)

        self.button_layout = QVBoxLayout()

        self.addDownloadTask = QPushButton("添加下载任务", self)
        self.addDownloadTask.setObjectName("button")
        self.addDownloadTask.clicked.connect(self.add_download_task)
        self.button_layout.addWidget(self.addDownloadTask)

        self.setting = QPushButton("设置", self)
        self.setting.setObjectName("button")
        self.setting.clicked.connect(self.open_setting)
        self.button_layout.addWidget(self.setting)

        self.cleanAction = QPushButton("清除历史记录", self)
        self.cleanAction.setObjectName("button")
        self.cleanAction.clicked.connect(self.clear_history)
        self.button_layout.addWidget(self.cleanAction)

        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addStretch(1)
        self.bottom_layout.addLayout(self.button_layout)

        self.main_layout.addLayout(self.bottom_layout)

        style = """
                    QWidget {
                        background-color: rgb(135,206,250);
                    }
                    QScrollArea {
                        background-color: rgb(135,206,250);
                    }
                    QHBoxLayout {
                        background-color: rgb(135,206,250);
                        margin-left: 0px;
                        margin-right: 0px;
                        margin-bottom: 0px;
                    }
                    QPushButton#button {
                        background-color: rgb(255,206,250);
                        position: absolute;
                        bottom: 10px;
                        left: 10px;
                    }
                """
        self.setStyleSheet(style)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)

        self.setLayout(self.main_layout)
        self.scroll_area.verticalScrollBar().installEventFilter(self)
        self.load_pages()

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.check_pages_value())
        self.timer.start(10)
    
    def check_pages_value(self):
        current_pages_value = self.database.get_pages()
        if current_pages_value != self.pages:
            self.pages = current_pages_value
            self.count = 1
            self.clear_scroll_area()
            self.load_pages()
    
    def clear_scroll_area(self):
        for i in range(self.scroll_layout.count(), 0, -1):
            widget = self.scroll_layout.itemAt(i-1).widget()
            if widget is not None:
                self.scroll_layout.removeWidget(widget)
                widget.deleteLater()
    
    def eventFilter(self, source, event):
        if source == self.scroll_area.verticalScrollBar():
            self.check_scroll_position()
        return super().eventFilter(source, event)

    def check_scroll_position(self):
        scrollbar = self.scroll_area.verticalScrollBar()
        max_value = scrollbar.maximum()
        current_value = scrollbar.value()
        threshold = 20

        if max_value - current_value <= threshold:
            if self.count <= self.pages:
                self.load_pages()

    def load_pages(self):
        if self.count > self.pages:
            return
        data = self.database.get_page_history(self.count)
        for item in data:
            entry = {
                'id': item[0],
                'filename': item[1],
                'url': item[2],
                'status': item[3],
                'start_time': item[4],
                'end_time': item[5],
                'size': item[6]
            }
            self.scroll_layout.addWidget(DownloadHistory(entry))
        self.count += 1
    
    def add_download_task(self):
        print("add_download_task")
        pass
    
    def open_setting(self):
        setting = Setting(self)
        setting.exec()
    
    def clear_history(self):
        result = QMessageBox.question(self, "确认", "是否删除所有历史记录？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if result == QMessageBox.StandardButton.Yes:
            self.database.clear_history()
            self.clear_scroll_area()

def main():
    database = Database(is_Develop)
    threads, download_dir, retry, UA = database.return_config()
    # Downloader.setup_retry_times(int(retry))
    # headers = {'User-Agent': f'{UA}'}
    # download = Downloader(headers=headers, root=download_dir, threads=threads).run()

if __name__ == "__main__":
    is_Develop = True
    multiprocessing.freeze_support()
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())