"""
    Author: Jonas Briguet
    Date: 06.12.2021
    Last Change: 23.02.2021
    version: 0.0.4
    This is a library with functions to interact with the stutterbuddy.ch api 
"""

import requests
import sys
from requests_toolbelt import MultipartEncoderMonitor
import urllib.parse
import os
import json
import time
import re

regex_url = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def make_submission_url(url, API_KEY, use_profile='false', resolution='720', threshold='10', min_silence='0', stutter_detection='true', share_data='false', submit='true', notify_email='false', debug='false', detach_cuts='false', cut_list='false', video_name='', verbose=1):
    """A function to submit urls to stutterbuddy using the API. More information on the arguments taken available at https://stutterbuddy.ch/api-doc 
    returns a boolean which is true or false to tell if a request was sucessful and a the http response of the API server"""
    ENDPOINT = 'https://stutterbuddy.ch/api/submit/link'
    r = requests.post(URL,
            json={
                'api_key': API_KEY,
                'video_url':video_url,
                'video_name':video_name,
                'use_profile':use_profile,
                'resolution':resolution,
                'threshold':threshold,
                'min_silence':min_silence,
                'stutter_detection':stutter_detection,
                'share_data':share_data,
                'submit':submit,
                'notify_email':notify_email,
                'detach_cuts':detach_cuts,
                'cut_list':cut_list,
                'debug':debug
                },
        ).json()

    if verbose >= 2: print(r)

    if 'error' in r:
        raise Exception("Error occured when submitting video by url: "+r['error'])
    elif 'message' in r and r['message'] == 'success':
        return r['settings'], r['settings']['upload_id']

def make_submission_file(path_to_file, API_KEY, use_profile='false', resolution='720', threshold='10', min_silence='0', stutter_detection='true', share_data='false', submit='true', notify_email='false', debug='false', detach_cuts='false', cut_list='false', video_name='', verbose=1):
    """A function to submit local files to stutterbuddy using the API. More information on the arguments taken available at https://stutterbuddy.ch/api-doc
     returns the settings applied to the video and the upload_id of the video.
     Has 3 verbose levels: 0 for no cmd line output, 1 for basic information on progress and 3 for debugging purposes"""

    # request new upload id
    r = requests.get('https://stutterbuddy.ch/api/upload/request-upload?key='+urllib.parse.quote(API_KEY)).json()

    if verbose >= 2: print(r)

    if 'error' in r:
        raise Exception("Error occured when requesting slot: "+r['error'])

    upload_id = r['upload_id']
    cdn_url = r['worker_url']

    m = MultipartEncoderMonitor.from_fields(
        fields={
                    'api_key':API_KEY,
                    'video_name':video_name,
                    'use_profile':use_profile,
                    'resolution':resolution,
                    'threshold':threshold,
                    'min_silence':min_silence,
                    'stutter_detection':stutter_detection,
                    'share_data':share_data,
                    'submit':submit,
                    'notify_email':notify_email,
                    'detach_cuts':detach_cuts,
                    'cut_list':cut_list,
                    'debug':debug,
                    'files':(path_to_file, open(path_to_file, 'rb'), 'text/plain')         
        },
        callback=(streamed_status_callback if verbose >= 1 else None)
    )

    if verbose >= 1: start_progress('Uploading to StutterBuddy')

    r = requests.post(cdn_url+'/api/worker/submit/file/'+urllib.parse.quote(upload_id), data=m,
                  headers={'Content-Type': m.content_type}, timeout=(10, 2000)).json()
    if verbose >= 1: end_progress()
    if verbose >= 2: print(r)

    if 'error' in r:
        raise Exception("Error occured when submitting video: "+r['error'])
    elif 'message' in r and r['message'] == 'success':
        return r['settings'], upload_id

def make_submission(file, API_KEY, use_profile='false', resolution='720', threshold='10', min_silence='0', stutter_detection='true', share_data='false', submit='true', 
            notify_email='false', debug='false', detach_cuts='false', cut_list='false', video_name='', verbose=1):
    """A function to submit both local files and urls to stutterbuddy using the API. More information on the arguments taken available at https://stutterbuddy.ch/api-doc
     returns two values: a boolean which is true or false to tell if a request was sucessful and the response of the API server"""
    if type(file) is str:
        if is_url(file):
            make_submission_url(file, API_KEY, use_profile='false', resolution='720', threshold='10', min_silence='0', stutter_detection='true', share_data='true', submit='true', notify_email='false', debug='false', detach_cuts='false', video_name='', verbose=1)
        else:
            successful, settings, upload_id = make_submission_file(file, API_KEY, use_profile='false', resolution='720', threshold='10', min_silence='0', stutter_detection='true', share_data='true', submit='true', notify_email='false', debug='false', detach_cuts='false', video_name='', verbose=1)

def request_info_by_id(upload_id, API_KEY):
    """
        Takes a single upload_id as string and the API_KEY
        returns video_name, video_url, status, timesaved corresponding to upload_id
    """
    result = requests.get('https://stutterbuddy.ch/api/data/request/single?key='+urllib.parse.quote(API_KEY)+"&uploadid="+urllib.parse.quote(upload_id)).json()

    if 'error' in result:
        raise Exception("Error occured when requesting info: "+result['error'])
    else:
        return result['data']

def is_url(string):
    """helper function to determine if string is a url"""
    return re.match(regex_url, string) is not None

def streamed_status_callback(m):
    progress(m.bytes_read/m.len*100)

def start_progress(title):
    global progress_x
    sys.stdout.write(title + ": [" + "-"*40 + "]" + chr(8)*41)
    sys.stdout.flush()
    progress_x = 0

def progress(x):
    global progress_x
    x = int(x * 40 // 100)
    sys.stdout.write("#" * (x - progress_x))
    sys.stdout.flush()
    progress_x = x

def end_progress():
    sys.stdout.write("#" * (40 - progress_x) + "]\n")
    sys.stdout.flush()