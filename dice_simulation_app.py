import streamlit as st
import pandas as pd
import numpy as np
import math
from collections import defaultdict

st.set_page_config(page_title="Dice Simulation with Entropy", layout="wide")

st.title("🎲 Dice-Based Production Simulation with Entropy Diagnostics")

# -----------------------------
# SIDEBAR INPUTS
# -----------------------------
st.sidebar.header("Simulation Settings")

num_members = st.sidebar.number_input("Number of Stations", min_value=2, value=4)
num_days = st.sidebar.number_input("Number of Cycles (Days)", min_value=1, value=1000)

members = [chr(65 + i) for i in range(num_members)]

st.sidebar.subheader("Dice Ranges (Capacity)")
dice_configs = {}
for m in members:
    low = st.sidebar.number_input(f"{m} Min", value=1)
    high = st.sidebar.number_input(f"{m} Max", value=6)
    dice_configs[m] = (low, high)

st.sidebar.subheader("Initial WIP")
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members)-1)]
wip_buffers = {}
for key in wip_keys:
    wip_buffers[key] = st.sidebar.number_input(key, value=4)

initial_wip_value = sum(wip_buffers.values())

run = st.sidebar.button("▶ Run Simulation")

# -----------------------------
# ENTROPY FUNCTION
# -----------------------------
def entropy(values):
    if len(values) == 0:
        return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------
# RUN SIMULATION
# -----------------------------
if run:
    dice_data = {
        m: np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1, num_days)
        for m in members
    }
    df_dice = pd.DataFrame(dice_data)

    station_output = defaultdict(list)
    station_wip = defaultdict(list)

    total_finished_goods = 0

    for day in range(num_days):
        for i, m in enumerate(members):
            roll = df_dice.loc[day, m]

            if i == 0:
                wip_buffers[f"WIP_{members[i]}{members[i+1]}"] += roll
                station_output[m].append(roll)

            elif i == len(members) - 1:
                prev = f"WIP_{members[i-1]}{members[i]}"
                move = min(roll, wip_buffers[prev])
                wip_buffers[prev] -= move
                station_output[m].append(move)
                total_finished_goods += move

            else:
                prev = f"WIP_{members[i-1]}{members[i]}"
                nxt = f"WIP_{members[i]}{members[i+1]}"
                move = min(roll, wip_buffers[prev])
                wip_buffers[prev] -= move
                wip_buffers[nxt] += move
                station_output[m].append(move)

        for key in wip_buffers:
            station = key.split("_")[1][0]
            station_wip[station].append(wip_buffers[key])

    # -----------------------------
    # TABLE B: STATION-LEVEL
    # -----------------------------
    station_rows = []
    for s in members:
        outputs = station_output[s]
        wips = station_wip[s]

        total_output = sum(outputs)
        avg_wip = np.mean(wips) if wips else 0
        H_i = entropy(outputs)

        if H_i > 2:
            interp = "High variability"
        elif avg_wip > np.mean([np.mean(v) for v in station_wip.values()]):
            interp = "Congested"
        else:
            interp = "Stable"

        station_rows.append({
            "Station": s,
            "Total Output": total_output,
            "Avg WIP": round(avg_wip, 2),
            "Entropy Hᵢ": round(H_i, 3),
            "Interpretation": interp
        })

    table_B = pd.DataFrame(station_rows)

    # -----------------------------
    # TABLE A: GLOBAL DIAGNOSTICS
    # -----------------------------
    T = total_finished_goods / num_days
    W = sum(wip_buffers.values())
    L = W / T if T > 0 else 0

    entropies = table_B["Entropy Hᵢ"].values
    H_bar = np.mean(entropies)
    sigma_H = np.std(entropies)

    table_A = pd.DataFrame([{
        "Initial WIP": initial_wip_value,
        "Mean Throughput (T)": round(T, 3),
        "Total WIP (W)": W,
        "Lead Time (L = W/T)": round(L, 3),
        "Avg Entropy H̄": round(H_bar, 3),
        "Entropy Spread σH": round(sigma_H, 3),
        "Throughput / WIP Ratio": round(T / W if W > 0 else 0, 3)
    }])

    # -----------------------------
    # DISPLAY RESULTS
    # -----------------------------
    st.subheader("📊 Table A: Global System Diagnostics")
    st.dataframe(table_A)

    st.subheader("📊 Table B: Station-Level Flow Diagnostics")
    st.dataframe(table_B)

    st.success("Simulation completed successfully!")
