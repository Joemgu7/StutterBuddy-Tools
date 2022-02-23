"""
Author: Jonas Briguet
Date: 19.11.2021
This is a simple script to submit a single file to stutterbuddy.ch
You are free to use this code as an example.
"""

from stutterbuddy import make_submission_file

# paste your personal api key which can be obtained at https://stutterbuddy.ch/api-doc
API_KEY = ""

DEBUG = False

FILEPATH = 'path_to_file.mp4'

def main():    
    # call this function using the filepath and your api key
    # arguments can be added as needed
    settings, upload_id = make_submission_file(FILEPATH, API_KEY, resolution='720')
    
    if DEBUG: print(settings)

    print("Submission successful")

if __name__ == '__main__':
    main()