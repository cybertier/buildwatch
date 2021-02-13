import logging
import random
import sys
import string
import numpy as np
from ...gibberish_detector.gib_detect_train import train, avg_transition_prob

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

from ...pattern_generation.helper_functions import *

dictionary = None
dict_len = None


def test_dictionary():
    global dict_len
    global dictionary
    with open("gibberish_detector/words_alpha.txt") as f:
        dictionary = f.readlines()
    dictionary = [x.strip() for x in dictionary]
    dict_len = len(dictionary)
    gibberish_amount = 0
    for word in dictionary:
        #print (word, ",", is_gibberish(word))
        if is_gibberish(word):
            gibberish_amount = gibberish_amount + 1
    print("Dictionary length:", dict_len)
    print("Number of gibberish words:", gibberish_amount)
    print("Gibberish Percentage:", (gibberish_amount / dict_len) * 100.0, "%")
    print("======================================")


def test_random():
    global dict_len
    global dictionary
    in_dict = []
    generated_non_gib = []
    #dict_len = int(dict_len/1000)
    gibberish_amount = 0
    dict_amount = 0
    false_pos = 0
    for i in range(int(dict_len)):
        word = "".join(random.SystemRandom().choice(string.ascii_lowercase)
                       for _ in range(random.randint(4, 16)))
        if i % 100 == 0:
            print(
                i,
                "/",
                dict_len,
                "\t", (i / dict_len) * 100,
                "%       ",
                end='\r')
            sys.stdout.flush()

        idx = np.searchsorted(dictionary, word)
        try:
            if dictionary[idx] == word:
                dict_amount = dict_amount + 1
                if is_gibberish(word):
                    false_pos = false_pos + 1
                    in_dict.append(word)
            elif is_gibberish(word):
                gibberish_amount = gibberish_amount + 1
            else:
                generated_non_gib.append(word)
        except IndexError:
            if is_gibberish(word):
                gibberish_amount = gibberish_amount + 1
            else:
                generated_non_gib.append(word)

    print("")
    print("Number of random words:", dict_len)
    print("Number of gibberish words:", gibberish_amount)
    print("Gibberish percentage:", (gibberish_amount / dict_len) * 100.0, "%")
    nongibberish = dict_len - gibberish_amount
    print("Number of non-gibberish words:", nongibberish)
    print("Non-gibberish percentage:", (nongibberish / dict_len) * 100.0, "%")
    print("Number of dictionary words:", dict_amount)
    print("Percentage of nongibberish words in dictionary",
          (dict_amount / nongibberish) * 100.0, "%")

    print("")
    print("false_pos:", false_pos)
    print("false_neg:", len(generated_non_gib))
    import yaml
    with open('non_gib.yml', 'w') as outfile:
        yaml.dump(generated_non_gib, outfile, default_flow_style=False)
    with open('in_dict.yml', 'w') as outfile:
        yaml.dump(in_dict, outfile, default_flow_style=False)


def main():
    test_dictionary()
    test_random()


if __name__ == "__main__":
    main()
