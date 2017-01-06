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


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'diffamp_sw_en_casc.yaml'))


# noinspection PyPep8Naming
class serdes_bm_templates__diffamp_sw_en_casc(Module):
    """Module for library serdes_bm_templates cell diffamp_sw_en_casc.

    This is the design class for a differential amplfiier with load_pmos
    and gm_sw_en_casc as the load and gm stage, respectively.
    """

    param_list = ['lch', 'wp', 'win', 'wsw', 'wen', 'wt', 'wcas',
                  'nfp', 'nfn', 'nduml', 'ndumr',
                  'input_intent', 'tail_intent', 'device_intent']

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        for par in self.param_list:
            self.parameters[par] = None

    def design(self):
        pass

    def design_specs(self, **kwargs):
        """Set the design parameters of this DiffAmp cell directly.

        nduml and ndumr are the number of additional left and right dummy fingers.

        number of fingers (nf) should be even.
        """
        for par in self.param_list:
            if par != 'nfp' and par != 'nfn':
                if par not in kwargs:
                    raise Exception('Parameter %s not defined' % par)
                self.parameters[par] = kwargs[par]

        if 'nf' in kwargs:
            # pmos and nmos have same number of fingers
            nfp = nfn = kwargs['nf']
            del kwargs['nf']
            # simply pass corresponding parameters to GM and LOAD.
            self.instances['XGM'].design_specs(nf=nfn, **kwargs)
            self.instances['XLOAD'].design_specs(nf=nfp, **kwargs)
        else:
            # pmos and nmos have different number of fingers
            # calculate new dummy finger parameter to make them match up.
            nfp = kwargs['nfp']
            nfn = kwargs['nfn']
            nextra = abs(nfp - nfn) // 2
            if nfp > nfn:
                ndumlp = kwargs['nduml']
                ndumrp = kwargs['ndumr']
                ndumln = ndumlp + nextra
                ndumrn = ndumrp + nextra
            else:
                ndumln = kwargs['nduml']
                ndumrn = kwargs['ndumr']
                ndumlp = ndumln + nextra
                ndumrp = ndumrn + nextra

            del kwargs['nduml']
            del kwargs['ndumr']
            self.instances['XGM'].design_specs(nf=nfn, nduml=ndumln, ndumr=ndumrn, **kwargs)
            self.instances['XLOAD'].design_specs(nf=nfp, nduml=ndumlp, ndumr=ndumrp, **kwargs)

        self.parameters['nfp'] = nfp
        self.parameters['nfn'] = nfn

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
