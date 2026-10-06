
import io
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


st.set_page_config(
    page_title="Engineering Diagram Studio",
    layout="wide"
)

st.title("Engineering Diagram Studio")

if "curves" not in st.session_state:
    st.session_state.curves = []

if "extra_commands" not in st.session_state:
    st.session_state.extra_commands = ""


def read_uploaded(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded_file), "general"

    raw = uploaded_file.getvalue()
    text = raw.decode("utf-8", errors="ignore")

    first_line = text.splitlines()[0] if text.splitlines() else ""

    antenna_columns = [
        "Elevation_deg",
        "Azimuth_deg",
        "Abs_Grlz_dB",
        "Abs_Cross_dB",
        "Phase_Cross_deg",
        "Abs_Copol_dB",
        "Phase_Copol_deg",
        "Ax_Ratio_dB",
    ]

    if "Elev." in first_line and "Azim." in first_line:
        df = pd.read_csv(
            io.StringIO(text),
            sep=r"\s+",
            skiprows=2,
            header=None,
            names=antenna_columns,
            engine="python"
        )

        for column in antenna_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        df = df.dropna(subset=["Elevation_deg", "Azimuth_deg"])
        return df, "antenna"

    try:
        df = pd.read_csv(io.StringIO(text), sep=None, engine="python")
        if df.shape[1] >= 2:
            return df, "general"
    except Exception:
        pass

    return pd.read_csv(io.StringIO(text), sep=r"\s+", engine="python"), "general"


def apply_safe_plot_commands(ax, code, np_namespace):
    """
    Intentionally restricted web console.
    Allows only a small set of plotting operations, not arbitrary Python execution.
    """
    allowed = {
        "axhline": ax.axhline,
        "axvline": ax.axvline,
        "set_xlim": ax.set_xlim,
        "set_ylim": ax.set_ylim,
        "set_title": ax.set_title,
        "set_xlabel": ax.set_xlabel,
        "set_ylabel": ax.set_ylabel,
        "grid": ax.grid,
    }

    messages = []

    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = re.fullmatch(r"ax\.(axhline|axvline)\(([-+0-9.eE]+)\)", line)
        if m:
            allowed[m.group(1)](float(m.group(2)))
            messages.append(f"OK: {line}")
            continue

        m = re.fullmatch(r"ax\.(set_xlim|set_ylim)\(([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\)", line)
        if m:
            allowed[m.group(1)](float(m.group(2)), float(m.group(3)))
            messages.append(f"OK: {line}")
            continue

        m = re.fullmatch(r"ax\.(set_title|set_xlabel|set_ylabel)\(['\"](.*)['\"]\)", line)
        if m:
            allowed[m.group(1)](m.group(2))
            messages.append(f"OK: {line}")
            continue

        if line == "ax.grid(True)":
            ax.grid(True)
            messages.append(f"OK: {line}")
            continue

        messages.append(f"Skipped (not allowed in web mode): {line}")

    return messages


with st.sidebar:
    st.header("Plot")

    plot_mode = st.selectbox(
        "Plot type",
        ["Cartesian", "Polar"]
    )

    title = st.text_input("Title", "")
    xlabel = st.text_input("X axis", "X")
    ylabel = st.text_input("Y axis", "Y")

    polar_floor = st.number_input(
        "Polar dB floor",
        value=-60.0,
        step=5.0
    )

    show_grid = st.checkbox("Grid", True)
    show_legend = st.checkbox("Legend", True)

    st.divider()

    uploaded = st.file_uploader(
        "Import TXT / CSV / Excel",
        type=["txt", "csv", "xlsx", "xls"]
    )

if uploaded is not None:
    df, detected = read_uploaded(uploaded)

    st.subheader("Import curve")

    columns = [str(c) for c in df.columns]

    c1, c2, c3 = st.columns(3)

    with c1:
        preset_options = [
            "General X/Y data",
            "Vertical antenna pattern",
            "Horizontal antenna pattern"
        ]

        preset_default = 1 if detected == "antenna" else 0

        preset = st.selectbox(
            "Preset",
            preset_options,
            index=preset_default
        )

    if preset == "Vertical antenna pattern" and detected == "antenna":
        default_x = columns.index("Elevation_deg")
        default_y = columns.index("Abs_Copol_dB")
        default_filter = "Azimuth_deg"

    elif preset == "Horizontal antenna pattern" and detected == "antenna":
        default_x = columns.index("Azimuth_deg")
        default_y = columns.index("Abs_Copol_dB")
        default_filter = "Elevation_deg"

    else:
        default_x = 0
        default_y = 1 if len(columns) > 1 else 0
        default_filter = "(none)"

    with c1:
        x_col = st.selectbox("X column", columns, index=default_x)

    with c2:
        y_col = st.selectbox("Y column", columns, index=default_y)

    with c3:
        filter_col = st.selectbox(
            "Filter column",
            ["(none)"] + columns,
            index=(["(none)"] + columns).index(default_filter)
            if default_filter in (["(none)"] + columns)
            else 0
        )

    filter_value = st.number_input("Filter value", value=0.0)

    normalize = st.checkbox(
        "Normalize Y maximum to 0 dB",
        value=(detected == "antenna")
    )

    curve_name = st.text_input(
        "Curve name",
        "Imported curve"
    )

    if st.button("Add curve"):
        work = df.copy()

        if filter_col != "(none)":
            numeric_filter = pd.to_numeric(work[filter_col], errors="coerce")

            available = np.asarray(
                sorted(numeric_filter.dropna().unique()),
                dtype=float
            )

            if len(available) == 0:
                st.error("Filter column contains no numeric values.")
            else:
                actual_value = available[
                    np.argmin(np.abs(available - filter_value))
                ]

                mask = np.isclose(
                    numeric_filter,
                    actual_value,
                    rtol=0,
                    atol=1e-8
                )

                work = work.loc[mask].copy()

        x = pd.to_numeric(work[x_col], errors="coerce")
        y = pd.to_numeric(work[y_col], errors="coerce")

        valid = x.notna() & y.notna()

        x = x[valid].to_numpy(dtype=float)
        y = y[valid].to_numpy(dtype=float)

        order = np.argsort(x)
        x = x[order]
        y = y[order]

        if normalize and len(y):
            y = y - np.nanmax(y)

        st.session_state.curves.append(
            {
                "name": curve_name,
                "x": x.tolist(),
                "y": y.tolist(),
            }
        )

        st.success(
            f"Added {len(x)} points."
        )


st.subheader("Curves")

if st.session_state.curves:
    remove_index = st.selectbox(
        "Curve to remove",
        list(range(len(st.session_state.curves))),
        format_func=lambda i: st.session_state.curves[i]["name"]
    )

    if st.button("Remove selected curve"):
        st.session_state.curves.pop(remove_index)
        st.rerun()
else:
    st.caption("No curves loaded yet.")


fig = plt.figure(figsize=(10, 7))

if plot_mode == "Polar":
    ax = fig.add_subplot(111, projection="polar")
    db_floor = min(float(polar_floor), -1.0)

    for curve in st.session_state.curves:
        angle_deg = np.asarray(curve["x"], dtype=float)
        gain_db = np.asarray(curve["y"], dtype=float)

        valid = np.isfinite(angle_deg) & np.isfinite(gain_db)
        angle_deg = np.mod(angle_deg[valid], 360.0)
        gain_db = gain_db[valid]

        order = np.argsort(angle_deg)
        angle_deg = angle_deg[order]
        gain_db = gain_db[order]

        gain_clipped = np.clip(gain_db, db_floor, 0.0)
        radius = gain_clipped - db_floor
        theta = np.deg2rad(angle_deg)

        if len(theta) > 1:
            theta = np.append(theta, theta[0] + 2 * np.pi)
            radius = np.append(radius, radius[0])

        ax.plot(theta, radius, label=curve["name"])

    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.arange(0, 360, 15))
    ax.set_ylim(0, abs(db_floor))

    ticks_db = np.array([-60, -50, -40, -30, -20, -10, 0], dtype=float)
    ticks_db = ticks_db[ticks_db >= db_floor]

    if db_floor not in ticks_db:
        ticks_db = np.insert(ticks_db, 0, db_floor)

    ticks_db = np.unique(ticks_db)

    ax.set_yticks(ticks_db - db_floor)
    ax.set_yticklabels([f"{v:g} dB" for v in ticks_db])
    ax.set_rlabel_position(135)

else:
    ax = fig.add_subplot(111)

    for curve in st.session_state.curves:
        ax.plot(curve["x"], curve["y"], label=curve["name"])

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

ax.set_title(title)

if show_grid:
    ax.grid(True)

if show_legend and st.session_state.curves:
    ax.legend()


st.subheader("Web plotting console")
st.caption(
    "For security, the public web version uses a restricted plotting console. "
    "It does not execute arbitrary Python. The desktop version contains the full local Python console."
)

safe_code = st.text_area(
    "Commands",
    value=st.session_state.extra_commands,
    height=150,
    placeholder="""ax.axhline(0)
ax.set_xlim(0, 900)
ax.set_ylim(0, 200)
ax.set_title("Coverage")"""
)

st.session_state.extra_commands = safe_code

messages = apply_safe_plot_commands(
    ax,
    safe_code,
    np
)

if messages:
    with st.expander("Console output"):
        st.code("\n".join(messages))


st.pyplot(fig, use_container_width=True)

buffer = io.BytesIO()
fig.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
buffer.seek(0)

st.download_button(
    "Download PNG",
    buffer,
    file_name="diagram.png",
    mime="image/png"
)
