import pickle
import keras
import uuid
from keras.models import Sequential
from keras.layers import Dense, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D, BatchNormalization
from keras.optimizers import Adam
from keras import backend as K

import msgpack
import random
import codecs
import numpy as np
import json
import msgpack_numpy
# https://github.com/lebedov/msgpack-numpy
import sys
import time

from flask import *
from flask_socketio import SocketIO
from flask_socketio import *
# https://flask-socketio.readthedocs.io/en/latest/
       

class GlobalModel(object):
    """docstring for GlobalModel"""
    def __init__(self):
        self.model = self.build_model()
        self.current_weights = self.model.get_weights()
        # for convergence check
        self.prev_train_loss = None

        # all rounds; losses[i] = [round#, timestamp, loss]
        # round# could be None if not applicable
        self.train_losses = []
        self.valid_losses = []
        self.train_accuracies = []
        self.valid_accuracies = []

        self.training_start_time = int(round(time.time()))
        
    
    def build_model(self):
        raise NotImplementedError()

    # client_updates = [(w, n)..]
    def update_weights(self, client_weights, client_sizes):
        
        time_start_update_weights = time.time()
        print("--------------------------------------------time_start_update_weights: ", time_start_update_weights-time_start)
        #fo.write("*" + "    time_start_update_weights:    " + str(time_start_update_weights) + "\n")
        
        
        new_weights = [np.zeros(w.shape) for w in self.current_weights]
        total_size = np.sum(client_sizes)
        sum_break = 0
        
        for c in range(len(client_weights)):
            for i in range(len(new_weights)):
                if client_weights[c][i]=='K' or client_weights[c][i]=='g':
                    total_size -= client_sizes[c]
                    break;
                
        print(client_weights[c][i][0], "------------------------------------------------------------------: " + str(type(client_weights[c][i][0])) )
        
        
        print("------------total_size=", total_size)
        
        for c in range(len(client_weights)):
            for i in range(len(new_weights)):
                #print("------------c=", c, "------------i=", i)
                #print(client_weights[c][i])
                if client_weights[c][i]=='K' or client_weights[c][i]=='g':
                    sum_break += 1
                    break
                new_weights[i] += client_weights[c][i] * client_sizes[c] / total_size
        self.current_weights = new_weights
        print("-----------sum_break: ", sum_break)
        
        time_finish_update_weights = time.time()
        print("-------------------------------------------time_finish_update_weights: ", time_finish_update_weights-time_start)
        #fo.write("*" + "    time_finish_update_weights:    " + str(time_finish_update_weights) + "\n")
        
        

    def aggregate_loss_accuracy(self, client_losses, client_accuracies, client_sizes):
        total_size = np.sum(client_sizes)
        # weighted sum
        aggr_loss = np.sum(client_losses[i] / total_size * client_sizes[i]
                for i in range(len(client_sizes)))
        aggr_accuraries = np.sum(client_accuracies[i] / total_size * client_sizes[i]
                for i in range(len(client_sizes)))
        return aggr_loss, aggr_accuraries

    # cur_round coule be None
    def aggregate_train_loss_accuracy(self, client_losses, client_accuracies, client_sizes, cur_round):
        cur_time = int(round(time.time())) - self.training_start_time
        aggr_loss, aggr_accuraries = self.aggregate_loss_accuracy(client_losses, client_accuracies, client_sizes)
        self.train_losses += [[cur_round, cur_time, aggr_loss]]
        self.train_accuracies += [[cur_round, cur_time, aggr_accuraries]]
        with open('stats.txt', 'w') as outfile:
            json.dump(self.get_stats(), outfile)
        return aggr_loss, aggr_accuraries

    # cur_round coule be None
    def aggregate_valid_loss_accuracy(self, client_losses, client_accuracies, client_sizes, cur_round):
        cur_time = int(round(time.time())) - self.training_start_time
        aggr_loss, aggr_accuraries = self.aggregate_loss_accuracy(client_losses, client_accuracies, client_sizes)
        self.valid_losses += [[cur_round, cur_time, aggr_loss]]
        self.valid_accuracies += [[cur_round, cur_time, aggr_accuraries]]
        with open('stats.txt', 'w') as outfile:
            json.dump(self.get_stats(), outfile)
        return aggr_loss, aggr_accuraries

    def get_stats(self):
        return {
            "train_loss": self.train_losses,
            "valid_loss": self.valid_losses,
            "train_accuracy": self.train_accuracies,
            "valid_accuracy": self.valid_accuracies
        }
        

class GlobalModel_MNIST_CNN(GlobalModel):
    def __init__(self):
        super(GlobalModel_MNIST_CNN, self).__init__()

    def build_model_CNN(self):
        # ~5MB worth of parameters
        model = Sequential()
        model.add(Conv2D(32, kernel_size=(3, 3),
                         activation='relu',
                         input_shape=(28, 28, 1)))
        model.add(Conv2D(64, (3, 3), activation='relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))
        model.add(Flatten())
        model.add(Dense(128, activation='relu')) 
        model.add(Dropout(0.5))
        model.add(Dense(10, activation='softmax'))

        model.compile(loss=keras.losses.categorical_crossentropy,
                      optimizer=keras.optimizers.Adadelta(),
                      metrics=['accuracy'])
        return model

    def build_model(self):
        # ~?MB worth of parameters
        model = Sequential()
        model.add(Conv2D(96,(3,3),strides=(2,2),input_shape=(32,32,3),padding='same',activation='relu'))
        model.add(MaxPooling2D(pool_size=(2,2),strides=(2,2))) 
        model.add(BatchNormalization())
        
        model.add(Conv2D(256,(5,5),strides=(1,1),padding='same',activation='relu'))
        model.add(MaxPooling2D(pool_size=(3,3),strides=(2,2)))
        model.add(BatchNormalization())
        
        model.add(Conv2D(384,(3,3),strides=(1,1),padding='same',activation='relu'))
        model.add(Conv2D(384,(3,3),strides=(1,1),padding='same',activation='relu'))
        model.add(Conv2D(256,(3,3),strides=(1,1),padding='same',activation='relu'))
        model.add(MaxPooling2D(pool_size=(3,3),strides=(2,2)))
        model.add(BatchNormalization())
        
        model.add(Flatten())
        model.add(Dense(4096, activation='tanh')) 
        model.add(Dropout(0.5))
        model.add(Dense(2048, activation='tanh')) 
        model.add(Dropout(0.5))
        model.add(Dense(10,activation='softmax'))

        model.compile(loss='categorical_crossentropy',
                      optimizer=Adam(),
                      metrics=['accuracy'])
        
        return model


        
######## Flask server with Socket IO ########

# Federated Averaging algorithm with the server pulling from clients

class FLServer(object):
    
    MIN_NUM_WORKERS = 50
    MAX_NUM_ROUNDS = 3
    NUM_CLIENTS_CONTACTED_PER_ROUND = 50
    ROUNDS_BETWEEN_VALIDATIONS = 2

    def __init__(self, global_model, host, port):
        self.global_model = global_model()

        self.ready_client_sids = set()

        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app)
        self.host = host
        self.port = port

        self.model_id = str(uuid.uuid4())

        #####
        # training states
        self.current_round = -1  # -1 for not yet started
        self.current_round_client_updates = []
        self.eval_client_updates = []
        #####

        # socket io messages
        self.register_handles()


        @self.app.route('/')
        def dashboard():
            return render_template('dashboard.html')

        @self.app.route('/stats')
        def status_page():
            return json.dumps(self.global_model.get_stats())

        
    def register_handles(self):
        # single-threaded async, no need to lock

        @self.socketio.on('connect')
        def handle_connect():
            with open("clients.txt", 'a') as f_client:
                f_client.write(request.sid + "\n")
            print(request.sid, "connected")

        @self.socketio.on('reconnect')
        def handle_reconnect():
            print(request.sid, "reconnected")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print(request.sid, "disconnected")
            if request.sid in self.ready_client_sids:
                self.ready_client_sids.remove(request.sid)

        @self.socketio.on('client_wake_up')
        def handle_wake_up():
            print("client wake_up: ", request.sid)
            emit('init', {
                    'model_json': self.global_model.model.to_json(),
                    'model_id': self.model_id,
                    'min_train_size': 1200,
                    'data_split': (0.6, 0.3, 0.1), # train, test, valid
                    'epoch_per_round': 1,
                    'batch_size': 10
                })

        @self.socketio.on('client_ready')
        def handle_client_ready(data):
            print("client ready for training", request.sid, data)
            self.ready_client_sids.add(request.sid)
            if len(self.ready_client_sids) >= FLServer.MIN_NUM_WORKERS and self.current_round == -1:
                self.train_next_round()

        @self.socketio.on('client_update')
        def handle_client_update(data):
            
            
            time_start_client_update = time.time()
            
            with open("timeline_server.txt", 'a') as fo:
                fo.write(str(self.current_round) + "    " + request.sid + "    time_start_client_update:    " + str(time_start_client_update) + "\n")
            print("-------------------------------------------time_start_client_update: ", time_start_client_update-time_start)
            
            
            print("received client update of bytes: ", sys.getsizeof(data))
            print("handle client_update", request.sid)
            for x in data:
                if x != 'weights':
                    print(x, data[x])
            # data:
            #   weights
            #   train_size
            #   valid_size
            #   train_loss
            #   train_accuracy
            #   valid_loss?
            #   valid_accuracy?

            # discard outdated update
            if data['round_number'] == self.current_round:
                self.current_round_client_updates += [data]
                self.current_round_client_updates[-1]['weights'] = pickle_string_to_obj(data['weights'])
                
                # tolerate 30% unresponsive clients
                
                if len(self.current_round_client_updates) == FLServer.NUM_CLIENTS_CONTACTED_PER_ROUND * 1:
                    
                    time_start_js = time.time()
                    
                    self.global_model.update_weights(
                        [x['weights'] for x in self.current_round_client_updates],
                        [x['train_size'] for x in self.current_round_client_updates],
                    )
                    
                    time_end_js = time.time()
                    
                    with open("time_jisuan.txt", 'a') as f_js:
                        f_js.write(str(self.current_round) + "    time_js:    " + str(time_end_js-time_start_js) + "\n")
                    
                    aggr_train_loss, aggr_train_accuracy = self.global_model.aggregate_train_loss_accuracy(
                        [x['train_loss'] for x in self.current_round_client_updates],
                        [x['train_accuracy'] for x in self.current_round_client_updates],
                        [x['train_size'] for x in self.current_round_client_updates],
                        self.current_round
                    )
    
                    print("aggr_train_loss", aggr_train_loss)
                    print("aggr_train_accuracy", aggr_train_accuracy)
                    
                    if 'valid_loss' in self.current_round_client_updates[0]:
                        aggr_valid_loss, aggr_valid_accuracy = self.global_model.aggregate_valid_loss_accuracy(
                            [x['valid_loss'] for x in self.current_round_client_updates],
                            [x['valid_accuracy'] for x in self.current_round_client_updates],
                            [x['valid_size'] for x in self.current_round_client_updates],
                            self.current_round
                        )
                        print("aggr_valid_loss", aggr_valid_loss)
                        print("aggr_valid_accuracy", aggr_valid_accuracy)
                        
                        

                    time_finish_client_update = time.time()
                    print("---------------------------------time_finish_client_update: ", time_finish_client_update-time_start)
                    #fo.write(str(self.current_round) + "    time_finish_client_update:    " + str(time_finish_client_update) + "\n")

                    
                    if self.global_model.prev_train_loss is not None and \
                            (self.global_model.prev_train_loss - aggr_train_loss) / self.global_model.prev_train_loss < .01:
                        # converges
                        print("converges! starting test phase..")
                        self.stop_and_eval()
                        return
                    
                    self.global_model.prev_train_loss = aggr_train_loss

                    if self.current_round >= FLServer.MAX_NUM_ROUNDS:
                        self.stop_and_eval()
                    else:
                        self.train_next_round()

        @self.socketio.on('client_eval')
        def handle_client_eval(data):
            if self.eval_client_updates is None:
                return
            print("handle client_eval", request.sid)
            print("eval_resp", data)
            self.eval_client_updates += [data]

            # tolerate 30% unresponsive clients
            if len(self.eval_client_updates) == FLServer.NUM_CLIENTS_CONTACTED_PER_ROUND * 1:
                aggr_test_loss, aggr_test_accuracy = self.global_model.aggregate_loss_accuracy(
                    [x['test_loss'] for x in self.eval_client_updates],
                    [x['test_accuracy'] for x in self.eval_client_updates],
                    [x['test_size'] for x in self.eval_client_updates],
                );
                print("\naggr_test_loss", aggr_test_loss)
                print("aggr_test_accuracy", aggr_test_accuracy)
                print("== done ==")
                self.eval_client_updates = None  # special value, forbid evaling again

    
    # Note: we assume that during training the #workers will be >= MIN_NUM_WORKERS
    def train_next_round(self):
        
        self.current_round += 1
        # buffers all client updates
        self.current_round_client_updates = []

        print("### Round ", self.current_round, "###")
        client_sids_selected = random.sample(list(self.ready_client_sids), FLServer.NUM_CLIENTS_CONTACTED_PER_ROUND)
        print("request updates from", client_sids_selected)

        # by default each client cnn is in its own "room"
       
        for rid in client_sids_selected:
            time_start_train_next_round = time.time()
            print("-----------------------------------------time_start_train_next_round: ", time_start_train_next_round-time_start)
            
            with open("timeline_server.txt", 'a') as fo:
                fo.write(str(self.current_round) + "    " + rid + "    time_start_train_next_round:    " + str(time_start_train_next_round) + "\n")
        
            emit('request_update', {
                    'model_id': self.model_id,
                    'round_number': self.current_round,
                    'current_weights': obj_to_pickle_string(self.global_model.current_weights),

                    'weights_format': 'pickle',
                    'run_validation': self.current_round % FLServer.ROUNDS_BETWEEN_VALIDATIONS == 0,
                }, room=rid)
            
        time_finish_train_next_round = time.time()
        print("---------------------------------------time_finish_train_next_round: ", time_finish_train_next_round-time_start)
        #fo.write(str(self.current_round) + "    time_finish_train_next_round:    " + str(time_finish_train_next_round) + "\n")

    
    def stop_and_eval(self):
        self.eval_client_updates = []
        for rid in self.ready_client_sids:
            emit('stop_and_eval', {
                    'model_id': self.model_id,
                    'current_weights': obj_to_pickle_string(self.global_model.current_weights),
                    'weights_format': 'pickle'
                }, room=rid)

    def start(self):
        self.socketio.run(self.app, host=self.host, port=self.port)



def obj_to_pickle_string(x):
    return codecs.encode(pickle.dumps(x), "base64").decode()
    #return pickle.dumps(x)
    # return msgpack.packb(x, default=msgpack_numpy.encode)
    # TODO: compare pickle vs msgpack vs json for serialization; tradeoff: computation vs network IO

def pickle_string_to_obj(s):
    return pickle.loads(codecs.decode(s.encode(), "base64"))
    #return pickle.loads(s)
    # return msgpack.unpackb(s, object_hook=msgpack_numpy.decode)


if __name__ == '__main__':
    # When the application is in debug mode the Werkzeug development server is still used
    # and configured properly inside socketio.run(). In production mode the eventlet web server
    # is used if available, else the gevent web server is used.

    
    time_start = time.time()
    with open("timeline_server.txt", 'a') as fo:
        fo.write("*    " + "*    " + "time_start:    " + str(time_start) + "\n")
    print("------------------------------------------------time_start: ", time_start)
       
    server = FLServer(GlobalModel_MNIST_CNN, "172.31.14.70", 5000)
    print("listening on 172.31.14.70:5000");
    server.start()
