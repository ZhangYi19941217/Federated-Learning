from fl_client import FederatedClient
import datasource
import multiprocessing
import threading
import time

def start_client(fo_name, f_training_name):
    c = FederatedClient("172.31.14.70", 5000, datasource.Mnist, fo_name, f_training_name)


if __name__ == '__main__':
    jobs = []
    for i in range(3):
        # threading.Thread(target=start_client).start()
        print("start client" + str(i))
        fo_name = "timeline_clinet" + str(i) + ".txt"
        f_training_name = "time_training" + str(i) + ".txt" 
        
        p = multiprocessing.Process(target=start_client, args=(fo_name,f_training_name))
        jobs.append(p)
        p.start()
        #time.sleep(1)
    # TODO: randomly kill
