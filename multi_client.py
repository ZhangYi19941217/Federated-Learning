from fl_client import FederatedClient
import datasource
import multiprocessing
import threading
import time

def start_client():
    print("start client")
    c = FederatedClient("172.31.14.70", 5000, datasource.Mnist)


if __name__ == '__main__':
    jobs = []
    for i in range(10):
        # threading.Thread(target=start_client).start()

        p = multiprocessing.Process(target=start_client)
        jobs.append(p)
        p.start()
        time.sleep(1)
    # TODO: randomly kill
