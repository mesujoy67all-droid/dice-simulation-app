import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io

# --- Page Configuration ---
st.set_page_config(
    page_title="Operations & Flow Dynamics Simulation Platform", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- CSS Styling: Academic / Institutional Theme ---
st.markdown("""
    <style>
    /* ===================== Design tokens ===================== */
    :root {
        --ink: #1A2742;
        --ink-soft: #3A4459;
        --muted: #5C6478;
        --bg: #FAF9F6;
        --surface: #FFFFFF;
        --surface-alt: #F3F0E8;
        --accent: #A8842C;
        --accent-soft: #F4ECD8;
        --border: #E3DFD3;
        --success: #2F6F4F;
        --success-bg: #EAF2EC;
        --warn: #9B6B16;
        --warn-bg: #FBF1DF;
        --danger: #9B3B3B;
        --danger-bg: #F8EBEB;
    }

    /* ===================== Layout & base type ===================== */
    .main .block-container { padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1340px; }
    h1, h2, h3, h4 { font-family: 'Source Serif 4', Georgia, serif !important; color: var(--ink) !important; letter-spacing: -0.01em; }
    h1 { font-weight: 700 !important; font-size: 1.6rem !important; }
    h2 { font-weight: 600 !important; font-size: 1.25rem !important; }
    h3 { font-weight: 600 !important; font-size: 1.05rem !important; }
    h4 { font-weight: 600 !important; font-size: 0.95rem !important; }
    p, li, label, .stMarkdown { color: var(--ink-soft); }
    hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.75rem 0 !important; }

    /* Eyebrow + section header component */
    .section-eyebrow {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--accent);
        display: block;
        margin-bottom: 0.3rem;
    }
    .section-head { margin: 0.4rem 0 1.1rem 0; }
    .section-head h2, .section-head h3 { margin: 0 !important; }

    /* ===================== Metric tiles ===================== */
    div[data-testid="stMetric"] {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 3px solid var(--accent);
        border-radius: 10px;
        padding: 1.1rem 1.3rem 0.9rem 1.3rem;
    }
    div[data-testid="stMetricValue"] { font-family: 'Source Serif 4', serif; font-size: 2.1rem; font-weight: 700; color: var(--ink); }
    div[data-testid="stMetricLabel"] { font-family: 'IBM Plex Mono', monospace; font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); }

    /* ===================== Tabs ===================== */
    .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { font-family: 'Source Serif 4', serif; font-size: 1.05rem; font-weight: 600; padding: 10px 22px; color: var(--muted); }

    /* ===================== Sidebar ===================== */
    section[data-testid="stSidebar"] { background: var(--surface-alt); border-right: 1px solid var(--border); }
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--ink) !important;
        background: transparent !important;
        border-bottom: 2px solid var(--accent);
        padding-bottom: 0.4rem;
    }

    /* Nuke any red/coral Streamlit theme bleed on sidebar headers */
    section[data-testid="stSidebar"] [data-testid="stHeadingWithActionElements"],
    section[data-testid="stSidebar"] [data-testid="stHeadingWithActionElements"] * {
        background: transparent !important;
        background-color: transparent !important;
    }
    .session-badge {
        background: var(--ink);
        color: #FAF9F6;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        padding: 0.7rem 0.8rem;
        border-radius: 6px;
        text-align: center;
        border-left: 3px solid var(--accent);
    }

    /* ===================== Auth gateway ===================== */
    .auth-card { background: var(--surface); border: 1px solid var(--border); border-top: 3px solid var(--accent); padding: 2.75rem; border-radius: 12px; box-shadow: 0 10px 28px -16px rgba(26,39,66,0.25); }

    /* ===================== Alerts ===================== */
    div[data-testid="stAlert"] { border-radius: 8px; border: 1px solid var(--border); }

    /* ===================== Buttons ===================== */
    .stButton button, .stDownloadButton button { border-radius: 8px !important; font-weight: 600 !important; }

    /* ALL primary buttons: light cream bg, navy text, gold border — no red ever */
    .stButton button[kind="primary"] {
        background-color: var(--accent-soft) !important;
        border: 2px solid var(--accent) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }
    .stButton button[kind="primary"]:hover {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #FFFFFF !important;
    }

    /* Sidebar secondary buttons: white bg, dark text */
    section[data-testid="stSidebar"] .stButton button {
        background-color: #FFFFFF !important;
        border: 1.5px solid var(--border) !important;
        color: var(--ink) !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.82rem !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background-color: var(--accent-soft) !important;
        border-color: var(--accent) !important;
        color: var(--ink) !important;
    }
    /* Sidebar primary (Run) button: light cream, gold border */
    section[data-testid="stSidebar"] .stButton button[kind="primary"] {
        background-color: var(--accent-soft) !important;
        border: 2px solid var(--accent) !important;
        color: var(--ink) !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
        color: #FFFFFF !important;
    }

    /* ===================== Tables (Table A / B / C) ===================== */
    div[data-testid="stTable"] table { font-size: 1.05rem; border-collapse: collapse; }
    div[data-testid="stTable"] th {
        font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.04em;
        background: var(--surface-alt); color: var(--ink);
        border-bottom: 2px solid var(--accent);
    }
    div[data-testid="stTable"] td { font-family: 'IBM Plex Mono', monospace; font-size: 1rem; color: var(--ink-soft); border-bottom: 1px solid var(--border); }

    /* ===================== Interactive dataframes ===================== */
    div[data-testid="stDataFrame"] { zoom: 1.3; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }

    /* ===================== Methodology tab: compact headings ===================== */
    .meth-h1 {
        font-family: 'Source Serif 4', Georgia, serif;
        font-size: 1.3rem !important;
        font-weight: 700;
        color: var(--ink);
        margin: 1.2rem 0 0.4rem 0;
    }
    .meth-h2 {
        font-family: 'Source Serif 4', Georgia, serif;
        font-size: 1.05rem !important;
        font-weight: 600;
        color: var(--ink);
        margin: 1rem 0 0.3rem 0;
        border-bottom: 1px solid var(--border);
        padding-bottom: 0.2rem;
    }
    .meth-h3 {
        font-family: 'Source Serif 4', Georgia, serif;
        font-size: 0.92rem !important;
        font-weight: 600;
        color: var(--ink-soft);
        margin: 0.8rem 0 0.2rem 0;
    }

    /* ===================== Optimization tab: star badges ===================== */
    .rec-badge {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
        white-space: nowrap;
    }
    .rec-gold   { background: var(--accent-soft); color: var(--ink); border: 1px solid var(--accent); }
    .rec-fail   { background: var(--danger-bg);   color: var(--danger); border: 1px solid var(--danger); }
    .rec-base   { background: var(--surface-alt); color: var(--muted); border: 1px solid var(--border); }
    </style>
""", unsafe_allow_html=True)

def section_header(eyebrow: str, title: str, level: str = "h3"):
    st.markdown(
        f"<div class='section-head'><span class='section-eyebrow'>{eyebrow}</span>"
        f"<{level} style='margin:0;'>{title}</{level}></div>",
        unsafe_allow_html=True
    )

def meth_h1(text): st.markdown(f"<p class='meth-h1'>{text}</p>", unsafe_allow_html=True)
def meth_h2(text): st.markdown(f"<p class='meth-h2'>{text}</p>", unsafe_allow_html=True)
def meth_h3(text): st.markdown(f"<p class='meth-h3'>{text}</p>", unsafe_allow_html=True)

# --- User Database Simulation ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 

if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None

if 'active_results' not in st.session_state:
    st.session_state.active_results = None

# --- Authentication Gateway ---
def auth_gateway():
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 1rem 0;'>
        <div style='font-size: 4.5rem; line-height: 1; margin-bottom: 0.6rem;'>🎲</div>
        <h1 style='color: #1A2742; margin-bottom: 0.3rem; font-family: Georgia, serif; font-size: 2.4rem; font-weight: 700; letter-spacing: -0.01em;'>
            Dice Simulation Game
        </h1>
        <p style='color: #A8842C; font-size: 1rem; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 0.4rem;'>
            Institutional Executive Simulation Portal
        </p>
        <p style='color: #64748B; font-size: 0.95rem; margin: 0;'>Strategic Operations &amp; Assembly Flow Dynamics Engine</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-bottom: 1.5rem; color: #334155;'>🔐 Secure Access Terminal</h3>", unsafe_allow_html=True)
        
        auth_mode = st.radio("Select Session Objective:", ["Sign In to Account", "Register New Profile"], horizontal=True, label_visibility="collapsed")
        st.markdown("<br>", unsafe_allow_html=True)
        
        user_id = st.text_input("👤 Operator ID / Username", placeholder="Enter unique ID...")
        pwd = st.text_input("🔑 Security Password", type="password", placeholder="Enter password...")
        
        st.markdown("<hr style='margin: 1.5rem 0;'>", unsafe_allow_html=True)
        
        if auth_mode == "Register New Profile":
            st.caption("ℹ️ *Operator IDs are persistent. Please ensure your username is uniquely identifiable.*")
            if st.button("Configure New Account", use_container_width=True, type="secondary"):
                if user_id in st.session_state.user_db:
                    st.error(f"❌ Execution Fault: User ID '{user_id}' is already registered in the database.")
                elif user_id and pwd:
                    st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                    st.success("✅ Profile successfully committed! Please toggle back to 'Sign In' mode to clear the gate.")
                else:
                    st.warning("⚠️ Access Rejected: Credentials cannot contain empty fields.")
                    
        elif auth_mode == "Sign In to Account":
            if st.button("Initialize Executive Session", use_container_width=True, type="primary"):
                if user_id in st.session_state.user_db:
                    if st.session_state.user_db[user_id]["password"] == pwd:
                        st.session_state.authenticated_user = user_id
                        st.session_state.active_results = None
                        st.rerun()
                    else:
                        st.error("❌ Authentication Failed: Cryptographic mismatch for security password.")
                else:
                    st.error("❌ Security Exception: Specified Operator ID was not found.")
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]

history_count = len(user_record["history"])
is_base_run = (history_count == 0)

st.sidebar.markdown(f"<div style='background-color:#1E3A8A; padding:10px; border-radius:6px; color:white; text-align:center; font-weight:bold;'>👤 ACTIVE SESSION: {current_user.upper()}</div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Capacity Input Mode")
capacity_mode = st.sidebar.radio("Choose Capacity Input Mode:", ["Random Generation", "Import Data File (Excel/CSV)"])

uploaded_df = None
num_days = 1500
num_members = st.session_state.get("num_members", 7)
dice_configs = {}
choke_target_station = None
activate_choke_release = False

if capacity_mode == "Random Generation":
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = None

    keep_seed = st.sidebar.toggle("🔒 Lock Environmental Seed", value=False)

    if not keep_seed:
        st.session_state.sim_seed = np.random.randint(0, 1000000)

    st.sidebar.caption(f"Active Deterministic Seed: `{st.session_state.sim_seed}`")
    
    members_list = [chr(64 + i) for i in range(1, 10)]
    
    if not is_base_run:
        st.sidebar.subheader("🚨 Intervention Control Room")
        activate_choke_release = st.sidebar.checkbox("🔓 Relieve Bottleneck ('Release Choke' on A)", value=False)
    if activate_choke_release:
            choke_target_station = st.sidebar.selectbox("Align Station A production capacity to:", [m for m in members_list if m != 'A' and ord(m)-64 <= 9])
            st.sidebar.info(f"Station A will dynamically mirror Station {choke_target_station}'s constraints.")

    if 'num_members' not in st.session_state:
        st.session_state.num_members = 7

    for m in members_list[:st.session_state.num_members]:
        if m == 'A' and activate_choke_release and choke_target_station:
            st.sidebar.caption("Station A Range: *Mirrored from Target*")
            continue
        dice_configs[m] = st.sidebar.slider(f"Dice Range for Workstation {m}", 1, 20, (1, 6))

    num_days = st.sidebar.number_input("Simulation Duration (Days)", min_value=1, value=1500, max_value=3000)
    num_members = st.sidebar.number_input("Active Processing Stations", min_value=2, value=7, max_value=9, key="num_members")

else:
    uploaded_file = st.sidebar.file_uploader("Upload operational 'Table of Dice Rolls' data source", type=["xlsx", "xls", "csv"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                uploaded_df = pd.read_csv(uploaded_file, index_col=0)
            else:
                uploaded_df = pd.read_excel(uploaded_file, index_col=0)
            
            uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            num_days = len(uploaded_df)
            num_members = len(uploaded_df.columns)
            st.sidebar.success(f"📂 Verification Success: {num_days} Days, {num_members} Stations Loaded.")
        except Exception as e:
            st.sidebar.error(f"Error parsing file: {e}. Ensure day counts are structural records.")
            
    if uploaded_df is not None:
        temp_members = [chr(64 + i) for i in range(1, num_members + 1)]
        
        if is_base_run:
            st.sidebar.warning("🔒 Baseline Protection Active: Scenario parameters are locked.")
            for m in temp_members:
                dice_configs[m] = (1, 6)
        else:
            st.sidebar.markdown("---")
            st.sidebar.header("🚀 Scenario Interventions")
            st.sidebar.info(f"Configuring Interactive Scenario Expansion #{history_count}. Adjust parameters below:")
            
            activate_choke_release = st.sidebar.checkbox("🔓 Relieve Bottleneck ('Release Choke' on A)", value=False)
            if activate_choke_release:
                choke_target_station = st.sidebar.selectbox("Align Station A production capacity to:", [m for m in temp_members if m != 'A'])
            
            for m in temp_members:
                if m == 'A' and activate_choke_release:
                    st.sidebar.caption("Station A Range: *Mirrored from Target File Column*")
                    continue
                dice_configs[m] = st.sidebar.slider(f"Operational Range {m}", 1, 20, (1, 6))

members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

st.sidebar.markdown("---")
st.sidebar.header("📦 Line-Stock WIP Initialization")
initial_wip = {k: st.sidebar.number_input(f"Initial Buffer {k.replace('WIP_', '')}", min_value=0, value=4) for k in wip_keys}

st.sidebar.markdown("---")
st.sidebar.header("🚀 Execution Terminal")
run_sim_clicked = st.sidebar.button("▶ Compile & Execute Trial", use_container_width=True, type="primary")

st.sidebar.markdown("---")
st.sidebar.header("🧹 Workspace Maintenance")
clear_history_clicked = st.sidebar.button("🗑️ Purge Historical Logs", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.header("🚪 Session Management")
logout_clicked = st.sidebar.button("🚪 Terminate Session & Exit", use_container_width=True)

if clear_history_clicked:
    user_record["history"] = []
    user_record["stations"] = []
    st.session_state.active_results = None
    st.rerun()

if logout_clicked:
    st.session_state.authenticated_user = None
    st.session_state.active_results = None
    st.rerun()

def calculate_entropy(values):
    if len(values) == 0: return 0
    unique, counts = np.unique(values, return_counts=True)
    p = counts / counts.sum()
    return -np.sum(p * np.log2(p))

if run_sim_clicked:
    if "Import" in capacity_mode and uploaded_df is None:
        st.sidebar.error("Execution Fault: Please upload an analytical capacity CSV/Excel matrix first!")
    else:
        if activate_choke_release and choke_target_station:
            dice_configs['A'] = dice_configs[choke_target_station]

        if capacity_mode == "Random Generation":
            np.random.seed(st.session_state.sim_seed)
            dice_rolls = {}
            
            for m in members:
                if m == 'A' and activate_choke_release and choke_target_station:
                    continue
                dice_rolls[m] = [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)]
            
            if activate_choke_release and choke_target_station:
                dice_rolls['A'] = list(dice_rolls[choke_target_station])
                
            df_dice = pd.DataFrame(dice_rolls)
            df_dice = df_dice.reindex(columns=members)
            df_dice.index = range(1, num_days + 1)
            df_dice.index.name = "Day"
        else:
            df_dice = uploaded_df.copy()
            df_dice.columns = members
            df_dice.index.name = "Day"
            
            if not is_base_run and dice_configs:
                np.random.seed(42) 
                for m in members:
                    if m == 'A' and activate_choke_release:
                        continue
                    low, high = dice_configs[m]
                    if (low != 1) or (high != 6):
                        df_dice[m] = [np.random.randint(low, high + 1) for _ in range(num_days)]
                
                if activate_choke_release and choke_target_station:
                    df_dice['A'] = df_dice[choke_target_station].copy()
                    
            df_dice = df_dice.reindex(columns=members)

        applied_configs_desc = []
        for m in members:
            if m == 'A' and activate_choke_release:
                applied_configs_desc.append(f"A(Choke-Released to {choke_target_station})")
            else:
                applied_configs_desc.append(f"{m}(Range:{dice_configs[m][0]}-{dice_configs[m][1]})")

        dice_info = " | ".join(applied_configs_desc)

        wip_buffers = {k: initial_wip[k] for k in wip_keys}
        history = []
        total_fg = 0
        st_output = defaultdict(list)
        st_wip_trend = defaultdict(list)
        pennies_movement_data = defaultdict(list)

        for day in df_dice.index:
            day_rolls = df_dice.loc[day]
            daily_fg_out = 0
            
            for i, m in enumerate(members):
                roll = day_rolls[m]
                
                if i == 0:
                    move_a = roll
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    wip_buffers[nxt] += move_a
                    st_output[m].append(move_a)
                    pennies_movement_data[m].append(move_a)
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    move_last = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move_last
                    daily_fg_out = move_last
                    total_fg += move_last
                    st_output[m].append(move_last)
                    pennies_movement_data[m].append(move_last)
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    move_mid = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= move_mid
                    wip_buffers[nxt] += move_mid
                    st_output[m].append(move_mid)
                    pennies_movement_data[m].append(move_mid)

            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)

            history.append({
                "Day": day, 
                **wip_buffers.copy(), 
                "Daily_Total_WIP": sum(wip_buffers.values()), 
                "Day Wise Total FG": daily_fg_out
            })

        df_pennies = pd.DataFrame(pennies_movement_data)
        df_pennies = df_pennies.reindex(columns=members)
        df_pennies.index = range(1, num_days + 1)
        df_pennies.index.name = "Day"
        total_output_row = df_pennies.sum().to_frame().T
        total_output_row.index = ["THROUGHPUT"]
        entropy_vals = {m: round(calculate_entropy(pennies_movement_data[m]), 3) for m in members}
        entropy_row = pd.DataFrame([entropy_vals])
        entropy_row.index = ["ENTROPY (H)"]
        df_pennies_final = pd.concat([df_pennies, total_output_row, entropy_row])

        results_df = pd.DataFrame(history).set_index("Day")
        results_df["Cumulative Throughput"] = results_df["Day Wise Total FG"].cumsum()
        sum_total_wip = int(results_df["Daily_Total_WIP"].sum())
        final_wip_inventory = sum(wip_buffers.values())

        scen_label = "Base-Run" if is_base_run else f"Scenario #{history_count}"
        wip_summary = ", ".join([f"{k.replace('WIP_', '')}= {initial_wip[k]}" for k in wip_keys])
        run_description = f"Days={num_days} | Mode={capacity_mode} | WIP: {wip_summary} | Configs: {dice_info}"

        avg_throughput_rate = total_fg / num_days
        avg_total_wip_per_day = sum_total_wip / num_days
        calculated_lead_time = round(avg_total_wip_per_day / avg_throughput_rate, 2) if avg_throughput_rate > 0 else 0

        user_record["history"].append({
            "Scenarios": scen_label,
            "Days, Initial WIP & Dice Range": run_description,
            "Throughput": int(total_fg), 
            "Throughput Rate (TR)": round(avg_throughput_rate, 2),
            "Avg WIP (W_avg)": round(avg_total_wip_per_day, 2),
            "WIP at the End of the Simulation": int(final_wip_inventory),
            "Lead Time (L = Avg WIP / TR)": calculated_lead_time,
            "Avg Entropy Ḣ": round(np.mean([calculate_entropy(st_output[m]) for m in members]), 2),
            "Entropy Spread σH": round(np.std([calculate_entropy(st_output[m]) for m in members]), 2)
        })

        days_per_month = 20
        num_months = int(np.ceil(num_days / days_per_month))
        for m in members:
            station_label = m
            low, high = dice_configs.get(m, (1, 6))
            d_range = f"{low}-{high}"
            if m == 'A' and activate_choke_release:
                d_range = f"Choked ({choke_target_station})"
                
            tot_out = sum(st_output[m])
            avg_wip_val = 0.0
            if m != 'A':
                try:
                    target_key = next(k.replace("WIP_", "") for k in wip_keys if k.endswith(m))
                    avg_wip_val = round(np.mean(st_wip_trend[target_key]), 2)
                except StopIteration:
                    avg_wip_val = 0.0

            monthly_entropies = []
            for i in range(num_months):
                start = i * days_per_month
                end = min((i + 1) * days_per_month, num_days)
                month_data = st_output[m][start:end]
                if len(month_data) > 0:
                    monthly_entropies.append(calculate_entropy(month_data))
            avg_h_monthly = round(np.mean(monthly_entropies), 3) if monthly_entropies else 0.0
            spread_h_monthly = round(np.std(monthly_entropies), 3) if monthly_entropies else 0.0

            user_record["stations"].append({
                "Scenario": scen_label, "Station": station_label, "Dice Range": d_range,
                "Throughput": tot_out, "Avg WIP": avg_wip_val, "Entropy Hi (Monthly Avg)": avg_h_monthly,
                "Entropy Spread σH (Monthly)": spread_h_monthly, "Interpretation": "Variable" if avg_h_monthly > 2.4 else "Stable"
            })

        st.session_state.active_results = {
            "scen_label": scen_label,
            "df_dice": df_dice,
            "df_pennies_final": df_pennies_final,
            "results_df": results_df,
            "total_fg": total_fg,
            "num_days": num_days,
            "final_wip_inventory": final_wip_inventory
        }
        st.rerun()

# --- Application Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Live Operations Console",
    "📊 Strategic Performance Analytics",
    "🎯 Optimization Evaluation",
    "📖 Methodology"
])

with tab1:
    st.markdown("<h2 style='color:#1E3A8A; margin-top:10px;'>🚀 Operational Execution Cockpit</h2>", unsafe_allow_html=True)
    st.write("Monitor plant line behaviors, active structural parameters, and real-time station outputs below.")
    
    if st.session_state.active_results is not None:
        res = st.session_state.active_results

        st.markdown(f"### 🏁 Executive Target Summary ({res['scen_label']})")
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label="Total Throughput Yield", value=f"{int(res['total_fg'])} units", delta=None)
        with m_col2:
            st.metric(label="System Throughput Rate (TR)", value=f"{round(res['total_fg'] / res['num_days'], 2)} units/day", delta=None)
        with m_col3:
            st.metric(label="Terminating WIP Stockpile", value=f"{int(res['final_wip_inventory'])} units", delta=None)
        
        st.markdown("<hr>", unsafe_allow_html=True)

        st.subheader("🎲 Table of Dice Rolls (Capacity Applied)")
        dice_col_config = {col: st.column_config.Column(width="small") for col in res["df_dice"].columns}
        st.dataframe(res["df_dice"], use_container_width=True, column_config=dice_col_config)

        st.subheader("🪙 Day-wise Pennies Movement")
        pennies_col_config = {col: st.column_config.Column(width="small") for col in res["df_pennies_final"].columns}
        st.dataframe(res["df_pennies_final"], use_container_width=True, column_config=pennies_col_config)

        st.subheader("📦 Work-In-Progress (WIP) History")
        wip_col_config = {col: st.column_config.Column(width="small") for col in res["results_df"].columns}
        st.dataframe(res["results_df"], use_container_width=True, column_config=wip_col_config)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📥 Export Live Console Tables")
        st.caption("Download the Dice Rolls, Pennies Movement, and WIP History tables together in a single Excel workbook (one sheet each).")

        live_console_output = io.BytesIO()
        with pd.ExcelWriter(live_console_output, engine='xlsxwriter') as writer:
            res["df_dice"].to_excel(writer, sheet_name='Dice Rolls')
            res["df_pennies_final"].to_excel(writer, sheet_name='Pennies Movement')
            res["results_df"].to_excel(writer, sheet_name='WIP History')
        live_console_excel_data = live_console_output.getvalue()

        st.download_button(
            label="⬇️ Download All Tables (Excel)",
            data=live_console_excel_data,
            file_name=f"Live_Console_{res['scen_label'].replace(' ', '_')}_{current_user}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.markdown("""
            <div style="background-color: #EFF6FF; border-left: 5px solid #3B82F6; padding: 1.5rem; border-radius: 4px; margin-top: 2rem;">
                <h4 style="color: #1E40AF; margin-top:0;">💡 Terminal Ready for Simulation Run</h4>
                <p style="color: #1E3A8A; margin-bottom:0;">Configure initial parameters, distribution capacity limits, and buffer sizing targets inside the executive sidebar panel. Click <strong>Run & Save Simulation</strong> to plot current platform analytical data streams.</p>
            </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("<h2 style='color:#1E3A8A; margin-top:10px;'>📊 Strategic Performance Analytics</h2>", unsafe_allow_html=True)
    st.write("Compare cross-run scenarios, audit workflow variation variances, and map structural information.")
    
    if user_record["history"]:
        df_table_a = pd.DataFrame(user_record["history"]).set_index("Scenarios")
        s_df = pd.DataFrame(user_record["stations"])

        st.subheader("Table A: Summary History")
        st.table(df_table_a)
        
        st.markdown("---")
        st.subheader("Table B: Station-Level Flow Diagnostics")
        
        metrics_to_show = ["Dice Range", "Throughput", "Avg WIP", "Entropy Hi (Monthly Avg)", "Entropy Spread σH (Monthly)", "Interpretation"]
        rows_b = []
        for scen in s_df['Scenario'].unique():
            for i, metric in enumerate(metrics_to_show):
                row_data = {"Scenario": scen if i == 0 else "", "Metric": metric}
                for s_label in s_df['Station'].unique():
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == s_label)]
                    row_data[s_label] = subset[metric].values[0] if not subset.empty and metric in subset.columns else "N/A"
                rows_b.append(row_data)
        
        if rows_b:
            df_table_b = pd.DataFrame(rows_b).set_index(["Scenario", "Metric"])
            st.table(df_table_b)
            
        st.markdown("---")
        st.subheader("Table C: Temporal WIP Averages (By Buffer)")
        all_recorded_stations = s_df['Station'].unique()
        recorded_letters = sorted([s for s in all_recorded_stations])
        buffer_labels = [f"{recorded_letters[i]}{recorded_letters[i+1]}" for i in range(len(recorded_letters) - 1)]

        rows_c = []
        for scen in s_df['Scenario'].unique():
            for period in ["Day-wise Avg WIP", "Week-wise Avg WIP", "Month-wise Avg WIP"]:
                row_data = {"Scenario": scen, "Time Metric": period}
                for b_label in buffer_labels:
                    target_station = b_label[1] 
                    subset = s_df[(s_df['Scenario'] == scen) & (s_df['Station'] == target_station)]
                    if not subset.empty:
                        val = subset["Avg WIP"].values[0]
                        row_data[b_label] = round(val, 2)
                    else:
                        row_data[b_label] = 0.0
                rows_c.append(row_data)

        if rows_c:
            df_table_c = pd.DataFrame(rows_c).set_index(["Scenario", "Time Metric"])
            st.table(df_table_c)
            
        st.markdown("---")
        st.subheader("📥 Export Analytics")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_table_a.to_excel(writer, sheet_name='Summary History')
            df_table_b.reset_index().to_excel(writer, sheet_name='Station Diagnostics', index=False)
            df_table_c.reset_index().to_excel(writer, sheet_name='Temporal WIP', index=False)
        excel_data = output.getvalue()
        st.download_button(label="Download Full Analytics Excel", data=excel_data, file_name=f"Full_Simulation_{current_user}.xlsx")
    else:
        st.info("No recorded history found for this User ID.")

# --- TAB 3: OPTIMIZATION EVALUATION ---
with tab3:
    st.markdown("<h2 style='color:#1E3A8A; margin-top:10px;'>🎯 Optimization Evaluation</h2>", unsafe_allow_html=True)
    st.write(
        "Every scenario is scored against a single learning objective: **achieve at least a 5% increase "
        "in throughput over the Base-Run while changing the fewest possible stations.** This turns the "
        "exercise into a targeting problem — improving the right station(s), not every station."
    )

    if not user_record["history"]:
        st.info("No recorded history yet. Run a **Base-Run** first, then run one or more scenarios to evaluate against the target.")
    else:
        hist_df = pd.DataFrame(user_record["history"])
        stn_df = pd.DataFrame(user_record["stations"])

        base_rows = hist_df[hist_df["Scenarios"] == "Base-Run"]

        if base_rows.empty:
            st.warning("⚠️ No **Base-Run** found. Purge history and run a fresh Base-Run first — every comparison here is measured against it.")
        else:
            base_row = base_rows.iloc[0]
            base_throughput = base_row["Throughput"]
            base_ranges = stn_df[stn_df["Scenario"] == "Base-Run"].set_index("Station")["Dice Range"].to_dict()

            TARGET_GAIN_PCT = 5.0
            TOTAL_STATIONS = len(members)
            base_avg_wip = base_row["Avg WIP (W_avg)"]

            def clamp(x, lo=0.0, hi=100.0):
                return max(lo, min(hi, x))

            eval_rows = []
            for _, row in hist_df.iterrows():
                scen = row["Scenarios"]
                tp = row["Throughput"]
                avg_wip = row["Avg WIP (W_avg)"]
                lead_time = row["Lead Time (L = Avg WIP / TR)"]

                gain_pct = ((tp - base_throughput) / base_throughput * 100) if base_throughput > 0 else 0.0

                scen_ranges = stn_df[stn_df["Scenario"] == scen].set_index("Station")["Dice Range"].to_dict()
                changed_stations = sorted([s for s in scen_ranges if scen_ranges.get(s) != base_ranges.get(s)]) \
                    if scen != "Base-Run" else []
                num_changes = len(changed_stations)

                is_base = (scen == "Base-Run")
                meets_target = (not is_base) and (gain_pct >= TARGET_GAIN_PCT)

                if is_base:
                    tp_score = cap_score = wip_score = total_score = None
                else:
                    # Throughput Score (weight 50): 0 at no gain, 100 once the 5% target is reached.
                    # No bonus past 100 -- overshooting the target isn't rewarded further.
                    tp_score = clamp((gain_pct / TARGET_GAIN_PCT) * 100)

                    # Capacity Score (weight 30): % of stations left untouched. Fewer changes = higher score.
                    cap_score = clamp(100 * (1 - num_changes / TOTAL_STATIONS))

                    # WIP Score (weight 20): centered at 50 (= no change in WIP vs base).
                    # Reducing avg WIP earns bonus points, increasing it costs points.
                    wip_improvement_pct = ((base_avg_wip - avg_wip) / base_avg_wip * 100) if base_avg_wip > 0 else 0.0
                    wip_score = clamp(50 + wip_improvement_pct)

                    total_score = 0.5 * tp_score + 0.3 * cap_score + 0.2 * wip_score

                if is_base:
                    target_flag, badge_class, recommendation = "➖", "rec-base", "Baseline"
                else:
                    target_flag = "✅" if meets_target else "❌"
                    if meets_target:
                        # Quality tiers (⭐ labels) are ONLY ever awarded to scenarios that meet the
                        # 5% target. A failing scenario must never be able to out-rank a passing one
                        # by tier name, even if its raw Total Score happens to be numerically higher.
                        tier_labels = {5: "⭐⭐⭐⭐⭐ Excellent", 4: "⭐⭐⭐⭐ Strong",
                                       3: "⭐⭐⭐ Good", 2: "⭐⭐ Marginal", 1: "⭐ Weak"}

                        if total_score >= 85:
                            base_rank = 5
                        elif total_score >= 70:
                            base_rank = 4
                        elif total_score >= 55:
                            base_rank = 3
                        elif total_score >= 40:
                            base_rank = 2
                        else:
                            base_rank = 1

                        # WIP Gate: hitting the throughput target by letting WIP/Lead Time balloon
                        # must not be rewarded with a "Good"+ tier just because Throughput Score
                        # is maxed out. Cap the tier using WIP Score on the same 5-point scale --
                        # the WORSE of the two ranks wins.
                        if wip_score >= 85:
                            wip_cap_rank = 5
                        elif wip_score >= 70:
                            wip_cap_rank = 4
                        elif wip_score >= 55:
                            wip_cap_rank = 3
                        elif wip_score >= 40:
                            wip_cap_rank = 2
                        else:
                            wip_cap_rank = 1

                        final_rank = min(base_rank, wip_cap_rank)
                        tier = tier_labels[final_rank]
                        badge_class = "rec-gold"
                        recommendation = tier
                        if wip_cap_rank < base_rank:
                            recommendation += " ⚠️ capped — WIP/Lead Time rose"
                    else:
                        badge_class = "rec-fail"
                        recommendation = f"❌ Below Target (Score: {total_score:.1f}/100)"

                eval_rows.append({
                    "Scenario": scen,
                    "Capacity Changes": ", ".join(changed_stations) if changed_stations else ("—" if is_base else "None"),
                    "# Changes": num_changes,
                    "Throughput": int(tp),
                    "Gain vs Base (%)": round(gain_pct, 2),
                    "Meets 5% Target?": target_flag,
                    "Avg WIP": avg_wip,
                    "Lead Time": lead_time,
                    "Throughput Score (50%)": round(tp_score, 1) if tp_score is not None else "—",
                    "Capacity Score (30%)": round(cap_score, 1) if cap_score is not None else "—",
                    "WIP Score (20%)": round(wip_score, 1) if wip_score is not None else "—",
                    "Total Score": round(total_score, 1) if total_score is not None else "—",
                    "_badge_class": badge_class,
                    "Recommendation": recommendation
                })

            eval_df = pd.DataFrame(eval_rows)

            # --- Summary metrics ---
            scored = eval_df[eval_df["Total Score"] != "—"].copy()
            qualifying = eval_df[eval_df["Meets 5% Target?"] == "✅"].copy()
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Base Throughput", f"{int(base_throughput)} units")
            with m2:
                st.metric("Scenarios Run", f"{len(eval_df) - 1}")
            with m3:
                st.metric("Scenarios Meeting Target", f"{len(qualifying)}")
            with m4:
                if not scored.empty:
                    best = scored.sort_values("Total Score", ascending=False).iloc[0]
                    st.metric("Top-Scoring Scenario", f"{best['Scenario']} ({best['Total Score']})")
                else:
                    st.metric("Top-Scoring Scenario", "—")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.subheader("Table D: Optimization Scorecard")
            st.caption("Score = 50 × Throughput Score + 30 × Capacity Score + 20 × WIP Score  (each sub-score is 0–100, so Total Score is out of 100)")

            display_df = eval_df.drop(columns=["_badge_class"]).set_index("Scenario")
            st.dataframe(display_df, use_container_width=True)

            if not qualifying.empty:
                best = qualifying.sort_values("Total Score", ascending=False).iloc[0]
                st.success(
                    f"🏆 **{best['Scenario']}** has the best overall Score ({best['Total Score']}/100) among scenarios "
                    f"meeting the target: **+{best['Gain vs Base (%)']}%** throughput with **{best['# Changes']}** "
                    f"capacity change(s) ({best['Capacity Changes']}) and a WIP Score of {best['WIP Score (20%)']}."
                )
            else:
                st.warning("No scenario has reached the 5% throughput target yet. Try widening the dice range on the current bottleneck station rather than every station.")

            st.markdown("---")
            st.subheader("📥 Export Optimization Scorecard")
            opt_output = io.BytesIO()
            with pd.ExcelWriter(opt_output, engine='xlsxwriter') as writer:
                display_df.to_excel(writer, sheet_name='Optimization Scorecard')
            opt_excel_data = opt_output.getvalue()
            st.download_button(
                label="⬇️ Download Scorecard (Excel)",
                data=opt_excel_data,
                file_name=f"Optimization_Scorecard_{current_user}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            with st.expander("📐 How the scorecard is calculated"):
                st.markdown("""
**Score = 50 × Throughput Score + 30 × Capacity Score + 20 × WIP Score** (Total Score out of 100)

- **Capacity Changes**: stations whose dice range in a scenario differs from that same station's range in the Base-Run.
- **Gain vs Base (%)**: `(Scenario Throughput − Base Throughput) / Base Throughput × 100`.
- **Meets 5% Target?**: ✅ if Gain vs Base ≥ 5% — shown regardless of Total Score, so a high-scoring scenario that hasn't hit the target is still clearly flagged.
- **Throughput Score (0–100)**: `min(Gain% / 5%, 1) × 100`. Reaches 100 exactly at the 5% target; no extra credit for overshooting it.
- **Capacity Score (0–100)**: `100 × (1 − Changes / Total Stations)`. Rewards touching fewer stations — 1 change out of 7 stations scores ~86, changing all 7 scores 0.
- **WIP Score (0–100)**: centered at 50 = "WIP unchanged from base." `clamp(50 + %WIP reduction vs base, 0, 100)` — reducing average WIP earns bonus points above 50, increasing it costs points below 50.
- **Tiers**: ⭐⭐⭐⭐⭐ ≥ 85 · ⭐⭐⭐⭐ ≥ 70 · ⭐⭐⭐ ≥ 55 · ⭐⭐ ≥ 40 · ⭐ below that. **Tiers are only ever assigned to scenarios that meet the 5% target** — a scenario that misses the target always shows as "Below Target (Score: X/100)" with no quality label, even if its raw Total Score is numerically high. This keeps a failing scenario from ever appearing to out-rank a passing one.
- **WIP Gate**: a scenario's tier is also capped by its WIP Score on the same 5-point scale — whichever rank is worse (Total Score tier or WIP Score tier) wins. This stops a scenario from hitting the throughput target by letting WIP/Lead Time balloon and still walking away with a "Good" or better rating. When the gate kicks in, the row is marked **⚠️ capped — WIP/Lead Time rose**.
                """)

# --- TAB 4: METHODOLOGY ---
with tab4:
    meth_h1("📖 Simulation Methodology & Logic")
    st.markdown("""
    This page explains how **dependency** and **fluctuation** (the core of the Dice Game / Theory of Constraints) are modelled in this simulation.
    """)

    meth_h2("🔄 The Flow Logic (Station A ➔ Buffer ➔ Station B)")
    meth_h3("System Architecture")
    st.markdown("The simulation follows a linear production chain where each station is linked by an inventory buffer:")
    st.success("🏭 **Station A** (Source) $\longrightarrow$ 📦 **Buffer AB** (WIP) $\longrightarrow$ ⚙️ **Station B** (Processor) $\longrightarrow$ 📦 **Buffer BC** (WIP) $\longrightarrow$ ⚙️ **Station C**...")

    st.info("""
    **The Student's Guide to Movement Logic:**
    The actual work done is the **minimum** of your ability (Dice) and your availability (Buffer).
    """)

    st.latex(r"\text{Movement}_{B} = \min(\text{Dice Roll}_{B}, \text{Buffer}_{A \to B})")

    st.markdown("---")

    meth_h2("📊 Table A: Summary History")
    col1, col2 = st.columns(2)
    with col1:
        meth_h3("Throughput Rate ($TR$)")
        st.latex(r"TR = \frac{\sum_{day=1}^{n} \text{Daily Throughput}}{n}")

        meth_h3("Average System Entropy ($\\bar{H}$)")
        st.latex(r"\bar{H} = \frac{1}{M} \sum_{i=1}^{M} H_i")

    with col2:
        meth_h3("Lead Time ($L$)")
        st.markdown("Calculated based on average daily WIP levels relative to throughput rate.")
        st.latex(r"L = \frac{(\sum \text{Daily Total WIP} / n)}{TR}")

        meth_h3("Entropy Spread ($\sigma H$)")
        st.latex(r"\sigma H = \sqrt{\frac{\sum (H_i - \bar{H})^2}{M}}")

    st.markdown("---")

    meth_h2("🔬 Table B: Station-Level Flow Diagnostics")
    st.latex(r"H = -\sum P(x) \log_2 P(x)")

    st.markdown("""
    **How to read Table B:**
    * **Avg WIP:** High WIP indicates this station is a **Bottleneck**.
    * **Entropy ($H_i$):**
        * **Stable (< 2.4):** Predictable output.
        * **Variable (≥ 2.4):** High 'jitter' or chaos.
    """)

    st.markdown("---")

    meth_h2("🎯 Table D: Optimization Scorecard")
    st.markdown("""
    The naive learning objective — *"maximize throughput"* — invites students to widen every station's dice
    range at once. It works, but it doesn't teach anything about **where** constraints actually live.
    """)
    st.info("""
    **The real objective:** reach at least a **5% throughput increase** over the Base-Run using the
    **fewest capacity changes possible**, without inflating WIP inventory to get there. This forces
    students to identify the binding constraint(s), resize only those, re-run, and check whether one
    more change is actually worth it.
    """)

    meth_h3("The Weighted Score")
    st.latex(r"\text{Score} = 50 \times \text{Throughput Score} + 30 \times \text{Capacity Score} + 20 \times \text{WIP Score}")
    st.markdown("Each sub-score is bounded 0–100, so the Total Score is out of 100. The weights reflect what matters most: hitting the throughput target (50%), doing it with minimal capacity changes (30%), and not bloating inventory to get there (20%).")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        meth_h3("Throughput Score (50%)")
        st.latex(r"\min\!\left(\frac{\text{Gain \%}}{5\%},\ 1\right) \times 100")
        st.caption("Gain % = (Scenario TP − Base TP) / Base TP × 100. Reaches 100 exactly at the 5% target — no bonus for overshooting.")
    with col_b:
        meth_h3("Capacity Score (30%)")
        st.latex(r"100 \times \left(1 - \frac{\text{Changes}}{\text{Total Stations}}\right)")
        st.caption("Rewards touching fewer stations. 1 change out of 7 stations ≈ 86; changing all 7 stations = 0.")
    with col_c:
        meth_h3("WIP Score (20%)")
        st.latex(r"\text{clamp}\big(50 + \%\Delta\text{WIP}_{\text{base}\to\text{scenario}},\ 0,\ 100\big)")
        st.caption("Centered at 50 = WIP unchanged from base. Reducing WIP earns bonus points; increasing it costs points.")

    st.markdown("""
    A scenario only counts as **meeting the target** once Gain % ≥ 5 — that flag is always shown
    alongside the Total Score, so a scenario can't disguise a missed target behind a decent Capacity
    or WIP Score. On top of that, a **WIP Gate** caps the star tier at whatever the WIP Score alone
    would earn: a scenario can't hit the throughput target by letting WIP/Lead Time balloon and still
    walk away with a "Good" or better rating just because Throughput Score maxed out. Among scenarios
    that clear both the target and the WIP gate, the Total Score ranks them — a scenario that hits +6%
    with one targeted change and a leaner buffer will out-score one that hits +8% by widening every
    station's dice range and stacking up WIP to get there.
    """)
