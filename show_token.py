import pickle
import pprint

# Path to your token.pickle file
TOKEN_PATH = 'token.pickle'

def main():
    with open(TOKEN_PATH, 'rb') as f:
        token = pickle.load(f)
    pprint.pprint(token.__dict__)

if __name__ == '__main__':
    main()
