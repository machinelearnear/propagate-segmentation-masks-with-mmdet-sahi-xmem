# sources:
# - https://yiyixuxu.github.io/2022/06/12/It-Happened-One-Frame.html
# - https://huggingface.co/spaces/YiYiXu/it-happened-one-frame-2/blob/main/app.py

import os, sys
import shutil
import numpy as np
import datetime
import cv2
try:
    import youtube_dl
except:
    os.system("pip install youtube_dl")
    import youtube_dl

from pathlib import Path
from PIL import Image,ImageDraw, ImageFont
from functools import partial
from multiprocessing.pool import Pool


def select_video_format(url, ydl_opts={}, format_note='240p', ext='mp4', max_size = 500000000, **kwargs):
    defaults = ['480p', '360p','240p','144p']
    ydl_opts = ydl_opts
    ydl = youtube_dl.YoutubeDL(ydl_opts)
    info_dict = ydl.extract_info(url, download=False)
    formats = info_dict.get('formats', None)
    # filter out formats we can't process
    formats = [f for f in formats if f['ext'] == ext 
               and f['vcodec'].split('.')[0] != 'av01' 
               and f['filesize'] is not None and f['filesize'] <= max_size]
    available_format_notes = set([f['format_note'] for f in formats])
    
    if format_note not in available_format_notes:
        format_note = [d for d in defaults if d in available_format_notes][0]
    formats = [f for f in formats if f['format_note'] == format_note]
    
    format = formats[0]
    format_id = format.get('format_id', None)
    fps = format.get('fps', None)
    print(f'format selected: {format}')
    return(format, format_id, fps)
  
def download_video(url, **kwargs):
    # create "videos" foder for saved videos
    path_videos = Path('videos')
    try:
        path_videos.mkdir(parents=True)
    except FileExistsError:
        pass
    # clear the "videos" folder 
    videos_to_keep = ['v1rkzUIL8oc', 'k4R5wZs8cxI','0diCvgWv_ng']
    if len(list(path_videos.glob('*'))) > 10:
        for path_video in path_videos.glob('*'):
            if path_video.stem not in set(videos_to_keep):
                path_video.unlink()
                print(f'removed video {path_video}')
    # select format to download for given video
    # by default select 240p and .mp4 
    try:
        format, format_id, fps = select_video_format(url)
        ydl_opts = {
            'format':format_id,
            'outtmpl': "videos/%(id)s.%(ext)s"}

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.cache.remove()
                meta = ydl.extract_info(url)
                save_location = 'videos/' + meta['id'] + '.' + meta['ext']
            except youtube_dl.DownloadError as error:
                print(f'error with download_video function: {error}')
                save_location = None
    except IndexError as err:
        print(f"can't find suitable video formats. we are not able to process video larger than 95 Mib at the moment")
        fps, save_location = None, None
        
    return(fps, save_location)

def process_video_parallel(video, skip_frames, dest_path, num_processes, process_number, **kwargs):
    cap = cv2.VideoCapture(video)
    frames_per_process = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // (num_processes)
    count =  frames_per_process * process_number
    cap.set(cv2.CAP_PROP_POS_FRAMES, count)
    print(f"worker: {process_number}, process frames {count} ~ {frames_per_process * (process_number + 1)} \n total number of frames: {cap.get(cv2.CAP_PROP_FRAME_COUNT)} \n video: {video}; isOpen? : {cap.isOpened()}")
    while count < frames_per_process * (process_number + 1) :
        ret, frame = cap.read()
        if not ret:
            break
        if count  % skip_frames ==0:
            filename =f"{dest_path}/{count}.png"
            cv2.imwrite(filename, frame)
        count += 1
    cap.release()


def vid2frames(url, sampling_interval=1, **kwargs):
    # create folder for extracted frames - if folder exists, delete and create a new one
    path_frames = Path('frames')
    try:
        path_frames.mkdir(parents=True)
    except FileExistsError:
        shutil.rmtree(path_frames)
        path_frames.mkdir(parents=True)
 
    # download the video 
    fps, video = download_video(url)
    if video is not None: 
        if fps is None: fps = 30
        skip_frames = int(fps * sampling_interval)
        print(f'video saved at: {video}, fps:{fps}, skip_frames: {skip_frames}')
        # extract video frames at given sampling interval with multiprocessing - 
        n_workers = min(os.cpu_count(), 12)
        print(f'now extracting frames with {n_workers} process...')

        with Pool(n_workers) as pool:
            pool.map(partial(process_video_parallel, video, skip_frames, path_frames, n_workers), range(n_workers))
    else:
        skip_frames, path_frames = None, None
        
    return(skip_frames, path_frames)