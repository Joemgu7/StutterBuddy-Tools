"""
Author: Jonas Briguet
Date: 19.11.2021
This is a script to load a list of video-urls from a json file and submit the corresponding videos to stutterbuddy.ch 
"""

import requests
import urllib.parse
import os
import json
import time

# paste your personal api key which can be obtained at https://stutterbuddy.ch/api-doc
API_KEY = ''
# path to the file containing a dict of video_name:video_url pairs, ex: {'real_video':'https://yoururl.com/video.mp4}
FILE_TO_LOAD = 'example_submission.json'
# flag to debug the program and make sure that the requests go through as expected
DEBUG = False

# this is the url of the stutterbuddy api DO NOT CHANGE
URL = 'https://stutterbuddy.ch/api/submit/link'

def main():
    # load data from json database
    Data = None
    with open(FILE_TO_LOAD, 'r') as rawData:
        Data = json.load(rawData)
    if Data == None: raise "No dict"

    for video_name in Data:
        video_url = Data[video_name]
        r = requests.post(URL,
        # if needed, more parameters can be defined here and altered
        # for more information visit https://stutterbuddy.ch/api-doc
                json={
                    'api_key': API_KEY,
                    'video_url':video_url,
                    'share_data':False,
                    'video_name': video_name,
                    'debug':DEBUG,
                    'resolution': '1080'
                    },
            )

        if DEBUG: print(r.json())
        # small wait time to not overload the server with requests
        time.sleep(5)

if __name__ == '__main__':
    main()