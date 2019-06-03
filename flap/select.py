# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 19:23:25 2019

@author: Zoletnik
"""
import math
import matplotlib.pyplot as plt
import matplotlib
import time

from .coordinate import *
from .data_object import *

def select_intervals(object_descr, coordinate=None, exp_id='*', intervals=None, options=None, plot_options=None, output_name=None):
    """
    Select intervals from data interactively.
    INPUT:
        object_descr: If a data object: Plot this data object to select.
           String: Will be interpreted as a data object name in flap storage.
        exp_id: The exp_id is dobject_descr is a string
                intervals: Information of processing intervals.
                           If dictionary with a single key: {selection coordinate: description})
                               Key is a coordinate name which can be different from the calculation
                               coordinate.
                               Description can be flap.Intervals, flap.DataObject or
                               a list of two numbers. If it is a data object with data name identical to
                               the coordinate the error ranges of the data object will be used for
                               interval. If the data name is not the same as coordinate a coordinate with the
                               same name will be searched for in the data object and the value_ranges
                               will be used fromm it to set the intervals.
                           If not a dictionary and not None is is interpreted as the interval
                               description, the selection coordinate is taken the same as
                               coordinate.
                           If None, the whole data interval will be used as a single interval.
        coordinate: The name of the coordinate to use for x axis. (string) This will be the
                    coordinate of the selection.
        plot_options: Passed to plot().
        options: Dictionary of options:
                 'Select': 'Start': Select start of intervals. (Needs Lenght to be set.)
                           'End': Select end of intervals. (Needs Lenght to be set.)
                           'Full': Select start and end of interval.
                           'Center': Select center of interval.
                           None: No interactive selection
                 'Length': Length of intervals.
                 'Event' : Dictionary desribing events to search for. A reference time will be
                           determined for each event and a Length interval will be selected
                           symmetrically around it. Trend removal and/or filtering should be done
                           before calling this function.
                           'Type': 'Maximum' or 'Minimum':
                                     Will look for signal pieces above/below threshold
                                     and calculate maximum place of signal in this piece.
                                   'Max-weight' or 'Min-weight':
                                     Same as Maximum and Minimum but selects senter of gravity
                                     for signal piece.
                           'Threshold': The threshold for the event.
                           'Thr-type' Threshold type:
                                         'Absolute': Absolute signal value
                                         'Sigma': Threshold times sigma

        output_name: Output object name in flap storage.

    Return value:
        A data object. Data name is the coordinate name. The error gives the intervals.
    """

    global stop_select, start_coord, end_coord, y_coord, _options, length

    def mouse_event_press(event):
        global stop_select, start_coord, end_coord, y_coord, _options, length
        if (type(event) is  matplotlib.backend_bases.KeyEvent):
            return
        else:
            if (event.button == 3):
                stop_select = True
                print("stop")
                return
            if ((_options['Select'] == 'Full') or (_options['Select'] == 'Start')):
                start_coord.append(event.xdata)
                if (_options['Select'] == 'Start'):
                    end_coord.append(event.xdata + length)
            elif (_options['Select'] == 'Center'):
                start_coord.append(event.xdata - length / 2)
                end_coord.append(event.xdata + length / 2)
            else:
                end_coord.append(event.xdata)
                start_coord.append(event.xdata - length)
            y_coord.append(event.ydata)

    def mouse_event_release(event):
        global stop_select, start_coord, end_coord, _options, length
        if (type(event) is  matplotlib.backend_bases.KeyEvent):
            return
        else:
            if (event.button == 3):
                return
            if (_options['Select'] == 'Full'):
                if (event.xdata <= start_coord[-1]):
                    print("Bad interval")
                    del start_coord[-1]
                    del y_coord[-1]
                else:
                    end_coord.append(event.xdata)

    # Getting the data object
    if (type(object_descr) is str):
        try:
            d = get_data_object(object_descr,exp_id=exp_id)
        except Exception as e:
            raise e
    elif (type(object_descr) is DataObject):
        d = object_descr
    else:
        raise ValueError("Bad object description for interval selection. Use flap.DataObject or string.")

    default_options = {'Select':'Full',
                       'Length': None,
                       'Event': None
                       }
    # Handling options here, as we need the data source
    _options = flap.config.merge_options(default_options, options, data_source=d.data_source, section='Select')

    if ((_options['Select'] is not None) and (_options['Select'] != 'Start')
         and (_options['Select'] != 'End') and (_options['Select'] != 'Full')
         and (_options['Select'] != 'Center')):
        raise ValueError("Invalid value for Select option: " + _options['Select'])

    if (_options['Length'] is not None):
        try:
            length = float(_options['Length'])
        except ValueError:
            raise ValueError("Invalid value to Lenght.")
    else:
        length = None

    if (_options['Select'] is None):
        if (_options['Event'] is None):
            raise ValueError("Either Select or Event option must be set.")
        if (len(d.shape) != 1):
            raise ValueError("Event selection can be done on 1D data only.")
        event = _options['Event']
        try:
            ev_type = event['Type']
        except KeyError:
            raise ValueError("Event type is not set. Use Maximum, Minimum, Max-weight or Min-weight.")
        try:
            ev_thr = event['Threshold']
        except KeyError:
            raise ValueError("Event Threshold is not set.")
        try:
            ev_thr_type = event['Thr-type']
        except KeyError:
            raise ValueError("Event threshold type (Thr-type) is not set. Use Absolute or Sigma.")
    else:
        if (((_options['Select'] == 'Start') or (_options['Select'] == 'End')
             or (_options['Select'] == 'Center'))
             and (length is None)):
            raise ValueError("Missing interval lenght in options.")

    if (coordinate is None):
        raise ValueError("Coordinate should be set for select_intervals.")

    # Getting the coordinate object for the selection coordinate
    try:
        coord_obj = d.get_coordinate_object(coordinate)
    except Exception as e:
        raise e
    if (len(coord_obj.dimension_list) != 1):
        raise ValueError("Select can be done only for coordinates changing along one dimension.")

    if (type(intervals) is dict):
        select_coordinate = list(intervals.keys())[0]
        try:
            select_coord_obj = d.get_coordinate_object(select_coordinate)
        except Exception as e:
            raise e
    else:
        select_coordinate = coordinate
        select_coord_obj = coord_obj
    if (len(select_coord_obj.dimension_list) != 1):
        raise ValueError("Interval selection can be done only for coordinates changing along one dimension.")

    calc_int, calc_int_ind, sel_int, sel_int_ind = d.proc_interval_limits(coordinate, intervals=intervals)
    interval_n = len(sel_int[0])

    if ((_options['Select'] is None) and (ev_thr_type == 'Sigma')):
        # Determining the signal scatter (sigma)
        var = 0
        ndat = 0
        for i_int in range(interval_n):
            # For event selection the data object is suerly 1D
            var += np.sum(d.data[sel_int_ind[0][i_int]:sel_int_ind[1][i_int]] ** 2)
            ndat += sel_int_ind[1][i_int] - sel_int_ind[0][i_int]
        ev_thr = math.sqrt(var / ndat) * ev_thr


    #plt.ioff()
    fig = plt.figure()

    selected_n = 0
    start_coord = []
    end_coord = []
    y_coord = []

    for i_int in range(interval_n):
        if (_options['Select'] is not None):
            if (i_int != 0):
                plt.clf()
            try:
                d.plot(axes=coordinate,
                       slicing={select_coordinate:Intervals(sel_int[0][i_int], sel_int[1][i_int])},
                       options=plot_options)
            except Exception as e:
                raise e
            plt.show()
            plt.draw()
            if (interval_n != 1):
                print("Processing selection interval #"+str(i_int+1)+".")
            if (_options['Select'] == 'Full'):
                print("Select intervals by clicking and dragging mouse. Click right mouse button to finish.")
            elif (_options['Select'] == 'Start'):
                print("Select interval starts by clicking with mouse. Click right mouse button to finish.")
            elif (_options['Select'] == 'End'):
                print("Select interval ends by clicking with mouse. Click right mouse button to finish.")
            elif (_options['Select'] == 'Center'):
                print("Select interval centers by clicking with mouse. Click right mouse button to finish.")
            cid_press = fig.canvas.mpl_connect('button_press_event', mouse_event_press)
            cid_release = fig.canvas.mpl_connect('button_release_event', mouse_event_release)
            stop_select = False
            while stop_select is False:
                time.sleep(0.1)
                plt.pause(0.05)
                if (len(start_coord) == len(end_coord)):
                    if (len(end_coord) > selected_n):
                        plt.plot(np.array([start_coord[-1],end_coord[-1]]),[y_coord[-1],y_coord[-1]])
                        plt.draw()
                        selected_n = len(end_coord)
            fig.canvas.mpl_disconnect(cid_press)
            fig.canvas.mpl_disconnect(cid_release)
            time.sleep(0.1)
        else:
            # Getting the data and the coordinate for this interval
            ind = [0]*len(d.shape)
            data_act = d.data[sel_int_ind[0][i_int]:sel_int_ind[1][i_int]]
            ind[select_coord_obj.dimension_list[0]] = slice(sel_int_ind[0][i_int], sel_int_ind[1][i_int])
            coord_act, cl, ch = coord_obj.data(data_shape=d.shape, index=ind)
            if (sel_int[0][i_int] > sel_int[1][i_int]):
                data_act = np.flip(data_act)
                coord_act = np.flip(coord_act)
            # Finding indices where the condition switches on and off
            if ((ev_type == 'Maximum') or (ev_type == 'Max-weight')):
                cond_on = np.logical_and(data_act[1:] > ev_thr,
                                         data_act[0:-1] <= ev_thr)
                cond_off = np.logical_and(data_act[0:-1] > ev_thr,
                                         data_act[1:] <= ev_thr)
            elif ((ev_type == 'Minimum') or (ev_type == 'Min-weight')):
                cond_on = np.logical_and(data_act[1:] < ev_thr,
                                         data_act[0:-1] >= ev_thr)
                cond_off = np.logical_and(data_act[0:-1] < ev_thr,
                                         data_act[1:] >= ev_thr)
            else:
                raise ValueError("Invalid event condition.")
            ind_on = np.nonzero(cond_on)[0] + 1
            ind_off = np.nonzero(cond_off)[0]
            if (ind_on[0] > ind_off[0]):
                ind_off = ind_off[1:]
            if (len(ind_on) > len(ind_off)):
                if (len(ind_on) == 1):
                    ind_on = np.array([])
                else:
                    ind_on = ind_on[0:-1]
            if (len(ind_off) > len(ind_on)):
                if (len(ind_off) == 1):
                    ind_off = np.array([])
                else:
                    ind_off = ind_on[1:]
            for i_event in range(len(ind_on)):
                if (ev_type == 'Maximum'):
                    act_ev_coord = coord_act[np.argmax(data_act[ind_on[i_event]
                                                                : ind_off[i_event] + 1
                                                                ]
                                                       ) + ind_on[i_event]
                                             ]
                elif (ev_type == 'Minimum'):
                    act_ev_coord = coord_act[np.argmin(data_act[ind_on[i_event]
                                                                : ind_off[i_event] + 1
                                                                ]
                                                       ) + ind_on[i_event]
                                             ]
                elif ((ev_type == 'Max-weight') or (ev_type == 'Min-weight')):
                    act_ev_coord = np.sum(data_act[ind_on[i_event] : ind_off[i_event] + 1]
                                          * coord_act[ind_on[i_event] : ind_off[i_event] + 1]
                                          ) / np.sum(data_act[ind_on[i_event] : ind_off[i_event] + 1])
                if ((act_ev_coord - length / 2 > coord_act[0])
                     and (act_ev_coord + length / 2 < coord_act[-1])):
                    start_coord.append(act_ev_coord - length / 2)
                    end_coord.append(start_coord[-1] + length)
                    y_coord.append(ev_thr)
                    selected_n += 1

    print("Selected "+str(selected_n)+" intervals.")

    plt.clf()
    d.plot(axes=coordinate,
           slicing={coordinate:Intervals(min(sel_int[0]), max(sel_int[1]))},
               options=plot_options)

    if (selected_n != 0):
        for i in range(selected_n):
            plt.plot(np.array([start_coord[i],end_coord[i]]),[y_coord[i],y_coord[i]])
        plt.draw()
        plt.show()

        start_coord = np.array(start_coord)
        end_coord = np.array(end_coord)
        err = [np.zeros(len(start_coord), dtype=start_coord.dtype), end_coord - start_coord]
        coord_int = Coordinate(name='Interval',
                               unit='a.u.',
                               mode=CoordinateMode(equidistant=True),
                               start=1,
                               step=1,
                               dimension_list=[0]
                               )
        d_out= DataObject(data_array=start_coord,
                          error=err,
                          data_unit = Unit(name=coordinate,unit=d.get_coordinate_object(coordinate).unit.unit),
                          exp_id = d.exp_id,
                          data_source = d.data_source,
                          coordinates = [coord_int]
                          )
        if (output_name is not None):
            try:
                add_data_object(d_out, output_name)
            except Exception as e:
                raise e

        return d_out
    else:
        return None







