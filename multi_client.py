from fl_client import FederatedClient
from fl_client import FL_run
import datasource
import multiprocessing
import threading
import time

def start_client():
    c = FL_run()


if __name__ == '__main__':
    jobs = []
    for i in range(8):
        # threading.Thread(target=start_client).start()
        print("start client" + str(i))
        fo_name = "timeline_clinet" + str(i) + ".txt"
        f_training_name = "time_training" + str(i) + ".txt"
        
        fo = open(fo_name, "w")
        f_training = open(f_training_name, "w")   
        
        time_start = time.time()
        print("------------------------------------------------time_start: ", time_start)
        fo.write("time_start:    " + str(time_start) + "\n")
        
        p = multiprocessing.Process(target=start_client)
        jobs.append(p)
        p.start()
        #time.sleep(1)
    # TODO: randomly kill
