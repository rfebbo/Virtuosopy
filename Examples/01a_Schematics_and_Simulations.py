import virtuosopy as vp

import numpy as np

# This creates (or overwrites if it exists) a schematic called example_circuit under the vp_demonstration library
# If overwrite=True is not there and you try to create an instance that already exists you will get an error.
sch = vp.Schematic('vp_demonstration', 'example_circuit', overwrite=True)

# create a nmos and print its details
nmos = sch.create_instance('analogLib', 'nmos4', [0.,0.], 'nmos')

#  apply a width, length, and model
nmos['w'] = '5u'
nmos['l'] = '1u'
nmos['model'] = 'nfet'
print(nmos)

# connect the body to the source
sch.create_wire('route', [nmos.pins.S, nmos.pins.B], 'B')

# create a resistor above the nmos connected to the drain
R1 = sch.create_instance('analogLib', 'res', ([nmos.pins.D, 'MINUS'], 'above'), 'R1', conn_name='r_bot')
R1['r'] = '1k'

# create a resistor below the nfet connected to the source
R2 = sch.create_instance('analogLib', 'res', ([nmos.pins.S, 'PLUS'], 'below'), 'R2')
R2['r'] = '10k'

# connect pins to the loose ends
pin_G = sch.create_pin('G', 'input', (nmos.pins.G, 'left', 2))
pin_D = sch.create_pin('D', 'input', (R1.pins.PLUS, 'above', 2), 'R270')
pin_S = sch.create_pin('S', 'input', (R2.pins.MINUS, 'below', 2), 'R90')

if sch.save():
    print('error saving')
else:
    print('Save successful')


model_files = ['/home/rfebbo/Emergent_Circuits/lab4/FinFETdemo/model/FinFET/14nfet.pm']

s = vp.Simulator('100n', sch, model_files)

# setup stimuli
s.bit_stim_defaults = {'val0' : 0, 'val1' : 3300e-3, 'period' : 2e-8, 'rise' : 1e-9, 'fall' : 1e-9}

D_stim = '11111'
S_stim = '00000'
G_stim = '11000'

stims = {}
stims['D'] = {'type' : 'bit', 'data' : D_stim}

stims['G'] = {'type' : 'bit', 'data' : G_stim}

stims['B'] = {'type' : 'bit', 'data' : S_stim}

s.apply_stims(stims)


s.track_net('D')
s.track_net('G')
s.track_net('B')
s.track_net('r_bot', sig_type='r bot')

s.track_pin(nmos.pins.D, group='current')


def calc_vdrop(waves):
    v = waves[0] - waves[1]
    return v

def lv1(waves):
    ids = 0.5 * 29.11e-9
    ids *= (1e-6/500e-9)
    vgs = waves[0] - waves[2]
    vt = 677e-3
    vds = waves[1] - waves[2]
    ids *= ((vgs - vt)**2)*(1+0.05*vds)
    return ids * 1e6

def lv3(waves):
    return waves[0] * 1e6


s.track_custom(fn=calc_vdrop, name='Vd', y_label='NMOS Voltage Drop(V)', signal_types=['v', 'v'], pins=['r_bot', 'B'], group='v_drop')
s.track_custom(fn=calc_vdrop, name='Vr', y_label='Resistor Voltage Drop(V)', signal_types=['v', 'v'], pins=['D', 'r_bot'], group='v_drop')

p_values = None
s.run(plot_in_v=False, p_values=p_values)

s.plot(interactive=False)
