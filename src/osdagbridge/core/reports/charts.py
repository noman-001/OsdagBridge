import os
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from osdagbridge.core.utils.common import (
    KEY_DD_HAS_OVERHANG,
    KEY_DD_MU_BOT,
    KEY_DD_MU_OH,
    KEY_DD_MU_TOP,
    KEY_DD_M_ULS_HOG,
    KEY_DD_M_ULS_OH,
    KEY_DD_M_ULS_SAG,
    KEY_DD_PUNCH_VED,
    KEY_DD_SHEAR_VED,
    KEY_DD_SHEAR_VRDC,
    KEY_DD_VRD_C_MPA,
    KEY_DD_WK_BOT,
    KEY_DD_WK_LIMIT,
    KEY_DD_WK_OH,
    KEY_DD_WK_TOP,
)
from osdagbridge.core.reports.styles import (
    CHART_DPI,
    CHART_GREEN,
    CHART_BLUE,
    CHART_AMBER,
    CHART_PASS,
    CHART_FAIL,
)


def _to_float(val):
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        return float(val)
    m = re.search(r"[-+]?\d*\.?\d+", str(val))
    return float(m.group(0)) if m else None


def extract_primary_urs(bridge):
    """Return governing UR for each primary bridge component."""
    out = bridge.output_dict or {}
    dr = out.get("design_results", {}) or {}
    per_girder = dr.get("per_girder", {}) or {}
    deck_rpt = out.get("deck_report_values", {}) or {}

    # 1. Steel Plate Girders
    girder_urs = []
    for g, gd in per_girder.items():
        if str(g).startswith("EB"):
            continue
        for chk in (gd.get("checks") or []):
            d = _to_float(chk.get("dcr"))
            if d is not None:
                girder_urs.append(d)
    girder_ur = max(girder_urs) if girder_urs else 0.0

    # 2. Concrete Deck Slab (includes bottom, top, and overhang crack width checks)
    deck_urs = []
    pair_ratios = []
    wks = []
    wk_limit = None
    if deck_rpt:
        has_oh = bool(deck_rpt.get(KEY_DD_HAS_OVERHANG))
        ratio_pairs = [
            (KEY_DD_M_ULS_SAG, KEY_DD_MU_BOT),
            (KEY_DD_M_ULS_HOG, KEY_DD_MU_TOP),
            (KEY_DD_PUNCH_VED, KEY_DD_VRD_C_MPA),
            (KEY_DD_SHEAR_VED, KEY_DD_SHEAR_VRDC),
        ]
        if has_oh:
            ratio_pairs.append((KEY_DD_M_ULS_OH, KEY_DD_MU_OH))

        for dk, ck in ratio_pairs:
            dem = _to_float(deck_rpt.get(dk))
            cap = _to_float(deck_rpt.get(ck))
            ratio = (dem / cap) if (dem is not None and cap and cap > 0) else None
            pair_ratios.append((dk, ck, dem, cap, ratio))
            if ratio is not None:
                deck_urs.append(ratio)

        wk_limit = _to_float(deck_rpt.get(KEY_DD_WK_LIMIT))
        wks = [
            _to_float(deck_rpt.get(KEY_DD_WK_BOT)) or 0.0,
            _to_float(deck_rpt.get(KEY_DD_WK_TOP)) or 0.0,
        ]
        if has_oh:
            wks.append(_to_float(deck_rpt.get(KEY_DD_WK_OH)) or 0.0)
        gov_wk = max(wks) if wks else None
        if gov_wk is not None and wk_limit and wk_limit > 0:
            deck_urs.append(gov_wk / wk_limit)

    deck_ur = max(deck_urs) if deck_urs else 0.0

    # 3. Cross Bracing
    cb_urs = []
    for pair in bridge.get_cb_pairs():
        for member in ("diagonal", "chord"):
            for ftype in ("compression", "tension"):
                fv = _to_float(bridge.get_cb_efficiency(pair, member, ftype))
                if fv is not None:
                    cb_urs.append(fv)
    cb_ur = max(cb_urs) if cb_urs else 0.0

    # 4. End Diaphragms (mirrors cross bracing UR when bracing-type diaphragm is used)
    ed_type = ""
    for k, v in (bridge.input_dict or {}).items():
        if "end_diaphragm" in str(k).lower() and "type" in str(k).lower() and v:
            ed_type = str(v)
            break
    ed_ur = cb_ur if "brac" in ed_type.lower() else 0.0

    return {
        "Steel Plate\nGirders": girder_ur,
        "Concrete\nDeck Slab": deck_ur,
        "Cross\nBracing": cb_ur,
        "End\nDiaphragms": ed_ur,
    }


def generate_ur_chart(bridge, out_path):
    """Generate Section 5.5 Utilization Ratio summary bar chart."""
    ur_map = extract_primary_urs(bridge)
    labels = list(ur_map.keys())
    values = list(ur_map.values())
    colors = [CHART_FAIL if v > 1.0 else CHART_PASS for v in values]

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bars = ax.bar(labels, values, color=colors, width=0.52, edgecolor="#333333", linewidth=0.6)

    ax.axhline(1.0, color=CHART_FAIL, linestyle="--", linewidth=1.4, label="Limit (UR = 1.0)")

    ymax = max(max(values) if values else 0.0, 1.15) * 1.18
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Utilization Ratio (Demand / Capacity)", fontsize=9.5)
    ax.set_title("Overall Utilization Ratio Summary — Primary Elements", fontsize=11, fontweight="bold", pad=10)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.set_axisbelow(True)

    for bar, val in zip(bars, values):
        txt = f"{val:.2f}" if val > 0 else "N/A"
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + ymax * 0.025,
            txt,
            ha="center",
            va="bottom",
            fontsize=8.8,
            fontweight="bold",
            color=CHART_FAIL if val > 1.0 else "#222222",
        )

    ax.legend(loc="upper right", frameon=True, fontsize=8.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_material_charts(input_dict, out_dir):
    """Generate Chapter 7 material quantity charts."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {}

    girders_mt = _to_float(input_dict.get("steel_girders_wt_total")) or 0.0
    cb_top = _to_float(input_dict.get("bracing_top_wt_total")) or 0.0
    cb_bot = _to_float(input_dict.get("bracing_bot_wt_total")) or 0.0
    cb_diag = _to_float(input_dict.get("bracing_diag_wt_total")) or 0.0
    cb_total_mt = cb_top + cb_bot + cb_diag
    studs_mt = _to_float(input_dict.get("shear_studs_wt_total")) or 0.0

    steel_labels = ["Plate Girders", "Cross Bracing", "Shear Studs"]
    steel_vals = [girders_mt, cb_total_mt, studs_mt]
    steel_colors = [CHART_BLUE, CHART_GREEN, CHART_AMBER]

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bars = ax.bar(steel_labels, steel_vals, color=steel_colors, width=0.45, edgecolor="#333333", linewidth=0.6)
    ymax = max(max(steel_vals), 1.0) * 1.2
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Weight (Metric Tonnes, MT)", fontsize=9.5)
    ax.set_title("Structural Steel Quantity Breakdown", fontsize=11, fontweight="bold", pad=10)
    ax.grid(axis="y", linestyle=":", alpha=0.45)
    ax.set_axisbelow(True)

    for bar, val in zip(bars, steel_vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + ymax * 0.025,
            f"{val:.2f} MT",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    steel_path = os.path.join(out_dir, "chart_steel_tonnage.png")
    fig.savefig(steel_path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    paths["chart_steel_tonnage"] = steel_path.replace("\\", "/")

    conc_vol = _to_float(input_dict.get("concrete_deck_vol_total")) or 0.0
    rebar_mt = _to_float(input_dict.get("rebar_deck_wt_total")) or 0.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 3.6))

    b1 = ax1.bar(["Deck Slab\nConcrete"], [conc_vol], color=CHART_BLUE, width=0.4, edgecolor="#333333", linewidth=0.6)
    y1 = max(conc_vol, 1.0) * 1.25
    ax1.set_ylim(0, y1)
    ax1.set_ylabel(r"Volume ($\mathrm{m^3}$)", fontsize=9.5)
    ax1.set_title("Concrete Volume", fontsize=10.5, fontweight="bold")
    ax1.grid(axis="y", linestyle=":", alpha=0.45)
    ax1.set_axisbelow(True)
    ax1.text(b1[0].get_x() + b1[0].get_width() / 2, conc_vol + y1 * 0.03,
             f"{conc_vol:.2f} m³", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    b2 = ax2.bar(["Reinforcement\nSteel (Fe 500)"], [rebar_mt], color=CHART_GREEN, width=0.4, edgecolor="#333333", linewidth=0.6)
    y2 = max(rebar_mt, 1.0) * 1.25
    ax2.set_ylim(0, y2)
    ax2.set_ylabel("Weight (MT)", fontsize=9.5)
    ax2.set_title("Reinforcement Steel Weight", fontsize=10.5, fontweight="bold")
    ax2.grid(axis="y", linestyle=":", alpha=0.45)
    ax2.set_axisbelow(True)
    ax2.text(b2[0].get_x() + b2[0].get_width() / 2, rebar_mt + y2 * 0.03,
             f"{rebar_mt:.2f} MT", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    fig.suptitle("Concrete Volume vs. Reinforcement Steel Weight", fontsize=11, fontweight="bold", y=1.02)
    plt.tight_layout()

    conc_path = os.path.join(out_dir, "chart_concrete_rebar.png")
    fig.savefig(conc_path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    paths["chart_concrete_rebar"] = conc_path.replace("\\", "/")

    return paths