import keras
from keras.preprocessing import sequence
from keras.models import Model
from keras.models import save_model, load_model
from keras.layers import Input, Embedding, LSTM, Dense, Concatenate
from keras.layers import TimeDistributed, Bidirectional
from keras.utils import plot_model
from keras import backend as K
import tensorflow as tf
from tensorflow.python import debug as tf_debug
from tensorflow.python.debug.lib.debug_data import has_inf_or_nan
from tensorflow.keras.backend import eval

import re
import sys
from pathlib import Path
import json
import time
from datetime import datetime, timedelta
import math
import numpy as np
from pprint import pprint
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from scraper import load_race_data, fetch_predicting_data

# Hyper parameters
input_dim = 17
output_dim = 18
n_hidden = 1024
epochs = 1000
batch_size = 32
maxlen = 18
is_train = False


class BidirectionalLSTMModel:

    def __init__(self, maxlen, input_dim, output_dim, n_hidden):
        self.maxlen = maxlen
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.n_hidden = n_hidden

    def build_model(self):
        # Encoder
        # enc_input = Input(shape=(self.maxlen, self.input_dim), dtype='float32', name='encoder_input')  # todo: maxlen->Noneでいいかも
        # enc_bilstm, [state_h, state_c] = Bidirectional(LSTM(self.n_hidden, name='encoder_bilstm', return_sequences=True))(enc_input)
        # enc_state = [state_h, state_c]
        # enc_model = Model(input_shape=enc_input, outputs=[enc_bilstm, state_h, state_c])

        # Decoder
        # dec_lstm = LSTM(self.n_hidden, name='decoder_lstm', return_state=True)()
        # dec_dense = Dense(self.output_dim, activation='softmax', name='decoder_dense')

        inputs = Input(shape=(self.maxlen, self.input_dim), dtype='float32', name='inputs')
        bilstm = Bidirectional(LSTM(self.n_hidden, return_sequences=False, activation='relu', name='bilstm1'),
                                                    input_shape=(self.maxlen, self.input_dim))(inputs)
        # state_h = Concatenate()([f_h, b_h])
        # state_c = Concatenate()([f_c, b_c])
        # bilstm = Bidirectional(LSTM(self.n_hidden, activation='tanh', name='bilstm2'))(state_h)
        # dense = TimeDistributed(Dense(self.output_dim, activation='softmax', name='dense'),
        #                         input_shape=(self.maxlen, self.n_hidden))(bilstm)
        dense = Dense(self.output_dim, activation='softmax', name='dense')(bilstm)

        model = Model(inputs=inputs, outputs=dense)
        adam = tf.keras.optimizers.Adam(lr=1e-3, beta_1=0.9, beta_2=0.999, epsilon=None, decay=0.0, amsgrad=False)
        adagrad = tf.keras.optimizers.Adagrad(lr=0.01, epsilon=1e-06)
        sgd = keras.optimizers.SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

        model.compile(loss='categorical_crossentropy',
                      optimizer=adam,
                      metrics=['accuracy'])
        return model

    def multi_crossentropy(self, y_true, y_pred):
        return tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(y_true, y_pred))

    def train(self, x_input, y_input, batch_size, epochs):
        print("[bilstm] build ...")
        model = self.build_model()

        x_i = x_input
        y_i = y_input
        z = list(zip(x_i, y_i))
        np.random.shuffle(z)  # シャッフル
        x_i, y_i = zip(*z)  # unzip z into x_i and y_i

        x_i = np.array(x_i).reshape(len(x_i), self.maxlen)
        y_i = np.array(y_i).reshape(len(y_i), self.maxlen)

        n_split = int(x_i.shape[0] * 0.9)  # 訓練データとテストデータを9:1に分割
        x_train, x_val = np.vsplit(x_i, [n_split])
        y_train, y_val = np.vsplit(y_i, [n_split])

        print("[bilstm] train ...")
        for j in range(0, epochs):
            print("Epoch {}/{}".format(j + 1, epochs))
            self.on_batch(model, x_train, y_train, x_val, y_val)
        return model

    def on_batch(self, model, x_train, y_train, x_val, y_val, batch_size):
        # 損失関数、評価関数の平均計算用リスト
        list_loss = []
        list_accuracy = []

        s_time = time.time()
        row = x_train.shape[0]  # 1バッチに含まれるサンプル数
        n_batch = math.ceil(row / batch_size)  # x_trainに含まれるバッチ数

        for i in range(0, n_batch):
            s = i * batch_size
            e = min([(i + 1) * batch_size, row])  # x_trainのケツインデックスを考慮している
            x_on_batch = x_train[s: e, :]
            y_on_batch = y_train[s: e, :]
            result = model.train_on_batch(x_on_batch, y_on_batch)
            list_loss.append(result[0])  # todo: モデルが単一の出力かつ評価関数なし？なので戻り値はスカラ値の可能性あり
            list_accuracy.append(result[1])

            elased_time = time.time() - s_time
            sys.stdout.write("TRAIN\r{}/{} time: {}s\tloss: {0:.4f}\taccuracy: {0:.4f}".format(
                str(e), str(row), str(int(elased_time)),
                np.average(list_loss), np.average(list_accuracy)))
            sys.stdout.flush()
            del x_on_batch, y_on_batch

        self.valid(model, x_val, y_val, batch_size)
        return

    def valid(self, model, x_val, y_val, batch_size):
        list_loss = []
        list_accuracy = []
        row = x_val.shape[0]

        s_time = time.time()
        n_batch = math.ceil(row / batch_size)

        n_loss = 0
        sum_loss = 0.0
        for i in range(0, n_batch):
            s = i * batch_size
            e = min([(i + 1) + batch_size, row])
            x_on_batch = x_val[s: e, :]
            y_on_batch = y_val[s: e, :]
            result = model.test_on_batch(x_on_batch, y_on_batch)
            list_loss.append(result[0])
            list_accuracy.append(result[1])

            elased_time = time.time() - s_time
            sys.stdout.write("VALID\r{}/{} time: {}s\tloss: {0:.4f}\taccuracy: {0:.4f}".format(
                str(e), str(row), str(int(elased_time)),
                np.average(list_loss), np.average(list_accuracy)))
            sys.stdout.flush()
            del x_on_batch, y_on_batch
        return


    def get_batch(self):
        pass


# def arrival_order_to_one_hot(arrival_order, maxlen):
    # one_hot = np.identity(maxlen)arrival_order
    # one_hot = np.zeros((maxlen, maxlen))
    # for i in arrival_order:
    #     one_hot[i][i] = 1.0
    # return one_hot


def load(maxlen, n_feature=17):
    list_score_and_racehead, list_arrival_order = load_race_data()
    # labels = arrival_order_to_one_hot(list_arrival_order, 18)

    list_sr = []
    for score_and_racehead in list_score_and_racehead:
        score_and_racehead = np.array(score_and_racehead)
        if score_and_racehead.shape[0] < maxlen:
            zero_vecs = np.zeros((1, n_feature))
            for i in range(maxlen - len(score_and_racehead)):
                # print(score_and_racehead.shape, zero_vecs.shape)
                score_and_racehead = np.vstack((score_and_racehead, zero_vecs))
        score_and_racehead = np.array(score_and_racehead, dtype=np.float32)
        list_sr.append(score_and_racehead)

    list_label = []
    for arrival_order in list_arrival_order:
        for i in range(maxlen - len(arrival_order)):
            arrival_order.append(0)

        for i in range(len(arrival_order)):
            try:
                if isinstance(arrival_order[i], str):
                    print(arrival_order[i])
                arrival_order[i] = 1.0 / arrival_order[i]
            except ZeroDivisionError:
                pass

        arrival_order = np.array(arrival_order, dtype=np.float32)
        arrival_order /= arrival_order.sum(axis=0)

        # try:
        #     label = np.eye(maxlen)[arrival_order]
        # except IndexError as e:
        #     print(e)
        # if label.shape[0] < maxlen:
        #     for i in range(maxlen - label.shape[0]):
        #         zero_label = np.zeros(maxlen)
        #         label = np.vstack((label, zero_label))
        list_label.append(arrival_order)

    # shuffle each race information including max to 18 horses
    for i in range(len(list_sr)):
        seed = np.random.randint(1, 100)
        np.random.seed(seed)
        np.random.shuffle(list_sr[i])
        np.random.seed(seed)
        np.random.shuffle(list_label[i])

    train_x = np.array(list_sr, dtype=np.float32)
    train_y = np.array(list_label, dtype=np.float32)

    print(train_x.shape)
    print(train_y.shape)

    for i in range(train_x.shape[0]):
        for j in range(train_x.shape[1]):
            for k in range(train_x.shape[2]):
                if np.isnan(train_x[i,j,k]):
                    print(i, j, train_x[i,j])
                if np.isinf(train_x[i,j,k]):
                    print(i, j, train_x[i, j])
                # print(np.isinf(train_x[i,j]))
            # print(train_x[i,j])
    print(np.isinf(train_y))

    return train_x, train_y

def train(train_x, train_y, maxlen, model_name):
    print("train_x", train_x.shape)
    print("train_y", train_y.shape)

    early_stopping = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        min_delta=0.0,
        patience=10,
    )

    # val_lossの改善が2エポック見られなかったら、学習率を0.5倍する。
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=2,
        min_lr=0.0001
    )

    BLM = BidirectionalLSTMModel(maxlen=maxlen,
                                 input_dim=input_dim,
                                 output_dim=output_dim,
                                 n_hidden=n_hidden)
    model = BLM.build_model()
    result = model.fit(train_x, train_y, batch_size=batch_size, epochs=epochs, verbose=1,
                       callbacks=[])

    plot_model(model, show_shapes=True, to_file='{}.png'.format(model_name))
    save_model(model, '{}.h5'.format(model_name))

    return model, result


def predict(model_name, input_dim):
    model = load_model('{}.h5'.format(model_name))
    url = 'https://keiba.yahoo.co.jp/race/result/2005020811/'

    score_and_racehead = fetch_predicting_data(url)

    # popularity
    # odds = []
    # for sr in score_and_racehead:
    #     odds.append(sr[9])
    # popurarities = np.array(odds).argsort()
    # popurs = []
    # for i in range(maxlen):
    #     if i >= popurarities.shape[0]:
    #         break
    #     #     popurarities = np.append(popurarities, 0)
    #     # else:
    #     popurs.append([popurarities[i] + 1])
    # popurs = np.array([popurs])

    test_x = np.array([score_and_racehead])
    # test_x = np.insert(test_x, [10], popurs, axis=2)

    if test_x.shape[0] < maxlen:
        for i in range(maxlen - test_x.shape[1]):
            zero_label = np.array([[[0] * input_dim]])  # input_dim = 17
            test_x = np.append(test_x, zero_label, axis=1)

    y = model.predict(test_x, batch_size=1, verbose=0, steps=None)
    return y


# FIXME: TF2.0以上ではsessionがないため使えない
def set_debugger_session():
    sess = K.get_session()
    sess = tf_debug.LocalCLIDebugWrapperSession(sess)
    sess.add_tensor_filter('has_inf_or_nan', has_inf_or_nan)
    K.set_session(sess)


def draw_race_result(result_mat):
    # todo: copy draw code
    return


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--debug':
            set_debugger_session()
        else:
            # raise ValueError('unknown option {}'.format(sys.argv[1]))
            pass

    cur_dir = Path.cwd()
    model_dir = cur_dir / 'models'
    model_path = model_dir / 'bilstm_model'

    if is_train:
        # Load train dataset
        train_x, train_y = load(maxlen)

        # Train
        model, result = train(train_x, train_y, maxlen, model_path)

        print(model.metrics_names)
        print(result.history.keys())  # ヒストリデータのラベルを見てみる

        plt.plot(range(1, epochs + 1), result.history['accuracy'], label="training")
        # plt.plot(range(1, epochs + 1), result.history['val_acc'], label="validation")
        plt.xlabel('Epochs')
        plt.ylabel('Accuracy')
        plt.legend()
        # plt.show()
        plt.savefig('accuracy.png')

    else:
        # Infer
        y = predict(model_path, input_dim=input_dim)
        print(y.shape)
        np.set_printoptions(suppress=True, precision=10)
        print(y)

        # todo: to draw_race_result function
        # plt.style.use('default')
        # sns.set()
        # sns.set_style('whitegrid')
        # sns.set_palette('gray')
        #
        # label = np.arange(1, maxlen+1)
        # fig = plt.figure(figsize=(16.0, 9.0))
        #
        # for i in range(1):
        #     d1 = np.array(y[i, :])
        #     ax1 = fig.add_subplot(maxlen, 1, i+1)
        #     ax1.bar(label, d1)
        #
        # fig.tight_layout()
        x = range(0, maxlen)
        # y = np.reshape((-1, ), y)
        labels = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R"]
        plt.bar(x, y[0], tick_label=labels)

        plt.savefig('result.png')
        # plt.show()


