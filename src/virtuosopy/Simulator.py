# aided by: https://iamanintrovert.github.io/notes/Running-Spectre-Simulation-from-python/
# aided by: https://github.com/unihd-cag/skillbridge/blob/master/docs/examples/custom_functions.rst
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams['axes.formatter.useoffset'] = False

from matplotlib.lines import Line2D
import matplotlib.colors as mcolors
from .Instance import _Pin
from .vp_utils import *

# from skillbridge.client.translator import Symbol
from skillbridge.client.hints import Symbol
import numpy as np
import os

import ipywidgets as w
from IPython.display import display

import time

class Simulator:
    '''
    Simulator Class Performs:
     -transient simulations\n
     -performs custom funcitons on waves\n
     -retieves data from Virtuoso in a readable format\n
     -plotting\n
    '''
    def __init__(self, sch, model_files = None, view='schematic', show_netlist = False, verbose=True, errpreset=None):
        self.sch = sch
        self.verbose = verbose

        self.errpreset = errpreset

        # set simulator
        self.sch.ws['simulator'](Symbol('spectre'))

        self.sch.ws['design'](sch.lib_name, sch.cell_name, view, 'w')
        self.sch.ws['resultsDir'](os.getcwd() + f'/sim_output/{self.sch.cell_name}')

        if sch.ws['createNetlist'](recreate_all=True, display=show_netlist) == None:
            if self.verbose:
                print('ERROR netlist not created')

        if model_files is not None:
            model_files = [os.path.abspath(m) for m in model_files]
            self.sch.ws['modelFile'](*model_files)


        # analysis order in case of multiple analysis
        self.sch.ws['envOption'](Symbol('analysisOrder'), ['tran'])

        # the time values for each simulation
        self.x = []

        # dictionary of waves keyed on netname containing another dictionary with wave data:
        # 'y' - list of ydata, [0] is a list from the 1st simulation etc.
        # 'type' - used by virtuoso to denote voltage ('v') or current ('i') for custom waves this is the y_axis label
        # 'group' - name of the group for checkboxes in plot
        # 'data type' - used to denote a custom wave
        # 'fn' - function to pass wave data to for custom functions
        self.waves = {}

        # custom functions
        self.custom_wave_names = []
        self.cust_data_types = []

        # spectre stimuli
        self.bit_stim_defaults = {'val0' : 0, 'val1' : 1.2, 'period' : 1e-9, 'rise' : 200e-12, 'fall' : 200e-12}

        # plot widgets (checkboxes)
        self.groups = []

        # paramter analysis sets
        self.param_sets = None

    def tran(self, duration):
        if isinstance(duration, str):
            duration = convert_str_to_num(duration)

        self.duration = duration

        if self.errpreset is None:
            self.sch.ws['analysis'](Symbol('tran'), '?start', '0', '?stop', duration, '?errpreset', 'moderate')
        elif self.errpreset == 'liberal' or self.errpreset == 'conservative' or self.errpreset == 'moderate':
            self.sch.ws['analysis'](Symbol('tran'), '?start', '0', '?stop', duration, '?errpreset', self.errpreset)
        else:
            raise Exception(f'Invalid errpreset: {self.errpreset}')



# stimulus file example:
# cat /<path to netlist>/_graphical_stimuli.scs
    # _vreset_b_1 (reset_b_1 0) vsource data="011" rptstart=1 rpttimes=0 val1=0 val0=3.3 period=2n type=bit
    # _v0 (0 0) vsource dc=0 type=dc
    # _vmtop (mtop 0) vsource wave=[ 0 800.0m 2n 1.2 5n 0 ] type=pwl
    # _vvg (vg 0) vsource dc=1.2 type=dc
    # _vout_2 (out_2 0) vsource dc=1.2 type=dc

# spectre snipit using stimulus file:
    # stimulusFile( ?xlate nil
    #     "/<path to netlist>/_graphical_stimuli.scs")
    def apply_stims(self, stims):
        stim_filename = os.getcwd() + f'/sim_output/{self.sch.cell_name}/graphical_stimuli.scs'

        with open(stim_filename, 'w') as f:
            for name, s in stims.items():
                
                if s['type'] == 'bit':
                    for d in self.bit_stim_defaults.keys():
                        if d not in s:
                            s[d] = self.bit_stim_defaults[d]
                    
                    f.write(f"""_v{name} ({name} 0) vsource data="{s['data']}" rptstart=1 rpttimes=0 val1={s['val1']} val0={s['val0']} rise={s['rise']} fall={s['fall']} period={s['period']} type=bit\n""")
                elif s['type'] == 'pwl':
                    f.write(f"""_v{name} ({name} 0) vsource wave=\\[ {s['wave']} \\] type=pwl\n""")
                elif s['type'] == 'dc':
                    f.write(f"""_v{name} ({name} 0) vsource dc={s['voltage']} type=dc\n""")

        self.sch.ws['stimulusFile'](stim_filename)

    def save_pin(self, pin, signal_type):
        pinfname = pin
        if type(pin) == _Pin:
            pinfname = pin.fname

        self.sch.ws['save'](Symbol(signal_type), pinfname)

        return pinfname

    def track_pin(self, pin, group=None, sig_type='Current'):
        pinfname = self.save_pin(pin, 'i')

        self.waves[pinfname] = {}
        self.waves[pinfname]['type'] = sig_type

        if sig_type not in self.cust_data_types:
            self.cust_data_types.append(sig_type)

        if group != None:
            self.waves[pinfname]['group'] = group
            if group not in self.groups:
                self.groups.append(group)

    def track_net(self, net, group=None, sig_type='Voltage'):
        if not isinstance(net, str):
            if self.verbose:
                print("Please provide a net in the form of a string.")
            return

        self.sch.ws['save'](Symbol('v'), net)
        net_name = f'/{net}'
        self.waves[net_name] = {}
        self.waves[net_name]['type'] = sig_type

        if sig_type not in self.cust_data_types:
            self.cust_data_types.append(sig_type)

        if group != None:
            self.waves[net_name]['group'] = group
            if group not in self.groups:
                self.groups.append(group)

    # enables the user to provide a custom function for calculating things such as resistance
    # fn - a funciton which will recieve an array of np arrays of the requested pins
    def track_custom(self, fn, name, y_label, signal_types, pins, group=None):
        # holds the full names of the pins needed in the function
        pin_fns = []
        # track the pins required for the custom funciton
        for signal_type, pin in zip(signal_types, pins):
            
            pinfname = self.save_pin(pin, signal_type)

            if pinfname not in self.waves:
                self.waves[pinfname] = {}
                self.waves[pinfname]['type'] = signal_type
                self.waves[pinfname]['no plot'] = True
            pin_fns.append(pinfname)

        if name in self.custom_wave_names:
            raise Exception(f'{name} is already a custom wave name.')

        self.custom_wave_names.append(name)
        self.waves[name] = {}
        self.waves[name]['pins'] = pin_fns
        self.waves[name]['type'] = y_label
        self.waves[name]['data type'] = 'custom'
        self.waves[name]['fn'] = fn

        if y_label not in self.cust_data_types:
            self.cust_data_types.append(y_label)

        if group != None:
            self.waves[name]['group'] = group
            if group not in self.groups:
                self.groups.append(group)

    # builds a list of waves needed for each custom function and calls them
    def calc_custom(self):
        for cw in self.custom_wave_names:
            self.waves[cw]['y'] = []
            for x_i in range(len(self.x)):
                wave_y_data = []
                for p in self.waves[cw]['pins']:
                    
                    wave_y_data.append(self.waves[p]['y'][x_i])
            
                y = self.waves[cw]['fn'](wave_y_data)
                self.waves[cw]['y'].append(y)

    # calls getData to extract the waves from spectre
    def extract_waves(self):
        if len(self.waves) == 0:
            return None
        
        waveforms = []
        extracted_names = []
        bad_waves = []
        self.run_ok = True

        # call get data for each wave
        for name in self.waves:
            # skip custom calculated waves
            if 'fn' in self.waves[name]:
                continue

            w = self.sch.ws.get.data(name)

            if w != None:
                waveforms.append(w)
                extracted_names.append(name)
                self.waves[name]['signal_type'] = w.leaf_signal_type_name
            else:
                self.run_ok = False
                if self.verbose:
                    print(f'Error: Unable to extract {name}. Does it exist? Check that it is saved or try track_net')
                bad_waves.append(name)
            
        # remove waves which were not able to be extracted
        for name in bad_waves:
            self.waves.pop(name)
        
        # check to see if there are any waves left
        if len(waveforms) == 0:
            if self.verbose:
                print('No valid waves to extract')
            return

        # convert the virtuoso wave format into a list of numpy arrays for each parameter set
        # if there are no param sets, the length of the list is 1
        if self.param_sets == None:
            y, x = self.waveform_to_vector(waveforms)
        else:
            y, x = self.param_waveform_to_vector(waveforms)
            

        self.x = x

        for name, y_i in zip(extracted_names, y):
            self.waves[name]['y'] = y_i

        return self.waves

    # used in extract_waves()
    def waveform_to_vector(self, waveforms):
        vectors = []
        x_vec = []
        
        # convert the y data in each wave to numpy array
        for wave in waveforms:
            y_wave = self.sch.ws.dr.get_waveform_y_vec(wave)

            y_vec = []
            # each timestep
            for i in range(self.sch.ws.dr.vector_length(y_wave)):
                y_vec.append(self.sch.ws.dr.get_elem(y_wave, i))

            vectors.append([np.asarray(y_vec)])

        # x vector is same for all these y vector
        x_wave = self.sch.ws.dr.get_waveform_x_vec(waveforms[0])
        
        for i in range(self.sch.ws.dr.vector_length(x_wave)):
            x_vec.append(self.sch.ws.dr.get_elem(x_wave, i))
        
        return vectors, [np.asarray(x_vec)]


    def unpack_nested_waveform(self, waveform):
        # construct the first waveform set
        y_vecs = [self.sch.ws.dr.get_waveform_y_vec(waveform)]
        x_vecs = [self.sch.ws.dr.get_waveform_x_vec(waveform)]
                    
        # labels = []

        # check if the first waveform in the current waveform set is a number or another waveform
        while type(self.sch.ws.dr.get_elem(y_vecs[0], 0)) != float:
            next_x_vecs = []
            next_y_vecs = []

            # labels.append([]*self.sch.ws.dr.vector_length(x_vec))

            # for x_vec in x_vecs:
            #     for i in range(self.sch.ws.dr.vector_length(x_vec)):
            #         labels[i].append(self.sch.ws.dr.get_elem(x_vec, i))
            
            for y_vec in y_vecs:
                # get the labels for the next loop
                for i in range(self.sch.ws.dr.vector_length(y_vec)):
                    next_x_vecs.append(self.sch.ws.dr.get_waveform_x_vec(self.sch.ws.dr.get_elem(y_vec, i)))
                
                # get the waveforms for the next loop
                for i in range(self.sch.ws.dr.vector_length(y_vec)):
                    next_y_vecs.append(self.sch.ws.dr.get_waveform_y_vec(self.sch.ws.dr.get_elem(y_vec, i)))

            y_vecs = next_y_vecs
            x_vecs = next_x_vecs

        return y_vecs, x_vecs


    # used in extract waves during parametric analysis
    def param_waveform_to_vector(self, waveforms):
        waves_y_data = []
        x_data = []

        # convert the y data in each wave to numpy array
        for wave in waveforms:
            y_vecs, _ = self.unpack_nested_waveform(wave)

            y_data = []
            for y_vec in y_vecs:
                y_data.append([])
                for i in range(self.sch.ws.dr.vector_length(y_vec)):
                    y_data[-1].append(self.sch.ws.dr.get_elem(y_vec, i)) #type:ignore

                y_data[-1] = np.asarray(y_data[-1])

            waves_y_data.append(y_data)

        # x vector is same for all y vectors
        _, x_vecs = self.unpack_nested_waveform(waveforms[0])

        for x_vec in x_vecs:
            x_data.append([])
            for i in range(self.sch.ws.dr.vector_length(x_vec)):
                x_data[-1].append(self.sch.ws.dr.get_elem(x_vec, i)) #type:ignore

            x_data[-1] = np.asarray(x_data[-1])
        
        return waves_y_data, x_data

# Example OCEAN script for parametric analysis:
    # desVar(	  "w_read_t" 1u	)
    # desVar(	  "wt_read_b" 2u	)
    # envOption(
    # 	'analysisOrder  list("tran") 
    # )
    # temp( 27 ) 
    # paramAnalysis("wt_read_b" ?values '(1e-06 2e-06 ) ?sweepType 'paramset
    #   paramAnalysis("w_read_t" ?values '(3e-06 4e-06 ) ?sweepType 'paramset
    # ))
    # paramRun()

    def call_paramAnalysis(self, p_values):
        l, v = list(p_values.items())[0]
        if len(p_values) == 1:
            return self.sch.ws['paramAnalysis'](l, values=v, sweep_type=Symbol('paramset'))
        else:
            p_values.pop(l)
            return self.sch.ws['paramAnalysis'](l, self.call_paramAnalysis(p_values), values=v, sweep_type=Symbol('paramset'))

    
    # runs the simulation
    def run(self, plot_in_v=False, p_values=None):

        if p_values != None:
            # store the parameter sets
            self.param_sets = p_values

            self.sch.ws['temp'](27)

            # set the default value of each parameter
            for param in self.param_sets:
                self.sch.ws['desVar'](param, self.param_sets[param][0])

            # call the recusive paramAnalysis function
            self.call_paramAnalysis(p_values.copy())
            self.sch.ws['paramRun']()
        else:
            # set temp and run
            self.sch.ws['temp'](27)
            self.sch.ws['run']()

        try:  # skillbridge cannot parse stdobj@0xhexnumber type data. But I don't need any parsing of that data so keeping it in try to prevent error
            self.sch.ws['selectResult'](Symbol('tran'))
        except:
            if self.verbose:
                print('stdobj0x type data encountered! nothing to panic about.')

        # opens plot window in Virtuoso
        if plot_in_v:
            for name in self.waves:
                # skip custom calculated waves
                if 'fn' in self.waves[name]:
                    continue
                self.sch.ws['plot'](self.sch.ws.get.data(name))

        self.extract_waves()

        if self.run_ok == False:
            return None

        # check if the simulation ran as long as requested
        for x in self.x:
            if not np.isclose(self.duration,x[-1]):
                self.run_ok = False
                if self.verbose:
                    print(f"convergence error {x[-1]} != {self.duration}")
                return None
        
        self.calc_custom()
        return 0

    # for the checkboxes in the interactive plot
    def toggle(self, state):
        if isinstance(state['new'], bool):
            mins = []
            maxes = []
            ax = None
            ax_type = None
            for name in self.waves:
                if 'group' in self.waves[name]:
                    for pl in self.waves[name]['pl']:
                        if self.waves[name]['group'] == state['owner'].description:
                            # set the wave equal to the checkbox value
                            pl.set_visible(state['new'])

                            # track the number of visible waves in this ax
                            if state['new'] == True:
                                self.ax_info[self.waves[name]['type']]['count'] += 1
                                pl.set_label(name)
                            else:
                                self.ax_info[self.waves[name]['type']]['count'] -= 1
                                pl.set_label('_nolegend_')

                            # set the number of columns in the legend so that it is not taller than 5
                            ncol = np.max((1,int(self.ax_info[self.waves[name]['type']]['count']/ 5)))
                            self.waves[name]['ax'].legend(loc=(1.01,0.0), ncol = ncol)

                            # store the ax and type so we can change the limits
                            ax_type = self.waves[name]['type']
                            ax = self.waves[name]['ax']
                            # self.waves[name]['ax'].set_ylim((0.0,1.0))

            # resize the axis ylim
            if ax != None:
                for name in self.waves:
                    if self.waves[name]['type'] == ax_type:
                        for pl in self.waves[name]['pl']:
                            if pl.get_visible():
                                mins.append(np.min(self.waves[name]['y']))
                                maxes.append(np.max(self.waves[name]['y']))

                
                if len(mins) > 0:
                    ax_min = min(mins) * self.ax_info[ax_type]['scale_factor']
                    ax_max = max(maxes) * self.ax_info[ax_type]['scale_factor']
                    border = (ax_max - ax_min) * 0.1
                    ax_min -= border
                    ax_max += border
                    ax.set_ylim((ax_min,ax_max))


            
            self.fig.canvas.draw()
            # plt.autoscale()
            # plt.draw()

    def plot(self, interactive=True):
        if self.run_ok == False:
            print('Simulation Failed. see ' + f'"./sim_output/{self.sch.cell_name}/psf/spectre.out" for details.' )
            print('From spectre.out :\n')
            with open(f'./sim_output/{self.sch.cell_name}/psf/spectre.out', 'r') as f:
                for l in f:
                    if 'error' in l.lower() or 'warning' in l.lower():
                        print('\t' + l)
            # return

        self.ax_info = {}
        linestyles = ['solid', 'dashed', 'dashdot', 'dotted']
        colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']
        colors += list(mcolors.BASE_COLORS) # type: ignore
        colors += list(mcolors.CSS4_COLORS) # type: ignore
 
        if interactive:
            plt.ion()

        self.fig, _ = plt.subplots(len(self.cust_data_types), figsize=(13, 10), sharex=True)

        ax = self.fig.axes

        # y labels for voltage, current, and custom
        y_labels = self.cust_data_types
        # pair each y label with an axis
        ax_dict = {}
        legend_elements = {}
        for l, ax_i in zip(y_labels, ax):
            ax_dict[l] = ax_i
            legend_elements[l] = []
            self.ax_info[l] = {'count' : 0, 'scale_factor' : 1}

        for name in self.waves:
            if 'no plot' in self.waves[name]:
                continue

            y_label = self.waves[name]['type']
            self.ax_info[y_label]['count'] += 1
            cur_ax = ax_dict[y_label]
            pls = []
            for (i,x), y in zip(enumerate(self.x), self.waves[name]['y']):
                pls.append(cur_ax.plot(x * 1e9, y, label=name, linestyle=linestyles[i], color=colors[self.ax_info[y_label]['count']-1])[0])
                if i == 0:
                    legend_elements[y_label].append(Line2D([0], [0], color=colors[self.ax_info[y_label]['count']-1], label=name))

            cur_ax.set_ylabel(y_label)
            self.waves[name]['ax'] = cur_ax
            self.waves[name]['pl'] = pls
        
        for l, ax_i in ax_dict.items():
            ncol = max((1,int(self.ax_info[l]['count']/ 5)))
            # ax_i.legend(tuple(lines[l]), tuple(labels[l]), loc=(1.01,0.0), shadow=True)
            if self.param_sets != None:
                for i in range(len(list(self.param_sets.values())[0])):
                    v = []
                    p = '['
                    for v_i in list(self.param_sets.values()):
                        v.append(v_i[i])

                    for p_i in self.param_sets.keys():
                        p += p_i + ', '
                        
                    p = p[:-2] + ']'
                    legend_elements[l].append(Line2D([0], [0], color='k', linestyle=linestyles[i], label=f'{p} = {v}'))
            
            ax_i.legend(handles=legend_elements[l], loc=(1.01,0.0), shadow=True)
            # ax_i.legend(loc=(1.01,0.0), ncol = ncol)
    
        ax[-1].set_xlabel('Time (ns)')

        if interactive:
            # widgets (check boxes)
            ch_bxs = []
            for g in self.groups:
                c = w.Checkbox(
                    value=True,
                    description=g,
                    disabled=False,
                    indent=False
                )
                c.observe(self.toggle)
                ch_bxs.append(c)

            
            h = w.HBox(ch_bxs)
            display(h)

        plt.tight_layout()
        plt.show()

