import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# -----------------------------------
# Page Configuration
# -----------------------------------
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# Initialize Session States
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'scenario_history' not in st.session_state:
    st.session_state.scenario_history = []
if 'station_history' not in st.session_state:
    st.session_state.station_history = []

# 1. Login Screen
if not st.session_state.user_name:
    st.title("🔐 Access Production Simulation")
    name_input = st.text_input("Enter your name to start recording:")
    if st.button("Start Session"):
        if name_input:
            st.session_state.user_name = name_input
            st.rerun()
    st.stop()

# -----------------------------------
# Sidebar: Settings
# -----------------------------------
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Number of Workstations", min_value=2, value=7, step=1)
num_days = st.sidebar.number_input("Number of Days", min_value=1, value=20, step=1)

members = [chr(65 + i) for i in range(num_members)]

st.sidebar.subheader("Dice Range per Member")
dice_configs = {}
for m in members:
    low, high = st.sidebar.slider(f"Dice range for {m}", 1, 20, (1, 6))
    dice_configs[m] = (low, high)

st.sidebar.subheader("Initial WIP Buffers")
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {}
for key in wip_keys:
    initial_wip[key] = st.sidebar.number_input(f"{key}", min_value=0, value=4, step=1)

def entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# -----------------------------------
# Navigation Tabs
# -----------------------------------
tab1, tab2 = st.tabs(["🚀 Active Simulation", "📊 Global System Diagnostics"])

with tab1:
    st.title("🎲 Active Simulation")
    
    # NEW: Display Pre-Day 1 Configuration
    st.subheader("📋 Pre-Day 1 Configuration")
    config_cols = st.columns(len(members))
    for idx, m in enumerate(members):
        with config_cols[idx]:
            st.metric(f"Member {m}", f"{dice_configs[m][0]}-{dice_configs[m][1]}", "Dice Range")
    
    pre_wip_df = pd.DataFrame([initial_wip], index=["Initial Set"])
    st.write("**Starting WIP Levels:**")
    st.dataframe(pre_wip_df, use_container_width=True)

    if st.sidebar.button("▶ Run Simulation & Record"):
        dice_data = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_data)
        df_dice.index += 1

        wip_buffers = initial_wip.copy()
        history = []
        total_finished_goods = 0
        station_output = defaultdict(list)
        station_wip_history = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg = 0
            for i, m in enumerate(members):
                roll = day_rolls[m]
                if i == 0:
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += roll
                    station_output[m].append(roll)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    daily_fg = move
                    total_finished_goods += move
                    station_output[m].append(move)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    wip_buffers[nxt] += move
                    station_output[m].append(move)

            for key, val in wip_buffers.items():
                pair = key.split("_")[1]
                station_wip_history[pair].append(val)

            rec = {"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values()), "Daily_FG": daily_fg}
            history.append(rec)

        results_df = pd.DataFrame(history).set_index("Day")
        
        # Calculate Labels
        scen_count = len(st.session_state.scenario_history)
        scen_label = "Base-4" if scen_count == 0 else f"Scenario #{scen_count}"
        
        # Metrics
        t_put = total_finished_goods / num_days
        avg_wip_total = results_df["Daily_Total_WIP"].mean()
        station_entropies = [entropy(station_output[m]) for m in members]

        # CURRENT SCENARIO SUMMARY
        st.markdown("---")
        st.subheader(f"🏁 Current Results: {scen_label}")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Finished Goods", int(total_finished_goods))
        m_col2.metric("Mean Throughput (T)", round(t_put, 2))
        m_col3.metric("Avg Total WIP (W)", round(avg_wip_total, 2))

        # GRAPHS
        st.subheader("📈 Performance Trends")
        st.line_chart(results_df[["Daily_Total_WIP", "Daily_FG"]])
        

        st.subheader("🎲 Daily Activity Log")
        st.dataframe(results_df, use_container_width=True)

        # Save History
        st.session_state.scenario_history.append({
            "Scenarios": scen_label,
            "Initial WIP": f"WIP={list(initial_wip.values())[0]}, Range {dice_configs['A'][0]}-{dice_configs['A'][1]}",
            "Total Finished Goods": int(total_finished_goods),
            "Mean Throughput (T)": round(t_put, 2),
            "Total WIP (W)": round(avg_wip_total, 2),
            "Lead Time (L)": round(avg_wip_total/t_put, 2) if t_put > 0 else 0,
            "Avg Entropy Ḣ": round(np.mean(station_entropies), 3),
            "Entropy Spread σH": round(np.std(station_entropies), 3)
        })

        for m in members:
            current_pair = next((k.split("_")[1] for k in wip_keys if k.endswith(m)), m)
            avg_station_wip = np.mean(station_wip_history[current_pair]) if current_pair in station_wip_history else 0
            st.session_state.station_history.append({
                "Scenario": scen_label,
                "Station": f"Station {current_pair}",
                "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(station_output[m]),
                "Avg WIP": round(avg_station_wip, 2),
                "Entropy Hi": round(entropy(station_output[m]), 3),
                "Interpretation": "High Var" if entropy(station_output[m]) > 2 else "Bottleneck" if avg_station_wip > 8 else "Stable"
            })

with tab2:
    st.subheader("📊 Table A: Global System Diagnostics")
    if st.session_state.scenario_history:
        st.table(pd.DataFrame(st.session_state.scenario_history).set_index("Scenarios"))
        
        st.markdown("---")
        st.subheader("📊 Table B: Station-Level Flow Diagnostics")
        
        if st.session_state.station_history:
            s_df = pd.DataFrame(st.session_state.station_history)
            metrics = ["Dice Range", "Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
            all_labels = s_df['Station'].unique()

            # MERGING ROWS LOGIC: Grouping by Scenario
            rows = []
            for scen in s_df['Scenario'].unique():
                for i, metric in enumerate(metrics):
                    row_data = {}
                    # Only show scenario name on the first metric row to simulate merging
                    row_data["Scenario"] = scen if i == 0 else "" 
                    row_data["Metric"] = metric
                    for s_label in all_labels:
                        filtered = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                        row_data[s_label] = filtered[metric].values[0] if not filtered.empty else ""
                    rows.append(row_data)
            
            st.table(pd.DataFrame(rows).set_index(["Scenario", "Metric"]))
            

if st.button("Reset Data"):
    st.session_state.scenario_history = []
    st.session_state.station_history = []
    st.rerun()
