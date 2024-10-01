import os
import sqlite3
from configparser import ConfigParser


class Database:
    def __init__(self, Develop: bool = False):
        if Develop:
            self.ROOT = r'Downloader\\'
        else:
            self.ROOT = os.path.join(os.getenv('APPDATA'), 'Downloader')
        self.database_filename = 'downloader.db'
        self.table_name = 'download_history'
        self.config_filename = 'config.ini'
        self.config = ConfigParser()
        self.init_database()
        self.init_data_info()
        self.init_download_history_table()

    def init_database(self):
        if not os.path.exists(self.ROOT):
            os.makedirs(self.ROOT)

        db_file = os.path.join(self.ROOT, self.database_filename)
        sqlite3.connect(db_file)

    def check_table_exist(self, tablename):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (tablename, ))
        return True if cursor.fetchone()[0] == 1 else False

    def init_data_info(self):
        if os.path.exists(os.path.join(self.ROOT, self.config_filename)):
            return
        new_section = 'Default'
        self.config.add_section(new_section)
        self.config.set(new_section, 'threads', '5')
        self.config.set(new_section, 'download_dir', './Download')
        self.config.set(new_section, 'retry', '3')
        self.config.set(new_section, 'User-Agent',
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0')

        with open(os.path.join(self.ROOT, self.config_filename), 'w', encoding='utf-8') as f:
            self.config.write(f)
        return
    
    def init_download_history_table(self):
        if self.check_table_exist(self.table_name):
            return
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id INTEGER PRIMARY KEY UNIQUE,
                            filename TEXT NOT NULL,
                            url TEXT NOT NULL,
                            status TEXT NOT NULL,
                            start_time DATETIME NOT NULL,
                            end_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                            size TEXT NOT NULL
                        )""")
        conn.commit()
        conn.close()
        return

    def return_config(self):
        """
        Return: list, [threads, download_dir, retry, User-Agent]
        """
        
        self.config.read(os.path.join(self.ROOT, self.config_filename), encoding='utf-8')
        section = 'Default'
        options = self.config.options(section)
        result = []
        for option in options:
            value = self.config.get(section, option)
            if value.isdigit():
                result.append(int(value))
            else:
                result.append(value)
        return result

    def update_config(self, threads, download_dir, retry, user_agent):
        self.config.read(os.path.join(self.ROOT, self.config_filename), encoding='utf-8')
        section = 'Default'
        self.config.set(section, 'threads', str(threads))
        self.config.set(section, 'download_dir', download_dir)
        self.config.set(section, 'retry', str(retry))
        self.config.set(section, 'User-Agent', user_agent)
        with open(os.path.join(self.ROOT, self.config_filename), 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def add_download_record(self, filename, url, status, start_time, size):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        table_id = self.get_max_id() + 1
        cursor.execute(f"INSERT INTO {self.table_name} (id, filename, url, status, start_time, size) VALUES (?, ?, ?, ?, ?, ?)",
                       (table_id, filename, url, status, start_time, size))
        conn.commit()
        conn.close()
    
    def get_history(self, offset, limit):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM {self.table_name} ORDER BY id DESC LIMIT ?, ?",
            (offset, limit),
        )
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_max_id(self):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"SELECT MAX(id) FROM {self.table_name}")
        max_id = cursor.fetchone()[0]
        if max_id is None:
            max_id = 0
        conn.close()
        return int(max_id)

    def get_records_history(self):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
        total_records = cursor.fetchone()[0]
        if total_records is None:
            total_records = 0
        conn.close()
        return int(total_records)
    
    def get_pages(self):
        total_records = self.get_records_history()
        if total_records == 0:
            return 0
        records_per_page = 20
        pages = (total_records + records_per_page - 1) // records_per_page
        return pages
    
    def get_page_history(self, page):
        """
        从末尾开始获取历史记录，每页20条
        """
        pages = self.get_pages()
        assert page <= pages, f"Page {page} is out of range (1-{pages})"
        total_records = self.get_records_history()
        # offset = total_records - ((page) * 20)
        offset = (page - 1) * 20
        history = self.get_history(offset, 20)
        return history
    
    def delete_history(self, id):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {self.table_name} WHERE id=?", (id,))
        conn.commit()
        conn.close()
    
    def clear_history(self):
        conn = sqlite3.connect(os.path.join(self.ROOT, self.database_filename))
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {self.table_name}")
        conn.commit()
        conn.close()

# if __name__ == "__main__":
d = Database(True)
print(d.return_config())
d.clear_history()
import random
for _ in range(50):
    a = random.random()
    if a < 0.8:
        status = 'ok'
    else:
        status = 'error'
    d.add_download_record(
        f'test{_}', f'http://test{_}.com', status, '2023-03-01 12:00:00', '100MB')
print(d.get_page_history(1))