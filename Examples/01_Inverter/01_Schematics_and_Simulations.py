import virtuosopy as vp
import matplotlib.pyplot as plt

# This creates (or overwrites if it exists) a schematic called example_circuit under the vp_demonstration library
# If overwrite=True is not there and you try to create an instance that already exists you will get an error.
sch = vp.Schematic('vp_demonstration', 'inverter', overwrite=True)

## create an nmos
nmos = sch.create_instance('analogLib', 'nmos4', [0.,0.], 'nmos')

# apply a width, length, and model
nmos['w'] = '0.5u'
nmos['l'] = '1u'
nmos['model'] = 'nfet'
# print its details
print(nmos)

# connect the body to the source
sch.create_wire([nmos.pins.S, nmos.pins.B], 'gnd!')

## create a pmos
pmos = sch.create_instance('analogLib', 'pmos4', vp.ConnPos(nmos.pins.D, 'D', 'above'), 'pmos')

# apply a width, length, and model
pmos['w'] = '0.5u'
pmos['l'] = '1u'
pmos['model'] = 'pfet'

# connect the body to the source
sch.create_wire([pmos.pins.S, pmos.pins.B], 'vdd!')

# connect the gates
sch.create_wire([nmos.pins.G, pmos.pins.G])

# connect input pin
pin_In = sch.create_pin('In', 'input', vp.ConnPos(nmos.pins.G, None, 'left', 2))
pin_Out = sch.create_pin('Out', 'output', vp.ConnPos(nmos.pins.D, None, 'right', 2))

if sch.save():
    print('error saving')
else:
    print('Save successful')

# Setup Simulator
print('Setting up Simulation...')
model_files = ['../../model/FinFET/14nfet.pm', '../../model/FinFET/14pfet.pm']

# simulate for 100ns
s = vp.Simulator(sch, model_files)
s.tran('20n')

# setup stimuli
stims = {}

# Piecewise linear voltage stimulus 
stims['In'] = {'function' : 'pwl', 'wave' : vp.create_wave([0.0, 1.2], 10e-9, 1e-9)}

# DC stimulus
stims['vdd!'] = {'function' : 'dc', 'voltage' : 1.2}
stims['gnd!'] = {'function' : 'dc', 'voltage' : 0.0}

# apply the stims
s.apply_stims(stims)

s.track_net('In')
s.track_net('Out')

s.track_pin(nmos.pins.D, group='current')

s.run(plot_in_v=False)

s.plot(save='./images/sim_waves.png')

# create a voltage transfer curve
x = s.waves['/In']['y']
y = s.waves['/Out']['y']

fig, ax = plt.subplots(1,1,figsize=(5,4), dpi=200)
plt.xlabel('Input (V)')
plt.ylabel('Output (V)')
plt.plot(x,y)
plt.tight_layout()
plt.savefig('./images/VTC.png')
plt.show()



