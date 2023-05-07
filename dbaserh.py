#
# dbaserh.py: digibaseRH Python-control program
# (2018 Emily Frame)
#
# ==============================================================================
#
# This program is a wrapper for `libdbaserh`, a C-library for device control
# and data acquisition of DigiBase-RH PMT bases (Jan Kamenik). The library is
# an adaption of `libdbase 0.2` for DigiBase-RH modules (Peter Kock).
#
# ==============================================================================

# Modules
import numpy as np
from ctypes import *
import ctypes
import time as TIME
import pandas as pd
import matplotlib.pyplot as plt
import yaml

# Load libdbaserh.so.0.1
cdll.LoadLibrary("libdbaserh.so.0.1")
libc = CDLL("libdbaserh.so.0.1")

# Find all digiBASES (max allowed: 32)
serials = np.zeros(32).astype(int)
serials = (ctypes.c_int * len(serials))(*serials)
found = libc.libdbase_list_serials(byref(serials), 32)

# Listmode Data Class
class DATA(ctypes.Structure):
    _fields_ = [("amp", c_int), ("time", c_int)]

# Detector Class
class DBASE():
    """
    A detector with a digibase-rh PMT base
    """
    def __init__(self, serial=serials[0], hvt=1100, fgn=0.5, pw=0.75, realtime=float("inf"),
                sleept=0.05, energy=[1, 2, 3], channel=[1, 2, 3]):
        """
        Args:
            serial (int):       serial number of digibase-rh

            realtime (float):   measurement time in seconds (default is
                                continous measurment)

            hvt (int):          high voltage target in volts (50-1200 V)

            fgn (float):        fine gain (0.5-1.2)

            pw (float):         pulse width in microseconds (0.75-2.0 us)

            sleept (int):       listmode sampling integration time in seconds

            energy (array):     calibration energies in keV; required to get
                                spectra

            channel (array):    calibration channels corresponding to energies
                                defined in energy array; required to get
                                spectra (max 1023 channels)

            det (int):          detector pointer

            fit (array-like):   linear fit for energy calibration

        Measurment Methods:
            measure_list_mode:  outputs listmode data

            count:              outputs histogramed counts and corresponding
                                channels

            spectra:            outputs histogramed counts and corresponding
                                energies

        Important:
            1. Always call `end_process` method after any measurment method to
            prevent high voltage from being left on

            2. Use `count` method to acquire `energy` and `channel` calibration
            data
        """
        # Parameter Definitions
        self.serial = ctypes.c_int(serial)
        self.realtime = float(realtime)
        self.hvt = ctypes.c_int(hvt)
        self.fgn = ctypes.c_float(fgn)
        self.pw = ctypes.c_float(pw)
        self.sleept = float(sleept)
        self.energy = energy
        self.channel = channel
        self.det = self.libdbase_init()

        # Linearly Calibrates Detector (if energy and channel are provided)
        p = np.polyfit(channel, energy, 1)
        self.fit = np.poly1d(p)

        # Initialize Detector
        self.hv_on()
        self.gs_off()
        self.zs_off()

        # Set Parameters
        self.set_hvt()
        self.set_fgn()
        self.set_pw()
        self.status()

# Detector Methods
    def libdbase_init(self):
        """
        Finds and opens a connection to detector with given serial number.

        Returns:
            det: detector pointer
        """
        det = libc.libdbase_init(self.serial)
        return det

    def hv_on(self):
        """
        Turns high voltage on. Automatically performed upon calling DBASERH
        """
        libc.libdbase_hv_on(self.det)

    def hv_off(self):
        """
        Turns high voltage off
        """
        libc.libdbase_hv_off(self.det)

    def gs_on(self):
        """
        Turns gain stabilization on. Gain stabilization only works for 800V
        (need to fix source code)
        """
        libc.libdbase_gs_on(self.det)

    def gs_off(self):
        """
        Turns gain stabilization off (default). Automatically performed upon
        calling DBASERH
        """
        libc.libdbase_gs_off(self.det)

    def zs_on(self):
        """
        Turns zero stabilization on. Zero stabilization only works for 800V
        (need to fix source code)
        """
        libc.libdbase_zs_on(self.det)

    def zs_off(self):
        """
        Turns zero stabilization off (default). Automatically performed upon
        calling DBASERH
        """
        libc.libdbase_zs_off(self.det)

    def set_hvt(self):
        """
        Sets high voltage to specified hvt value (default 1100 V). Automatically
        performed upon calling DBASERH
        """
        libc.libdbase_set_hv(self.det, self.hvt)

    def set_fgn(self):
        """
        Sets fine gain to specified fgn value (default 0.5). Automatically
        performed upon calling DBASERH
        """
        libc.libdbase_set_fgn(self.det, self.fgn)

    def set_pw(self):
        """
        Sets pulse width to specified pw value (default 0.75 us). Automatically
        performed upon calling DBASERH
        """
        libc.libdbase_set_pw(self.det, self.pw)

    def status(self):
        """
        Prints detector status. Automatically performed upon calling DBASERH.
        """
        libc.libdbase_print_status(self.det)

    def start(self):
        """
        Starts measurement
        """
        libc.libdbase_start(self.det)

    def stop(self):
        """
        Stops measurement
        """
        libc.libdbase_stop(self.det)

    def clear(self):
        """
        Clears all presets
        """
        libc.libdbase_clear_all(self.det)

    def close(self):
        """
        Close connection to each detector and free list
        """
        libc.libdbase_close(self.det)

    def measure_list_mode(self):
        """
        Starts listmode measurement.

        Returns:
            amplitude:  array
                        amplitudes
            timestamp:  array
                        timestamps corresponding to amplitudes

        """
        libc.libdbase_set_list_mode(self.det)
        libc.libdbase_start(self.det)
        read = ctypes.c_int(0)
        tme = ctypes.c_int(0)
        DataArrayType = DATA * 2048
        data = DataArrayType()
        cycles = int(self.realtime/self.sleept)
        amplitude = []
        timestamp = []
        for c in range(0, cycles):
            TIME.sleep(self.sleept)
            libc.libdbase_read_lm_packets(self.det, byref(data), 2048, byref(read), byref(tme))
            for e in range(read.value):
                amplitude.append(data[e].amp)
                timestamp.append(TIME.time())

        return amplitude, timestamp

    def count(self, plot=False, output=False, filename='output.csv'):
        """
        Starts measurement. Uses measure_list_mode.

        Args:
            plot:       bool, optional
                        If True, spectrum is plotted in realtime
            output:     bool, optional
                        If True, data is saved to a .csv file called filename
            filename:   string
                        default `output.csv`; required only if output is True
        Returns:
            channels:   array
                        1023 channel bins
            counts:     array
                        counts binned

        """
        amplitude, timestamp = self.measure_list_mode()
        hist, bin_edges = np.histogram(amplitude, bins=1023, range=(0, 1023))
        lower_edges = np.resize(bin_edges, len(bin_edges)-1)
        channel = lower_edges + 0.5*np.diff(bin_edges)

        if plot is True:
            figure, ax = plt.subplots()
            ax.fill(channel, hist, label='%i' %self.serial.value)
            plt.xlim(0)
            plt.xlabel('channel')
            plt.ylabel('counts')
            plt.legend()
            plt.show()

        if output is True:
            d = {'1': channel, '2': hist}
            df = pd.DataFrame(data=d)
            df.to_csv(filename, index=False, header=False)

        return channel, hist

    def spectra(self, plot=False, output=False, filename='output.csv'):
        """
        Starts measurement. Uses measure_list_mode. Calibration data (`channel`
        and `energy` must be provided)

        Args:
            plot:       bool, optional
                        If True, data is plotted
            output:     bool, optional
                        If True, data is saved to a .csv file called filename
            filename:   string
                        default `output.csv`; required only if output is True
        Returns:
            energies:   array
                        1023 energy bins
            counts:     array
                        counts binned

        """
        amplitude, timestamp = self.measure_list_mode()
        hist, bin_edges = np.histogram(amplitude, bins=1023, range=(0, 1023))
        lower_edges = np.resize(bin_edges, len(bin_edges)-1)
        bins = lower_edges + 0.5*np.diff(bin_edges)
        energy = self.fit(bins)

        if plot is True:
            figure, ax = plt.subplots()
            ax.fill(energy, hist, label='%i' %self.serial.value)
            plt.xlim(0)
            plt.xlabel('energy')
            plt.ylabel('counts')
            plt.legend()
            plt.show()

        if output is not False:
            d = {'1': energy, '2': hist}
            df = pd.DataFrame(data=d)
            df.to_csv(filename, index=False, header=False)

        return energy, hist

    def end_process(self):
        """
        Stops the detector. Clears all presets. Turns high voltage off. Prints
        status. This method should be called after each measurement method
        (e.g measure_list_mode, count, spectra)
        """
        self.stop()
        self.clear()
        self.hv_off()
        self.status()
        self.close()
