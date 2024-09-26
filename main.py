import os
import re
import copy
import requests
import multiprocessing
import hashlib
from retry import retry

class Downloader:
    retry_times = 3
    def __init__(self, url: str, headers: dict=None, root: str='./', threads: int=5):
        """
        初始化函数，用于创建一个新的下载器对象。
        
        Args:
            url (str): 需要下载的文件的URL地址。
            headers (dict, optional): 自定义请求头。默认为None。
            root (str, optional): 本地保存文件的根目录。默认为当前目录。
            threads (int, optional): 使用的线程数。默认为5。
        
        """
        self.url = url
        self.headers = headers
        self.filename = re.findall(r"[^/]+$", url)[0]
        self.root = root
        self.threads = threads
        self.filepath = os.path.join(root, self.filename)
        self.session = requests.Session()

        if os.path.exists(self.filepath):
            os.remove(self.filepath)
        with open(self.filepath, 'wb') as f:
            pass
    
    def check_file(self):
        """
        检查本地文件是否与远程文件一致。
        
        Returns:
            bool: 如果本地文件与远程文件不一致，返回True；否则返回False。
        
        """
        head = self.session.head(self.url, headers=self.headers)
        head.raise_for_status()
        try:
            md5 = head.headers['Content-MD5']
        except KeyError:
            return None
        with open(self.filepath, mode='rb') as f:
            content = f.read()
            local_md5 = hashlib.md5(content).hexdigest()
            if local_md5 != md5:
                return False
        return True

    @property
    def partition(self):
        """
        将文件按照线程数进行分区，并返回每个分区的起始和结束位置。
        
        Returns:
            List[Tuple[int, int]]: 包含多个元组的列表，每个元组表示一个分区的起始和结束位置。
        
        """
        file_size = self.get_file_size()
        part_size = file_size // self.threads
        parts = []
        for i in range(self.threads):
            start = i * part_size
            if i == self.threads - 1:
                end = file_size - 1
            else:
                end = (i + 1) * part_size - 1
            parts.append((start, end))
        return parts
    
    def get_file_size(self):
        """
        获取文件大小。
        
        Returns:
            int: 返回文件大小，单位为字节。
        
        Raises:
            HTTPError: 如果请求失败，则会抛出HTTPError异常。
        """
        head = self.session.head(self.url, headers=self.headers)
        head.raise_for_status()
        file_size = head.headers['Content-Length']
        return int(file_size)
    
    @classmethod
    def setup_retry_times(cls, times):
        """
        设置重试次数。
        
        Args:
            times: 重试次数，整型。
        
        """
        cls.retry_times = times

    @retry(tries=retry_times)
    def download_parts(self, lock: object, start: int, end: int, total: int):
        """
        下载文件的一部分内容，并写入到本地文件中。
        
        Args:
            start (int): 下载内容的起始位置（字节）。
            end (int): 下载内容的结束位置（字节）。
        
        """
        headers = copy.deepcopy(self.headers)
        headers['Range'] = f'bytes={start}-{end}'
        response = self.session.get(
            self.url, headers=headers, stream=True)
        response.raise_for_status()
        chunks = []
        for chunk in response.iter_content(chunk_size=128):
            chunks.append(chunk)
            lock.acquire()
            total.value += len(chunk)
            lock.release()

        lock.acquire()
        f = open(self.filepath, 'r+b')
        f.seek(start)
        for chunk in chunks:
            f.write(chunk)
        f.close()
        lock.release()

    def print_progress(self, total):
        file_size = self.get_file_size()
        while True:
            print(f"\r{total.value / 1024 ** 2:.2f}MB /{file_size / 1024 ** 2:.2f}MB", end='\t\t\t')
    
    def run(self):
        """
        下载指定分片区间的文件并合并。

        Returns:
            bool: True, 检测函数运行是否结束...tips：为了后续处理做的准备
        
        """
        lock = multiprocessing.Lock()
        total = multiprocessing.Value('i', 0)
        file_size = self.get_file_size()
        parts = self.partition
        processes = []
        for start, end in parts:
            p = multiprocessing.Process(
                target=self.download_parts, args=(lock, start, end, total))
            p.start()
            processes.append(p)
        
        pr = multiprocessing.Process(target=self.print_progress, args=(total,))
        pr.start()

        for p in processes:
            p.join()
        
        pr.kill()
        print()

        if self.check_file() is None:
            print("Server Not MD5")
        elif self.check_file():
            print(f"{self.filename} download success, MD5 match")
        print('-'*30, "File Size", '-'*30)
        print("本地文件大小：", os.path.getsize(self.filepath))
        print("远程文件大小：", file_size)

        return True

if __name__ == '__main__':
    url = r"https://dldir1.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.15_240925_x64_01.exe"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0'
    }

    d = Downloader(url, headers=headers, threads=5)
    d.run()