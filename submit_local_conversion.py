"""
    Author: Jonas Briguet
    Date: 25.02.2022
    Last Change: 
    version: 0.0.1
    script for local cutting of videos, needs stutterbuddy.py and ffmpeg
    Need to install sudo apt install intel-media-va-driver-non-free for vaapi to work (scaling feature)
"""

import argparse
import requests
import urllib.parse
import os
import shutil
import json
import time
from stutterbuddy import make_submission_file, request_info_by_id, start_progress, progress, end_progress
import numpy as np
import subprocess

def seconds_to_timestamp(seconds):
    milliseconds = round(seconds*1000)
    seconds, ms = divmod(milliseconds, 1000)
    min, sec = divmod(seconds, 60)
    hour, min = divmod(min, 60)
    return "%02d:%02d:%02d.%03d" % (hour, min, sec, ms)

def vaapi_command(input_name, output_name, start, duration, scale='720x1080', fps=25):
    scale_width = scale.split("x")[1]
    scale_height = scale.split("x")[0]

    return f"ffmpeg -loglevel error -init_hw_device vaapi=foo:/dev/dri/renderD128 -hwaccel vaapi -hwaccel_output_format vaapi -hwaccel_device foo -ss {start} -i {input_name} -t {duration} -filter_hw_device foo -vf 'format=nv12|vaapi,hwupload,fps=fps={fps},scale_vaapi=w={scale_width}:h={scale_height}' -c:v h264_vaapi {output_name}"

def libx264_command(input_name, output_name, start, duration, scale='720x1080', fps=25):
    return f"ffmpeg -loglevel error -ss {start} -i {input_name} -t {duration} -vf 'fps=fps={fps},scale={scale.split('x')[1]}x{scale.split('x')[0]}' -c:v libx264 -preset veryfast -crf 19 {output_name}"

def nvenc_command(input_name, output_name, start, duration, scale='720x1080', fps=25):
    return f"ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -resize {scale} -ss {start} -i {input_name} -t {duration} -c:v h264_nvenc -preset fast {output_name}"



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-api_key",help="Your api_key from Stutterbuddy")
    parser.add_argument("-file",help="Path to a local file to be converted")
    parser.add_argument("-tmp_directory",help="Path to a temporary directory to create, default is 'tmp'")
    parser.add_argument("-local_conversion",help=" 'cpu', 'nvenc' or 'vaapi', Will use this machines ressources to convert the video, potentially being faster")
    parser.add_argument("-use_profile",help="Use your standard settings for submission")
    parser.add_argument("-resolution",help="Max resolution of output file")
    parser.add_argument("-threshold",help="Threshold to use, standard is 10")
    parser.add_argument("-min_silence",help="Minimal silence length, standard is 0")
    parser.add_argument("-stutter_detection",help="Recognize stutters and noise, standard is true")
    parser.add_argument("-share_data",help="Do you want to share data to improve stutterbuddy (according to https://stutterbuddy.ch/datashared)")
    parser.add_argument("-submit",help="Submit the job on upload, standard is true")
    parser.add_argument("-detach_cuts",help="Do not merge cuts to a whole continuous video/audio file, standard is false")
    parser.add_argument("-cut_list",help="Only return a list with timestamps")
    parser.add_argument("-video_name",help="Which name do you want to give to your video")
    parser.add_argument("-scale",help="Rescale when rendering, defaults to '720x1280' (same format)")
    parser.add_argument("-fps",help="fps of new video, defaults to 25")

    args = parser.parse_args()

    if not args.api_key:
        print("Please provide your api_key")
        exit()

    if not args.file:
        print("Please provide a path to a local file")
        exit()

    API_KEY = args.api_key
    FILE_PATH = args.file
    TMP_DIR = os.path.join('tmp')

    video_name = FILE_PATH
    use_profile = 'false'
    resolution = '720'
    min_silence = '0' 
    threshold = '10' 
    stutter_detection = 'true' 
    share_data = 'false' 
    submit = 'true' 
    notify_email = 'false' 
    detach_cuts = 'false' 
    cut_list = 'false' 
    debug = 'false'
    scale = '720x1280'
    fps = 25

    if args.tmp_directory:
        TMP_DIR = args.tmp_directory
    if args.use_profile:
        use_profile = args.use_profile
    if args.resolution:
        resolution = args.resolution
    if args.threshold:
        threshold = args.threshold
    if args.min_silence:
        min_silence = args.min_silence
    if args.stutter_detection:
        stutter_detection = args.stutter_detection
    if args.share_data:
        share_data = args.share_data
    if args.submit:
        submit = args.submit
    if args.detach_cuts:
        detach_cuts = args.detach_cuts
    if args.cut_list:
        cut_list = args.cut_list
    if args.scale:
        scale = args.scale

    if args.local_conversion:
        start_time = time.time()
        PrepareDirectories(TMP_DIR)
        audio_path = os.path.join(TMP_DIR, 'tmp_audio.m4a')
        txt_path = os.path.join(TMP_DIR, 'cutlist.txt')

        print("Extracting Audio")
        subprocess.run(f'ffmpeg -loglevel error -i "{FILE_PATH}" -vn "{audio_path}"', shell=True, capture_output=False)

        settings, upload_id = make_submission_file(
            path_to_file=audio_path, API_KEY=API_KEY,
            threshold=threshold, min_silence=min_silence, stutter_detection=stutter_detection,
            share_data=share_data, notify_email=notify_email, cut_list='true',video_name=FILE_PATH
            )

        print(f"Submitted {FILE_PATH} successfully")
        is_done = False
        while(not is_done):
            response = request_info_by_id(upload_id, API_KEY)
            if response['status'] == 'Failed':
                print(f"Conversion of {FILE_PATH} failed")
                exit()
            elif response['status'] == 'Finished':
                try:
                    print(f"Cut out {seconds_to_timestamp(int(response['timesaved']))}")
                except:
                    print('error')
                # download file
                r = requests.get(response['video_url'])
                # write to fs
                with open(txt_path, 'wb') as f:
                    f.write(r.content)

                cut_list = np.loadtxt(txt_path, dtype='float64')

                # Codec to use for conversion, can be adjusted to your liking
                CodecUsed = "-c:v libx264 -preset veryfast -crf 19"
                merging_codec = "-c copy"
                split_command = libx264_command

                if args.local_conversion == 'nvenc':
                    print('Using nvenc')
                    split_command = nvenc_command
                elif args.local_conversion == 'vaapi':
                    print('Using vaapi')
                    split_command = vaapi_command

                conversion_extension = '.mp4'

                splitlist = []
                for i in range(len(cut_list)):
                    splitlist.append(split_command(FILE_PATH, os.path.join(TMP_DIR, 'splits', str(i)+conversion_extension), cut_list[i][1], cut_list[i][2]), scale=scale, fps=fps)

                ############ CUT VIDEO ############
                start_progress('Cutting Video')
                for i in range(len(splitlist)):
                    progress(i/len(splitlist)*90)
                    subprocess.run(splitlist[i], capture_output=False, shell=True)

                ############ CREATE CLIPLIST TO MERGE VIDEOCLIPS ############

                f = os.listdir(os.path.join(TMP_DIR, 'splits'))
                with open(os.path.join(TMP_DIR, 'cliplist.txt'), 'w+') as cliplist:
                    for i in range(0, len(f)):
                        # path of splits is relative to cliplist.txt
                        line = str("file '"+os.path.join('splits', str(i)+'.mp4'+"'\n"))
                        cliplist.write(line)
                    cliplist.close()

                ############ MERGE AND MOVE VIDEOCLIP ############

                #merge created splits
                progress(95)
                subprocess.run(f"ffmpeg -loglevel error -f concat -safe 0 -i {os.path.join(TMP_DIR, 'cliplist.txt')} {merging_codec} {os.path.splitext(FILE_PATH)[0]+'_stutterbuddy.mp4'}", capture_output=False, shell=True)
                progress(100)
                end_progress()
                print(f"This conversion took {seconds_to_timestamp(round(time.time()-start_time))}")
                break
            else:
                time.sleep(10)
        
    else:
        settings, upload_id = make_submission_file(
            path_to_file=FILE_PATH, API_KEY=API_KEY, use_profile=use_profile, resolution=resolution,
            threshold=threshold, min_silence=min_silence, stutter_detection=stutter_detection,
            share_data=share_data, notify_email=notify_email, video_name=FILE_PATH, submit=submit,
            detach_cuts=detach_cuts, cut_list=cut_list
            )

def PrepareDirectories(workpath):
    if os.path.exists(workpath):
        shutil.rmtree(workpath)
        os.makedirs(workpath)
        os.makedirs(os.path.join(workpath,'splits'))
    else:
        os.makedirs(workpath)
        os.makedirs(os.path.join(workpath,'splits'))

if __name__ == '__main__':
    main()