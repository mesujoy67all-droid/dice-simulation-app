import streamlit as st
import pandas as pd
import numpy as np

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(
    page_title="Dice Simulation Platform",
    layout="wide"
)

st.title("🎲 Dice-Based Production Simulation Platform")
st.markdown(
    "This platform simulates capacity variability using dice rolls, "
    "WIP buffers, and finished goods output."
)

# -----------------------------------
# Sidebar: Simulation Settings
# -----------------------------------
st.sidebar.header("Simulation Settings")

num_members = st.sidebar.number_input(
    "Number of Members (Workstations)",
    min_value=2,
    value=7,
    step=1
)

num_days = st.sidebar.number_input(
    "Number of Days",
    min_value=1,
    max_value=100000,
    value=20,
    step=1
)

members = [chr(65 + i) for i in range(num_members)]

# -----------------------------------
# Sidebar: Dice Configuration
# -----------------------------------
st.sidebar.subheader("Dice Range per Member")

dice_configs = {}
for m in members:
    low, high = st.sidebar.slider(
        f"Dice range for {m}",
        min_value=1,
        max_value=20,
        value=(1, 6)
    )
    dice_configs[m] = (low, high)

# -----------------------------------
# Sidebar: Initial WIP Buffers
# -----------------------------------
st.sidebar.subheader("Initial WIP Buffers")

wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {}

for key in wip_keys:
    initial_wip[key] = st.sidebar.number_input(
        f"{key}",
        min_value=0,
        value=4,
        step=1
    )

# -----------------------------------
# Run Simulation
# -----------------------------------
if st.sidebar.button("▶ Run Simulation"):

    # Generate Dice Rolls
    dice_data = {
        m: [
            np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1)
            for _ in range(num_days)
        ]
        for m in members
    }

    df_dice = pd.DataFrame(dice_data)
    df_dice.index += 1
    df_dice.index.name = "Day"

    st.subheader("🎲 Dice Roll Table (Capacity)")
    st.dataframe(df_dice, use_container_width=True)

    # Simulation Logic
    wip_buffers = initial_wip.copy()
    history = []
    total_finished_goods = 0

    for day in df_dice.index:
        day_rolls = df_dice.loc[day]
        daily_fg = 0

        for i, m in enumerate(members):
            roll = day_rolls[m]

            if i == 0:
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                wip_buffers[next_wip] += roll

            elif i == len(members) - 1:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                daily_fg = move_amount
                total_finished_goods += move_amount

            else:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                wip_buffers[next_wip] += move_amount

        daily_record = {"Day": day}
        daily_record.update(wip_buffers.copy())
        daily_record["Daily_Total_WIP"] = sum(wip_buffers.values())
        daily_record["Daily_FG"] = daily_fg
        history.append(daily_record)

    # Results
    results_df = pd.DataFrame(history).set_index("Day")

    st.subheader("📊 Simulation Results")
    st.dataframe(results_df, use_container_width=True)

    # KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Finished Goods", total_finished_goods)
    col2.metric("Average Daily FG", round(results_df["Daily_FG"].mean(), 2))
    col3.metric("Average Total WIP", round(results_df["Daily_Total_WIP"].mean(), 2))

    # Charts
    st.subheader("📈 Performance Trends")
    st.line_chart(results_df[["Daily_Total_WIP", "Daily_FG"]])

# =====================================================
# ADD-ON: ENTROPY & DIAGNOSTIC TABLES (NO UI CHANGES)
# =====================================================

from collections import defaultdict
import math

# -----------------------------
# Helper: Entropy Function
# -----------------------------
def entropy(values):
    if len(values) == 0:
        return 0
    values = np.array(values)
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------
# Reconstruct Station Outputs & WIP
# -----------------------------
station_output = defaultdict(list)
station_wip = defaultdict(list)

for day in df_dice.index:
    day_rolls = df_dice.loc[day]
    temp_wip = initial_wip.copy()

    for i, m in enumerate(members):
        roll = day_rolls[m]

        if i == 0:
            next_wip = f"WIP_{members[i]}{members[i+1]}"
            temp_wip[next_wip] += roll
            station_output[m].append(roll)

        elif i == len(members) - 1:
            prev_wip = f"WIP_{members[i-1]}{members[i]}"
            move = min(roll, temp_wip[prev_wip])
            temp_wip[prev_wip] -= move
            station_output[m].append(move)

        else:
            prev_wip = f"WIP_{members[i-1]}{members[i]}"
            next_wip = f"WIP_{members[i]}{members[i+1]}"
            move = min(roll, temp_wip[prev_wip])
            temp_wip[prev_wip] -= move
            temp_wip[next_wip] += move
            station_output[m].append(move)

    for key in temp_wip:
        station = key.split("_")[1][0]
        station_wip[station].append(temp_wip[key])

# =====================================================
# TABLE B: STATION-LEVEL FLOW DIAGNOSTICS
# =====================================================
table_b_rows = []

for s in members:
    outputs = station_output[s]
    wips = station_wip[s]

    total_output = sum(outputs)
    avg_wip = np.mean(wips) if wips else 0
    H_i = entropy(outputs)

    if H_i > 2:
        interpretation = "High variability / Unpredictable"
    elif avg_wip > np.mean(list(map(np.mean, station_wip.values()))):
        interpretation = "Congested / Bottleneck"
    else:
        interpretation = "Stable / Well-controlled"

    table_b_rows.append({
        "Station": s,
        "Total Output": total_output,
        "Avg WIP": round(avg_wip, 2),
        "Entropy Hᵢ": round(H_i, 3),
        "Interpretation": interpretation
    })

table_B = pd.DataFrame(table_b_rows)

st.subheader("📊 Table B: Station-Level Flow Diagnostics")
st.dataframe(table_B, use_container_width=True)

# =====================================================
# TABLE A: GLOBAL SYSTEM DIAGNOSTICS
# =====================================================
T = total_finished_goods / num_days                     # Mean Throughput
W = sum(wip_buffers.values())                           # Total WIP
L = W / T if T > 0 else 0                                # Lead Time

station_entropies = table_B["Entropy Hᵢ"].values
H_bar = np.mean(station_entropies)                      # Avg Entropy
sigma_H = np.std(station_entropies)                     # Entropy Spread

table_A = pd.DataFrame([{
    "Initial WIP": sum(initial_wip.values()),
    "Mean Throughput (T)": round(T, 3),
    "Total WIP (W)": W,
    "Lead Time (L = W / T)": round(L, 3),
    "Avg Entropy H̄": round(H_bar, 3),
    "Entropy Spread σH": round(sigma_H, 3),
    "Throughput / WIP Ratio": round(T / W if W > 0 else 0, 3)
}])

st.subheader("📊 Table A: Global System Diagnostics")
st.dataframe(table_A, use_container_width=True)
