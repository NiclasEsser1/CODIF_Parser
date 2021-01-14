# Australia Telescope National Facility (ATNF)
# Commonwealth Scientific and Industrial Research Organisation (CSIRO)
# PO Box 76, Epping NSW 1710, Australia
# atnf-enquiries@csiro.au
#
# This file is part of the ASKAP software distribution.
#
# The ASKAP software distribution is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License
# or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA.
#
# @author Aaron Chippendale <Aaron.Chippendale@csiro.au>
#
import os
import glob
import numpy as np
import h5py
from collections import OrderedDict

from inc.constants import *
from inc.utils import *


class ACMFile(h5py.File):
    def __init__(self, name, mode='r', count_scale=True, acm_stats=True, **kwds):
        """
        Create a new read only acm.hdf5 File object inheriting from h5py.  See :meth:`h5py.File.__init__` for further
        options and the `h5py user guide`_ for a detailed explanation of the options.

        Assumes user will want to use all of the ACM data (all frequencies, ports, cycles, so it reads the whole file
        into memory in one shot in the initialisation of the object.  Will have to rethink this if we need to
        efficiently extract snippets.

        Will also optionally check ACM

        :param str name: Name of the file on disk. Note: for files created with the 'core' driver, HDF5 still requires
                         this be non-empty.
        :param str mode: file access mode

                         =======  ================================================
                         Mode        Behaviour
                         =======  ================================================
                         r        Readonly, file must exist (default)
                         r+       Read/write, file must exist
                         w        Create file, truncate if exists
                         w- or x  Create file, fail if exists
                         a        Read/write if exists, create otherwise
                         =======  ================================================

        :param bool acm_stats: will calculate acm stats if True and write them to acmstats.hdf5 file
        .. _h5py User Guide: http://docs.h5py.org/en/latest/index.html
        """
        # write_modes = ['r+', 'w', 'w-', 'x', 'a']

        super(ACMFile, self).__init__(name, mode, **kwds)
        self.prefix = 'ACM'
        if mode in ["w", "w-", "x"]:
            print("Created HDF5 file " + name)
            return

        self.acm_count = self[self.prefix + 'count'][...]

        # dictionary of (cycle, frequency) indices keyed on frequency in MHz
        self.freq_dict = self.make_freq_ind_dict()

        # convenience parameters
        self.freq = self.freq_dict.keys()
        self.n_cycles = self[self.prefix + 'data'].shape[0]
        self.n_freq = len(self.freq)

        # todo: should be n_freq_per_cycle (but check uses before change)
        self.n_freqs_per_cycle = self[self.prefix + 'data'].shape[1]
        self.band = self[self.prefix + 'data'].attrs['band']
        self.count_scale = count_scale

        # todo: add test if stats file already generated
        # todo: maybe move this to AntennaWeightsWriter (so it can operate over all beams).
        # if acm_stats:
        #    self.acmcheck = ACMcheck(self)

        self.acm = acm = np.asarray(self[self.prefix + 'data'][...], dtype=np.complex64)
        if self.count_scale:
            self.load_scale_acm()

        if acm_stats:
            pass
        #    self.acmcheck.to_file(os.path.dirname(self.filename))


    def create_from_dict(self, dictionary, group='/'):
        base = self['/']
        for key, val in dictionary.items():

            if isinstance(val['dtype'], dict):
                val['dtype'] = np.dtype(val['dtype'])
            if val['kind'] == 'attribute':
                self[group].attrs.create(name=key, data=val['value'], shape=val['space'], dtype=val['dtype'])
            elif val['kind'] == 'dataset':
                self.create_dataset(key, shape=val['space'], dtype=val['dtype'], data=val['value'])

                if 'attributes' in val.keys():
                    self.create_from_dict(val['attributes'], key)

    def create_empty(self):
        self.create_dataset(self.prefix + 'count', (CODIF_CHANNELS_IN_BLOCK+1, PAF_N_FREQ_GROUP), dtype='uint32')
        self.create_dataset(self.prefix + 'data', (CODIF_CHANNELS_IN_BLOCK+1, PAF_N_FREQ_GROUP, N_ELEMENTS, N_ELEMENTS), dtype=np.complex64)
        self.create_dataset(self.prefix + 'status', (CODIF_CHANNELS_IN_BLOCK+1, PAF_N_FREQ_GROUP), dtype='int32')
        self.create_dataset('azimuth', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='double')
        self.create_dataset('bat', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='uint64')
        self.create_dataset('decJ2000', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='double')
        self.create_dataset('elevation', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='double')
        self.create_dataset('onSource', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='int8')
        self.create_dataset('raJ2000', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='double')
        self.create_dataset('rollAngle', (CODIF_CHANNELS_IN_BLOCK+1,), dtype='double')
        self.create_dataset('skyFrequency', (CODIF_CHANNELS_IN_BLOCK+1, PAF_N_FREQ_GROUP), dtype='double')


    def make_freq_ind_dict(self, flagged=True):
        """
        Make a dictionary containing cycle and frequency indices for ACMs of a
        particular sky frequency.  Ignores cycles with errors or zero/low integration
        counts.

        :return: dictionary of ACM indices where the key is frequency in MHz.
                 Each entry in the dictionary is the tuple (ind_cyc, ind_freq)
                 where ind_cyc is an array of cycles at
                 which that frequency occurs in the ACM data and ind_freq is the
                 frequency index in 0..47 for the 48 frequencies downloaded at
                 each cycle.
        :rtype: dict

        """

        sky_frequency = self['skyFrequency'][...]
        self.acm_status = self[self.prefix + 'status'][...]

        # extract a sorted list of unique frequencies in the acm file
        freq_vec = sorted(set(sky_frequency.flatten()))
        freq_dict = OrderedDict()
        for freq_val in freq_vec:
            # noinspection PyTypeChecker
            ind_cyc, ind_freq = np.nonzero(sky_frequency == freq_val)

            # ditch first cycle if it is included as the first cycle after the
            # ACM event is enabled is corrupt.
            # only the first cycle of the first scan is corrupt if using SBs
            # to observe
            # TODO: why are we ditching the first cycle ASKAPTOS-3929
            # if ind_cyc[0] == 0:
            #     ind_cyc = np.delete(ind_cyc, 0)
            #     ind_freq = np.delete(ind_freq, 0)
                # logger.debug("Dropped first ACM cycle ind_cyc={}, ind_freq={}".format(ind_cyc, ind_freq))

            # now remove cycles with errors and zero/low integration counts
            if flagged:
                for i_meas, i_cyc, i_freq in zip(range(len(ind_cyc)), ind_cyc, ind_freq):
                    if self.acm_status[i_cyc, i_freq] != 0:
                        # logger.warning("Bad status for ACM i_cyc={}, i_freq={} at {} MHz".format(i_cyc, i_freq, freq_val))
                        ind_cyc = np.delete(ind_cyc, i_meas)
                        ind_freq = np.delete(ind_freq, i_meas)
                        # logger.debug("Remaining ACMs at {} MHz:  ind_cyc={}, ind_freq={}".format(freq_val, ind_cyc, ind_freq))
                    elif self.acm_count[i_cyc, i_freq] <= 10:
                        # logger.warning("Low integration count of {} for ACM i_cyc={}, i_freq={} at {} MHz".format(
                            #self.acm_count[i_cyc, i_freq], i_cyc, i_freq, freq_val))
                        ind_cyc = np.delete(ind_cyc, i_meas)
                        ind_freq = np.delete(ind_freq, i_meas)
                        # logger.debug("Remaining ACMs at {} MHz:  ind_cyc={}, ind_freq={}".format(freq_val, ind_cyc, ind_freq))

            # only add a particular frequency if there is valid data at that frequency:
            if len(ind_cyc) > 0 and len(ind_freq) > 0:
                freq_dict[freq_val] = (ind_cyc, ind_freq)

        return freq_dict

    def reshape_to_3d(self, element_list=ELEMENT_LIST, flagged=True):
        freq_dict = self.make_freq_ind_dict(flagged)
        # data = np.zeros((len(freq_dict)), dtype=np.complex64)
        data = [0 for __ in range(len(freq_dict))]
        for idx, (key, value) in enumerate(freq_dict.items()):
            data[idx] = select_from_list(self.acm[value[0], value[1]],element_list)[0]

        return np.asarray(data, dtype=np.complex64)

    # todo: make acm a parameter and optionally run count_scale on it at init time?
    # todo: this might be a good spot to calculate the matrix quality stats as the data is traversed
    def load_scale_acm(self, count_scale):
        """
        Retrieves all ACM data and optionally normalises ACMs by integration count and dumps ACMs that
        have error flags or zero/low integration counts if self.count_scale == True.

        :param bool count_scale: if true normalise ACMs by integration count
        """


        if count_scale:
            for i_cyc in range(self.n_cycles):
                for i_freq in range(self.n_freqs_per_cycle):
                    if self.acm_count[i_cyc, i_freq] > 10:
                        # NB: Dimensions in CC and ACM files are different
                        acm[i_cyc, i_freq, ...] /= 1.0 * self.acm_count[i_cyc, i_freq]
                    else:
                        # logger.warn('Low ACM integration count at cyc={}, freq={} ' 'in {}'.format(i_cyc, i_freq, self.filename))
                        # todo: should we set NaN instead of zero for bad integration?
                        # NB: Dimensions in CC and ACM files are different
                        acm[i_cyc, i_freq, ...] = 0.
        return acm

    def get_ccv_reshaped(self):
        """
        Get cross correlation vector (nominally with cicada return port)
        :return: ccv (cross correlation vector)
        """
        # todo: if ACM, chose single row

        if self.prefix not in ['CC', 'ACM']:
            # logger.error('Expected a calibration correlator file or ACM file.')
            raise ValueError('Expected a calibration correlator or ACM file.')

        n_freq_reps = self.n_cycles / 8

        ccv = np.zeros((n_freq_reps, self.n_freq, N_ELEMENTS), np.complex)
        # cnt_cc = np.zeros((n_freq_reps, len(ccfile.freq)))
        for i_freq, freqMHz in enumerate(self.freq):
            ind_cyc, ind_freq = self.freq_dict[freqMHz]
            if self.prefix == 'CC':
                ccv[:, i_freq] = self.acm[ind_cyc[:n_freq_reps], ind_freq[:n_freq_reps], :]
            else:
                ccv[:, i_freq] = self.acm[ind_cyc[:n_freq_reps], ind_freq[:n_freq_reps], :, ODC_PORT-1]*4

        # ccv[:, i_freq] = ccv[ind_cyc[:n_freq_reps], ind_freq[:n_freq_reps]]

        # ccv[:, i_freq, :] /= np.dot(np.reshape(ccv[:, i_freq, 140], (ccv.shape[0],1)), np.ones((1, 192)))

        return ccv

    def estimate_gains_from_ccv(self, paf_ref_port=141, shrink=True):
        """
        Filter calibration correlator response to estimate complex PAF port gains
        """

        ccv_in = self.get_ccv_reshaped()

        # first normalise to reference paf port
        for i_cyc in range(ccv_in.shape[0]):
            for i_freq in range(ccv_in.shape[1]):
                ccv_in[i_cyc, i_freq, :] /= ccv_in[i_cyc, i_freq, paf_ref_port - 1]

        # amplitudes (take median over frequency at each time step)
        # noinspection PyUnresolvedReferences
        # amplitudes = np.median(np.abs(ccv_in), 1)

        # phases (fit linear function across frequency at each time step)
        # gains = np.zeros((ccv_in.shape[0], ccv_in.shape[1], N_PAF_PORTS), 'complex128')

        # for i_freq in range(ccv_in.shape[1]):
            # noinspection PyUnresolvedReferences
        #    gains[:, i_freq, :] = amplitudes[:, :N_PAF_PORTS] * np.exp(1j * np.angle(ccv_in[:, i_freq, :N_PAF_PORTS]))

        if shrink:
            ccv_in = np.median(ccv_in, axis=0)

        return ccv_in

    # noinspection PyPep8Naming
    def get_odc_response(self,
                         ref_port=None,
                         guard_cyc=0,
                         num_cyc_avg=0,
                         freqMHz=None):
        """
        Return the ODC response only
        :param ref_port: Port to normalise to (1 indexed), port 141 is recommended
        :type: int
        :param int guard_cyc: skip this number of cycles at beginning
        :param freqMHz: Frequency in MHz for which to return ODC response.  If None will return
             data for all frequencies which user needs to manually index using self.freq_dict
        :type: int
        :param num_cyc_avg: number of ACM integration cycles to average for
                            input to weights calculation [default 0]
        :type num_cyc_avg: int
        :return: Array of the gain at each port (length=192)
        :type: np_array

        """
        # todo: think about screening for RFI or other errors
        # todo: add option to normalise to cal source autocorrelation

        average_flag = False
        if num_cyc_avg >= 1:
            average_flag = True
            # logger.info("ACM will be averaged.")

        averaged_acm = None
        if average_flag:
            averaged_acm = self.average_acm(guard_cyc=guard_cyc, num_cyc_avg=num_cyc_avg)

        # Get ODC Response
        # Can only Normalise if a particular frequency has been selected (?):
        if freqMHz is None and ref_port is not None:
            # logger.warn('freqMHz: {}, ref_port: {}'.format(freqMHz, ref_port))
            raise IOError('Can only normalise if a particular frequency has been selected')

        if freqMHz is None:
            # logger.info("ODC Response for single frequency is being returned, Freq: {}.".format(freqMHz))
            if average_flag:
                odc_response = averaged_acm[:, ODC_PORT - 1, :]
            else:
                odc_response = self.acm[:, :, ODC_PORT - 1, :]

        # Particular Freq is specified
        else:
            if average_flag:
                odc_response = averaged_acm[self.freq.index(freqMHz), ODC_PORT - 1, :]
            else:
                ind_cyc, ind_freq = self.freq_dict[freqMHz]
                odc_response = self.acm[ind_cyc[0], ind_freq[0], ODC_PORT - 1, :]

            # Assume that if a ref_port is set, the ODC response should be normalised
            if ref_port is not None:
                # logger.info("Reference port specified, normalising ODC response to port: {}.".format(ref_port))
                odc_response = odc_response / odc_response[ref_port - 1]

        return odc_response

    def average_acm(self, guard_cyc, num_cyc_avg):

        # for all frequencies, average the acm and store the ODC
        averaged_acm = np.zeros((len(self.freq), N_ELEMENTS, N_ELEMENTS), np.complex64)
        for i_freq, freqMHz in enumerate(self.freq):
            ind_cyc, ind_freq = self.freq_dict[freqMHz]

            cycles_selected = ind_cyc[guard_cyc:guard_cyc + num_cyc_avg]

            averaged_acm[i_freq][:][:] = np.average(
                self.acm[cycles_selected, ind_freq[guard_cyc:guard_cyc + num_cyc_avg], ODC_PORT - 1, :], 0)

        return averaged_acm

    def __str__(self):
        """
        Text summary of acm.hdf5 file contents
        """
        txt = "ACM Summary\n"
        txt += "===========\n"
        txt += 'Filename: {}\n\n'.format(self.filename)

        txt += "{0:<20} {2:<10} {1:<19}\n".format('Dataset', 'Shape', 'Type')
        txt += "{0:<20} {2:<10} {1:<19}\n".format('-------', '-----', '----')
        txt += '/\n'  # root group

        # print attributes of root group
        for key, value in self.attrs.iteritems():
            txt += "|-{0:<18} {2:<10} {1:<19} {3:<10}\n".format(key, value.shape, value.dtype, value)

        # print datasets of root group
        for key, value in self.iteritems():
            txt += "{0:<20} {2:<10} {1:<19}\n".format(key, value.shape, value.dtype)
            # print attributes of datasets
            for attr_key, attr_value in value.attrs.iteritems():
                if attr_key == 'DIMENSION_LIST':
                    dims = []
                    for i_dim in range(len(attr_value)):
                        if not bool(attr_value[i_dim]):
                            dims += ['->NULL']
                        else:
                            dims += ['->{}'.format(self[attr_value[i_dim]].name)]
                    txt += "  |-{0:<16} {2:<10} {1:<19} {3:<10}\n".format(attr_key, attr_value.shape,
                                                                          attr_value.dtype, dims)
                elif attr_key == 'REFERENCE_LIST':
                    refs = []
                    for i_ref in range(len(attr_value)):
                        refi = attr_value[0]
                        if not bool(refi[0]):
                            refs += ['->NULL']
                        else:
                            try:
                                refs += ['->{} dim {:d}'.format(self[refi[0]].name, refi[1])]
                            except TypeError:
                                if not refi:
                                    refs += '[]'
                            except ValueError:
                                refs += ['unable_to_dereference']
                    txt += "  |-{0:<16} {2:<10} {1:<19} {3:<10}\n".format(attr_key, attr_value.shape,
                                                                          'object_list', refs)
                else:
                    #    print h5file[attr_value[0]].name
                    txt += "  |-{0:<16} {2:<10} {1:<19} {3:<10}\n".format(attr_key, attr_value.shape,
                                                                          attr_value.dtype, attr_value)
        return txt

    def paf2odc(self, threshold=-25, cal_port=ODC_PORT - 1):
        """
        Calculate the PAf_2_ODC Power Ratio
        :param threshold: Value for which PAF2ODC error should be flagged (in dB)
        :type: int
        :param cal_port: 0 indexed value of column from which to extract the ODC response
        :type: int
        :return odc_pow_dB: PAF2ODC value in dB
        :type: float
        :return port_ratios: array of len = 188, True/False depending on if the port is above the threshold or not
        :type: array of booleans
        """

        if self.prefix != "ACM":
            raise IOError('PAF to ODC ratio cannot be calculated for a calibration coefficient file')

        # create array to store the Pearson correlation coefficient
        rho = np.zeros((len(self.freq), N_PAF_PORTS))

        # Calculate the Pearson correlation coefficient at each PAF port for each frequency
        for i_freq, freq_mhz in enumerate(self.freq):

            # No averaging is occuring
            ind_cyc, ind_freq = self.freq_dict[freq_mhz]
            for i_port in range(N_PAF_PORTS):
                # noinspection PyUnresolvedReferences
                rho[i_freq, i_port] = np.abs(self.acm[ind_cyc[0], ind_freq[0], i_port, cal_port] /
                                             np.sqrt(self.acm[ind_cyc[0], ind_freq[0], i_port, i_port] *
                                                     self.acm[ind_cyc[0], ind_freq[0], cal_port, cal_port]))

        # Calculate the paf2odc ratio for all frequencies
        odc_pow_frac = (rho ** 2 / (1 - rho ** 2))

        paf2odc_ratio_db_per_port = np.zeros(N_PAF_PORTS)

        for i in range(N_PAF_PORTS):
            paf2odc_ratio_db_per_port[i] = np.median(odc_pow_frac[:, i])

        # noinspection PyUnresolvedReferences
        paf2odc_ratio_db_per_port = 10 * np.log10(paf2odc_ratio_db_per_port)
        port_working = paf2odc_ratio_db_per_port > threshold

        # Get the median
        odc_pow_frac_med = np.median(odc_pow_frac[:, :].flatten())

        # Convert to dB
        # noinspection PyPep8Naming, PyUnresolvedReferences
        odc_pow_dB = 10 * np.log10(odc_pow_frac_med)

        # convert to bool (remove this to return the actual value)
        # noinspection PyPep8Naming
        odc_working = odc_pow_dB > threshold

        # Check the paf2odc ration is large enough
        #if odc_working:
            # logger.info("PAF to ODC ratio is: {}."
                        #.format(odc_pow_dB))
        #else:
            # logger.warn('PAF to ODC ratio is less than threshold, PAF2ODC: {}dB, Threshold: {}dB'
                        #.format(odc_pow_dB, threshold))

        return odc_working, port_working, paf2odc_ratio_db_per_port

# Added by Niclas Esser
def data_to_dict(acm, sky_frequency, frames, flagged, odir="", antenna=1, sbid=9999, site='pk', schedulingblock=0, band='FILTER_1450', fc=1340, comment='No comment', azimuth=90.0, elevation=90.0, bat=5103284240024128, decj2000=42.2361, raj2000=316, roll_angle=90.0, on_source=1):
    acm_dict = {
        'antenna' : {
            'kind' : 'attribute',
            'dtype' : 'int32',
            'space' : None,
            'value' : antenna
        },
        'scan' : {
            'kind' : 'attribute',
            'dtype' : 'int32',
            'space' : None,
            'value' : sbid
        },
        'site' : {
            'kind' : 'attribute',
            'dtype' : 'S3',
            'space' : None,
            'value' : site
        },
        'schedulingblock' : {
            'kind' : 'attribute',
            'dtype' : 'int32',
            'space' : None,
            'value' : schedulingblock
        },
        'ACMcount' : {
            'kind' : 'dataset',
            'dtype' : 'uint32',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK, PAF_N_FREQ_GROUP),
            'value' : frames,
        },
        'ACMdata' : {
            'kind' : 'dataset',
            'dtype' : {
                'names' : ['r', 'i'],
                'formats' : ['<f4', '<f4']
             },
            'space' : (1+CODIF_CHANNELS_IN_BLOCK, PAF_N_FREQ_GROUP, N_ELEMENTS, N_ELEMENTS),
            'value' : acm,
            'attributes' : {
                'DIMENSION_LABELS' : {
                    'kind' : 'attribute',
                    'dtype' : 'S16',
                    'space' : (4,),
                    'value' : np.asarray(["Measurement Time", "Sky Frequency", "PAF Port X", "PAF Port Y"]),
                },
                'band' : {
                    'kind' : 'attribute',
                    'dtype' : 'S12',
                    'space' : None,
                    'value' : band,
                },
                'centreFrequency' : {
                    'kind' : 'attribute',
                    'dtype' : 'int64',
                    'space' : None,
                    'value' : fc,
                },
                'comment' : {
                    'kind' : 'attribute',
                    'dtype' : 'S11',
                    'space' : None,
                    'value' : comment,
                },
                'filepath' : {
                    'kind' : 'attribute',
                    'dtype' : 'S11',
                    'space' : None,
                    'value' : odir,
                }
            }
        },
        "ACMstatus" : {
            'kind' : 'dataset',
            'dtype' : 'int32',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK, PAF_N_FREQ_GROUP),
            'value' : flagged
        },
        "azimuth" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(azimuth)
        },
        "bat" : {
            'kind' : 'dataset',
            'dtype' : 'uint64',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(bat)
        },
        "decJ2000" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(decj2000)
        },
        "elevation" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(elevation)
        },
        "onSource" : {
            'kind' : 'dataset',
            'dtype' : 'int8',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(on_source)
        },
        "raJ2000" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(raj2000)
        },
        "rollAngle" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK,),
            'value' : np.empty(1+CODIF_CHANNELS_IN_BLOCK).fill(roll_angle)
        },
        "skyFrequency" : {
            'kind' : 'dataset',
            'dtype' : 'double',
            'space' : (1+CODIF_CHANNELS_IN_BLOCK, PAF_N_FREQ_GROUP),
            'value' : sky_frequency,
            'attributes' : {
                "CLASS" : {
                    'kind' : 'attribute',
                    'dtype' : 'S16',
                    'space' : (1,),
                    'value' : 'DIMENSION_SCALE'
                },
                "NAME" : {
                    'kind' : 'attribute',
                    'dtype' : 'S16',
                    'space' : (1,),
                    'value' : 'Frequency (MHz)'
                }
            }
        }
        # "flagged" : {
        #     'kind' : 'dataset',
        #     'dtype' : 'int32',
        #     'space' : (PAF_BANDWIDTH,),
        #     'value' : flagged,
        # }
    }
    return acm_dict
