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

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'mos_char.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__mos_char(Module):
    """Module for library serdes_bm_templates cell mos_char.

    Fill in high level description here.
    """

    param_list = ['mos_type', 'w', 'lch', 'fg', 'fg_dum', 'threshold', 'draw_other']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self, mos_type=None, lch=None, w=None, fg=None, fg_dum=None, threshold=None,
               draw_other=False):
        """Create a new transistor schematic for characterization.

        Parameters
        ----------
        mos_type : str
            transistor type.  Either 'pch' or 'nch'.
        lch : float
            the channel length, in meters.
        w : float or int
            the transistor width, in meters/number of fins.
        fg : int
            number of fingers.
        fg_dum : int
            number of dummies on each side.
        threshold : str
            the threshold type.
        draw_other : bool
            True to draw the other type transistor.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        if fg % 2 != 0:
            raise ValueError('number of fingers must be even.')
        if fg_dum % 2 != 0 or fg_dum <= 0:
            raise ValueError('dummy fingers must be positive and even.')

        if draw_other:
            other_fg = fg + 2 * fg_dum
        else:
            other_fg = 0
        dum_term_list = [{}, {'D': 's', 'G': 'b', 'S': 'b'}, {'D': 'b', 'G': 'b', 'S': 'b'}]
        if mos_type == 'nch':
            self.array_instance('XN', ['XN0', 'XN1', 'XN2'], dum_term_list)
            main = 'XN'
            other = 'XP'
        else:
            self.array_instance('XP', ['XP0', 'XP1', 'XP2'], dum_term_list)
            main = 'XP'
            other = 'XN'

        self.reconnect_instance_terminal(other, 'D', 'b')
        self.reconnect_instance_terminal(other, 'G', 'b')
        self.reconnect_instance_terminal(other, 'S', 'b')
        self.instances[other].design(w=w, l=lch, nf=other_fg, intent=threshold)
        self.instances[main][0].design(w=w, l=lch, nf=fg, intent=threshold)

        # take care of technology where no dummys exist.
        tech_params = self.prj.tech_info.tech_params
        if tech_params['layout']['analog_base'].get('dummy_exist', True):
            self.instances[main][1].design(w=w, l=lch, nf=2, intent=threshold)
            self.instances[main][2].design(w=w, l=lch, nf=2 * fg_dum - 2,
                                           intent=threshold)
        else:
            self.instances[main][1].design(w=w, l=lch, nf=0, intent=threshold)
            self.instances[main][1].design(w=w, l=lch, nf=0, intent=threshold)

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
        layout_params = dict(
            mos_type=self.parameters['mos_type'],
            lch=self.parameters['lch'],
            w=self.parameters['w'],
            fg=self.parameters['fg'],
            fg_dum=self.parameters['fg_dum'],
            threshold=self.parameters['threshold'],
            draw_other=self.parameters['draw_other'],
        )

        layout_params.update(kwargs)
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
        return {}
