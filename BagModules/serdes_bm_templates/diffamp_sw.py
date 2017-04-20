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
from typing import Union, Dict

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_sw.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__diffamp_sw(Module):
    """Module for library serdes_bm_templates cell diffamp_sw.

    This is the design class for a differential amplfiier with load_pmos
    and gm_sw as the load and gm stage, respectively.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'fg_dict', 'fg_tot']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, w_dict, th_dict, fg_dict, fg_tot=0, **kwargs):
        # type: (float, Dict[str, Union[float, int]], Dict[str, str], Dict[str, int], int) -> None
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
        fg_dict : Dict[str, int]
            dictionary from transistor type to single-sided number of fingers.
            Expect keys: 'load', 'casc', 'in', 'sw', 'tail'.
        fg_tot : int
            total number of fingers.
            this parameter is optional.  If positive, we will calculate the number of dummy transistor
            and add that in schematic.
        **kwargs
            optional parameters.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        load_w = {'load': w_dict['load']}
        load_th = {'load': th_dict['load']}
        load_fg = {'load': fg_dict['load']}
        self.instances['XLOAD'].design_specs(lch, load_w, load_th, load_fg)

        key_list = ['in', 'sw', 'tail']
        gm_w = {key: w_dict[key] for key in key_list}
        gm_th = {key: th_dict[key] for key in key_list}
        gm_fg = {key: fg_dict[key] for key in key_list}
        self.instances['XGM'].design_specs(lch, gm_w, gm_th, gm_fg)

        if fg_tot > 0:
            # dummy pmos
            w = w_dict['load']
            th = th_dict['load']
            fg = fg_tot - (fg_dict['load'] * 2 + 4)
            self.instances['XDP'].design(w=w, l=lch, nf=fg, intent=th)
            # dummy nmos
            self.array_instance('XDN', ['XDN%d' % idx for idx in range(len(key_list))])
            for idx, key in enumerate(key_list):
                w = w_dict[key]
                th = th_dict[key]
                fg = fg_tot - (fg_dict[key] * 2 + 4)
                self.instances['XDN'][idx].design(w=w, l=lch, nf=fg, intent=th)
        else:
            self.delete_instance('XDP')
            self.delete_instance('XDN')

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
