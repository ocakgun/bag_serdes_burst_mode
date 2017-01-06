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

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'gm_sw_en.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__gm_sw_en(Module):
    """Module for library serdes_bm_templates cell gm_sw_en.

    This is the design class for a differential GM stage with tail and
    enable switch.  It is meant to be used in a dynamic latch.
    """

    param_list = ['lch', 'win', 'wsw', 'wen', 'wt', 'nf', 'nduml', 'ndumr',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, win, wsw, wen, wt, nf, nduml, ndumr,
                     input_intent, tail_intent, device_intent, **kwargs):
        """Set the design parameters of this Gm cell directly.

        nduml and ndumr are the number of additional left and right dummy fingers.

        number of fingers (nf) should be even.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        ndum = nduml + ndumr
        self.instances['XINP'].design(w=win, l=lch, nf=nf, intent=input_intent)
        self.instances['XINN'].design(w=win, l=lch, nf=nf, intent=input_intent)
        self.instances['XDUMI'].design(w=win, l=lch, nf=4, intent=input_intent)
        self.instances['XDUMI2'].design(w=win, l=lch, nf=ndum, intent=input_intent)
        self.instances['XSW'].design(w=wsw, l=lch, nf=2 * nf, intent=device_intent)
        self.instances['XDUMW'].design(w=wsw, l=lch, nf=4, intent=device_intent)
        self.instances['XDUMW2'].design(w=wsw, l=lch, nf=ndum, intent=device_intent)
        self.instances['XEN'].design(w=wen, l=lch, nf=2 * nf, intent=device_intent)
        self.instances['XDUME'].design(w=wen, l=lch, nf=4, intent=device_intent)
        self.instances['XDUME2'].design(w=wen, l=lch, nf=ndum, intent=device_intent)
        self.instances['XTAIL'].design(w=wt, l=lch, nf=2 * nf, intent=tail_intent)
        self.instances['XDUMT'].design(w=wt, l=lch, nf=4, intent=tail_intent)
        self.instances['XDUMT2'].design(w=wt, l=lch, nf=ndum, intent=tail_intent)

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
