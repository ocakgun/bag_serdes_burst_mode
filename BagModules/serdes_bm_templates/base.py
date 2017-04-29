# -*- coding: utf-8 -*-


"""This module contains common design functions for various flavors of serdes schematics"""


def design_gm(m, port_list, lch, w_dict, th_dict, fg_dict, fg_tot, flip_sd=False, decap=False):
    """Design components of a Gm cell.

    Parameters
    ----------
    m : DesignModule
        the Gm design module.
    port_list : List[Tuple[str, Tuple[str, str], Tuple[str, str]]]
        a list of mappings from transistor types to the drain/source node names.
    lch : float
        channel length, in meters.
    w_dict : Dict[str, Union[float, int]]
        dictionary from transistor type to transistor width.
    th_dict : Dict[str, str]
        dictionary from transistor type to transistor threshold flavor.
    fg_dict : Dict[str, int]
        dictionary from transistor type to single-sided number of fingers.
    fg_tot : int
        total number of fingers.
    flip_sd : bool
        True to flip source/drain connections.  Defaults to False.
    decap : bool
        True to draw tail decap.  Defaults to False.
    """
    fg_ref = fg_dict.get('ref', 0)
    if decap or fg_ref > 0:
        fg_cap = fg_tot - 2 * fg_dict['tail'] - fg_ref
        if fg_cap < 0:
            raise ValueError('number of decap fingers is negative.')
    else:
        fg_cap = 0

    for name, d_ports, s_ports in port_list:
        w = w_dict[name]
        fg = fg_dict[name]
        intent = th_dict[name]
        name_upper = name.upper()
        m.instances['X%sP' % name_upper].design(w=w, l=lch, nf=fg, intent=intent)
        m.instances['X%sN' % name_upper].design(w=w, l=lch, nf=fg, intent=intent)
        dum_tran_name = 'X%sD' % name_upper

        if name == 'tail' and (fg_ref > 0 or fg_cap > 0):
            # all tail dummies used as decap
            m.delete_instance(dum_tran_name)
        else:
            dum_ports = d_ports if flip_sd else s_ports
            fg_extra = fg_tot - fg * 2 - 4
            if fg_extra < 0:
                raise ValueError('fg_tot = %d is less than minimum required fingers.' % fg_tot)
            if dum_ports[0] != dum_ports[1]:
                if fg_extra > 0:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(3)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': dum_ports[1]}, {'D': 'VSS'}]
                    m.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                    m.instances[dum_tran_name][2].design(w=w, l=lch, nf=fg_extra, intent=intent)
                else:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(2)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': dum_ports[1]}]
                    m.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                m.instances[dum_tran_name][0].design(w=w, l=lch, nf=2, intent=intent)
                m.instances[dum_tran_name][1].design(w=w, l=lch, nf=2, intent=intent)
            else:
                if fg_extra > 0:
                    dum_names = ['X%sD%d' % (name_upper, idx) for idx in range(2)]
                    dum_terms = [{'D': dum_ports[0]}, {'D': 'VSS'}]
                    m.array_instance(dum_tran_name, dum_names, term_list=dum_terms)
                    m.instances[dum_tran_name][0].design(w=w, l=lch, nf=4, intent=intent)
                    m.instances[dum_tran_name][1].design(w=w, l=lch, nf=fg_extra, intent=intent)
                else:
                    m.reconnect_instance_terminal(dum_tran_name, 'D', dum_ports[0])
                    m.instances[dum_tran_name].design(w=w, l=lch, nf=4, intent=intent)

    # design tail reference current/decap
    w_tail = w_dict['tail']
    intent_tail = th_dict['tail']
    if fg_ref == 0:
        m.delete_instance('XREF')
    else:
        m.instances['XREF'].design(w=w_tail, l=lch, nf=fg_ref, intent=intent_tail)
    if fg_cap == 0:
        m.delete_instance('XCAP')
    else:
        m.instances['XCAP'].design(w=w_tail, l=lch, nf=fg_cap, intent=intent_tail)

    # add dummies for unused transistors
    all_keys = list(w_dict.keys())
    w_th_list = []
    for key in all_keys:
        if key not in fg_dict and key != 'load':
            w_th_list.append((w_dict[key], th_dict[key]))
    if not w_th_list:
        m.delete_instance('XDUM')
    else:
        m.array_instance('XDUM', ['XDUM%d' % idx for idx in range(len(w_th_list))])
        for idx, (w_cur, th_cur) in enumerate(w_th_list):
            m.instances['XDUM'][idx].design(w=w_cur, l=lch, nf=fg_tot, intent=th_cur)


def design_diffamp(m, gm_types, lch, w_dict, th_dict, fg_dict, fg_tot, flip_sd=False, decap=False, load_decap=False):
    """Design components of a differential amplifier.

    Parameters
    ----------
    m : DesignModule
        the Gm design module.
    gm_types : List[str]
        list of transistor types in the Gm cell.
    lch : float
        channel length, in meters.
    w_dict : Dict[str, Union[float, int]]
        dictionary from transistor type to transistor width.
        Expect keys: 'casc', 'in', 'sw', 'tail'.
    th_dict : Dict[str, str]
        dictionary from transistor type to transistor threshold flavor.
        Expect keys: 'casc', 'in', 'sw', 'tail'.
    fg_dict : Dict[str, int]
        dictionary from transistor type to single-sided number of fingers.
        Expect keys: 'casc', 'in', 'sw', 'tail'.
    fg_tot : int
        total number of fingers.
    flip_sd : bool
        True to flip source/drain connections.  Defaults to False.
    decap : bool
        True to draw tail decap.  Defaults to False.
    load_decap : bool
        True to draw load decap.  Defaults to False.
    """
    load_w = {'load': w_dict['load']}
    load_th = {'load': th_dict['load']}
    load_fg = {'load': fg_dict['load']}
    m.instances['XLOAD'].design_specs(lch, load_w, load_th, load_fg, fg_tot, flip_sd=flip_sd, decap=load_decap)

    gm_fg = {key: fg_dict[key] for key in gm_types if key in fg_dict}
    if 'ref' in fg_dict:
        gm_fg['ref'] = fg_dict['ref']
    m.instances['XGM'].design_specs(lch, w_dict, th_dict, gm_fg, fg_tot, flip_sd=flip_sd, decap=decap)


def design_summer(m, name_list, lch, w_dict, th_dict, amp_fg_list, amp_fg_tot_list,
                  sgn_list, fg_tot, decap_list, load_decap_list, flip_sd_list):
    """Design components of a Gm summer.

    Parameters
    ----------
    m : DesignModule
        the Gm summer design module.
    name_list : List[str]
        list of summer stage names.
    lch : float
        channel length, in meters.
    w_dict : Dict[str, Union[float, int]]
        dictionary from transistor type to transistor width.
        Expect keys: 'load', 'casc', 'in', 'sw', 'tail'.
    th_dict : Dict[str, str]
        dictionary from transistor type to transistor threshold flavor.
        Expect keys: 'load', 'casc', 'in', 'sw', 'tail'.
    amp_fg_list : List[Dict[str, int]]
        list of amplifier finger dictionaries.  Must include fg_tot for each amplifier.
    amp_fg_tot_list : List[int]
            list of total number of fingers for each amplifier.
    sgn_list : List[int]
        list of amplifier signs.
    fg_tot : int
        total number of fingers.
    decap_list : List[bool]
        list of whether to draw decaps for each amplifier.
    load_decap_list : Optional[List[bool]]
        list of whether to draw load decaps for each amplifier.
    flip_sd_list : List[bool]
        list of whether to flip source/drain connections for each amplifier.
    """

    fg_dum = fg_tot
    for name, fg_dict, fg_tot_cur, sgn, decap, load_decap, flip_sd in \
            zip(name_list, amp_fg_list, amp_fg_tot_list, sgn_list, decap_list, load_decap_list, flip_sd_list):
        if sgn < 0:
            m.reconnect_instance_terminal(name, 'outp', 'outn')
            m.reconnect_instance_terminal(name, 'outn', 'outp')
        else:
            m.reconnect_instance_terminal(name, 'outp', 'outp')
            m.reconnect_instance_terminal(name, 'outn', 'outn')
        m.instances[name].design_specs(lch, w_dict, th_dict, fg_dict, fg_tot_cur, flip_sd=flip_sd,
                                       decap=decap, load_decap=load_decap)
        fg_dum -= fg_tot_cur

    if fg_dum < 0:
        raise ValueError('fg_tot = %d less than minimum required number of fingers.' % fg_tot)

    # design pmos dummies
    load_w = w_dict['load']
    load_th = th_dict['load']
    m.instances['XDP'].design(w=load_w, l=lch, nf=fg_dum, intent=load_th)

    # design nmos dummies
    key_list = [k for k in w_dict.keys() if k != 'load']
    m.array_instance('XDN', ['XDN%d' % idx for idx in range(len(key_list))])
    for inst, key in zip(m.instances['XDN'], key_list):
        w_cur = w_dict[key]
        th_cur = th_dict[key]
        inst.design(w=w_cur, l=lch, nf=fg_dum, intent=th_cur)
