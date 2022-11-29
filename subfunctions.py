import pyxdf
import numpy as np
import pathlib
import mne

def read_xdf(fname):
    """
    fname = pathlib object to .xdf file
    
    Return:
    
    raw: Mmne.Raw object
    events: numpy array shape (num,3) with strings (to be converted to float)
    
    """
    # load xdf data
    streams, header = pyxdf.load_xdf(fname)
    
    stream_count = 0

    for stream in streams:
        if stream['info']['channel_count'] == ['16']:
            eeg_stream = stream
            #data_eeg = stream["time_series"].T
            stream_count += 1
        elif stream['info']['channel_count'] == ['1']:
            marker_stream = stream
            stream_count += 1
        else:
            print('Not recognized channel')


    print (f'{stream_count} streams loaded') 

    # Prepare the time series data

    eeg_data = eeg_stream["time_series"].T

    # Create Info object 

    ch_types = ['eeg'] * 13 
    ch_names = ['C3','C4','Cz','FC1','FC2','FC5','FC6','CP1','CP2','CP5','CP6','O1','O2']

    #data_marker = streams[0]

    eeg_data = eeg_data[0:13]
   
    eeg_data *= (1e-6 / 2)  # Not sure if that is the correct way (uV -> V and preamp gain)
    sfreq = float(eeg_stream["info"]["nominal_srate"][0])
    info = mne.create_info(ch_names= ch_names, ch_types=ch_types, sfreq=sfreq)
    info.set_montage('standard_1020')
    
    # Now lets create the Raw instance
    raw = mne.io.RawArray(eeg_data, info)
    
    # Convert markers to annotations and add them to the Raw instance

    # lets align the time of events to the recording onset by seconds
    start_time = eeg_stream['time_stamps'][0]
    marker_stream['time_stamps'] -= start_time

    events_num = len(marker_stream['time_series'])
    zeros = np.zeros(len(marker_stream['time_series'])).reshape(events_num,1)
    # need to solve the string thing
    events = np.concatenate((marker_stream['time_stamps'].reshape(events_num,1),zeros,np.array(marker_stream['time_series']).reshape(events_num,1)),axis = 1)
    return raw, events


def add_annot(raw, events):
    """
    raw: Mne.raw 
    events: [events,3] numpy array of strings. the output of read_xdf function
    
    Retrurn: Mne.raw, with annotations
    
    """
    # make sure no strings in marker
    names=  np.unique(events[:,2])
    mapping = dict(list(enumerate(names))) #create a dict with a number for unique string
    for m in mapping.items():
        events[:,2] = np.char.replace(events[:,2], m[1], str(m[0]))
    
    #events[:,2] = np.char.replace(events[:,2], 'Standard Trial', '20')
    #events[:,2] = np.char.replace(events[:,2], 'Target Trial', '21')
    # delete last row as it contains empty string
    if events[-1,2] == '':   
        events = np.delete(events, -1, 0)
    events = events.astype(float)
    events[:,0] *= 125 # time to time stamp
    
    # PAY ATTENTION. sfreq=raw.info['sfreq'] is not good. since raw.info['sfreq'] is 250 and not 125
    annot_from_events = mne.annotations_from_events(
    events=events, event_desc=mapping, sfreq=125,
    orig_time=None)
    raw.set_annotations(annot_from_events)
    
    return raw
    
    