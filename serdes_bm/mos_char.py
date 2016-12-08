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

import numpy as np

from bag.tech.mos import MosCharacterization
from abs_templates_ec.mos_char import Transistor


class AnalogMosCharacterization(MosCharacterization):
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
        MosCharacterization.__init__(self, prj, root_dir, impl_lib,
                                     impl_cell, layout_params)

    def create_schematic_design(self, mos_type, l, w, intent, fg, fg_dum=4):
        """Create a new DesignModule with the given transistor parameters.

        Parameters
        ----------
        mos_type : str
            the transistor type.  Either 'pch' or 'nch'.
        w : float or int
            the transistor width in meters, or number of fins.
        l : float
            the channel length, in meters.
        intent : str
            the design intent of the transistor.
        fg : int
            the number of fingers.
        fg_dum : int
            number of dummy fingers per side.

        Returns
        -------
        dsn : bag.design.Module
            the DesignModule with the given transistor parameters.
        """
        params = dict(
            mos_type=mos_type,
            lch=l,
            w=w,
            fg=fg,
            threshold=intent,
            fg_dum=fg_dum,
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

    def setup_testbench(self, dut_lib, dut_cell, impl_lib, env_list, freq_list, sweep_params, extracted):
        """Create and setup the characterization testbench.

        the testbench should have complex-valued outputs named 'y11', 'y12', 'y13', and so on.

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
        freq_list : list[float]
            a list of Y parameter characterization frequencies.
        sweep_params: dict[str, any]
            the bias voltage sweep parameters.  The keys are 'vgs', 'vds', and 'vbs',
            and the values are (<start>, <stop>, <num_points>).
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
            vgs_dc=(start + stop) / 2.0,
            vgs_start=start,
            vgs_stop=stop,
            # ADEXL adds one extra point.
            vgs_num=num - 1,
        )

        tb = self.prj.create_testbench(self.tb_lib, self.tb_cell, dut_lib, dut_cell, impl_lib)
        for key, val in tb_params.iteritems():
            tb.set_parameter(key, val)

        start, stop, num = sweep_params['vds']
        vds_list = np.linspace(start, stop, num, endpoint=True)
        start, stop, num = sweep_params['vbs']
        vbs_list = np.linspace(start, stop, num, endpoint=True)

        tb.set_sweep_parameter('vds_dc', values=vds_list)
        tb.set_sweep_parameter('vbs_dc', values=vbs_list)
        tb.set_sweep_parameter('char_freq', values=freq_list)
        tb.set_simulation_environments(env_list)

        for name in self.output_names:
            if name != 'ids':
                tb.add_output(name, """getData("%s" ?result 'sp)""" % name)

        tb.add_output('ids', """getData("/VDS/MINUS" ?result 'dc)""")

        if extracted:
            tb.set_simulation_view(impl_lib, dut_cell, 'calibre')

        tb.update_testbench()
        return tb
