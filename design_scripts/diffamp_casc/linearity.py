# -*- coding: utf-8 -*-

from typing import List, Union, Dict, Tuple, Any, Optional

import numpy as np
import scipy.optimize
import scipy.signal
import scipy.interpolate
import pprint
import yaml

import bag
from bag.core import BagProject, Testbench
from bag.layout import RoutingGrid, TemplateDB
from bag.tech.mos import MosCharDB
from bag.math.dfun import DiffFunction
from bag.data.lti import LTICircuit
from bag.data.dc import DCCircuit
from bag.util.search import BinaryIterator

from abs_templates_ec.serdes.amplifier import DiffAmp


def solve_casc_diff_dc(env_list,  # type: List[str]
                       ndb,  # type: MosCharDB
                       pdb,  # type: MosCharDB
                       lch,  # type: float
                       intent_list,  # type: List[str]
                       w_list,  # type: List[Union[float, int]]
                       fg_list,  # type: List[int]
                       vbias_list,  # type: List[float]
                       vload_list,  # type: List[float]
                       vtail_list,  # type: List[float]
                       vmid_list,  # type: List[float]
                       vdd,  # type: float
                       vincm,  # type: float
                       voutcm,  # type: float
                       vin_max,  # type: float
                       inl_max,  # type: float
                       num_points=20,
                       inorm=1e-6,  # type: float
                       itol=1e-9  # type: float
                       ):
    # type: (...) -> Tuple[np.ndarray, List[np.ndarray], List[float], List[float]]

    intent_tail, intent_in, intent_casc, intent_load = intent_list
    w_tail, w_in, w_casc, w_load = w_list
    fg_tail, fg_in, fg_casc, fg_load = fg_list
    # construct DC circuit
    circuit = DCCircuit(ndb, pdb)
    circuit.add_transistor('tail', 'bias', 'gnd', 'gnd', 'nch', intent_tail, w_tail, lch, fg=2 * fg_tail)
    circuit.add_transistor('midn', 'inp', 'tail', 'gnd', 'nch', intent_in, w_in, lch, fg=fg_in)
    circuit.add_transistor('midp', 'inn', 'tail', 'gnd', 'nch', intent_in, w_in, lch, fg=fg_in)
    circuit.add_transistor('outn', 'vdd', 'midn', 'gnd', 'nch', intent_casc, w_casc, lch, fg=fg_casc)
    circuit.add_transistor('outp', 'vdd', 'midp', 'gnd', 'nch', intent_casc, w_casc, lch, fg=fg_casc)
    circuit.add_transistor('outn', 'load', 'vdd', 'vdd', 'pch', intent_load, w_load, lch, fg=fg_load)
    circuit.add_transistor('outp', 'load', 'vdd', 'vdd', 'pch', intent_load, w_load, lch, fg=fg_load)
    circuit.set_voltage_source('vdd', vdd)

    vin_vec = np.linspace(0, vin_max, num_points, endpoint=True)
    vin_vec_diff = np.linspace(-vin_max, vin_max, 2 * num_points - 1, endpoint=True)  # type: np.ndarray
    vmat_list = []
    inl_list = []
    gain_list = []
    for env, vbias, vload, vt, vm in zip(env_list, vbias_list, vload_list, vtail_list, vmid_list):
        circuit.set_voltage_source('bias', vbias)
        circuit.set_voltage_source('load', vload)
        guess_dict = {'tail': vt, 'midp': vm, 'midn': vm, 'outp': voutcm, 'outn': voutcm}
        vmat = np.empty((2 * num_points - 1, 5))

        for idx, vin_diff in enumerate(vin_vec):
            circuit.set_voltage_source('inp', vincm + vin_diff / 2)
            circuit.set_voltage_source('inn', vincm - vin_diff / 2)

            op_dict = circuit.solve(env, guess_dict, inorm=inorm, itol=itol)
            vts, vmps, vmns = op_dict['tail'], op_dict['midp'], op_dict['midn']
            vops, vons = op_dict['outp'], op_dict['outn']
            vmat[idx + num_points - 1, 0] = vts
            vmat[num_points - 1 - idx, 0] = vts
            vmat[idx + num_points - 1, 1] = vmps
            vmat[num_points - 1 - idx, 1] = vmns
            vmat[idx + num_points - 1, 2] = vmns
            vmat[num_points - 1 - idx, 2] = vmps
            vmat[idx + num_points - 1, 3] = vops
            vmat[num_points - 1 - idx, 3] = vons
            vmat[idx + num_points - 1, 4] = vons
            vmat[num_points - 1 - idx, 4] = vops

        gain, inl = get_inl(vin_vec_diff, vmat[:, 3] - vmat[:, 4])
        if inl > inl_max:
            # we didn't meet linearity spec, abort.
            raise ValueError('inl = %.4g, failed linearity error spec at env = %s' % (inl, env))

        gain_list.append(gain)
        inl_list.append(inl)
        vmat_list.append(vmat)

    return vin_vec_diff, vmat_list, inl_list, gain_list


def solve_casc_gm_dc(env_list,  # type: List[str]
                     db_list,  # type: List[MosCharDB]
                     w_list,  # type: List[Union[float, int]]
                     fg_list,  # type: List[int]
                     vdd,  # type: float
                     vincm,  # type: float
                     voutcm,  # type: float
                     vstar_targ,  # type: float
                     inorm=1e-6,  # type: float
                     itol=1e-9,  # type: float
                     vtol=1e-6  # type: float
                     ):
    # type: (...) -> Tuple[List[Dict[str, float]], List[float], List[float]]
    vtail_list = []
    vmid_list = []
    in_params_list = []

    db_in, db_casc = db_list
    w_in, w_casc = w_list
    fg_in, fg_casc = fg_list
    x0 = np.array([0, voutcm / 2])

    # in_op = (w, -vtail, vmid - vtail, vcm - vtail)
    in_amat = np.array([[0, 0],
                        [-1, 0],
                        [-1, 1],
                        [-1, 0]])
    in_bmat = np.array([w_in, 0, 0, vincm])
    # casc_op = (w, -vmid, vcm - vmid, vdd - vmid)
    casc_amat = np.array([[0, 0],
                          [0, -1],
                          [0, -1],
                          [0, -1]])
    casc_bmat = np.array([w_casc, 0, voutcm, vdd])

    for env in env_list:
        vstar_in = db_in.get_function('vstar', env=env)
        ids_in = db_in.get_function('ids', env=env)
        ids_casc = db_casc.get_function('ids', env=env)

        ids_in = (fg_in / inorm) * ids_in.transform_input(in_amat, in_bmat)
        vstar_diff = vstar_in.transform_input(in_amat, in_bmat) - vstar_targ  # type: DiffFunction
        ids_casc = (fg_casc / inorm) * ids_casc.transform_input(casc_amat, casc_bmat)
        idiff = ids_casc - ids_in  # type: DiffFunction

        def fun1(vin1):
            ans = np.empty(2)
            ans[0] = vstar_diff(vin1)
            ans[1] = idiff(vin1)
            return ans

        result = scipy.optimize.root(fun1, x0, tol=min(vtol, itol / inorm), method='hybr')
        if not result.success:
            raise ValueError('solution failed.')
        vtail, vmid = result.x

        in_params = db_list[0].query(env=env, w=w_in, vbs=-vtail, vds=vmid - vtail, vgs=vincm - vtail)
        vtail_list.append(vtail)
        vmid_list.append(vmid)
        in_params_list.append(in_params)

    return in_params_list, vtail_list, vmid_list


def solve_load_bias(env_list, pdb, w_load, fg_load, vdd, voutcm, ibias_list, vtol=1e-6):
    # type: (List[str], MosCharDB, float, int, float, float, List[float], float) -> List[float]
    # find load bias voltage

    vload_list = []
    for env, ibias in zip(env_list, ibias_list):
        ids_load = pdb.get_function('ids', env=env)

        def fun2(vin2):
            return (-fg_load * ids_load(np.array([w_load, 0, voutcm - vdd, vin2 - vdd])) - ibias) / 1e-6

        vload_list.append(scipy.optimize.brentq(fun2, 0, vdd, xtol=vtol))

    return vload_list


def solve_tail_bias(env, ndb, w_tail, fg_tail, vdd, vtail, ibias, vtol=1e-6):
    # type: (str, MosCharDB, float, int, float, float, float, float) -> float
    # find load bias voltage
    ids_tail = ndb.get_function('ids', env=env)

    def fun2(vin2):
        return (fg_tail * ids_tail(np.array([w_tail, 0, vtail, vin2])) - ibias) / 1e-6

    vbias = scipy.optimize.brentq(fun2, 0, vdd, xtol=vtol)  # type: float

    return vbias


def design_tail(env_list, ndb, fg_in, in_params_list, vtail_list, fg_swp, w_tail, vdd, tau_max):
    fg_opt = None
    ro_opt = 0
    vbias_list_opt = []
    ro_list_opt = None
    for fg_tail in fg_swp:
        tau_worst = 0
        ro_worst = float('inf')
        ro_list = []
        vbias_list = []
        for env, vtail, in_params in zip(env_list, vtail_list, in_params_list):
            ibias = in_params['ids'] * fg_in
            try:
                vbias = solve_tail_bias(env, ndb, w_tail, fg_tail, vdd, vtail, ibias)
            except ValueError:
                tau_worst = None
                break

            vbias_list.append(vbias)
            tail_params = ndb.query(env=env, w=w_tail, vbs=0, vds=vtail, vgs=vbias)
            ro_tail = 1 / (fg_tail * tail_params['gds'])
            gm_in = fg_in * in_params['gm']
            cdd_tail = fg_tail * tail_params['cdd']
            css_gm = fg_in * in_params['css']
            tau = (css_gm + cdd_tail) / (1 / ro_tail + gm_in)
            ro_list.append(ro_tail)
            if tau > tau_worst:
                tau_worst = tau
            if ro_tail < ro_worst:
                ro_worst = ro_tail

        if tau_worst is not None:
            if tau_worst <= tau_max and ro_worst > ro_opt:
                ro_opt = ro_worst
                fg_opt = fg_tail
                vbias_list_opt = vbias_list
                ro_list_opt = ro_list

    if fg_opt is None:
        raise ValueError('No solution for tail current source.')

    return fg_opt, ro_list_opt, vbias_list_opt


def get_inl(xvec, yvec):
    def fit_fun(xval, scale):
        return scale * xval

    in_max = xvec[-1]
    mvec = scipy.optimize.curve_fit(fit_fun, xvec, yvec, p0=1)[0]
    full_scale = mvec[0] * in_max
    inl = (yvec - mvec[0] * xvec) / full_scale
    return mvec[0], np.max(np.abs(inl))


def characterize_casc_amp(env_list, lch, intent_list, fg_list, w_list, db_list, vbias_list, vload_list,
                          vtail_list, vmid_list, vincm, voutcm, vdd, vin_max,
                          cw, rw, fanout, ton, k_settle_targ, inl_max,
                          scale_res=0.1, scale_min=0.25, scale_max=20):
    # compute DC transfer function curve and compute linearity spec
    ndb, pdb = db_list[0], db_list[-1]
    results = solve_casc_diff_dc(env_list, ndb, pdb, lch, intent_list, w_list, fg_list, vbias_list, vload_list,
                                 vtail_list, vmid_list, vdd, vincm, voutcm, vin_max, inl_max, num_points=20)
    vin_vec, vmat_list, inl_list, gain_list = results
    vin_max = vin_vec[-1]
    # compute settling ratio
    fg_tail, fg_in, fg_casc, fg_load = fg_list
    db_tail, db_in, db_casc, db_load = db_list
    w_tail, w_in, w_casc, w_load = w_list
    fzin = 1.0 / (2 * ton)
    wzin = 2 * np.pi * fzin
    tvec = np.linspace(0, ton, 200, endpoint=True)
    scale_list = []
    cin_list = []
    for env, vbias, vload, vtail, vmid, vmat in zip(env_list, vbias_list, vload_list, vtail_list, vmid_list, vmat_list):
        # step 1: get half circuit parameters and compute input capacitance
        in_par = db_in.query(env=env, w=w_in, vbs=-vtail, vds=vmid - vtail, vgs=vincm - vtail)
        casc_par = db_casc.query(env=env, w=w_casc, vbs=-vmid, vds=voutcm - vmid, vgs=vdd - vmid)
        load_par = db_load.query(env=env, w=w_load, vbs=0, vds=voutcm - vdd, vgs=vload - vdd)
        cir = LTICircuit()
        cir.add_transistor(in_par, 'mid', 'in', 'gnd', fg=fg_in)
        cir.add_transistor(casc_par, 'out', 'gnd', 'mid', fg=fg_casc)
        cir.add_transistor(load_par, 'out', 'gnd', 'gnd', fg=fg_load)
        zin = cir.get_impedance('in', fzin)
        cin = (1 / zin).imag / wzin
        cin_list.append(cin)
        # step 3A: construct differential circuit with vinmax.
        vts, vmps, vmns, vops, vons = vmat[-1, :]
        vinp = vincm + vin_max / 2
        vinn = vincm - vin_max / 2
        tail_par = db_tail.query(env=env, w=w_tail, vbs=0, vds=vts, vgs=vbias)
        inp_par = db_in.query(env=env, w=w_in, vbs=-vts, vds=vmns - vts, vgs=vinp - vts)
        inn_par = db_in.query(env=env, w=w_in, vbs=-vts, vds=vmps - vts, vgs=vinn - vts)
        cascp_par = db_casc.query(env=env, w=w_casc, vbs=-vmns, vds=vons - vmns, vgs=vdd - vmns)
        cascn_par = db_casc.query(env=env, w=w_casc, vbs=-vmps, vds=vops - vmps, vgs=vdd - vmps)
        loadp_par = db_load.query(env=env, w=w_load, vbs=0, vds=vons - vdd, vgs=vload - vdd)
        loadn_par = db_load.query(env=env, w=w_load, vbs=0, vds=vops - vdd, vgs=vload - vdd)
        cir = LTICircuit()
        cir.add_transistor(tail_par, 'tail', 'gnd', 'gnd', fg=fg_tail)
        cir.add_transistor(inp_par, 'midn', 'inp', 'tail', fg=fg_in)
        cir.add_transistor(inn_par, 'midp', 'inn', 'tail', fg=fg_in)
        cir.add_transistor(cascp_par, 'dn', 'gnd', 'midn', fg=fg_casc)
        cir.add_transistor(cascn_par, 'dp', 'gnd', 'midp', fg=fg_casc)
        cir.add_transistor(loadp_par, 'dn', 'gnd', 'gnd', fg=fg_load)
        cir.add_transistor(loadn_par, 'dp', 'gnd', 'gnd', fg=fg_load)
        cir.add_vcvs(0.5, 'inp', 'gnd', 'inac', 'gnd')
        cir.add_vcvs(-0.5, 'inn', 'gnd', 'inac', 'gnd')
        # step 3B: compute DC gain
        cir.add_vcvs(1, 'dac', 'gnd', 'dp', 'dn')
        dc_tf = cir.get_transfer_function('inac', 'dac')
        _, gain_vec = dc_tf.freqresp(w=[0.1])
        dc_gain = gain_vec[0].real
        # step 3C add cap loading
        cload = fanout * cin
        cir.add_cap(cload, 'outp', 'gnd')
        cir.add_cap(cload, 'outn', 'gnd')
        cir.add_vcvs(1, 'outac', 'gnd', 'outp', 'outn')
        # step 4: find scale factor to achieve k_settle
        bin_iter = BinaryIterator(scale_min, None, step=scale_res, is_float=True)
        while bin_iter.has_next():
            # add scaled wired parasitics
            cur_scale = bin_iter.get_next()
            cap_cur = cw / 2 / cur_scale
            res_cur = rw * cur_scale
            cir.add_cap(cap_cur, 'dp', 'gnd')
            cir.add_cap(cap_cur, 'dn', 'gnd')
            cir.add_cap(cap_cur, 'outp', 'gnd')
            cir.add_cap(cap_cur, 'outn', 'gnd')
            cir.add_res(res_cur, 'dp', 'outp')
            cir.add_res(res_cur, 'dn', 'outn')
            # get settling factor
            sys = cir.get_state_space('inac', 'outac')
            _, yvec = scipy.signal.step(sys, T=tvec)  # type: Tuple[np.ndarray, np.ndarray]
            k_settle_cur = 1 - abs(yvec[-1] - dc_gain) / abs(dc_gain)
            # print('scale = %.4g, k_settle = %.4g' % (cur_scale, k_settle_cur))
            # update next scale factor
            if k_settle_cur >= k_settle_targ:
                # print('save scale = %.4g' % cur_scale)
                bin_iter.save()
                bin_iter.down()
            else:
                if cur_scale > scale_max:
                    raise ValueError('kset = %.4g, cannot meet settling time spec '
                                     'at scale = %d' % (k_settle_cur, cur_scale))
                bin_iter.up()
            # remove wire parasitics
            cir.add_cap(-cap_cur, 'dp', 'gnd')
            cir.add_cap(-cap_cur, 'dn', 'gnd')
            cir.add_cap(-cap_cur, 'outp', 'gnd')
            cir.add_cap(-cap_cur, 'outn', 'gnd')
            cir.add_res(-res_cur, 'dp', 'outp')
            cir.add_res(-res_cur, 'dn', 'outn')
        scale_list.append(bin_iter.get_last_save())

    return vmat_list, inl_list, gain_list, scale_list, cin_list


def design_diffamp(root_dir, vin_max, inl_targ, gain_min, fanout, ton, k_settle_targ, rw, cw, env_range,
                   vdd, vincm, vincm_min, voutcm, lch, min_fg, fg_in, w_list, th_list):
    tau_tail_max = ton / 20

    vstar_targ_range = np.arange(18, 23) / 20 * vin_max
    fg_casc_range = list(range(6, 13, 2))
    fg_tail_range = list(range(4, 9, 2))
    fg_load_range = list(range(2, 5, 2))

    db_method = 'linear'
    db_tail = MosCharDB(root_dir, 'nch', ['intent', 'l'], env_range, intent=th_list[0], l=lch, method=db_method)
    db_in = MosCharDB(root_dir, 'nch', ['intent', 'l'], env_range, intent=th_list[1], l=lch, method=db_method)
    db_casc = MosCharDB(root_dir, 'nch', ['intent', 'l'], env_range, intent=th_list[2], l=lch, method=db_method)
    db_load = MosCharDB(root_dir, 'pch', ['intent', 'l'], env_range, intent=th_list[3], l=lch, method=db_method)

    db_list = [db_tail, db_in, db_casc, db_load]
    db_gm_list = [db_in, db_casc]
    w_gm_list = w_list[1:3]
    w_load = w_list[3]
    w_tail = w_list[0]

    opt_ibias = None  # type: Optional[float]
    opt_info = dict(lch=lch,
                    w_dict={'tail': w_list[0], 'in': w_list[1], 'casc': w_list[2], 'load': w_list[3]},
                    th_dict={'tail': th_list[0], 'in': th_list[1], 'casc': th_list[2], 'load': th_list[3]},
                    fanout=fanout,
                    cw=cw,
                    rw=rw,
                    env_list=env_range,
                    vdd=vdd,
                    vincm=vincm,
                    voutcm=voutcm,
                    vin_max=vin_max,
                    ton=ton,
                    )

    for vstar_targ in vstar_targ_range:
        for fg_casc in fg_casc_range:
            fg_gm_list = [fg_in, fg_casc]
            try:
                in_params_list, vtail_list, vmid_list = solve_casc_gm_dc(env_range, db_gm_list, w_gm_list, fg_gm_list,
                                                                         vdd, vincm, voutcm, vstar_targ)
            except ValueError as ex:
                print('failed to solve cascode with fg_casc = %d' % fg_casc)
                print(ex)
                continue

            try:
                fg_tail, rtail_list_opt, vbias_list = design_tail(env_range, db_tail, fg_in, in_params_list, vtail_list,
                                                                  fg_tail_range, w_tail, vdd, tau_tail_max)
            except ValueError as ex:
                print('failed to solve tail with fg_casc = %d' % fg_casc)
                print(ex)
                continue

            # noinspection PyUnresolvedReferences
            ibias_list = [fg_in * in_params['ids'][0] for in_params in in_params_list]
            if opt_ibias is not None and max(ibias_list) > opt_ibias:
                # there's no hope for this design point to be better.
                print('worst ibias = %.4g > %.4g' % (max(ibias_list), opt_ibias))
                continue

            for fg_load in fg_load_range:
                try:
                    vload_list = solve_load_bias(env_range, db_load, w_load, fg_load, vdd, voutcm, ibias_list)
                except ValueError:
                    print('failed to solve load with fg_load = %d' % fg_load)
                    continue

                fg_list = [fg_tail, fg_in, fg_casc, fg_load]
                scale_min = min(fg_list) / min_fg
                try:
                    results = characterize_casc_amp(env_range, lch, th_list, fg_list, w_list, db_list, vbias_list,
                                                    vload_list, vtail_list, vmid_list, vincm, voutcm, vdd, vin_max,
                                                    cw, rw, fanout, ton, k_settle_targ, inl_targ, scale_min=scale_min)
                    mresults = characterize_casc_amp(env_range, lch, th_list, fg_list, w_list, db_list, vbias_list,
                                                     vload_list, vtail_list, vmid_list, vincm_min, voutcm, vdd, vin_max,
                                                     cw, rw, fanout, ton, k_settle_targ, inl_targ, scale_min=scale_min)
                except ValueError as ex:
                    print(ex)
                    continue

                vmat_list, inl_list, gain_list, scale_list, cin_list = results
                max_scale = max(scale_list)
                ibias_list = [max_scale * val for val in ibias_list]
                ibias_worst = max(ibias_list)
                gain_worst = min(gain_list)
                print('fg: %s' % ' '.join(['%.4g' % val for val in fg_list]))
                print('vstar_targ = %.4g' % vstar_targ)
                print('vincm = %.4g:' % vincm)
                print('max inl: %.4g' % max(inl_list))
                print('max ibias: %.4g' % max(ibias_list))
                print('gain min: %.4g' % gain_worst)
                print('vincm = %.4g:' % vincm_min)
                print('max inl: %.4g' % max(mresults[1]))
                print('gain min: %.4g' % min(mresults[2]))
                if gain_worst >= gain_min:
                    if opt_ibias is None or ibias_worst < opt_ibias:
                        opt_ibias = ibias_worst
                        opt_info['fg_dict'] = {'tail': fg_list[0], 'in': fg_list[1],
                                               'casc': fg_list[2], 'load': fg_list[3]}
                        opt_info['vbias_list'] = vbias_list
                        opt_info['vload_list'] = vload_list
                        opt_info['vtail_list'] = vtail_list
                        opt_info['vmid_list'] = vmid_list
                        opt_info['inl_list'] = inl_list
                        opt_info['gain_list'] = gain_list
                        opt_info['ibias_list'] = ibias_list
                        opt_info['scale'] = max_scale
                        opt_info['cin_list'] = cin_list

    if opt_ibias is None:
        raise ValueError('No solution found.')

    return opt_info


def generate_diffamp(prj, temp_db, dsn_params, layout_params, run_lvs=False, run_rcx=False):
    # type: (BagProject, TemplateDB, Dict[str, Any], Dict[str, Any], bool, bool) -> None
    lib_name = 'serdes_bm_templates'
    cell_name = 'diffamp_casc'

    params = dict(
        lch=dsn_params['lch'],
        w_dict=dsn_params['w_dict'],
        th_dict=dsn_params['th_dict'],
        fg_dict=dsn_params['fg_dict'],
    )

    layout_params.update(params)

    pprint.pprint(layout_params)
    template = temp_db.new_template(params=layout_params, temp_cls=DiffAmp, debug=False)
    fg_tot = template.num_fingers
    print('total number of fingers: %d' % fg_tot)
    temp_db.instantiate_layout(prj, template, cell_name, debug=True)

    run_lvs = run_lvs or run_rcx

    if run_lvs:
        dsn = prj.create_design_module(lib_name, cell_name)
        dsn.design_specs(fg_tot=fg_tot, **params)
        dsn.implement_design(temp_db.lib_name, top_cell_name=cell_name, erase=True)
        print('run lvs')
        success, log_fname = prj.run_lvs(temp_db.lib_name, cell_name)
        if not success:
            raise ValueError('lvs failed.  Check log file: %s' % log_fname)
        else:
            print('lvs passed')

    if run_rcx:
        print('run rcx')
        success, log_fname = prj.run_rcx(temp_db.lib_name, cell_name)
        if not success:
            raise ValueError('rcx failed.  Check log file: %s' % log_fname)
        else:
            print('rcx passed')


def create_tb_bias(prj, targ_lib, dsn_params):
    # type: (BagProject, str, Dict[str, Any]) -> Testbench
    tb_lib = 'serdes_bm_testbenches'
    tb_cell = 'diffamp_casc_tb_bias'
    cell_name = 'diffamp_casc'

    print('creating testbench %s__%s' % (targ_lib, tb_cell))
    tb = prj.create_testbench(tb_lib, tb_cell, targ_lib, cell_name, targ_lib)

    print('setting testbench parameters')
    tb.set_simulation_environments(dsn_params['env_list'])
    tb.set_parameter('amp_gain', 200)
    tb.set_parameter('vdd', dsn_params['vdd'])
    tb.set_parameter('vcasc', dsn_params['vdd'])
    tb.set_parameter('vindc', dsn_params['vincm'])
    tb.set_parameter('voutdc', dsn_params['voutcm'])
    tb.set_env_parameter('vtail', dsn_params['vbias_list'])

    tb.set_simulation_view(impl_lib, cell_name, 'calibre')
    tb.update_testbench()

    return tb


def create_tb_dc(prj, targ_lib, opt_info):
    # type: (BagProject, str, Dict[str, Any]) -> Testbench
    tb_lib = 'serdes_bm_testbenches'
    tb_cell = 'diffamp_casc_tb_dc'
    cell_name = 'diffamp_casc'

    print('creating testbench %s__%s' % (targ_lib, tb_cell))
    tb = prj.create_testbench(tb_lib, tb_cell, targ_lib, cell_name, targ_lib)

    print('setting testbench parameters')
    tb.set_simulation_environments(opt_info['env_list'])
    tb.set_parameter('cload', opt_info['fanout'] * max(opt_info['cin_list']))
    tb.set_parameter('cw', opt_info['cw'])
    tb.set_parameter('rw', opt_info['rw'])
    tb.set_env_parameter('vbias', opt_info['vbias_list'])
    tb.set_parameter('vdd', opt_info['vdd'])
    tb.set_parameter('vindc', opt_info['vincm'])
    tb.set_env_parameter('vload', opt_info['vload_list'])
    tb.set_parameter('vin_step', opt_info['vin_max'])
    tb.set_parameter('vindc_diff', 0)
    tb.set_parameter('vin_max', opt_info['vin_max'])
    tb.set_parameter('tsim', 10 * opt_info['ton'])
    tb.set_parameter('tstep', opt_info['ton'] / 100)
    tb.set_parameter('td', 100e-12)
    tb.set_parameter('tr', 0.1e-12)

    tb.set_simulation_view(impl_lib, cell_name, 'calibre')
    tb.update_testbench()

    return tb


def post_process_dc(results, dsn_params):
    ton = dsn_params['ton']
    td = 100e-12

    env_list = results['corner'].tolist()
    outac_dc = results['outac_dc'][0, 0, :, :]
    outdc_dc = results['outdc_dc'][0, 0, :, :]
    outac_tran = results['outac_tran'][0, 0, :, :]

    vindc_diff = results['vindc_diff']
    time = results['time']

    import matplotlib.pyplot as plt
    plt.figure(1)
    ax = plt.subplot(211)
    for idx, env in enumerate(env_list):
        sig = outac_dc[idx, :]
        gain, inl = get_inl(vindc_diff, sig)
        print('corner %s gain = %.4g, inl = %.4g%%' % (env, gain, inl * 100))
        ax.plot(vindc_diff, sig, label=env)
    ax.legend()

    ax = plt.subplot(212, sharex=ax)
    for idx, env in enumerate(env_list):
        sig = outdc_dc[idx, :]
        ax.plot(vindc_diff, sig, label=env)
    ax.legend()

    plt.figure(2)
    for idx, env in enumerate(env_list):
        sig = outac_tran[idx, :]
        vfinal = sig[-1]
        fun = scipy.interpolate.interp1d(time, sig, copy=False, assume_sorted=False)
        vcheck = fun(td + ton)
        k_settle = 1 - abs(vcheck - vfinal) / vfinal  # type: float
        print('corner %s k_settle = %.4g' % (env, k_settle))
        plt.plot(time, sig, label=env)
    plt.legend()

    plt.show()


def run_simulation(tb):
    print('running simulation')
    tb.run_simulation()

    print('loading results')
    results = bag.data.load_sim_results(tb.save_dir)

    return results


def design_explore():
    root_dir = 'mos_data'
    spec_file = 'specs/diffamp_casc_linearity.yaml'
    with open(spec_file, 'r') as f:
        spec_info = yaml.load(f)

    specs = spec_info['specs']
    layout_params = spec_info['layout_params']

    dsn_params = design_diffamp(root_dir, **specs)
    return dsn_params


def design_top(prj, temp_db):
    run_lvs = True
    run_rcx = True

    root_dir = 'mos_data'
    spec_file = 'specs/diffamp_casc_linearity.yaml'
    with open(spec_file, 'r') as f:
        spec_info = yaml.load(f)

    specs = spec_info['specs']
    layout_params = spec_info['layout_params']

    dsn_params = design_diffamp(root_dir, **specs)

    pprint.pprint(dsn_params)

    generate_diffamp(prj, temp_db, dsn_params, layout_params, run_lvs=run_lvs, run_rcx=run_rcx)

    # create tb_bias to compute load bias voltages
    tb_bias = create_tb_bias(prj, temp_db.lib_name, dsn_params)
    tb_bias.run_simulation()
    bias_results = bag.data.load_sim_results(tb_bias.save_dir)

    vload_dict = dict(zip(bias_results['corner'].tolist(), bias_results['bias_load'][0, :].tolist()))
    vload_list = [vload_dict[env] for env in dsn_params['env_list']]
    print('pmos bias: %s' % str(vload_list))
    dsn_params['vload_list'] = vload_list

    # create and run tb_dc
    tb_dc = create_tb_dc(prj, temp_db.lib_name, dsn_params)
    tb_dc.run_simulation()
    dc_results = bag.data.load_sim_results(tb_dc.save_dir)
    post_process_dc(dc_results, dsn_params)

    return dsn_params


if __name__ == '__main__':

    impl_lib = 'demo_diffamp_linearity'

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()
        temp = 70.0
        layers = [4, 5, 6, 7]
        spaces = [0.084, 0.080, 0.084, 0.080]
        widths = [0.060, 0.100, 0.060, 0.100]
        bot_dir = 'x'

        routing_grid = RoutingGrid(bprj.tech_info, layers, spaces, widths, bot_dir)

        tdb = TemplateDB('template_libs.def', routing_grid, impl_lib, use_cybagoa=True)
    else:
        print('loading BAG project')
