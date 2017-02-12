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

from bag.layout.template import MicroTemplate

from abs_templates_ec.serdes import SerdesRXBase


class RXHalfTop(SerdesRXBase):
    """A chain of dynamic latches.

    Parameters
    ----------
    grid : :class:`bag.layout.routing.RoutingGrid`
            the :class:`~bag.layout.routing.RoutingGrid` instance.
    lib_name : str
        the layout library name.
    params : dict
        the parameter values.  Must have the following entries:
    used_names : set[str]
        a set of already used cell names.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        SerdesRXBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        self._draw_layout_helper(**self.params)

    def _draw_layout_helper(self, lch, ptap_w, ntap_w, w_dict, th_dict,
                            analatch_params, integ_params, summer_params,
                            fg_stage, nduml, ndumr, global_gnd_layer, global_gnd_name,
                            show_pins, diff_space, cur_track_width, **kwargs):
        # get width of each block
        fg_amp = self.get_diffamp_info(**analatch_params)
        fg_integ, _, _ = self.get_summer_info(**integ_params)
        fg_summer, _, _ = self.get_summer_info(**summer_params)

        fg_tot = fg_amp + fg_integ + fg_summer + 2 * fg_stage + nduml + ndumr

        # figure out number of tracks
        kwargs['pg_tracks'] = [1]
        kwargs['pds_tracks'] = [2 + diff_space]
        ng_tracks = []
        nds_tracks = []

        # check if butterfly switches are used
        has_but = False
        gm_fg_list = integ_params['gm_fg_list']
        for fdict in gm_fg_list:
            if fdict.get('but', 0) > 0:
                has_but = True
                break

        # compute nmos gate/drain/source number of tracks
        for row_name in ['tail', 'w_en', 'sw', 'in', 'casc']:
            if w_dict.get(row_name, -1) > 0:
                if row_name == 'in' or (row_name == 'casc' and has_but):
                    ng_tracks.append(2 + diff_space)
                else:
                    ng_tracks.append(1)
                nds_tracks.append(cur_track_width + kwargs['gds_space'])
        kwargs['ng_tracks'] = ng_tracks
        kwargs['nds_tracks'] = nds_tracks

        # draw rows with width/threshold parameters.
        for key, val in w_dict.items():
            kwargs['w_' + key] = val
        for key, val in th_dict.items():
            kwargs['th_' + key] = val
        del kwargs['rename_dict']
        self.draw_rows(lch, fg_tot, ptap_w, ntap_w, **kwargs)

        # draw blocks
        cur_col = nduml
        fg_amp, analatch_ports = self.draw_diffamp(cur_col, cur_track_width=cur_track_width,
                                                   diff_space=diff_space, **analatch_params)
        cur_col += fg_amp + fg_stage
        fg_integ, integ_ports = self.draw_gm_summer(cur_col, cur_track_width=cur_track_width,
                                                    diff_space=diff_space, **integ_params)
        cur_col += fg_integ + fg_stage
        fg_summer, summer_ports = self.draw_gm_summer(cur_col, cur_track_width=cur_track_width,
                                                      diff_space=diff_space, **summer_params)

        # export supplies
        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()
        for warr in ptap_wire_arrs:
            self.add_pin(self.get_pin_name('VSS'), warr, show=show_pins)
        for warr in ntap_wire_arrs:
            self.add_pin(self.get_pin_name('VDD'), warr, show=show_pins)

        # add global ground
        if global_gnd_layer is not None:
            _, global_gnd_box = next(ptap_wire_arrs[0].wire_iter(self.grid))
            self.add_pin_primitive(global_gnd_name, global_gnd_layer, global_gnd_box)

    @classmethod
    def get_default_param_values(cls):
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : dict[str, any]
            dictionary of default parameter values.
        """
        return dict(
            th_dict={},
            gds_space=1,
            diff_space=1,
            fg_stage=6,
            nduml=4,
            ndumr=4,
            cur_track_width=1,
            show_pins=True,
            rename_dict={},
            guard_ring_nf=0,
            global_gnd_layer=None,
            global_gnd_name='gnd!',
        )

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            analatch_params='Analog latch parameters',
            integ_params='Integrator parameters.',
            summer_params='DFE tap-1 summer parameters.',
            fg_stage='separation between stages.',
            nduml='number of dummy fingers on the left.',
            ndumr='number of dummy fingers on the right.',
            gds_space='number of tracks reserved as space between gate and drain/source tracks.',
            diff_space='number of tracks reserved as space between differential tracks.',
            cur_track_width='width of the current-carrying horizontal track wire in number of tracks.',
            show_pins='True to create pin labels.',
            rename_dict='port renaming dictionary',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            global_gnd_layer='layer of the global ground pin.  None to disable drawing global ground.',
            global_gnd_name='name of global ground pin.',
        )


class RXHalfBottom(SerdesRXBase):
    """A chain of dynamic latches.

    Parameters
    ----------
    grid : :class:`bag.layout.routing.RoutingGrid`
            the :class:`~bag.layout.routing.RoutingGrid` instance.
    lib_name : str
        the layout library name.
    params : dict
        the parameter values.  Must have the following entries:
    used_names : set[str]
        a set of already used cell names.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        SerdesRXBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        self._draw_layout_helper(**self.params)

    def _draw_layout_helper(self, lch, ptap_w, ntap_w, w_dict, th_dict,
                            analatch_params, diglatch_params_list,
                            fg_stage, nduml, ndumr, global_gnd_layer, global_gnd_name,
                            show_pins, diff_space, cur_track_width, **kwargs):

        # get width of each block
        fg_amp = self.get_diffamp_info(**analatch_params)
        fg_dig_list = [self.get_diffamp_info(**pdict) for pdict in diglatch_params_list]

        fg_tot = fg_amp + sum(fg_dig_list) + 2 * fg_stage + nduml + ndumr

        # figure out number of tracks
        kwargs['pg_tracks'] = [1]
        kwargs['pds_tracks'] = [2 + diff_space]
        ng_tracks = []
        nds_tracks = []

        # compute nmos gate/drain/source number of tracks
        for row_name in ['tail', 'w_en', 'sw', 'in', 'casc']:
            if w_dict.get(row_name, -1) > 0:
                if row_name == 'in':
                    ng_tracks.append(2 + diff_space)
                else:
                    ng_tracks.append(1)
                nds_tracks.append(cur_track_width + kwargs['gds_space'])
        kwargs['ng_tracks'] = ng_tracks
        kwargs['nds_tracks'] = nds_tracks

        # draw rows with width/threshold parameters.
        for key, val in w_dict.items():
            kwargs['w_' + key] = val
        for key, val in th_dict.items():
            kwargs['th_' + key] = val
        del kwargs['rename_dict']
        self.draw_rows(lch, fg_tot, ptap_w, ntap_w, **kwargs)

        # draw blocks
        cur_col = nduml
        fg_amp, analatch_ports = self.draw_diffamp(cur_col, cur_track_width=cur_track_width,
                                                   diff_space=diff_space, **analatch_params)
        cur_col += fg_amp + fg_stage
        for diglatch_params in diglatch_params_list:
            fg_amp, diglatch_ports = self.draw_diffamp(cur_col, cur_track_width=cur_track_width,
                                                       diff_space=diff_space, **diglatch_params)
            cur_col += fg_amp + fg_stage

        # export supplies
        ptap_wire_arrs, ntap_wire_arrs = self.fill_dummy()
        for warr in ptap_wire_arrs:
            self.add_pin(self.get_pin_name('VSS'), warr, show=show_pins)
        for warr in ntap_wire_arrs:
            self.add_pin(self.get_pin_name('VDD'), warr, show=show_pins)

        # add global ground
        if global_gnd_layer is not None:
            _, global_gnd_box = next(ptap_wire_arrs[0].wire_iter(self.grid))
            self.add_pin_primitive(global_gnd_name, global_gnd_layer, global_gnd_box)

    @classmethod
    def get_default_param_values(cls):
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : dict[str, any]
            dictionary of default parameter values.
        """
        return dict(
            th_dict={},
            gds_space=1,
            diff_space=1,
            fg_stage=6,
            nduml=4,
            ndumr=4,
            cur_track_width=1,
            show_pins=True,
            rename_dict={},
            guard_ring_nf=0,
            global_gnd_layer=None,
            global_gnd_name='gnd!',
        )

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            analatch_params='Analog latch parameters',
            diglatch_params_list='Digital latch parameters.',
            fg_stage='separation between stages.',
            nduml='number of dummy fingers on the left.',
            ndumr='number of dummy fingers on the right.',
            gds_space='number of tracks reserved as space between gate and drain/source tracks.',
            diff_space='number of tracks reserved as space between differential tracks.',
            cur_track_width='width of the current-carrying horizontal track wire in number of tracks.',
            show_pins='True to create pin labels.',
            rename_dict='port renaming dictionary',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            global_gnd_layer='layer of the global ground pin.  None to disable drawing global ground.',
            global_gnd_name='name of global ground pin.',
        )


class RXHalf(MicroTemplate):
    """A chain of dynamic latches.

    Parameters
    ----------
    grid : :class:`bag.layout.routing.RoutingGrid`
            the :class:`~bag.layout.routing.RoutingGrid` instance.
    lib_name : str
        the layout library name.
    params : dict
        the parameter values.  Must have the following entries:
    used_names : set[str]
        a set of already used cell names.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        MicroTemplate.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        analatch_params_list = self.params['analatch_params_list']
        integ_params = self.params['integ_params']
        summer_params = self.params['summer_params']

        bot_params = {key: self.params[key] for key in RXHalfBottom.get_params_info().keys()
                      if key in self.params}
        bot_params['analatch_params'] = analatch_params_list[0]
        bot_master = self.new_template(params=bot_params, temp_cls=RXHalfBottom)
        bot_inst = self.add_instance(bot_master)

        top_params = {key: self.params[key] for key in RXHalfTop.get_params_info().keys()
                      if key in self.params}

        top_params['analatch_params'] = analatch_params_list[1]
        top_params['integ_params'] = integ_params
        top_params['summer_params'] = summer_params
        top_master = self.new_template(params=top_params, temp_cls=RXHalfTop)
        top_inst = self.add_instance(top_master, orient='MX')
        top_inst.move_by(dy=bot_inst.array_box.top - top_inst.array_box.bottom)

    @classmethod
    def get_default_param_values(cls):
        """Returns a dictionary containing default parameter values.

        Override this method to define default parameter values.  As good practice,
        you should avoid defining default values for technology-dependent parameters
        (such as channel length, transistor width, etc.), but only define default
        values for technology-independent parameters (such as number of tracks).

        Returns
        -------
        default_params : dict[str, any]
            dictionary of default parameter values.
        """
        return dict(
            th_dict={},
            gds_space=1,
            diff_space=1,
            fg_stage=6,
            nduml=4,
            ndumr=4,
            cur_track_width=1,
            show_pins=True,
            rename_dict={},
            guard_ring_nf=0,
            global_gnd_layer=None,
            global_gnd_name='gnd!',
        )

    @classmethod
    def get_params_info(cls):
        """Returns a dictionary containing parameter descriptions.

        Override this method to return a dictionary from parameter names to descriptions.

        Returns
        -------
        param_info : dict[str, str]
            dictionary from parameter name to description.
        """
        return dict(
            lch='channel length, in meters.',
            ptap_w='NMOS substrate width, in meters/number of fins.',
            ntap_w='PMOS substrate width, in meters/number of fins.',
            w_dict='NMOS/PMOS width dictionary.',
            th_dict='NMOS/PMOS threshold flavor dictionary.',
            analatch_params_list='Analog latch parameters',
            integ_params='Integrator parameters.',
            summer_params='DFE tap-1 summer parameters.',
            diglatch_params_list='Digital latch parameters.',
            fg_stage='separation between stages.',
            nduml='number of dummy fingers on the left.',
            ndumr='number of dummy fingers on the right.',
            gds_space='number of tracks reserved as space between gate and drain/source tracks.',
            diff_space='number of tracks reserved as space between differential tracks.',
            cur_track_width='width of the current-carrying horizontal track wire in number of tracks.',
            show_pins='True to create pin labels.',
            rename_dict='port renaming dictionary',
            guard_ring_nf='Width of the guard ring, in number of fingers.  0 to disable guard ring.',
            global_gnd_layer='layer of the global ground pin.  None to disable drawing global ground.',
            global_gnd_name='name of global ground pin.',
        )
