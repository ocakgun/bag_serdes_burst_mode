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

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'gm.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__gm(Module):
    """Module for library serdes_bm_templates cell gm.

    Fill in high level description here.
    """

    param_list = ['lch', 'w_dict', 'th_dict', 'fg_dict', 'fg_tot', 'flip_sd']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, w_dict, th_dict, fg_dict, fg_tot=0, flip_sd=False, **kwargs):
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
            this parameter is optional.  If positive, we will calculate the number of dummy transistor
            and add that in schematic.
        flip_sd : bool
            True to flip source/drain connections.  Defaults to False.
        **kwargs
            optional parameters.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        for name, d_ports, s_ports in (('in', ('outn', 'outp'), ('tail', 'tail')),
                                       ('tail', ('VSS', 'VSS'), ('tail', 'tail'))):
            w = w_dict[name]
            fg = fg_dict[name]
            intent = th_dict[name]
            name_upper = name.upper()
            self.instances['X%sP' % name_upper].design(w=w, l=lch, nf=fg, intent=intent)
            self.instances['X%sN' % name_upper].design(w=w, l=lch, nf=fg, intent=intent)
            dum_tran_name = 'X%sD' % name_upper

            dum_ports = d_ports if flip_sd else s_ports
            fg_extra = max(fg_tot - fg * 2 - 4, 0)
            if dum_ports[0] != dum_ports[1]:
                if fg_extra > 0:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(3)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': dum_ports[1]}, {'D': 'VSS'}]
                    self.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                    self.instances[dum_tran_name][2].design(w=w, l=lch, nf=fg_extra, intent=intent)
                else:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(2)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': dum_ports[1]}]
                    self.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                self.instances[dum_tran_name][0].design(w=w, l=lch, nf=2, intent=intent)
                self.instances[dum_tran_name][1].design(w=w, l=lch, nf=2, intent=intent)
            else:
                if fg_extra > 0:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(2)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': 'VSS'}]
                    self.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                    self.instances[dum_tran_name][0].design(w=w, l=lch, nf=4, intent=intent)
                    self.instances[dum_tran_name][1].design(w=w, l=lch, nf=fg_extra, intent=intent)
                else:
                    self.reconnect_instance_terminal(dum_tran_name, 'D', dum_ports[0])
                    self.instances[dum_tran_name].design(w=w, l=lch, nf=4, intent=intent)

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
