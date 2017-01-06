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

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'gm_en_sgn.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__gm_en_sgn(Module):
    """Module for library serdes_bm_templates cell gm_en_sgn.

    This is the design class for a differential GM stage with butterfly
    cascode transistors and enable switch.  It is meant to be used in a
    dynamic latch.
    """

    param_list = ['lch', 'win', 'wen', 'wt', 'wsgn', 'nf', 'nduml', 'ndumr',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        """To be overridden by subclasses to design this module.

        This method should fill in values for all parameters in
        self.parameters.  To design instances of this module, you can
        call their design() method or any other ways you coded.

        To modify schematic structure, call:

        rename_pin()
        delete_instance()
        replace_instance_master()
        reconnect_instance_terminal()
        restore_instance()
        array_instance()
        """
        pass

    def design_specs(self, lch, win, wen, wt, wsgn, nf, nduml, ndumr,
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
        nsgn = nf // 2
        self.instances['XSPP'].design(w=wsgn, l=lch, nf=nsgn, intent=device_intent)
        self.instances['XSPN'].design(w=wsgn, l=lch, nf=nsgn, intent=device_intent)
        self.instances['XSNP'].design(w=wsgn, l=lch, nf=nsgn, intent=device_intent)
        self.instances['XSNN'].design(w=wsgn, l=lch, nf=nsgn, intent=device_intent)
        self.instances['XDUMSP'].design(w=wsgn, l=lch, nf=2, intent=device_intent)
        self.instances['XDUMSN'].design(w=wsgn, l=lch, nf=2, intent=device_intent)
        self.instances['XDUMS'].design(w=wsgn, l=lch, nf=ndum, intent=device_intent)
        self.instances['XINP'].design(w=win, l=lch, nf=nf, intent=input_intent)
        self.instances['XINN'].design(w=win, l=lch, nf=nf, intent=input_intent)
        self.instances['XDUMIP'].design(w=win, l=lch, nf=2, intent=input_intent)
        self.instances['XDUMIN'].design(w=win, l=lch, nf=2, intent=input_intent)
        self.instances['XDUMI'].design(w=win, l=lch, nf=ndum, intent=input_intent)
        self.instances['XEN'].design(w=wen, l=lch, nf=2 * nf, intent=device_intent)
        self.instances['XDUME'].design(w=wen, l=lch, nf=4, intent=device_intent)
        self.instances['XDUME2'].design(w=wen, l=lch, nf=ndum, intent=device_intent)
        self.instances['XTAIL'].design(w=wt, l=lch, nf=2 * nf, intent=tail_intent)
        self.instances['XDUMT'].design(w=wt, l=lch, nf=4, intent=tail_intent)
        self.instances['XDUMT2'].design(w=wt, l=lch, nf=ndum, intent=tail_intent)

        # if number of fingers is 2 mod 4, then source/drain of butterfly
        # cascode transistor swap.
        # therefore we need to modify schematic connections
        if (nf % 4) == 2:
            self.reconnect_instance_terminal('XDUMSP', 'D', 'outp')
            self.reconnect_instance_terminal('XDUMSN', 'D', 'outn')
            self.reconnect_instance_terminal('XDUMIP', 'D', 'tail')
            self.reconnect_instance_terminal('XDUMIN', 'D', 'tail')
            self.reconnect_instance_terminal('XDUME', 'D', 'tail')
            self.reconnect_instance_terminal('XDUMT', 'D', 'VSS')

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
