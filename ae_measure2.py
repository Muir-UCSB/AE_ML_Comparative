'''
Author: Nolan McCarthy
Contact: nolanrmccarthy@gmail.com
Version: 200312

This is a class definition and function definition file for reading and
parsing files generated by WaveExplorer, developed by the Daly Lab
'''

from scipy import signal
import numpy as np
import matplotlib.pyplot as plt
import pandas
from scipy.stats import linregress
from scipy.integrate import simps
from librosa import zero_crossings as zc
import json

nan = float('nan')
inf = float('inf')



def load_PLB(path=None):
    '''
    :param path: (str) path name the PLB_data.json file is located at.

    :return data: Dictionary-like with the following attributes:
                data : {ndarray} of shape (N, 1024)
                target : {ndarray} of shape (N, )
                target_angle : The angle corresponding to the target

    '''
    if path is None:
        raise ValueError('Please input path name')

    with open(path) as json_file:
        PLB = json.load(json_file)

    for key in PLB.keys():
        PLB[key]  = np.array(PLB[key])
    return PLB


def read_ae_file2(fname, channel_num, sig_length=1024):
    '''
    fname (str): file path of text file containing voltage over time
    sig_length (int): number of data points per signal
    channel_num (int): Channel to be read in, indexed from 0

    returns:
    (sig, ev): where sig are signals and
            ev is the event number indexed from 1
    '''
    f = open(fname)
    lines = f.readlines()[1:]
    v1 = np.array([
        float(line.split()[channel_num]) for line in lines])
    f.close()

    sig = []
    for i in range(0,len(v1),sig_length):
        sig.append(v1[i:i+sig_length])
    ev = np.arange(len(sig))+1
    return sig,  ev


def filter_ae(ae_file, filter_csv, channel_num, sig_length=1024):
    '''
    ae_file (array-like): text file containing voltage over time
    filter_csv (CSV): file of useful events, must be csv
    return: (v1, v2, event_num), where v1 and v2 are the within gauge signals and
            event_number is the event number indexed from 1
    '''
    csv = pandas.read_csv(filter_csv)
    ev = np.array(csv.Event)
    v1, _ = read_ae_file2(ae_file, channel_num, sig_length)
    v1 = np.array(v1)
    v1 = v1[ev-1]
    return v1, ev




def is_clipped(sig):
    '''
    Determines if a signal is clipped
    sig (N*1 array-like): AE signal
    return (Boolean): bool
    Rounding makes this function kinda questionable, need to come back to this
    '''
    bool = False
    sig = np.abs(sig)
    max = np.max(np.round(sig, decimals=2))
    sig = sig[np.where(sig==max)]
    if len(sig)>1:
        bool=True
    return bool

def remove_clipped(v1, v2, ev, time = []):
    '''
    if both signals are clipped, removes both signals.
    v1 (N*1 array-like): Signal from channel 1 (N*1 array-like)
    v2 (N*1 array-like): Signal from channel 2 (N*1 array-like)
    event_num: where v1 and v2 are the within gauge signals and
            event_number is the event number indexed from 1
    return: (v1, v2, event_num), where v1 and v2 are the within gauge signals and
            event_number is the event number indexed from 1
    '''
    if len(time)!=0:
        holder1 = []
        holder2 = []
        holder3 = []
        holder4 = []
        for i in range(len(v1)):
            if is_clipped(v1[i]) and is_clipped(v2[i]):
                pass
            else:
                holder1.append(v1[i])
                holder2.append(v2[i])
                holder3.append(ev[i])
                holder4.append(time[i])
        return holder1, holder2, holder3, holder4
    else:
        holder1 = []
        holder2 = []
        holder3 = []
        for i in range(len(v1)):
            if is_clipped(v1[i]) and is_clipped(v2[i]):
                pass
            else:
                holder1.append(v1[i])
                holder2.append(v2[i])
                holder3.append(ev[i])
                holder4.append(time[i])
        return holder1, holder2, holder3








def max_sig(signal1, signal2):
    '''
    Gets signal of maximum intensity, currrently

    signal1 (N*1 array-like): signal from channel 1, single event
    signal2 (N*1 array-like): signal from channel 2, single event

    returns:
    sig: maximum between the two signals (array-like)
    '''
    if max(abs(signal1)) > max(abs(signal2)):
        sig=signal1
    else:
        sig=signal2
    return sig


def min_sig(signal1, signal2):
    '''
    Gets signal of maximum intensity, currrently

    signal1: signal from channel 1, single event (array-like)
    signal2: signal from channel 2, single event (array-like)

    returns:
    sig: maximum between the two signals (array-like)
    '''
    if max(abs(signal1)) > max(abs(signal2)):
        sig=signal2
    else:
        sig=signal1
    return sig






def fft(dt, y, low_pass=None, high_pass=None):
    '''
    Performs FFT

    dt (float): Sampling rate
    y (array-like): Voltage time-series
    low_pass (float): Optional variable for a low band pass filter in the same units of w
    high_pass (float): Optional variable for a high band pass filter in the same units of w

    returns:
    w (array-like): Frequency
    z (array-liike): Power
    '''
    z = np.abs(np.fft.fft(y))
    w = np.fft.fftfreq(len(z), dt)
    w = w[np.where(w>=0)] # NOTE: Gets positive frequencies from spectrum
    z = z[np.where(w>=0)] # NOTE: Gets positive frequencies from spectrum

    if low_pass is not None:
        z = z[np.where(w > low_pass)]
        w = w[np.where(w > low_pass)]
    if high_pass is not None:
        z = z[np.where(w < high_pass)]
        w = w[np.where(w < high_pass)]

    return w, z

def get_freq_centroid(w, z):
    '''
    Gets frequency centroid of an fft

    w (array-like): Frequency list
    z (array-like): Power list

    returns:
    centroid (float): Frequency centroid
    '''
    return np.sum(z*w)/np.sum(z)







import scipy
from scipy.sparse import csgraph
from scipy.sparse.linalg import eigsh
from numpy import linalg as LA
def eigenDecomposition(A, plot = True, topK = 5):
    """
    :param A: Affinity matrix
    :param plot: plots the sorted eigen values for visual inspection
    :return A tuple containing:
    - the optimal number of clusters by eigengap heuristic
    - all eigen values
    - all eigen vectors

    This method performs the eigen decomposition on a given affinity matrix,
    following the steps recommended in the paper:
    1. Construct the normalized affinity matrix: L = D−1/2ADˆ −1/2.
    2. Find the eigenvalues and their associated eigen vectors
    3. Identify the maximum gap which corresponds to the number of clusters
    by eigengap heuristic

    References:
    https://papers.nips.cc/paper/2619-self-tuning-spectral-clustering.pdf
    http://www.kyb.mpg.de/fileadmin/user_upload/files/publications/attachments/Luxburg07_tutorial_4488%5b0%5d.pdf
    """
    L = csgraph.laplacian(A, normed=True)
    n_components = A.shape[0]

    # LM parameter : Eigenvalues with largest magnitude (eigs, eigsh), that is, largest eigenvalues in
    # the euclidean norm of complex numbers.
#     eigenvalues, eigenvectors = eigsh(L, k=n_components, which="LM", sigma=1.0, maxiter=5000)
    eigenvalues, eigenvectors = LA.eig(L)

    if plot:
        plt.title('Largest eigen values of input matrix')
        plt.scatter(np.arange(len(eigenvalues)), eigenvalues)
        plt.grid()
        plt.show()

    # Identify the optimal number of clusters as the index corresponding
    # to the larger gap between eigen values
    index_largest_gap = np.argsort(np.diff(eigenvalues))[::-1][:topK]
    nb_clusters = index_largest_gap + 1

    return nb_clusters, eigenvalues, eigenvectors




def wave2vec(dt, waveform, lower, upper, dims, FFT_units, upsample=10001):
    '''
    dt: time spacing in seconds
    waveform (array-like): 1D array of waveform
    lower: lower bound on FFT in Hz
    upper: upper bound on FFT in Hz
    dims (int): dimension of vector

    This is a helper function which takes a single waveform and casts it as a vector.
    Upsampling is nessecary to ensure the whole FFT is integrated.
    '''
    feature_vector = []
    w, z = fft(dt, waveform, low_pass=lower, high_pass= upper) # NOTE: verified works
    w = w/FFT_units

    upsampled_w = np.linspace(lower, upper, upsample)/FFT_units # NOTE: 10000 is a good number of samples
    upsampled_z = np.interp(upsampled_w, w, z)
    dw=upsampled_w[1]-upsampled_w[0]

    interval_width = int(len(upsampled_z)/dims) # NOTE: range of index that is integrated over
    true_bounds = []

    for j in range(dims):
        subinterval = upsampled_z[j*interval_width: (j+1)*interval_width]
        sub_int_mass = simps(subinterval) # NOTE: area under sub interval
        feature_vector.append(sub_int_mass) # single waveform as a vector, unnormalized

        true_bounds.append(lower/FFT_units+j*interval_width*dw)

    # NOTE: Calculate bounds and frequency spacing
    true_upper_bound = (j+1)*interval_width*dw+lower/FFT_units # NOTE: true upper bound in kHz, not exact due to numerical considerations
    spacing = interval_width*dw # NOTE: kHz

    if (upper/FFT_units-true_upper_bound)/(upper/FFT_units-lower/FFT_units)>.01:
        raise ValueError('Increase upsampling number')
        return None
    return feature_vector/np.sum(feature_vector), np.array(true_bounds), spacing
