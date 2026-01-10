import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(page_title="Dice Simulation Platform", layout="wide")

# --- User Database Simulation ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {}

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

# --- Authentication Gateway ---
def auth_gateway():
    st.title("🔐 Production Simulation Gateway")
    auth_mode = st.radio("Select Mode:", ["Login", "Signup"], horizontal=True)

    user_id = st.text_input("User ID (Unique Username)")
    pwd = st.text_input("Password", type="password")

    if auth_mode == "Signup":
        if st.button("Create Account"):
            if user_id in st.session_state.user_db:
                st.error("User ID already exists.")
            elif user_id and pwd:
                st.session_state.user_db[user_id] = {
                    "password": pwd,
                    "history": [],
                    "stations": [],
                    "wip_avg": []
                }
                st.success("Account created.")
            else:
                st.warning("Empty fields.")

    if auth_mode == "Login":
        if st.button("Sign In"):
            if user_id in st.session_state.user_db and \
               st.session_state.user_db[user_id]["password"] == pwd:
                st.session_state.authenticated_user = user_id
                st.rerun()
            else:
                st.error("Invalid credentials.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

# --- Current User ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# --- Sidebar ---
st.sidebar.header(f"👤 Active: {current_user}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Workstations", min_value=2, value=8)
num_days = st.sidebar.number_input("Days", min_value=1, value=1000)

members = [chr(64 + i) for i in range(1, num_members + 1)]
dice_configs = {m: st.sidebar.slider(f"Dice {m}", 1, 20, (1, 6)) for m in members}

wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members)-1)]
initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys}

def entropy(x):
    if not x: return 0
    v, c = np.unique(x, return_counts=True)
    p = c / c.sum()
    return -np.sum(p * np.log2(p))

tab1, tab2, tab3 = st.tabs(["🚀 Live Console", "📊 Analytics", "📖 Methodology"])

# =======================
# TAB 1: SIMULATION
# =======================
with tab1:
    if st.sidebar.button("▶ Run & Save Simulation"):

        scen_id = len(user_record["history"]) + 1
        scen_label = f"Scenario #{scen_id}"

        wip_buffers = initial_wip.copy()
        st_wip_trend = defaultdict(list)
        st_output = defaultdict(list)
        history = []
        total_fg = 0

        for day in range(1, num_days + 1):
            daily_fg = 0
            for i, m in enumerate(members):
                roll = np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1)

                if i == 0:
                    wip_buffers[f"WIP_{members[i]}{members[i+1]}"] += roll
                    st_output[m].append(roll)

                elif i == len(members) - 1:
                    prev = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prev])
                    wip_buffers[prev] -= move
                    daily_fg = move
                    total_fg += move
                    st_output[m].append(move)

                else:
                    prev = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prev])
                    wip_buffers[prev] -= move
                    wip_buffers[nxt] += move
                    st_output[m].append(move)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({
                "Day": day,
                "Daily_Total_WIP": sum(wip_buffers.values()),
                "Daily FG": daily_fg
            })

        df = pd.DataFrame(history)
        avg_tr = total_fg / num_days

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days": num_days,
            "Total Finished Goods": total_fg,
            "Throughput Rate (TR)": round(avg_tr, 2)
        })

        # ---- Store Station Diagnostics (Table B)
        for stn, wip_list in st_wip_trend.items():
            user_record["stations"].append({
                "Scenario": scen_label,
                "Station": f"Station {stn}",
                "Tot Output": sum(wip_list),
                "Avg WIP": round(np.mean(wip_list), 2),
                "Entropy Hi": round(entropy(wip_list), 3),
                "Interpretation": "Variable" if entropy(wip_list) >= 2.4 else "Stable"
            })

            # ---- Store Scenario-wise WIP for Table C
            user_record["wip_avg"].append({
                "Scenario": scen_label,
                "Station": f"Station {stn}",
                "Total WIP": sum(wip_list),
                "Days": num_days
            })

# =======================
# TAB 2: ANALYTICS
# =======================
with tab2:
    if user_record["history"]:

        # -------- TABLE A --------
        df_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        st.subheader("Table A: Summary History")
        st.table(df_a)

        # -------- TABLE B --------
        s_df = pd.DataFrame(user_record["stations"])
        metrics = ["Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        rows = []

        for scen in s_df["Scenario"].unique():
            for m in metrics:
                row = {"Scenario": scen, "Metric": m}
                for stn in s_df["Station"].unique():
                    val = s_df[(s_df["Scenario"] == scen) & (s_df["Station"] == stn)]
                    row[stn] = val[m].values[0] if not val.empty else ""
                rows.append(row)

        df_b = pd.DataFrame(rows).set_index(["Scenario", "Metric"])
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        st.table(df_b)

        # -------- TABLE C (SCENARIO-WISE) --------
        st.markdown("---")
        st.subheader("Table C: Station-wise Average WIP (Day / Week / Month)")

        w_df = pd.DataFrame(user_record["wip_avg"])
        rows = []

        for scen in w_df["Scenario"].unique():
            scen_df = w_df[w_df["Scenario"] == scen]
            days = scen_df["Days"].iloc[0]
            weeks = max(1, days // 5)
            months = max(1, days // 20)

            for _, r in scen_df.iterrows():
                rows.append({
                    "Scenario": scen,
                    "Station": r["Station"],
                    "Day-wise Avg WIP": round(r["Total WIP"] / days, 2),
                    "Week-wise Avg WIP": round(r["Total WIP"] / weeks, 2),
                    "Month-wise Avg WIP": round(r["Total WIP"] / months, 2)
                })

        df_c = pd.DataFrame(rows).set_index(["Scenario", "Station"])
        st.table(df_c)

    else:
        st.info("No data available.")

# =======================
# TAB 3: METHODOLOGY
# =======================
with tab3:
    st.title("📖 Simulation Methodology")
    st.markdown("Scenario-based TOC Dice Game with dependency and variability.")
