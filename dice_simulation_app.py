import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import math

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
        min_value=0,   # Changed: Allows any value from 0 up
        value=4,       # Default starting value is 4
        step=1
    )

# -----------------------------------
# Helper: Entropy Function
# -----------------------------------
def entropy(values):
    if len(values) == 0:
        return 0
    values = np.array(values)
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------------
# Run Simulation
# -----------------------------------
if st.sidebar.button("▶ Run Simulation"):

    # 1. Generate Dice Rolls
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

    # 2. Simulation Logic
    wip_buffers = initial_wip.copy()
    history = []
    total_finished_goods = 0
    
    # Track outputs for Entropy
    station_output = defaultdict(list)
    station_wip_history = defaultdict(list)

    for day in df_dice.index:
        day_rolls = df_dice.loc[day]
        daily_fg = 0

        for i, m in enumerate(members):
            roll = day_rolls[m]

            if i == 0:
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                wip_buffers[next_wip] += roll
                station_output[m].append(roll) # Record output

            elif i == len(members) - 1:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                daily_fg = move_amount
                total_finished_goods += move_amount
                station_output[m].append(move_amount) # Record output

            else:
                prev_wip = f"WIP_{members[i-1]}{members[i]}"
                next_wip = f"WIP_{members[i]}{members[i+1]}"
                move_amount = min(roll, wip_buffers[prev_wip])
                wip_buffers[prev_wip] -= move_amount
                wip_buffers[next_wip] += move_amount
                station_output[m].append(move_amount) # Record output

        # Record WIP for Entropy/Diagnostics
        for key, val in wip_buffers.items():
            station_code = key.split("_")[1][0] # Station receiving the WIP
            station_wip_history[station_code].append(val)

        daily_record = {"Day": day}
        daily_record.update(wip_buffers.copy())
        daily_record["Daily_Total_WIP"] = sum(wip_buffers.values())
        daily_record["Daily_FG"] = daily_fg
        history.append(daily_record)

    # 3. Results Table
    results_df = pd.DataFrame(history).set_index("Day")

    st.subheader("📊 Simulation Results")
    st.dataframe(results_df, use_container_width=True)

    # 4. KPIs
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Finished Goods", total_finished_goods)
    col2.metric("Average Daily FG", round(results_df["Daily_FG"].mean(), 2))
    col3.metric("Average Total WIP", round(results_df["Daily_Total_WIP"].mean(), 2))

    # 5. Charts
    st.subheader("📈 Performance Trends")
    st.line_chart(results_df[["Daily_Total_WIP", "Daily_FG"]])

# 6. TABLE B: STATION-LEVEL FLOW DIAGNOSTICS
    table_b_rows = []
    
    # We loop through the wip_keys (like WIP_AB, WIP_BC) to get the station pairs
    for key in wip_keys:
        # Extract the station names from the key (e.g., "WIP_AB" -> "AB")
        station_pair = key.split("_")[1] 
        
        # For diagnostics, we look at the station receiving the inventory (the second letter)
        receiving_station = station_pair[1]
        
        outputs = station_output[receiving_station]
        wips = station_wip_history[receiving_station]
        
        avg_wip = np.mean(wips) if wips else 0
        H_i = entropy(outputs)

        if H_i > 2:
            interpretation = "High variability"
        elif avg_wip > (sum(initial_wip.values()) / len(members)):
            interpretation = "Bottleneck"
        else:
            interpretation = "Stable"

        table_b_rows.append({
            "Station Pair": station_pair, # This will now show AB, BC, CD, etc.
            "Total Output": sum(outputs),
            "Avg WIP": round(avg_wip, 2),
            "Entropy Hᵢ": round(H_i, 3),
            "Interpretation": interpretation
        })

    table_B = pd.DataFrame(table_b_rows)
    st.subheader("📊 Table B: Station-Level Flow Diagnostics")
    st.dataframe(table_B, use_container_width=True)

    # 7. TABLE A: GLOBAL SYSTEM DIAGNOSTICS
    T = total_finished_goods / num_days
    W = results_df["Daily_Total_WIP"].mean()
    L = W / T if T > 0 else 0

    table_A = pd.DataFrame([{
        "Initial WIP": sum(initial_wip.values()),
        "Mean Throughput (T)": round(T, 3),
        "Total Avg WIP (W)": round(W, 2),
        "Lead Time (L = W / T)": round(L, 3),
        "Throughput / WIP Ratio": round(T / W if W > 0 else 0, 3)
    }])

    st.subheader("📊 Table A: Global System Diagnostics")
    st.dataframe(table_A, use_container_width=True)

