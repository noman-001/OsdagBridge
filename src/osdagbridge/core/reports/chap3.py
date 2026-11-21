from osdagbridge.core.utils.common import (
    KEY_CB_LOAD,
    KEY_LL_CUSTOM_VEHICLES,
    KEY_LL_FOOTPATH_PRESSURE_MODE,
    KEY_LL_FOOTPATH_PRESSURE_VALUE,
    KEY_LL_IRC_70R_BOGIE,
    KEY_LL_IRC_70R_TRACKED,
    KEY_LL_IRC_70R_WHEELED,
    KEY_LL_IRC_AA_TRACKED,
    KEY_LL_IRC_AA_WHEELED,
    KEY_LL_IRC_CLASS_A,
    KEY_LL_IRC_CLASS_FATIGUE,
    KEY_LL_IRC_CLASS_SV,
    KEY_MATERIAL_DECK_DENSITY,
    KEY_MATERIAL_GIRDER_DENSITY,
    KEY_PL_SELF_WEIGHT_FACTOR,
    KEY_RL_LOAD_VALUE,
    KEY_SL_HORIZONTAL_COEFF,
    KEY_SL_IMPORTANCE_FACTOR,
    KEY_SL_SOIL_TYPE,
    KEY_SL_SPECTRAL_COEFF,
    KEY_SL_VERTICAL_COEFF,
    KEY_SL_ZONE_FACTOR,
    KEY_SPAN,
    KEY_TL_BRIDGE_TEMP_MAX,
    KEY_TL_BRIDGE_TEMP_MIN,
    KEY_TL_TEMP_FALL,
    KEY_TL_TEMP_RISE,
    KEY_WC_LD_LANE_TABLE_COUNT,
    KEY_WC_MATERIAL,
    KEY_WC_THICKNESS,
    KEY_WL_AVG_EXPOSED_HEIGHT,
    KEY_WL_HOURLY_MEAN_WIND,
    KEY_WL_HOURLY_WIND_PRESSURE,
    KEY_WL_LONGITUDINAL_WIND_FORCE,
    KEY_WL_TERRAIN_TYPE,
    KEY_WL_TRANSVERSE_WIND_FORCE,
    KEY_WL_VERTICAL_WIND_FORCE,
)

from osdagbridge.core.reports.report_utils import _tex, _render_value


def _infer_lanes(input_dict):
    for k in (KEY_WC_LD_LANE_TABLE_COUNT, "lane_count", "no_of_lanes", "num_lanes", "lanes"):
        v = input_dict.get(k)
        if v not in (None, ""):
            try:
                n = int(float(v))
                if n > 0:
                    return n
            except Exception:
                pass
    # Fallback: IRC 5 Cl. 104.3.1 from carriageway width
    for k in ("carriageway_width", "Carriageway Width", "cw_width"):
        v = input_dict.get(k)
        if v not in (None, ""):
            try:
                w = float(str(v).split()[0])
                if w < 5.3:
                    return 1
                if w < 9.6:
                    return 2
                if w < 13.1:
                    return 3
                return max(4, int(w // 3.5))
            except Exception:
                pass
    return 2


def ch3_loads(input_dict):
    from osdagbridge.core.utils.codes.irc6_2017 import IRC6_2017

    span = input_dict.get(KEY_SPAN)
    span_m = None
    if span not in (None, ""):
        try:
            span_m = float(span)
        except Exception:
            span_m = None

    lanes = _infer_lanes(input_dict)
    braking_kN = None
    try:
        bf = IRC6_2017.cl_211_2_braking_force(lanes)
        if isinstance(bf, dict):
            val = bf.get("total_braking_force_kN") or bf.get("braking_force_kN")
            braking_kN = float(val) if val else None
        elif bf:
            braking_kN = float(bf) * 9.81
    except Exception:
        braking_kN = None

    im_a = None
    im_heavy = None
    if span_m is not None:
        try:
            im_a = 1.0 + IRC6_2017.cl_208_2_impact_factor(span_m)
        except Exception:
            pass
        try:
            im_heavy = 1.0 + IRC6_2017.cl_208_3_impact_factor(span_m)
        except Exception:
            pass

    vehicle_specs = [
        (KEY_LL_IRC_CLASS_A,       "Class A",             "554.0",  "A",     True),
        (KEY_LL_IRC_70R_WHEELED,   "Class 70R (Wheeled)", "1000.0", "heavy", True),
        (KEY_LL_IRC_70R_TRACKED,   "Class 70R (Tracked)", "700.0",  "heavy", True),
        (KEY_LL_IRC_70R_BOGIE,     "Class 70R (Bogie)",   "400.0",  "heavy", True),
        (KEY_LL_IRC_AA_WHEELED,    "Class AA (Wheeled)",  "400.0",  "heavy", True),
        (KEY_LL_IRC_AA_TRACKED,    "Class AA (Tracked)",  "700.0",  "heavy", True),
        (KEY_LL_IRC_CLASS_SV,      "Class SV",            "3850.0", "none",  False),
        (KEY_LL_IRC_CLASS_FATIGUE, "Class Fatigue",       "400.0",  "A",     True),
    ]

    veh_rows = []
    for key, label, load_kn, im_type, has_braking in vehicle_specs:
        if not input_dict.get(key):
            continue
        if im_type == "A" and im_a is not None:
            im_str = f"{im_a:.3f}"
        elif im_type == "heavy" and im_heavy is not None:
            im_str = f"{im_heavy:.3f}"
        elif im_type == "none":
            im_str = "1.000"
        else:
            im_str = "---"

        if has_braking:
            brk_cons = "Yes"
            # IRC 6 Cl. 211.2: 20% of first train load if code helper unavailable
            val_kn = braking_kN if braking_kN is not None else 0.20 * float(load_kn)
            brk_val = f"{val_kn:.2f} kN"
            brk_ecc = "1.20 m"
        else:
            brk_cons = "No"
            brk_val = "---"
            brk_ecc = "---"

        veh_rows.append(
            f"{_tex(label)} & {load_kn} & {im_str} & {brk_cons} & {brk_val} & {brk_ecc} \\\\[5pt]\n\\hline"
        )

    custom = input_dict.get(KEY_LL_CUSTOM_VEHICLES)
    if custom and isinstance(custom, list):
        for c in custom:
            cname = c.get("name") if isinstance(c, dict) else str(c)
            if cname:
                cload = str(c.get("total_load", "---")) if isinstance(c, dict) else "---"
                try:
                    val_kn = braking_kN if braking_kN is not None else 0.20 * float(cload)
                    brk_val = f"{val_kn:.2f} kN"
                except Exception:
                    brk_val = "---"
                veh_rows.append(
                    f"{_tex(cname)} & {_tex(cload)} & --- & Yes & {brk_val} & 1.20 m \\\\[5pt]\n\\hline"
                )

    if not veh_rows:
        veh_rows.append(r"\multicolumn{6}{|c|}{No live load vehicles selected} \\[5pt]" + "\n\\hline")

    veh_rows_str = "\n".join(veh_rows)

    fp_mode = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_MODE, "")
    fp_value = input_dict.get(KEY_LL_FOOTPATH_PRESSURE_VALUE, "")
    if str(fp_mode).strip().lower() in ("as per irc 6", "as per irc6", "automatic"):
        try:
            fp_val_str = f"{IRC6_2017.cl_206_1_footway_load():.3f}"
            fp_ref = "IRC 6 Cl. 206.1"
        except Exception:
            fp_val_str = "N/A"
            fp_ref = "IRC 6 Cl. 206.1"
    elif fp_value not in (None, ""):
        fp_val_str = _tex(fp_value)
        fp_ref = "User Defined"
    else:
        fp_val_str = "Not Applicable"
        fp_ref = "---"

    _LOAD_LABEL_MAP = {
        'dead_load':         'DL',
        'surfacing':         'SIDL',
        'live_load':         'LL',
        'wind_load':         'WL',
        'thermal_load':      'TL',
        'vehicle_collision': 'VC',
        'barge_impact':      'BI',
        'floating_bodies':   'FB',
        'seismic':           'EQ',
    }

    def _fmt_factors(factors):
        parts = []
        for load, val in factors.items():
            label = _LOAD_LABEL_MAP.get(load, load.upper())
            if isinstance(val, dict):
                add = val.get('adding')
                rel = val.get('relieving')
                add_s = f"{add:.2f}" if add is not None else '--'
                rel_s = f"{rel:.2f}" if rel is not None else '--'
                parts.append(f"{label}({add_s}/{rel_s})")
            else:
                if val is None:
                    continue
                parts.append(f"{label}({val:.2f})")
        return ' + '.join(parts)

    uls_combos = IRC6_2017.uls_load_combinations()
    sls_combos = IRC6_2017.sls_load_combinations()
    lc_rows = []
    for i, combo in enumerate(uls_combos, start=1):
        lc_rows.append(f"ULS-{i:02d}" + r" & " + _fmt_factors(combo['factors']) + r" \\[6pt]" + "\n" + r"\hline")
    for i, combo in enumerate(sls_combos, start=1):
        lc_rows.append(f"SLS-{i:02d}" + r" & " + _fmt_factors(combo['factors']) + r" \\[6pt]" + "\n" + r"\hline")
    lc_rows_str = "\n".join(lc_rows)

    return r"""
\chapter{Loads and Load Combinations}

This section summarizes all loads applied to the bridge and the load combinations considered for analysis and design.

\begin{table}[H]
\centering
\caption{\textbf{Dead Load -- Self Weight}}
\begin{tabular}{|L{5.5cm}|p{10.0cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Steel Self-Weight Applied} & """ + (_render_value(input_dict, KEY_MATERIAL_GIRDER_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Concrete Deck Weight} & """ + (_render_value(input_dict, KEY_MATERIAL_DECK_DENSITY, ' kN/m\\textsuperscript{3}')) + r""" \\[6pt]
\hline
\textnormal{Self-Weight Factor} & """ + (_render_value(input_dict, KEY_PL_SELF_WEIGHT_FACTOR)) + r""" \\[6pt]
\hline
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Dead Load for Surfacing (DW)}}
\begin{tabular}{|L{5.5cm}|p{10.0cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Wearing Course Load} & """ + (_render_value(input_dict, KEY_WC_MATERIAL)) + r""" x """ + (_render_value(input_dict, KEY_WC_THICKNESS)) + r""" \\[6pt]
\hline
\textnormal{Additional SIDL (Crash Barrier)} & """ + (_render_value(input_dict, KEY_CB_LOAD)) + r""" kN/m per barrier \\[6pt]
\hline
\textnormal{Railing Load} & """ + (_render_value(input_dict, KEY_RL_LOAD_VALUE)) + r""" kN/m\sdstar{} \\[6pt]
\hline
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Vehicle Live Loads (LL) --- per IRC 6}}
\begin{tabular}{|L{3.4cm}|C{2.4cm}|C{2.2cm}|C{2.2cm}|C{2.6cm}|C{2.4cm}|}
\hline
\rowcolor{tableHeaderBg}
 & & & \multicolumn{3}{c|}{\textbf{Braking Load}} \\
\cline{4-6}
\rowcolor{tableHeaderBg}
\multirow{-2}{*}{\textbf{Vehicle}} & \multirow{-2}{*}{\textbf{Total Load (kN)}} & \multirow{-2}{*}{\textbf{Impact Factor}} & \textbf{Considered?} & \textbf{Value} & \textbf{Eccentricity} \\
\hline
""" + veh_rows_str + r"""
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Footpath Live Load (if applicable)}}
\begin{tabular}{|L{5.5cm}|C{4.5cm}|L{5.5cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value (kN/m\textsuperscript{2})} & \textbf{Reference / Mode} \\
\hline
\textnormal{Footpath Live Load Pressure} & """ + fp_val_str + r""" & """ + _tex(fp_ref) + r""" \\[6pt]
\hline
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Wind Load (WL) --- per IRC 6}}
\begin{tabular}{|L{5.5cm}|p{10.0cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Basic Wind Speed, Vb} & """ + (_render_value(input_dict, 'wind_speed', ' m/s')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Terrain Type} & """ + (_render_value(input_dict, KEY_WL_TERRAIN_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Average Exposed Height, H (m)} & """ + (_render_value(input_dict, KEY_WL_AVG_EXPOSED_HEIGHT, ' m')) + r""" \\[6pt]
\hline
\textnormal{Hourly Mean Wind Speed, Vz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_MEAN_WIND, ' m/s')) + r""" \\[6pt]
\hline
\textnormal{Hourly Wind Pressure, Pz} & """ + (_render_value(input_dict, KEY_WL_HOURLY_WIND_PRESSURE, ' N/m\\textsuperscript{2}')) + r""" \\[6pt]
\hline
\textnormal{Transverse Wind Force} & """ + (_render_value(input_dict, KEY_WL_TRANSVERSE_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Longitudinal Wind Force} & """ + (_render_value(input_dict, KEY_WL_LONGITUDINAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\textnormal{Vertical Wind Force} & """ + (_render_value(input_dict, KEY_WL_VERTICAL_WIND_FORCE, ' kN')) + r""" \\[6pt]
\hline
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Earthquake Load (EL) --- per IRC 6}}
\begin{tabular}{|L{5.5cm}|p{10.0cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Seismic Zone} & """ + (_render_value(input_dict, 'seismic_zone')) + r""" [from Project Location] \\[6pt]
\hline
\textnormal{Zone Factor, Z} & """ + (_render_value(input_dict, KEY_SL_ZONE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Importance Factor, I} & """ + (_render_value(input_dict, KEY_SL_IMPORTANCE_FACTOR)) + r""" \\[6pt]
\hline
\textnormal{Type of Soil} & """ + (_render_value(input_dict, KEY_SL_SOIL_TYPE)) + r""" \\[6pt]
\hline
\textnormal{Sa/g} & """ + (_render_value(input_dict, KEY_SL_SPECTRAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Horizontal Seismic Coefficient, Ah} & """ + (_render_value(input_dict, KEY_SL_HORIZONTAL_COEFF)) + r""" \\[6pt]
\hline
\textnormal{Vertical Seismic Coefficient, Av} & """ + (_render_value(input_dict, KEY_SL_VERTICAL_COEFF)) + r""" \\[6pt]
\hline
\end{tabular}
\end{table}

\begin{table}[H]
\centering
\caption{\textbf{Temperature Load (TL) --- per IRC 6}}
\begin{tabular}{|L{5.5cm}|p{10.0cm}|}
\hline
\rowcolor{tableHeaderBg}
\textbf{Parameter} & \textbf{Value} \\
\hline
\textnormal{Maximum Shade Temperature} & """ + (_render_value(input_dict, 'shade_temp_max')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Minimum Shade Temperature} & """ + (_render_value(input_dict, 'shade_temp_min')) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Effective Bridge Temp. Range} & """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MIN)) + r""" to """ + (_render_value(input_dict, KEY_TL_BRIDGE_TEMP_MAX)) + r""" $^\circ$C \\[6pt]
\hline
\textnormal{Temperature Rise / Fall for Design} & +""" + (_render_value(input_dict, KEY_TL_TEMP_RISE)) + r""" $^\circ$C / $-$""" + (_render_value(input_dict, KEY_TL_TEMP_FALL)) + r""" $^\circ$C \\[6pt]
\hline
\end{tabular}
\end{table}

\vspace{1em}
\begin{longtable}{|C{4.0cm}|p{11.5cm}|}
\caption{\textbf{Load Combinations}}
\hline
\textbf{Combination ID} & \textbf{Load Cases} \\[6pt]
\hline
""" + lc_rows_str + r"""
\end{longtable}

\noindent\textit{Note: All IRC 6 load combinations are auto-generated by OsdagBridge. User-defined custom combinations, if any, are appended.}
"""