from .Instance import _Inst, _Params, _Pins, _Pin
from skillbridge import Workspace
from .vp_utils import *
import numpy as np
import os

class Schematic:
    def __init__(self, lib_name, cell_name, ws_name="default", overwrite=False, verbose=True):
        # ws_name = os.getenv('key')

        if ws_name == "default":
            net_id = os.getenv('USER')
            print(net_id)
            ws = Workspace.open(workspace_id=f'{net_id}_0')

        else:
            ws = Workspace.open(workspace_id=ws_name)

        
        self.ws = ws

        if overwrite:
            cv = ws.db.open_cell_view_by_type(lib_name, cell_name, "schematic",
                                          "schematic", "w")
        else:
            cv = ws.db.open_cell_view_by_type(lib_name, cell_name, "schematic",
                                          "schematic", "a")


        self.cv = cv
        self.lib_name = lib_name
        self.cell_name = cell_name
        self.instances = {}
        self.wires = []
        self.voltage_sources = []
        self.verbose = verbose
        self.param_vars = []
        self.cdf_ignore = []
        self.pin_nets = []

    def create_instance(self, lib_name, cell_name, pos, name, rot='R0'):
        """
        Instantiate a component in the schematic

        Parameters
        ----------
        lib_name : string
            library for the component (eg. 'analoglib')
        cell_name : string
            cell name for the component (eg. 'nmos4')
        pos : [float, float] or ConnPos
            position of the component (eg. [0., 0.] or ConnPos(nmos.pins.D, 'MINUS', 'above') )
        name : string
            instance name for the component (eg. 'MN1')
        rot : string
            rotation (eg. 'R90')
        """
        inst: _Inst = None # type: ignore

        if isinstance(pos, ConnPos):
            inst = _Inst(self.ws, self.cv, lib_name, cell_name, pos.pos1, name, rot)
            self.create_wire([pos.external_pin, inst.pins[pos.internal_pin]], label=pos.net_name, label_offset=pos.label_offset)
        elif isinstance(pos, list) or isinstance(pos, np.ndarray):
            if len(pos) == 2:
                inst = _Inst(self.ws, self.cv, lib_name, cell_name, pos, name, rot)
        else:
            print('Pos parameter must be:')
            print('\tan xy coordinate represented by an array of length 2')
            print('\ta ConnPos')
            print("\t (eg. [0., 0.] or ConnPos(nmos.pins.D, 'MINUS', 'above') )")
            print(f"\t {pos}")
            return inst

        self.instances[name] = inst
        return inst

    def create_wire(self, positions, label=None, label_offset=None, mode='route'):

        # transform into virtuoso coords
        pos = []
        for i in range(len(positions)):
            if isinstance(positions[i], _Pin):
                pos.append(list(transform(positions[i].pos)))
            elif 'base_name' in dir(
                    positions[i]) and positions[i].base_name[:3] == 'PIN':
                pos.append(positions[i].xy)
            else:
                pos.append(list(transform(positions[i])))

        w = self.ws.sch.create_wire(self.cv, mode, "full", pos, snap_spacing,
                                    snap_spacing, 0.0)

        if label != None:
            l_pos = pos[0]
            if label_offset != None:
                label_offset = transform(label_offset)
                l_pos = np.asarray(l_pos) + np.asarray(label_offset)
                l_pos = list(l_pos)
            self.ws.sch.create_wire_label(
                self.cv,
                w[0],
                l_pos,
                label,
                "upperLeft",
                "R0",
                "fixed",
                snap_spacing,
                None,
            )

        self.wires.append(w)
        return w

    def create_vsource(self,
                       type,
                       pos,
                       name,
                       p_name,
                       n_name="gnd!",
                       rotation="R0"):
        V_src = _Inst(self.ws, self.cv, "analogLib", type, pos, name, rotation)

        # vdd = _Inst(self.ws, self.cv, "analogLib", 'vdd', pos + [0.,4.], 'vdd', rotation)
        
        # inst_cv = self.ws.db.open_cell_view('analogLib', 'vdd', "symbol")
        # inst = self.ws.sch.create_inst(self.cv, inst_cv, 'vdd', list(pos + [0.,4.]), rotation)

        

        self.create_wire(
            [V_src.pins.PLUS, [V_src.pins.PLUS.x, V_src.pins.PLUS.y + 4.0]],
            p_name,
            [1.0, 3.0],
        )

        self.create_wire(
            [V_src.pins.MINUS, [V_src.pins.MINUS.x, V_src.pins.MINUS.y - 4.0]],
            n_name,
            [1.0, -1.5],
        )

        self.voltage_sources.append(V_src)
        return V_src

    def create_note(self, note, pos, size=0.125):
        pos = transform(pos)
        self.ws.sch.create_note_label(self.cv, list(pos), note, "lowerLeft",
                                      "R0", "fixed", size, "normalLabel")

    def create_pin(self, name, direction, pos, rot='R0'):
        if isinstance(pos, ConnPos):
            pin_pos = pos.pos1
            pos.external_pin.netname = name
            self.create_wire([pos.external_pin, pin_pos], label=pos.net_name, label_offset=pos.label_offset)
            if direction == 'wire':
                return
            pos = pin_pos

        pos = transform(pos)
        cell_name = None
        if direction == "input":
            cell_name = "ipin"
        elif direction == "output":
            cell_name = "opin"
        elif direction == "inputOutput":
            cell_name = "iopin"
        else:
            if self.verbose:
                print(f"Creation of Pin {name} Failed! \ndirection should be one of: [input, output, inputOutput]. got {direction}")
            return 0

        inputCVId = self.ws.db.open_cell_view("basic", cell_name, "symbol")
        p_id = self.ws.sch.create_pin(self.cv, inputCVId, name, direction,
                                      None, list(pos), rot)

        if name not in self.pin_nets:
            self.pin_nets.append(name)
        return p_id

    def add_param_vars(self, vars):
        self.param_vars += vars

    def add_cdf_ignore(self, vars):
        self.cdf_ignore += vars

    def redraw(self):
        self.ws.hi.redraw()

    def do_cdf_callbacks(self):

        # self.ws['CCSinvokeCdfCallbacks'](f"{self.cv} ?callInitProc t ?useInstCDF t")
        self.ws['CCSinvokeCdfCallbacks'](self.cv, debug=True, callInitProc=True,useInstCDF=True)
        # self.ws['CCSinvokeCdfCallbacks'](self.cv, addFormFields=True)
        # self.ws['CCSinvokeCdfCallbacks'](self.cv, debug=False, order=['wt', 'wf']) #'l', 'wt', 
        # self.ws['CCSinvokeCdfCallbacks'](self.cv, debug=True)

        # CDF callbacks use the user applied parameters to calculate the actual parameters
        # Sometimes user applied parameters don't stick
        # let the user know if that happens:
        for _, i in self.instances.items():
            for a_p_name, a_p_value in i.applied_params.items():
                if a_p_value == '' or a_p_value in self.param_vars or a_p_value in self.cdf_ignore:
                    break
                
                calc_val = i.params[a_p_name].value
                app_val = a_p_value

                # convert strings to floats for comparison
                if isinstance(app_val, str):
                    app_val = convert_str_to_num(app_val)
                    calc_val = convert_str_to_num(calc_val)
                
                if isinstance(app_val, str):
                    if calc_val != app_val:
                        if self.verbose:
                            print(f'Error: Calculated Parameter not equal to Applied Parameter for {a_p_name} on {i.name}.')
                            print(f'{i.params[a_p_name].value} != {a_p_value}')
                        return 1
                
                elif not np.isclose(calc_val, app_val):
                    if self.verbose:
                        print(f'Error: Calculated Parameter not equal to Applied Parameter for {a_p_name} on {i.name}.')
                        print(f'{i.params[a_p_name].value} != {a_p_value}')
                    return 1
        
        return 0

    def save(self, do_callbacks=True):
        rv = 0
        if do_callbacks and self.do_cdf_callbacks():
            rv = 1

        self.ws.sch.check(self.cv)
        self.ws.db.save(self.cv)
        return rv

    def close(self):
        self.ws.close()
