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

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'rxhalf_ffe1_dfe4.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__rxhalf_ffe1_dfe4(Module):
    """Module for library serdes_bm_templates cell rxhalf_ffe1_dfe4.

    Fill in high level description here.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'nac_off', 'integ_params', 'alat_params_list',
                  'intsum_params', 'summer_params', 'dlat_params_list', 'fg_tot']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, w_dict, th_dict, nac_off, integ_params, alat_params_list,
                     intsum_params, summer_params, dlat_params_list, fg_tot, **kwargs):
        """Set the design parameters of this block directly.

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
        nac_off : int
            number of off transistor fingers for dlev AC coupling.
        integ_params : Dict[str, Any]
            frontend integrator finger parameters.
        alat_params_list : List[Dict[str, Any]]
            analog latch finger parameters.
        intsum_params : Dict[str, Any]
            integrator summer parameters.
        summer_params : Dict[str, Any]
            DFE summer parameters.
        dlat_params_list : List[Dict[str, Any]]
            digital latch finger parameters.
        fg_tot : int
            total number of fingers.
        **kwargs
            optional parameters.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        if 'casc' in w_dict:
            w_dlev = w_dict['casc']
            th_dlev = th_dict['casc']
            key_dlev = 'casc'
        else:
            w_dlev = w_dict['in']
            th_dlev = th_dict['in']
            key_dlev = 'in'

        self.instances['XINTAMP'].design_specs(lch, w_dict, th_dict, **integ_params)
        self.instances['XALAT0'].design_specs(lch, w_dict, th_dict, **alat_params_list[0])
        self.instances['XALAT1'].design_specs(lch, w_dict, th_dict, **alat_params_list[1])
        self.instances['XINTSUM'].design_specs(lch, w_dict, th_dict, **intsum_params)
        self.instances['XSUM'].design_specs(lch, w_dict, th_dict, **summer_params)
        self.instances['XDLAT0'].design_specs(lch, w_dict, th_dict, **dlat_params_list[0])
        self.instances['XDLAT1'].design_specs(lch, w_dict, th_dict, **dlat_params_list[1])
        self.instances['XDLAT2'].design_specs(lch, w_dict, th_dict, **dlat_params_list[2])

        self.instances['XDLEVP'].design(w=w_dlev, l=lch, nf=nac_off, intent=th_dlev)
        self.instances['XDLEVN'].design(w=w_dlev, l=lch, nf=nac_off, intent=th_dlev)
        self.instances['XDLEVDUMP'].design(w=w_dlev, l=lch, nf=2, intent=th_dlev)
        self.instances['XDLEVDUMN'].design(w=w_dlev, l=lch, nf=2, intent=th_dlev)

        fg_dum_top = fg_tot - alat_params_list[1]['fg_tot'] - intsum_params['fg_tot'] - summer_params['fg_tot']
        num_dlev = 2 * nac_off + 4
        fg_dum_bot = fg_tot - integ_params['fg_tot'] - alat_params_list[0]['fg_tot']
        for dlat_params in dlat_params_list:
            fg_dum_bot -= dlat_params['fg_tot']

        if fg_dum_top < num_dlev or fg_dum_bot < 0:
            raise ValueError('fg_tot = %d less than minimum required number of fingers.' % fg_tot)

        fg_dum_tot = fg_dum_top + fg_dum_bot
        # design pmos dummies
        load_w = w_dict['load']
        load_th = th_dict['load']
        self.instances['XDP'].design(w=load_w, l=lch, nf=fg_dum_tot, intent=load_th)

        # design nmos dummies
        key_list = [k for k in w_dict.keys() if k != 'load']
        self.array_instance('XDN', ['XDN%d' % idx for idx in range(len(key_list))])
        for inst, key in zip(self.instances['XDN'], key_list):
            w_cur = w_dict[key]
            th_cur = th_dict[key]
            fg_cur = fg_dum_tot - num_dlev if key == key_dlev else fg_dum_tot
            inst.design(w=w_cur, l=lch, nf=fg_cur, intent=th_cur)

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
