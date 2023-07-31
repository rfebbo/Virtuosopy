import virtuosopy as vp
import numpy as np
from skillbridge import Workspace
import numpy as np
import os

class Layout:
    def __init__(self, lib_name, cell_name, ws_name="default", overwrite=False, verbose=True):
        # ws_name = os.getenv('key')

        if ws_name == "default":
            net_id = os.getenv('USER')
            ws = Workspace.open(workspace_id=f'{net_id}_0')

        # raise
        cv = ws.db.open_cell_view_by_type(lib_name, cell_name, "layout",
                                        "maskLayout", "w")
        
        self.lib_name = lib_name
        self.cell_name = cell_name
        self.cv = cv
        self.ws = ws
        self.instances = []

    def create_instance(self, cell_name, lib_name, name, pos, rot='R0', props = None):
        inst = {}

        # cv = ws.db.open_cell_view_by_type(lib_name, cell_name, "schematic",
        #    
        cell_cv = self.ws.db.open_cell_view(lib_name, cell_name, 'layout')
        pos = list(pos)
        inst['name'] = name
        inst['cell'] = cell_name
        inst['props'] = props
        inst['pos'] = np.asarray(pos)
        inst['rot'] = rot
        if props is not None:
            param = vp.convert_props_to_param(props.copy())
            inst['props'] = props
            if rot == 'R180':
                pos = [pos[0] + inst['props']['l'], pos[1] - inst['props']['wf']]
            if 'fet' in cell_name:
                inst['pins'] = self.find_fet_pins(inst)
                
                inst['bnds'] = self.find_bounds(inst)
            inst['inst'] = self.ws.db.create_param_inst(self.cv, cell_cv, name, pos, rot, 1, param)
        else:
            inst['inst'] = self.ws.db.create_param_inst(self.cv, cell_cv, name, pos, rot, 1)

        self.instances.append(inst)
        return inst
        
    def create_via(self, pos, layers, ncol=1, nrow=1, j='c'):
        
        params = [['cutColumns', ncol], ['cutRows', nrow]]
        cut_spacing = 0.11

        if layers in ['VRX_M1', 'VNW', 'M1_M2', 'M2_M3', 'M3_M4']:
            params.append(['cutSpacing', [0.14, 0.14]])
            cut_spacing = 0.14
        elif layers in ['VM4_BA']:
            params.append(['cutSpacing', [0.25, 0.25]])
            cut_spacing = 0.25
        else:
            params.append(['cutSpacing', [0.11, 0.11]])
        
        if layers == 'VPC_M1':
            edge_dist = 0.02
            pad_size = 0.09
        elif layers == 'VRX_M1':
            edge_dist = 0.02
            pad_size = 0.1
        elif layers == 'VNW':
            edge_dist = 0.18
            pad_size = 0.09
        elif layers == 'M1_M2':
            edge_dist = 0.04
            pad_size = .1
        elif layers == 'M2_M3':
            edge_dist = 0.04
            pad_size = .1
        elif layers == 'M3_M4':
            edge_dist = 0.05
            pad_size = .1
        else:
            edge_dist = 0.02
            pad_size = .1

        # params.append(['cutWidth', 0.1])
        # params.append(['cutHeight', 0.1])

        # pos = list(pos)

        via = {}
        via['ncol'] = ncol
        via['nrow'] = nrow
        via['cut_sp'] = cut_spacing

        via['w'] = (pad_size* ncol) + ((ncol-1) * cut_spacing) + (2*edge_dist)
        via['h'] = pad_size * nrow + (nrow-1) * cut_spacing + 2*edge_dist

        if j == 'l':
            pos = [pos[0] + via['w']/2, pos[1]]

        via['pos'] = np.asarray(pos)
        
        via['tl'] = via['pos'] + [-via['w']/2, via['h']/2]
        via['tr'] = via['pos'] + [via['w']/2, via['h']/2]
        via['bl'] = via['pos'] + [-via['w']/2, -via['h']/2]
        via['br'] = via['pos'] + [via['w']/2, -via['h']/2]
        (via['l'],via['t']) = via['tl']
        (via['r'],via['b']) = via['br']

        via['bot'] = via['pos'][1] - via['h']/2

        tf=self.ws.tech.get_tech_file(self.cv)
        viaDef=self.ws.tech.find_via_def_by_name(tf, layers)

        self.ws.db.create_via(self.cv, viaDef, list(via['pos']), 'R0', params)
        return via

    def create_path(self, layer, positions, width, style=None, net_name = None, dir = 'inputOutput'):
        l_positions = []
        for p in positions:
            l_positions.append(list(p))
        if style is None:
            if net_name is None:
                self.ws.db.create_path(self.cv, layer, l_positions, width)
            else:
                path = self.ws.db.create_path(self.cv, layer, l_positions, width)
                pathPin = self.ws.db.create_path(self.cv, [layer, 'pin'], l_positions, width)
                net = self.ws.db.create_net(self.cv, net_name)
                term = self.ws.db.create_term(net, net_name, dir)
                self.ws.db.create_pin(net, pathPin, net_name, term)
                self.ws.db.create_label(self.cv, [layer,'label'], l_positions[0], net_name, 'lowerLeft', 'R0', 'stick', 0.2)
                
                # self.ws.db.create_pin(net, path)
        else:
            self.ws.db.create_path(self.cv, layer, l_positions, width, style)

    def create_rect(self, layer, bbox, net_name = None, dir = 'inputOutput'):
        l_positions = []
        for p in bbox:
            l_positions.append(list(p))
        rect = {}
        rect['inst'] = self.ws.db.create_rect(self.cv, layer, l_positions)
        rect['tl'] = bbox[0]
        rect['br'] = bbox[1]
        (rect['l'],rect['t']) = rect['tl']
        (rect['r'],rect['b']) = rect['br']

        if type(net_name) is str:
            net = self.ws.db.create_net(self.cv, net_name)

            rect['pin_inst'] = self.ws.db.create_rect(self.cv, [layer, 'pin'], l_positions)
            # net = self.ws.db.make_net(self.cv, net_name)

            # self.ws.db.create_pin(net, rect['pin_inst'])#, net_name, term)
            # rect['pin_inst'] = self.ws.db.create_rect(self.cv, [layer, 'label'], l_positions)

            self.ws.db.create_label(self.cv, [layer,'label'], vp.vp_utils.calc_center(l_positions), net_name, 'lowerLeft', 'R0', 'stick', 0.2)
            # dbCreateLabel( 
            # d_cellView 
            # txl_layerPurpose
            # l_point 
            # t_label 
            # t_just 
            # t_orient 
            # t_font 
            # x_height 
            # ) 
            # => d_label / nil

            # net = self.ws.db.find_net_by_name(self.cv, net_name)
#             d_net 
            # t_name 
            # t_direction 
            term = self.ws.db.create_term(net, net_name, dir)

            # term = self.ws.db.get_net_terms(net)
            self.ws.db.create_pin(net, rect['pin_inst'], net_name, term)

        rect['pos'] = np.asarray(l_positions[0]) - (np.asarray(l_positions[0]) - np.asarray(l_positions[1]))/2
        return rect

    def find_fet_pins(self, inst):
        m1_pins = []
        m1_w = 0.09
        m1_w2 = m1_w/2
        pos = inst['pos']
        l = inst['props']['l']
        wt = inst['props']['wt']
        nf = inst['props']['nf']
        wf = inst['props']['wf']

        wt = np.round(wt, 10)
        l = np.round(l, 10)
        pins = {}
        pins['top'] = []
        pins['bot'] = []
        pins['gate'] = []
        pins['leftx'] = pos[0] - 2*0.09
        pins['rightx'] = pos[0] - 0.09 + nf*(l+3*m1_w)

        # tops
        for x in range(nf + 1):
            
            x_pos = pos[0]
            x_pos -= (m1_w+m1_w2)
            x_pos += x*(l+3*m1_w)

            y_pos = pos[1]
            y_pos += 0.005
            pins['top'].append(np.asarray([x_pos, y_pos]))
            # self.create_path('M1', [[x_pos, y_pos], [x_pos, y_pos + 0.09]], 0.09)

        # bottoms
        for x in range(nf + 1):
            x_pos = pos[0]
            x_pos -= (m1_w+m1_w2)
            x_pos += x*(l+3*m1_w)
            # x_pos += pos[0]
            
            y_pos = pos[1]
            y_pos -= 0.005
            y_pos -= wf
            pins['bot'].append(np.asarray([x_pos, y_pos]))
            # self.create_path('M1', [[x_pos, y_pos], [x_pos, y_pos- 0.09]], 0.09)

        # gates
        for x in range(nf):
            x_pos = pos[0]
            x_pos += l/2
            # x_pos -= (m1_w+m1_w2)
            x_pos += x*(l+3*m1_w)
            # x_pos += pos[0]
            
            y_pos = pos[1]
            y_pos += 0.13
            via1 = self.create_via([x_pos, y_pos], "VPC_M1", 2, 1)
            if 'p' in inst['cell']:
                self.create_rect('JZ', [[via1['pos'][0] - l/2, via1['tl'][1]+.01], [via1['pos'][0] + l/2, via1['pos'][1]-0.14/2]])
            else:
                self.create_rect('JX', [[via1['pos'][0] - l/2, via1['tl'][1]+.01], [via1['pos'][0] + l/2, via1['pos'][1]-0.14/2]])

            pins['gate'].append(via1['pos'])
        pins['gate_w'] = via1['w']

        return pins

    def find_bounds(self, inst):
        l = inst['props']['l']
        wt = inst['props']['wt']
        wf = inst['props']['wf']
        nf = inst['props']['nf']

        wt = np.round(wt, 10)
        l = np.round(l, 10)

        bnds = {}
        if 'p' in inst['cell']: #pfet
            bnds['nw'] = {}
            bnds['nw']['t'] = inst['pos'][1] + 0.31
            bnds['nw']['r'] = inst['pos'][0] - 0.09 + nf*(l+3*0.09) + .03 + 0.13
            bnds['nw']['l'] = inst['pos'][0] - 0.34
            bnds['nw']['b'] = inst['pos'][1] - wf - 0.31
            bnds['nw']['tl'] = np.asarray([bnds['nw']['l'], bnds['nw']['t']])
            bnds['nw']['tr'] = np.asarray([bnds['nw']['r'], bnds['nw']['t']])
            bnds['nw']['bl'] = np.asarray([bnds['nw']['l'], bnds['nw']['b']])
            bnds['nw']['br'] = np.asarray([bnds['nw']['r'], bnds['nw']['b']])
            inst['tl'] = bnds['nw']['tl']
            inst['br'] = bnds['nw']['br']
            inst['bl'] = bnds['nw']['bl']
            inst['tr'] = bnds['nw']['tr']
            (inst['l'],inst['t']) = inst['tl']
            (inst['r'],inst['b']) = inst['br']
        else: #nfet
            bnds['jx'] = {}
            bnds['jx']['t'] = inst['pos'][1] + 0.27
            bnds['jx']['r'] = inst['pos'][0] - 0.09 + nf*(l+3*0.09) + .03 + 0.13
            bnds['jx']['l'] = inst['pos'][0] - 0.34
            bnds['jx']['b'] = inst['pos'][1] - wf - 0.27
            bnds['jx']['tl'] = np.asarray([bnds['jx']['l'], bnds['jx']['t']])
            bnds['jx']['tr'] = np.asarray([bnds['jx']['r'], bnds['jx']['t']])
            bnds['jx']['bl'] = np.asarray([bnds['jx']['l'], bnds['jx']['b']])
            bnds['jx']['br'] = np.asarray([bnds['jx']['r'], bnds['jx']['b']])
            inst['tl'] = bnds['jx']['tl']
            inst['br'] = bnds['jx']['br']
            inst['bl'] = bnds['jx']['bl']
            inst['tr'] = bnds['jx']['tr']
            (inst['l'],inst['t']) = inst['tl']
            (inst['r'],inst['b']) = inst['br']
        return bnds
    def clear_cell(self):
        cv = self.ws.db.open_cell_view_by_type(self.lib_name, self.cell_name, "layout",
                                        "", "w")
        self.cv = cv

    def save(self):
        self.ws.hi.redraw()
        self.ws['CCSinvokeCdfCallbacks'](self.cv, debug=True, callInitProc=True,useInstCDF=True)
        self.ws.db.save(self.cv)
