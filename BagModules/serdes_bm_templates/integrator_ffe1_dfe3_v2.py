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

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

import os
import pkg_resources
from typing import Dict, Union, List, Optional

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'integrator_ffe1_dfe3_v2.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__integrator_ffe1_dfe3_v2(Module):
    """Module for library serdes_bm_templates cell integrator_ffe1_dfe3_v2.

    Fill in high level description here.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'load_fg_list', 'gm_fg_list', 'sgn_list', 'fg_tot']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch,  # type: float
                     w_dict,  # type: Dict[str, Union[float, int]]
                     th_dict,  # type: Dict[str, str]
                     load_fg_list,  # type: List[int]
                     gm_fg_list,  # type: List[Dict[str, int]]
                     sgn_list,  # type: List[int]
                     flip_sd_list=None,  # type: Optional[List[bool]]
                     fg_tot=0,  # type: int
                     **kwargs):
        # type: (...) -> None
        """Set the design parameters of this Gm cell directly.

        Parameters
        ----------
        lch : float
            channel length, in meters.
        w_dict : Dict[str, Union[float, int]]
            dictionary from transistor type to transistor width.
            Expect keys: 'load', 'casc', 'in', 'sw', 'tail'.
        th_dict : Dict[str, str]
            dictionary from transistor type to transistor threshold flavor.
            Expect keys: 'load', 'casc', 'in', 'sw', 'tail'.
        load_fg_list : List[int]
            number of load fingers per gm cell.
        gm_fg_list : List[Dict[str, int]]
            list of finger dictionaries for each Gm stage.
        sgn_list : List[int]
            list of feedback signs for each Gm stage.
        flip_sd_list : Optional[List[bool]]
            list of whether to flip source/drain directions.
        fg_tot : int
            total number of fingers.
            this parameter is optional.  If positive, we will calculate the number of dummy transistor
            and add that in schematic.
        **kwargs
            optional parameters.
        """
        if flip_sd_list is None:
            flip_sd_list = [False] * len(gm_fg_list)

        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        # find number of non-zero loads
        num_load = 0
        for fg_load in load_fg_list:
            if fg_load > 0:
                num_load += 1

        # design loads
        load_w = {'load': w_dict['load']}
        load_th = {'load': th_dict['load']}
        self.array_instance('XLOAD', ['XLOAD%d' % idx for idx in range(num_load)])
        load_idx = 0
        fg_dum_load = fg_tot
        for fg_load, flip_sd in zip(load_fg_list, flip_sd_list):
            if fg_load <= 0:
                continue
            self.instances['XLOAD'][load_idx].design_specs(lch, load_w, load_th, {'load': fg_load}, flip_sd=flip_sd)
            fg_dum_load -= (fg_load * 2 + 4)
            load_idx += 1

        # load dummy
        if fg_dum_load > 0:
            self.instances['XDP'].design(w=w_dict['load'], l=lch, nf=fg_dum_load, intent=th_dict['load'])
        else:
            self.delete_instance('XDP')

        key_list = ['casc', 'in', 'sw', 'tail']
        dum_table = {key: fg_tot for key in key_list}
        gm_w = {key: w_dict[key] for key in key_list}
        gm_th = {key: th_dict[key] for key in key_list}
        name_list = ['XAMP', 'XFFE', 'XOFFSET', 'XDFE3', 'XDFE2', 'XDFE1']
        for name, gm_fg_dict, sgn, flip_sd in zip(name_list, gm_fg_list, sgn_list, flip_sd_list):
            for key in key_list:
                if key in dum_table:
                    # keep track of number of dummies
                    cur_fg = gm_fg_dict.get(key, 0)
                    if cur_fg > 0:
                        dum_table[key] -= (gm_fg_dict[key] * 2 + 4)
                        if dum_table[key] <= 0:
                            del dum_table[key]

            self.instances[name].design_specs(lch, gm_w, gm_th, gm_fg_dict, flip_sd=flip_sd)
            if sgn < 0:
                self.reconnect_instance_terminal(name, 'outp', 'outn')
                self.reconnect_instance_terminal(name, 'outn', 'outp')

        # create dummy nmos
        num_dum = len(dum_table)
        if num_dum == 0:
            self.delete_instance('XDN')
        else:
            self.array_instance('XDN', ['XDN%d' % idx for idx in range(num_dum)])
            for idx, (key, nfg) in enumerate(dum_table.items()):
                w = w_dict[key]
                th = th_dict[key]
                self.instances['XDN'][idx].design(w=w, l=lch, nf=nfg, intent=th)

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
        return {}

    def get_layout_pin_mapping(self):
        """Returns the layout pin mapping dictionary.

        This method returns a dictionary used to rename the layout pins, in case they are different
        than the schematic pins.

        Returns
        -------
        pin_mapping : dict[str, str]
            a dictionary from layout pin names to schematic pin names.
        """
        return {}
