import virtuosopy as vp

# This creates (or overwrites if it exists) a schematic called example_circuit under the vp_demonstration library
# If overwrite=True is not there and you try to create an instance that already exists you will get an error.
sch = vp.Schematic('vp_demonstration', 'example_circuit', overwrite=True)

# create a nmos and print its details
nmos = sch.create_instance('analogLib', 'nmos4', [0.,0.], 'nmos')

#  apply a width, length, and model
nmos['w'] = 'w_read'
nmos['l'] = '1u'
nmos['model'] = 'nfet'
print(nmos)

# connect the body to the source
sch.create_wire([nmos.pins.B, nmos.pins.B.pos + [2., -0.]], 'gnd!')

# create a resistor above the nmos connected to the drain
# instead of supplying an absolute position, we supply a connection and relative position in the form:
#   vp.ConnPos(nmos.pins.D, 'MINUS', 'above', net_name='r_bot')
R1 = sch.create_instance('analogLib', 'res', vp.ConnPos(nmos.pins.D, 'MINUS', 'above', net_name='r_bot'), 'R1')
R1['r'] = 'r1'

# create a resistor below the nfet connected to the source
R2 = sch.create_instance('analogLib', 'res', vp.ConnPos(nmos.pins.S, 'PLUS', 'below'), 'R2')
R2['r'] = 'r2'

# connect pins to the loose ends
pin_G = sch.create_pin('G', 'input', vp.ConnPos(nmos.pins.G, None, 'left', 2))
pin_D = sch.create_pin('D', 'input', vp.ConnPos(R1.pins.PLUS, None, 'above', 2), 'R270')
pin_S = sch.create_pin('S', 'input', vp.ConnPos(R2.pins.MINUS, None, 'below', 2), 'R90')

sch.add_param_vars(['w_read', 'r1', 'r2'])

if sch.save():
    print('error saving')
else:
    print('Save successful')


# Setup Simulator
print('Setting up Simulation...')
model_files = ['../../model/FinFET/14nfet.pm']

# simulate for 60ns
s = vp.Simulator(sch, model_files)
s.tran('60n')

# setup stimuli
stims = {}

# Piecewise linear voltage stimulus 
stims['D'] = {'type' : 'pwl', 'wave' : vp.create_wave([0.0, 3.3], 20e-9, 200e-12)}

# bit stimulus
# for multiple bit stimuli using the same parameters use this variable to set the defaults
s.bit_stim_defaults = {'val0' : 0, 'val1' : 3.3, 'period' : 2e-8, 'rise' : 1e-9, 'fall' : 1e-9}
# to change anything just add the key and value to the stimuli
stims['G'] = {'type' : 'bit', 'data' : '11000'}

# DC stimulus
stims['S'] = {'type' : 'dc', 'voltage' : 0.0}

# apply the stims
s.apply_stims(stims)

s.track_net('D')
s.track_net('G')
s.track_net('S')
s.track_net('r_bot', sig_type='r bot')

s.track_pin(nmos.pins.D, group='current')

def calc_vdrop(waves):
    v = waves[0] - waves[1]
    return v

s.track_custom(fn=calc_vdrop, name='Vd', y_label='NMOS Voltage Drop(V)', signal_types=['v', 'v'], pins=['r_bot', 'S'], group='v_drop')
s.track_custom(fn=calc_vdrop, name='Vr', y_label='Resistor Voltage Drop(V)', signal_types=['v', 'v'], pins=['D', 'r_bot'], group='v_drop')

p_values = {'w_read' : [1e-6,2.5e-6, 5e-6], 'r1' : [300, 40000, 10], 'r2' : [200, 50000, 80]}

print('Running Simulation...')
s.run(plot_in_v=False, p_values=p_values)

print('Plotting...')
s.plot(interactive=False)


