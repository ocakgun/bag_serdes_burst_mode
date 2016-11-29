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

yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'summer_ffe1_dfe3.yaml'))


class serdes_bm_templates__summer_ffe1_dfe3(Module):
    """Module for library serdes_bm_templates cell summer_ffe1_dfe3.

    This is the design class for an integrating FFE/DFE summer.
    """

    param_list = ['lch', 'wp', 'win_list', 'wen_list', 'wt_list', 'wcas_list',
                  'nf_list', 'nduml_list', 'ndumr_list', 'nfp', 'nfo', 'ndumlp', 'ndumrp',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, lch, wp, win_list, wen_list, wt_list, wcas_list,
                     nf_list, nduml_list, ndumr_list, nfp, nfo, ndumlp, ndumrp,
                     input_intent, tail_intent, device_intent, **kwargs):
        """Set the design parameters of this cell directly.
        """
        local_dict = locals()
        for par in self.param_list:
            if par not in local_dict:
                raise Exception('Parameter %s not defined' % par)
            self.parameters[par] = local_dict[par]

        # design pmos
        self.instances['XLOAD'].design_specs(lch=lch, wp=wp, nf=nfp, nduml=ndumlp, ndumr=0,
                                             device_intent=device_intent)
        self.instances['XOFFSET'].design_specs(lch=lch, wp=wp, nf=nfp, nduml=0, ndumr=ndumrp,
                                               device_intent=device_intent)

        # design nmos
        for idx, name in enumerate(['XFFE', 'XMAIN', 'XDFE1', 'XDFE2', 'XDFE3']):
            win = win_list[idx]
            wen = wen_list[idx]
            wt = wt_list[idx]
            wsgn = wcas = wcas_list[idx]
            nf = nf_list[idx]
            nduml = nduml_list[idx]
            ndumr = ndumr_list[idx]
            local_dict = locals()
            del local_dict['self']
            self.instances[name].design_specs(**local_dict)

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
