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
        st.info("Your User ID must be unique. You can only sign up once.")
        if st.button("Create Account"):
            if user_id in st.session_state.user_db:
                st.error(f"User ID '{user_id}' is already taken.")
            elif user_id and pwd:
                st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                st.success("Account created! Please switch to Login mode.")
            else:
                st.warning("Fields cannot be empty.")
                
    elif auth_mode == "Login":
        if st.button("Sign In"):
            if user_id in st.session_state.user_db:
                if st.session_state.user_db[user_id]["password"] == pwd:
                    st.session_state.authenticated_user = user_id
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            else:
                st.error("User ID not found.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

# --- Access Current User's Data ---
current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

# --- Sidebar: User Controls ---
st.sidebar.header(f"👤 Active: {current_user}")
if st.sidebar.button("🚪 Logout & Exit"):
    st.session_state.authenticated_user = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Data Management")
if st.sidebar.button("🗑️ Clear Whole History"):
    user_record["history"] = []
    user_record["stations"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Simulation Settings")
num_members = st.sidebar.number_input("Workstations", min_value=2, value=8)
num_days = st.sidebar.number_input("Days", min_value=1, value=1000)

members = [chr(64 + i) for i in range(1, num_members + 1)]
dice_configs = {m: st.sidebar.slider(f"Dice for {m}", 1, 20, (1, 6)) for m in members}
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]
initial_wip = {k: st.sidebar.number_input(k, min_value=0, value=4) for k in wip_keys}

def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

# --- Application Tabs ---
tab1, tab2, tab3 = st.tabs(["🚀 Live Operations Console", "📊 Strategic Performance Analytics", "📖 Methodology & Logic"])

# --- TAB 1: LIVE OPERATIONS ---
with tab1:
    st.title("🚀 Live Operations Console")
    
    if st.sidebar.button("▶ Run & Save Simulation"):
        dice_rolls = {m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members}
        df_dice = pd.DataFrame(dice_rolls)
        df_dice.index = range(1, num_days + 1)
        df_dice.index.name = "Day"

        wip_buffers = initial_wip.copy()
        history = []
        total_fg = 0
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            for i, m in enumerate(members):
                roll = day_rolls[m]
                if i == 0:
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += roll
                    st_output[m].append(roll)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    daily_fg_out = move
                    total_fg += move
                    st_output[m].append(move)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move
                    wip_buffers[nxt] += move
                    st_output[m].append(move)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({"Day": day, **wip_buffers.copy(), "Daily_Total_WIP": sum(wip_buffers.values()), "Day Wise Total FG": daily_fg_out})

        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative FG"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())

        st.subheader("🎲 Table of Dice Rolls (Capacity)")
        st.dataframe(df_dice, use_container_width=True)

        st.subheader("📦 Work-In-Progress (WIP) History")
        st.dataframe(results_df, use_container_width=True)

        scen_id = len(user_record["history"]) + 1
        st.subheader(f"🏁 Scenario #{scen_id} Results")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Finished Goods", int(total_fg))
        c2.metric("Throughput (T)", round(total_fg / num_days, 2))
        c3.metric("Total WIP (Sum)", sum_total_wip)

        # Logging Logic
        scen_label = f"Scenario #{scen_id}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}={v}" for k, v in initial_wip.items()])
        dice_info = ", ".join([f"{m}:{dice_configs[m][0]}-{dice_configs[m][1]}" for m in members])
        
        throughput = total_fg / num_days
        lead_time = sum_total_wip / throughput if throughput > 0 else 0
        
        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": f"Days={num_days} | {wip_summary} | {dice_info}",
            "Total Finished Goods": int(total_fg),
            "Mean Throughput (T)": round(throughput, 2),
            "Total WIP (W)": sum_total_wip,
            "Lead Time (L = W / T)": round(lead_time, 2),
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 3),
            "Efficiency Score": round(throughput / lead_time, 4) if lead_time > 0 else 0
        })

        for m in members:
            pair = next((k.replace("WIP_", "") for k in wip_keys if k.endswith(m)), m)
            if pair == "A": continue
            h_val = calculate_entropy(st_output[m])
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {pair}", "Dice Range": f"{dice_configs[m][0]}-{dice_configs[m][1]}",
                "Tot Output": sum(st_output[m]), "Avg WIP": round(np.mean(st_wip_trend[pair]), 2) if pair in st_wip_trend else 0,
                "Entropy Hi": round(h_val, 3), "Interpretation": "Variable" if h_val > 2.4 else "Stable"
            })
        st.rerun()

# --- TAB 2: PERFORMANCE ANALYTICS ---
with tab2:
    st.title("📊 Strategic Performance Analytics")
    if user_record["history"]:
        # 1. Executive Leaderboard
        st.subheader("🏆 Scenario Leaderboard")
        summary_df = pd.DataFrame(user_record["history"])
        ranked_df = summary_df.sort_values(by='Efficiency Score', ascending=False).reset_index(drop=True)
        st.success(f"🥇 **Best Performing Setup:** {ranked_df.iloc[0]['Scenarios']} (Score: {ranked_df.iloc[0]['Efficiency Score']})")
        st.dataframe(ranked_df[['Scenarios', 'Total Finished Goods', 'Lead Time (L = W / T)', 'Efficiency Score']], use_container_width=True)

        # 2. Heatmap Table B
        st.markdown("---")
        st.subheader("🌡️ Station-Level Flow Heatmap")
        s_df = pd.DataFrame(user_record["stations"])
        
        def color_variability(val):
            if isinstance(val, (int, float)) and val > 2.4: return 'background-color: #ff4b4b; color: white'
            return ''

        metrics = ["Dice Range", "Tot Output", "Avg WIP", "Entropy Hi", "Interpretation"]
        rows = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty else ""
                rows.append(row_data)
        
        df_table_b = pd.DataFrame(rows).set_index(["Scenario", "Metric"])
        st.table(df_table_b.style.applymap(color_variability, subset=pd.IndexSlice[pd.Slice(None), "Entropy Hi"], axis=0))

# --- TAB 3: METHODOLOGY & BOTTLENECK ---
with tab3:
    st.title("📖 Simulation Methodology & Logic")
    
    st.header("🔄 The Logic of Flow")
    st.markdown("This simulation models **Statistical Fluctuations** and **Dependent Events**.")
    
    st.latex(r"\text{Movement}_{B} = \min(\text{Dice Roll}_{B}, \text{Buffer}_{A \to B})")

    st.header("📊 Key Formulas")
    c1, c2 = st.columns(2)
    with c1:
        st.latex(r"T = \frac{\sum FG}{Days}")
        st.latex(r"L = \frac{\text{Total WIP}}{T}")
    with c2:
        st.latex(r"H = -\sum P(x) \log_2 P(x)")
        st.write("**Entropy** identifies where variability is killing your flow.")

    st.markdown("---")
    st.header("🛠️ Bottleneck Diagnostic Tool")
    if user_record["stations"]:
        s_df = pd.DataFrame(user_record["stations"])
        latest_scen = s_df['Scenario'].iloc[-1]
        current_scen_df = s_df[s_df['Scenario'] == latest_scen]
        
        bn_row = current_scen_df.loc[current_scen_df['Avg WIP'].idxmax()]
        st.error(f"🚨 **Detected Bottleneck:** {bn_row['Station']} (Avg WIP: {bn_row['Avg WIP']})")
        

        st.subheader("🧪 Buffer Stock Recommender")
        target_st = st.selectbox("Select Station to Analyze:", current_scen_df['Station'].unique())
        st_val = current_scen_df[current_scen_df['Station'] == target_st].iloc[0]
        
        d_min, d_max = map(int, st_val['Dice Range'].split('-'))
        safety_stock = round((d_max - d_min) * st_val['Entropy Hi'], 1)
        st.info(f"To protect **{target_st}** from upstream starvation, set Initial WIP to **{safety_stock}** units.")
    else:
        st.info("Run a simulation to unlock diagnostic tools.")
