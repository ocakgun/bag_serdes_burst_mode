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
from .base import design_gm

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'gm_sw_casc.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__gm_sw_casc(Module):
    """Module for library serdes_bm_templates cell gm_sw_casc.

    This is the design class for a differential GM stage with cascode transistor
    and tail switch.  It is meant to be used in a dynamic latch.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'fg_dict', 'fg_tot', 'flip_sd', 'decap']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, w_dict, th_dict, fg_dict, fg_tot, flip_sd=False, decap=False, **kwargs):
        # type: (float, Dict[str, Union[float, int]], Dict[str, str], Dict[str, int], int, bool) -> None
        """Set the design parameters of this Gm cell directly.

        Parameters
        ----------
        lch : float
            channel length, in meters.
        w_dict : Dict[str, Union[float, int]]
            dictionary from transistor type to transistor width.
            Expect keys: 'casc', 'in', 'sw', 'tail'.
        th_dict : Dict[str, str]
            dictionary from transistor type to transistor threshold flavor.
            Expect keys: 'casc', 'in', 'sw', 'tail'.
        fg_dict : Dict[str, int]
            dictionary from transistor type to single-sided number of fingers.
            Expect keys: 'casc', 'in', 'sw', 'tail'.
        fg_tot : int
            total number of fingers.
        flip_sd : bool
            True to flip source/drain connections.  Defaults to False.
        decap : bool
            True to draw tail decap.  Defaults to False.
        **kwargs
            optional parameters.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        if fg_dict.get('casc', 0) == 0:
            # remove cascode, change to to gm_sw
            self.delete_instance('XCASCP')
            self.delete_instance('XCASCN')
            self.delete_instance('XCASCD')
            self.reconnect_instance_terminal('XINP', 'D', 'outn')
            self.reconnect_instance_terminal('XINN', 'D', 'outp')

            port_list = [('in', ('outn', 'outp'), ('tail', 'tail')),
                         ('sw', ('VDD', 'VDD'), ('tail', 'tail')),
                         ('tail', ('VSS', 'VSS'), ('tail', 'tail'))]
        else:
            port_list = [('casc', ('outn', 'outp'), ('midn', 'midp')),
                         ('in', ('tail', 'tail'), ('midn', 'midp')),
                         ('sw', ('tail', 'tail'), ('VDD', 'VDD')),
                         ('tail', ('tail', 'tail'), ('VSS', 'VSS'))]
        design_gm(self, port_list, lch, w_dict, th_dict, fg_dict, fg_tot=fg_tot, flip_sd=flip_sd, decap=decap)

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
