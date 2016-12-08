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


yaml_file = pkg_resources.resource_filename(__name__, os.path.join('netlist_info', 'mos_char.yaml'))


class serdes_bm_templates__mos_char(Module):
    """Module for library serdes_bm_templates cell mos_char.

    Fill in high level description here.
    """

    def __init__(self, bag_config, parent=None, prj=None, **kwargs):
        Module.__init__(self, bag_config, yaml_file, parent=parent, prj=prj, **kwargs)
        self.parameters['mos_type'] = None
        self.parameters['w'] = None
        self.parameters['lch'] = None
        self.parameters['fg'] = None
        self.parameters['fg_dum'] = None
        self.parameters['threshold'] = None

    def design(self, mos_type=None, lch=None, w=None, fg=None, fg_dum=None, threshold=None):
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
        """
        if fg % 2 != 0:
            raise ValueError('number of fingers must be even.')
        if fg_dum % 2 != 0 or fg_dum <= 0:
            raise ValueError('dummy fingers must be positive and even.')

        self.parameters['mos_type'] = mos_type
        self.parameters['w'] = w
        self.parameters['lch'] = lch
        self.parameters['fg'] = fg
        self.parameters['fg_dum'] = fg_dum
        self.parameters['threshold'] = threshold

        # change NMOS to PMOS
        if mos_type == 'pch':
            self.replace_instance_master('X0', 'BAG_prim', 'pmos4_standard')
            self.replace_instance_master('XD1', 'BAG_prim', 'pmos4_standard')
            self.replace_instance_master('XD2', 'BAG_prim', 'pmos4_standard')

        self.instances['X0'].design(w=w, l=lch, nf=fg, intent=threshold)
        self.instances['XD1'].design(w=w, l=lch, nf=2, intent=threshold)
        self.instances['XD2'].design(w=w, l=lch, nf=2 * fg_dum - 2,
                                     intent=threshold)

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
