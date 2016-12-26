# -*- coding: utf-8 -*-
########################################################################################################################
#
# Copyright (c) 2014, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
#   disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the
#    following disclaimer in the documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
########################################################################################################################


import os
import pkg_resources

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_sw_casc.yaml'))


class serdes_bm_templates__diffamp_sw_casc(Module):
    """Module for library serdes_bm_templates cell diffamp_sw_casc.

    This is the design class for a differential amplfiier with load_pmos
    and gm_sw_casc as the load and gm stage, respectively.
    """

    param_list = ['lch', 'pw', 'pfg', 'nw_list', 'nfg_list', 'nduml', 'ndumr', 'nsep',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, pw, pfg, nw_list, nfg_list, nduml, ndumr, nsep,
                     input_intent, tail_intent, device_intent):
        """Set the design parameters of this DiffAmp cell directly.

        Parameters
        ----------
        lch : float
            channel length, in meters.
        pw : float or int
            transistor width, in meters or number of fins.
        pfg : int
            number of single-sided fingers.
        nw_list : list[float or int]
            4-element list of widths, in [wt, wsw, win, wcas] format.
        nfg_list : list[int]
            4-element list of single-sided number of fingers, in
            [fg_t, fg_sw, fg_in, fg_cas] format.
        nduml : int
            number of additional left dummies.
        ndumr : int
            number of additional right dummies.
        nsep : int
            number of separator fingers.
        input_intent : str
            input transistor device intent.
        tail_intent : str
            tail transistor device intent.
        device_intent : str
            default device intent.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        # compute number of dummies
        nfg_max = max(nfg_list)
        fg_max = max(nfg_max, pfg)
        pnduml = nduml + fg_max - pfg
        pndumr = ndumr + fg_max - pfg
        nnduml = nduml + fg_max - nfg_max
        nndumr = ndumr + fg_max - nfg_max

        load_params = dict(
            lch=lch,
            w=pw,
            fg=pfg,
            nduml=pnduml,
            ndumr=pndumr,
            nsep=nsep,
            device_intent=device_intent,
        )

        gm_params = dict(
            lch=lch,
            w_list=nw_list,
            fg_list=nfg_list,
            nduml=nnduml,
            ndumr=nndumr,
            nsep=nsep,
            input_intent=input_intent,
            tail_intent=tail_intent,
            device_intent=device_intent,
        )

        # simply pass corresponding parameters to GM and LOAD.
        self.instances['XGM'].design_specs(**gm_params)
        self.instances['XLOAD'].design_specs(**load_params)

    def get_layout_params(self, **kwargs):
        """Returns a dictionary with layout parameters.

        This method computes the layout parameters used to generate implementation's
        layout.  Subclasses should override this method if you need to run post-extraction
        layout.

        Parameters
        ----------
        kwargs :
            any extra parameters you need to generate the layout parameters dictionary.
            Usually you specify layout-specific parameters here, like metal layers of
            input/output, customizable wire sizes, and so on.

        Returns
        -------
        params : dict[str, any]
            the layout parameters dictionary.
        """
        default_layout_params = dict(
            ptap_w=0.52e-6,
            ntap_w=0.52e-6,
            track_width=0.3e-6,
            track_space=0.4e-6,
            gds_space=0,
            diff_space=0,
            ng_tracks=[1, 1, 1, 2, 1],
            nds_tracks=[1, 1, 1, 1, 1],
            pg_tracks=1,
            pds_tracks=2,
            vm_layer='M3',
            hm_layer='M4',
            )

        default_layout_params.update(kwargs)

        ti = self.parameters['tail_intent']
        di = self.parameters['device_intent']
        ii = self.parameters['input_intent']
        nw_list = list(self.parameters['nw_list'])
        fg_list = list(self.parameters['nfg_list'])
        # set enable switch width/finger to be 0
        nw_list.insert(1, 0)
        fg_list.insert(1, 0)
        fg_list.append(self.parameters['pfg'])
        layout_params = dict(
            lch=self.parameters['lch'],
            nw_list=nw_list,
            nth_list=[ti, di, di, ii, di],
            pw=self.parameters['pw'],
            pth=di,
            fg_list=fg_list,
            nduml=self.parameters['nduml'] + 1,
            ndumr=self.parameters['ndumr'] + 1,
            nsep=self.parameters['nsep'],
            nstage=1,
            rename_dict=self.get_layout_pin_mapping(),
            )

        layout_params.update(default_layout_params)
        return layout_params

    def get_layout_pin_mapping(self):
        """Returns the layout pin mapping dictionary.

        This method returns a dictionary used to rename the layout pins, in case they are different
        than the schematic pins.

        Returns
        -------
        pin_mapping : dict[str, str]
            a dictionary from layout pin names to schematic pin names.
        """
        return dict(
            midp='',
            midn='',
            tail='',
            foot='',
            sw='bias_switch',
        )
