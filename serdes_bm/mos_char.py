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

"""This module defines classes for analog transistor characterization."""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# noinspection PyUnresolvedReferences,PyCompatibility
from builtins import *

import numpy as np

from bag.tech.core import CircuitCharacterization
from abs_templates_ec.mos_char import Transistor


class AnalogMosCharacterization(CircuitCharacterization):
    """A class that provides analog transistor characterization routines.

    Parameters
    ----------
    prj : bag.BagProject
        the BagProject instance.
    impl_lib : str
        the library to store the generated testbenches/schematics/layout.
    impl_cell : str
        the generated schematic cell name.
    layout_params : dict[str, any]
        dictionary of layout specific parameters.
    """
    sch_lib = 'serdes_bm_templates'
    sch_cell = 'mos_char'
    tb_lib = 'serdes_bm_testbenches'
    tb_cell = 'mos_char_tb_sp'

    def __init__(self, prj, root_dir, impl_lib, impl_cell, layout_params):
        output_list = ['y11', 'y12', 'y13',
                       'y21', 'y22', 'y23',
                       'y31', 'y32', 'y33',
                       'ids']
        CircuitCharacterization.__init__(self, prj, root_dir, output_list, impl_lib,
                                         impl_cell, layout_params, rtol=1e-5, atol=1e-6)

    def create_schematic_design(self, constants, attrs, **kwargs):
        """Create a new DesignModule with the given parameters.

        Parameters
        ----------
        constants : dict[str, any]
            simulation constants dictionary.
        attrs : dict[str, any]
            attributes dictionary.
        kwargs : dict[str, any]
            additional schematic parameters.

        Returns
        -------
        dsn : bag.design.Module
            the DesignModule with the given transistor parameters.
        """
        params = dict(
            mos_type=constants['mos_type'],
            lch=attrs['l'],
            w=attrs['w'],
            fg=constants['fg'],
            threshold=attrs['intent'],
            fg_dum=constants['fg_dum'],
        )

        dsn = self.prj.create_design_module(self.sch_lib, self.sch_cell)
        dsn.design(**params)
        return dsn

    def create_layout(self, temp_db, lib_name, cell_name, layout_params,
                      debug=False):
        """Create layout with the given parameters.

        Parameters
        ----------
        temp_db : bag.layout.template.TemplateDB
            the TemplateDB instance used to create templates.
        lib_name : str
            library to save the layout.
        cell_name : str
            layout cell name.
        layout_params : dict[str, any]
            the layout parameters dictionary.
        debug : bool
            True to print debug messages.
        """
        template = temp_db.new_template(params=layout_params, temp_cls=Transistor, debug=debug)
        temp_db.instantiate_layout(self.prj, template, cell_name, debug=debug)

    def setup_testbench(self, dut_lib, dut_cell, impl_lib, env_list, constants, sweep_params, extracted):
        """Create and setup the characterization testbench.

        Parameters
        ----------
        dut_lib : str
            the device-under-test library name.
        dut_cell : str
            the device-under-test cell name.
        impl_lib : str
            library to put the created testbench in.
        env_list : list[str]
            a list of simulation environments to characterize.
        constants : dict[str, any]
            simulation constants.
        sweep_params : dict[str, any]
            the sweep parameters dictionary, the values are (<start>, <stop>, <num_points>).
        extracted : bool
            True to run extracted simulation.

        Returns
        -------
        tb : bag.core.Testbench
            the resulting testbench object.
        """

        start, stop, num = sweep_params['vgs']
        tb_params = dict(
            cblk=1e-6,
            lblk=1e-6,
            rp=50,
            vb_dc=0.0,
            vgs=(start + stop) / 2.0,
            vgs_start=start,
            vgs_stop=stop,
            # ADEXL adds one extra point.
            vgs_num=num - 1,
            char_freq=constants['char_freq'],
        )

        tb = self.prj.create_testbench(self.tb_lib, self.tb_cell, dut_lib, dut_cell, impl_lib)
        for key, val in tb_params.items():
            tb.set_parameter(key, val)

        start, stop, num = sweep_params['vds']
        vds_list = np.linspace(start, stop, num, endpoint=True)
        start, stop, num = sweep_params['vbs']
        vbs_list = np.linspace(start, stop, num, endpoint=True)

        tb.set_sweep_parameter('vds', values=vds_list)
        tb.set_sweep_parameter('vbs', values=vbs_list)
        tb.set_simulation_environments(env_list)

        for name in self.output_list:
            if name != 'ids':
                tb.add_output(name, """getData("%s" ?result 'sp)""" % name)

        tb.add_output('ids', """getData("/VDS/MINUS" ?result 'dc)""")

        if extracted:
            tb.set_simulation_view(impl_lib, dut_cell, 'calibre')

        tb.update_testbench()
        return tb

    def get_sim_file_name(self, constants):
        """Returns the simulation file name with the given constants.

        Parameters
        ----------
        constants : dict[str, any]
            the constants dictionary.

        Returns
        -------
        fname : str
            the simulation file name.
        """
        return '%s.hdf5' % constants['mos_type']
