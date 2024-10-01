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
    QPushButton
    )
from PyQt6.QtGui import (
    QIcon, 
    QFont, 
    QPixmap, 
    QMovie, 
    QPalette, 
    QPen, 
    QColor,
    QPainter
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
import sys
import time
import copy
import requests
import multiprocessing

from data import Database
# from downloader import Downloader


def get_file_size(url, session, headers) -> int:
    head = session.head(url, headers=headers)
    head.raise_for_status()
    file_size = head.headers['Content-Length']
    return int(file_size)

def init_file(filepath):
    with open(filepath, 'wb') as fp:
        pass


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
    total = multiprocessing.Value('i', 0)
    file_size = get_file_size(url, session, headers)
    processes = []
    for start, end in partition(file_size, threads):
        p = multiprocessing.Process(target=download_parts, args=(url, session, lock, start, end, total))
        processes.append(p)
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
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
            self.setFixedSize(900, 700)
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
            d = Database(True)
            d.delete_history(self.data['id'])
            parent_layout = self.parent().parentWidget().layout()
            parent_layout.removeWidget(self.parent())
            self.deleteLater()
        
        def retry(self):
            pass

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.close()
            super().mousePressEvent(event)
        
        def showEvent(self, event) -> None:
            super().showEvent(event)
            self.fadeIn()
        
        def fadeIn(self):
            animation = QPropertyAnimation(self, b"windowOpacity", self)
            animation.setDuration(200)
            animation.setStartValue(0)
            animation.setEndValue(1)
            animation.start()


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.database = Database(True)
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
        self.scroll_area.setStyleSheet("background-color: rgb(135,206,250);")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(5)
        self.scroll_area.setWidget(self.scroll_content)

        self.main_layout.addWidget(self.scroll_area)

        self.setLayout(self.main_layout)
        self.scroll_area.verticalScrollBar().installEventFilter(self)
        self.load_pages()

        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda: self.check_pages_value())
        self.timer.start(100)
    
    def check_pages_value(self):
        current_pages_value = self.database.get_pages()
        if current_pages_value != self.pages:
            self.pages = current_pages_value
            print("Pages value changed:", self.pages)
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

def main():
    database = Database(True)
    threads, download_dir, retry, UA = database.return_config()
    # Downloader.setup_retry_times(int(retry))
    # headers = {'User-Agent': f'{UA}'}
    # download = Downloader(headers=headers, root=download_dir, threads=threads).run()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication([])
    window = Window()
    window.show()
    sys.exit(app.exec())