#!/usr/bin/python3

import pickle
import gib_detect_train

model_data = pickle.load(open('gib_model.pki', 'rb'))

while True:
    line = input()
    model_mat = model_data['mat']
    threshold = model_data['thresh']
    print(gib_detect_train.avg_transition_prob(line, model_mat) > threshold)
