#! /usr/bin/python3

# If you want preds on CPU only
GENERATE_ON_CPU = True

if GENERATE_ON_CPU:
    import os
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    # Check to see if GPU is not visible
    from tensorflow.python.client import device_lib
    # print(device_lib.list_local_devices())


import tensorflow as tf
from numpy import array
from datetime import datetime
import yaml
import os

from model import build_model, vocab, embedding_dim, rnn_units
from __init__ import basedir

# TODO: Use weights filepath directly instead of tf.checkpoint and drop basedir

class TrumpChange(tf.Module):
    def load_model(self, run_dir=None):
        model = build_model(self.vocab_size, embedding_dim, rnn_units, batch_size=1)

        run_dir = run_dir or 'trump_training_checkpoints/current'
        checkpoint_dir = os.path.join(os.getcwd(), run_dir)
        
        model.load_weights(tf.train.latest_checkpoint(checkpoint_dir))
        model.build(tf.TensorShape([1, None]))
        tf.train.latest_checkpoint(checkpoint_dir)

        return model

    def __init__(self, 
                 checkpoint_dir=None, 
                 num_generate=280, 
                 conditioning_string='China ', 
                 vocab_path='data/vocab.npy', 
                 temperature=0.9):
        super(TrumpChange, self).__init__()
        self.vocab_size = len(vocab)
        self.char2idx = {u:i for i, u in enumerate(vocab)}
        self.idx2char = array(vocab)
        self.num_generate = num_generate
        self.conditioning_string = conditioning_string
        self.temperature = temperature
        self.model = self.load_model()

    # TODO: Cleanup generated tweets via regex?
    def prettify_tweet(self, generated):
        pass

    def __call__(self, x=None):
        # Converting our start string to numbers (vectorizing)
        input_eval = [self.char2idx[s] for s in self.conditioning_string]
        input_eval = tf.expand_dims(input_eval, 0)

        # Empty string to store our results
        text_generated = []

        # Low temperatures results in more predictable text.
        # Higher temperatures results in more surprising text.
        # Experiment to find the best setting.

        # Here batch size == 1
        self.model.reset_states()
        for _ in range(self.num_generate):
            predictions = self.model(input_eval)
            # remove the batch dimension
            predictions = tf.squeeze(predictions, 0)

            # using a categorical distribution to predict the character returned by the model
            predictions = predictions / self.temperature
            predicted_id = tf.random.categorical(predictions, num_samples=1)[-1,0].numpy()

            # We pass the predicted character as the next input to the model
            # along with the previous hidden state
            input_eval = tf.expand_dims([predicted_id], 0)

            text_generated.append(self.idx2char[predicted_id])

        return (self.conditioning_string + ''.join(text_generated))

    def set_conditioning_str(self, new_string):
        self.conditioning_string = str(new_string)

    def set_num_generate(self, new):
        self.num_generate = int(new)
    
    def set_temperature(self, new_temp):
        self.temperature = float(new_temp)




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--checkpoint",   
                        help="Filepath to model checkpoint.", 
                        type=str, default="trump_training_checkpoints")
    parser.add_argument("-n", "--num_generate", 
                        help="Set the number of characters to generate per tweet.", 
                        type=int, default=280) # defalt twitter lengthc cap as of 5/2020
    parser.add_argument("-c", "--conditioning", 
                        help="Set the conditioning string to use as input to the model.", 
                        type=str, default="China")
    parser.add_argument("-v", "--vocab_path",
                        help="Path to vocabulary file [.npy array].", 
                        type=str, default="data/vocab.npy")
    parser.add_argument("-t", "--temperature",
                        help="Set the temperature of the annealer during prediction.", 
                        type=float, default=0.9)
    args = parser.parse_args()
    

    print("\nLoading model weights...")
    tc = TrumpChange(
        checkpoint_dir=args.checkpoint,
        num_generate=args.num_generate,
        conditioning_string=args.conditioning,  
        vocab_path=args.vocab_path,
        temperature=args.temperature
    )

    print("\nSetting initial params...")
    print(vars(args))
    tc.set_num_generate(args.num_generate)
    tc.set_temperature(args.temperature)
    tc.set_conditioning_str(args.conditioning)

    done = False
    while not done:
        n = int(input("\nHow many strings to generate?\n"))
        for _ in range(n):
            print(tc(), "\n")

        b = input("Do you wish to update parameters? (y/n)\n")

        if b.lower() in ["yes", "y"]:
            c = input("\nEnter conditioning string:\n")
            tc.set_conditioning_str(c)

            t = input("\nEnter temperature:\n")
            tc.set_temperature(t)

            n = input("\nEnter number of characters to generate per tweet:\n")
            tc.set_num_generate(n)

        else:
            x = input("\nDo you wish to generate more tweets? (y/n)\n")
            if x not in ['yes', 'y']:
                done = True
                print("Exiting...")

