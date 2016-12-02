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
from itertools import izip

from bag.design import Module


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'gm_en_casc.yaml'))


class serdes_bm_templates__gm_en_casc(Module):
    """Module for library serdes_bm_templates cell gm_en_casc.

    This is the design class for a differential GM stage with cascode
    transistor and enable switch.  It is meant to be used in a dynamic
    latch.
    """

    param_list = ['lch', 'w_list', 'fg_list', 'nduml', 'ndumr', 'nsep',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, w_list, fg_list, nduml, ndumr, nsep,
                     input_intent, tail_intent, device_intent, **kwargs):
        """Set the design parameters of this Gm cell directly.

        Parameters
        ----------
        lch : float
            channel length, in meters.
        w_list : list[float or int]
            4-element list of widths, in [wt, wen, win, wcas] format.
        fg_list : list[int]
            4-element list of single-sided number of fingers, in
            [fg_t, fg_en, fg_in, fg_cas] format.
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

        wt, wen, win, wcas = w_list
        fgt, fgen, fgin, fgcas = fg_list

        ndum = nduml + ndumr
        self.instances['XCASP'].design(w=wcas, l=lch, nf=fgcas, intent=device_intent)
        self.instances['XCASN'].design(w=wcas, l=lch, nf=fgcas, intent=device_intent)
        self.instances['XDUMCP'].design(w=wcas, l=lch, nf=2, intent=device_intent)
        self.instances['XDUMCN'].design(w=wcas, l=lch, nf=2, intent=device_intent)
        self.instances['XINP'].design(w=win, l=lch, nf=fgin, intent=input_intent)
        self.instances['XINN'].design(w=win, l=lch, nf=fgin, intent=input_intent)
        self.instances['XDUMIP'].design(w=win, l=lch, nf=2, intent=input_intent)
        self.instances['XDUMIN'].design(w=win, l=lch, nf=2, intent=input_intent)
        self.instances['XEN'].design(w=wen, l=lch, nf=2 * fgen, intent=device_intent)
        self.instances['XDUME'].design(w=wen, l=lch, nf=4, intent=device_intent)
        self.instances['XTAIL'].design(w=wt, l=lch, nf=2 * fgt, intent=tail_intent)
        self.instances['XDUMT'].design(w=wt, l=lch, nf=4, intent=tail_intent)

        # figure out number of dummies
        fg_tot = nduml + ndumr + nsep + 2 * max(fg_list) + 2
        fgdum_list = (fg_tot - 2 * fg_cur - 4 for fg_cur in fg_list)
        intent_list = (tail_intent, device_intent, input_intent, device_intent)

        arg_list = [arg for arg in izip(w_list, intent_list, fgdum_list) if arg[2] > 0]

        if not arg_list:
            # delete dummy instance
            self.delete_instance('XD')
        else:
            # create dummies
            self.array_instance('XD', ['XD%d' % idx for idx in xrange(len(arg_list))])
            for inst, arg in izip(self.instances['XD'], arg_list):
                inst.design(w=arg[0], l=lch, nf=arg[2], intent=arg[1])

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