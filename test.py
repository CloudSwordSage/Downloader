from ctypes import c_ulonglong

import multiprocessing

def add(total, lock):
    for i in range(0, 100000000):
        with lock:
            total.value += 128

def print_result(total):
    while True:
        print(f"\rtotal = {total.value}", end="")

if __name__ == "__main__":
    total = multiprocessing.Value(c_ulonglong, 0)
    lock = multiprocessing.Lock()
    processes = []
    for i in range(10):
        p = multiprocessing.Process(target=add, args=(total, lock))
        processes.append(p)
        p.daemon = True
        p.start()
    
    pr = multiprocessing.Process(target=print_result, args=(total,))
    pr.daemon = True
    pr.start()

    for p in processes:
        p.join()
    
    pr.kill()
