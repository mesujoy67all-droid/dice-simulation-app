import streamlit as st
import pandas as pd
import numpy as np
from collections import defaultdict
import io
import time

# --- Harvard Business Publishing Style Configuration ---
st.set_page_config(
    page_title="Operations Management Simulation: Process Analytics", 
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Crimson & Slate Blue Palette Override
st.markdown("""
<style>
    .stApp { background-color: #F9FAFB; }
    
    /* Global Corporate Typography & Design Headers */
    h1, h2, h3 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important; color: #111827 !important; }
    
    /* Top Brand Accent Bar mimicking HBP Canvas portal */
    .hbp-header {
        background-color: #A51C30; /* Harvard Crimson */
        padding: 15px;
        border-radius: 4px;
        color: white;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    
    /* HBP Styled Cards & Metric Telemetry Blocks */
    div[data-testid="stMetricValue"] {
        font-family: 'Courier New', Courier, monospace;
        font-size: 2.2rem;
        font-weight: 700;
        color: #A51C30;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #4B5563;
    }
    
    /* Interactive Process Map Elements */
    .node-card {
        background: white;
        border-top: 4px solid #A51C30;
        border-left: 1px solid #E5E7EB;
        border-right: 1px solid #E5E7EB;
        border-bottom: 1px solid #E5E7EB;
        border-radius: 4px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .node-name { font-size: 1.1rem; font-weight: 700; color: #111827; }
    
    /* Dynamic State-based Queue Buffers styling */
    .queue-card-normal {
        background: #FFFBEB;
        border: 1px solid #FCD34D;
        border-radius: 4px;
        padding: 10px;
        text-align: center;
        margin-top: 12px;
    }
    .queue-card-starved {
        background: #FEF2F2;
        border: 2px solid #EF4444;
        border-radius: 4px;
        padding: 10px;
        text-align: center;
        margin-top: 12px;
        animation: pulse 2s infinite;
    }
    
    /* Utility Tabs formatting overrides */
    .stTabs [data-baseweb="tab"] {
        font-size: 1rem;
        font-weight: 600;
        color: #4B5563 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #A51C30 !important;
        border-bottom-color: #A51C30 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Session Databases Setup ---
if 'user_db' not in st.session_state:
    st.session_state.user_db = {} 
if 'authenticated_user' not in st.session_state:
    st.session_state.authenticated_user = None
if 'active_results' not in st.session_state:
    st.session_state.active_results = None

# Step-wise tracking parameters for the simulation playback controller
if 'sim_current_day' not in st.session_state:
    st.session_state.sim_current_day = 1
if 'play_is_running' not in st.session_state:
    st.session_state.play_is_running = False

# --- Authentication Gateway Portal ---
def auth_gateway():
    st.markdown("<div class='hbp-header' style='text-align:center; font-size:1.6rem;'>HARVARD SIMULATION PLATFORM: PROCESS ANALYTICS</div>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 1.4, 1])
    with col_c:
        with st.container(border=True):
            auth_mode = st.radio("Access Level Input Mode:", ["Sign In to Account", "Create New Student Profile"], horizontal=True)
            user_id = st.text_input("Corporate Username / Network Unique ID")
            pwd = st.text_input("Access Password Key Verification", type="password")
            
            if "Create" in auth_mode:
                if st.button("Initialize Student Profile Sandbox", use_container_width=True):
                    if user_id in st.session_state.user_db:
                        st.error("Account ID string collision: Name already claimed.")
                    elif user_id and pwd:
                        st.session_state.user_db[user_id] = {"password": pwd, "history": [], "stations": []}
                        st.success("Sandbox account successfully provisioned. Proceed to Sign In.")
            else:
                if st.button("Establish Verified Terminal Connection", use_container_width=True):
                    if user_id in st.session_state.user_db and st.session_state.user_db[user_id]["password"] == pwd:
                        st.session_state.authenticated_user = user_id
                        st.rerun()
                    else:
                        st.error("Authentication rejected: Invalid security tokens.")

if st.session_state.authenticated_user is None:
    auth_gateway()
    st.stop()

current_user = st.session_state.authenticated_user
user_record = st.session_state.user_db[current_user]
history_count = len(user_record["history"])
is_base_run = (history_count == 0)

# --- Premium Layout Command Sidebar Panels ---
st.sidebar.markdown(f"<div style='background:#1F2937;color:white;padding:10px;font-size:0.85rem;border-radius:4px;font-weight:600;'>TERMINAL OPERATOR: {current_user.upper()}<br/>ROUTING PROFILE: RUN MATCH #{history_count}</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")

st.sidebar.subheader("📈 Capacity Sourcing Parameters")
capacity_mode = st.sidebar.radio("Data Sourcing Feed Model:", ["Random Stochastic Distribution", "Static Corporate Data Matrix (.CSV/.XLSX)"])

num_days = 1500
num_members = 7
dice_configs = {}
station_frequencies = {}
uploaded_df = None

if capacity_mode == "Random Stochastic Distribution":
    if 'sim_seed' not in st.session_state:
        st.session_state.sim_seed = np.random.randint(100, 99999)
    if not st.sidebar.toggle("Freeze Pipeline Seed Value (Strict Replication)", value=False):
        st.session_state.sim_seed = np.random.randint(100, 99999)
    st.sidebar.caption(f"System Operational Seed Profile Target: `{st.session_state.sim_seed}`")
    
    st.sidebar.markdown("### 🎲 Node Processing Capacities")
    members_list = [chr(64 + i) for i in range(1, 8)]
    for m in members_list:
        with st.sidebar.container(border=True):
            st.markdown(f"**Workstation Node {m}**")
            dice_configs[m] = st.slider(f"Roll Span Range Model:", 1, 20, (1, 6), key=f"r_{m}")
            station_frequencies[m] = 1 if is_base_run else st.selectbox("Interval Cadence Cycle:", list(range(1, 11)), index=0, format_func=lambda x: "Continuous Flow" if x==1 else f"Batch Skip / 1 per {x} Days", key=f"f_{m}")
else:
    uploaded_file = st.sidebar.file_uploader("Upload Factory Trace File", type=["xlsx", "csv"])
    if uploaded_file is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_file, index_col=0) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, index_col=0)
            uploaded_df = uploaded_df.apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
            num_days, num_members = len(uploaded_df), len(uploaded_df.columns)
            st.sidebar.success(f"Loaded Trace: {num_days} Cycles across {num_members} Nodes.")
        except Exception as e:
            st.sidebar.error(f"Trace ingestion fault: {e}")

members = [chr(64 + i) for i in range(1, num_members + 1)]
wip_keys = [f"WIP_{members[i]}{members[i+1]}" for i in range(len(members) - 1)]

st.sidebar.markdown("---")
st.sidebar.subheader("📦 Node Buffer Allocation Storage")
initial_wip = {k: st.sidebar.number_input(f"Initial Stock allocation {k.replace('WIP_', '')}:", min_value=0, value=4) for k in wip_keys}

st.sidebar.markdown("---")
run_sim_clicked = st.sidebar.button("📊 Compile Scenario Array", type="primary", use_container_width=True)
if st.sidebar.button("Clear Trial Execution Arrays", use_container_width=True):
    user_record["history"], user_record["stations"] = [], []
    st.session_state.active_results = None
    st.session_state.sim_current_day = 1
    st.rerun()

# --- Simulation Compilation Engine Logic ---
if run_sim_clicked:
    if "Static" in capacity_mode and uploaded_df is None:
        st.sidebar.error("Halting: Sourcing trace profile absent.")
    else:
        if capacity_mode == "Random Stochastic Distribution":
            np.random.seed(st.session_state.sim_seed)
            df_dice = pd.DataFrame({m: [np.random.randint(dice_configs[m][0], dice_configs[m][1] + 1) for _ in range(num_days)] for m in members})
            df_dice.index = range(1, num_days + 1)
        else:
            df_dice = uploaded_df.copy()
            df_dice.columns = members
        
        # Apply intermittent down-time constraints
        for m in members:
            freq = station_frequencies.get(m, 1)
            if freq > 1:
                for d in df_dice.index:
                    if (d - 1) % freq != 0:
                        df_dice.at[d, m] = 0

        # High Fidelity Step Tracing Array for HBP Playback Visualizer Engine
        wip_buffers = {k: initial_wip[k] for k in wip_keys}
        day_step_logs = {}
        total_fg = 0
        history_summary = []
        
        pennies_movement = defaultdict(list)
        st_wip_trend = defaultdict(list)
        
        for day in df_dice.index:
            rolls = df_dice.loc[day]
            realized_flows = {}
            current_day_wip_before = wip_buffers.copy()
            
            # Formulate cross-dependent serialization
            for i, m in enumerate(members):
                roll = rolls[m]
                if i == 0:
                    flow = roll
                    wip_buffers[f"WIP_{members[i]}{members[i+1]}"] += flow
                elif i == len(members) - 1:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    flow = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= flow
                    total_fg += flow
                else:
                    prv = f"WIP_{members[i-1]}{members[i]}"
                    nxt = f"WIP_{members[i]}{members[i+1]}"
                    flow = min(roll, wip_buffers[prv])
                    wip_buffers[prv] -= flow
                    wip_buffers[nxt] += flow
                
                realized_flows[m] = flow
                pennies_movement[m].append(flow)
            
            for k, v in wip_buffers.items():
                st_wip_trend[k.replace("WIP_", "")].append(v)
                
            day_step_logs[day] = {
                "rolls": rolls.to_dict(),
                "flows": realized_flows,
                "wip_end": wip_buffers.copy(),
                "cumulative_fg": total_fg
            }
            
            history_summary.append({
                "Day": day, **wip_buffers.copy(), 
                "Daily_Total_WIP": sum(wip_buffers.values()), "FG": realized_flows[members[-1]]
            })

        results_df = pd.DataFrame(history_summary).set_index("Day")
        scen_label = "🔥 Base Case Execution" if is_base_run else f"⚡ Trial Scenario #{history_count}"
        
        # Save structural metric payload
        avg_tr = total_fg / num_days
        avg_wip = results_df["Daily_Total_WIP"].sum() / num_days
        
        user_record["history"].append({
            "Scenarios": scen_label, "Throughput": int(total_fg), 
            "Throughput Rate (TR)": round(avg_tr, 2), "Avg WIP (W_avg)": round(avg_wip, 2),
            "Lead Time (L)": round(avg_wip / avg_tr, 2) if avg_tr > 0 else 0
        })
        
        for m in members:
            user_record["stations"].append({
                "Scenario": scen_label, "Station": f"Station {m}", 
                "Throughput": sum(pennies_movement[m]), "Avg WIP": 0.0 if m=='A' else round(np.mean(st_wip_trend[f"{members[members.index(m)-1]}{m}"]), 2)
            })

        st.session_state.active_results = {
            "scen_label": scen_label, "logs": day_step_logs, "max_days": num_days,
            "results_df": results_df, "total_fg": total_fg, "pennies": pd.DataFrame(pennies_movement)
        }
        st.session_state.sim_current_day = 1
        st.rerun()

# --- Main Dashboard Frame Space ---
st.markdown("<div class='hbp-header'><span style='font-size:1.3rem;'>Harvard Business Publishing Education</span> &nbsp;|&nbsp; Operations & Analytics Simulation Portfolio</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 Core Interactive Playback Arena", "📊 Multi-Trial Strategic Matrix", "📖 Operational Logic Documentations"])

with tab1:
    if st.session_state.active_results is None:
        st.info("💡 Sandbox Waiting for Pipeline Initialization Configuration Profile parameters. Adjust the configuration panel and compile to run.")
    else:
        res = st.session_state.active_results
        logs = res["logs"]
        
        st.subheader("🏁 Live Production Flow Execution Controller")
        st.markdown("Interact with the execution loop directly. Run a single cycle frame stepping block, sequence dynamically, or fast forward across all iterations.")
        
        # Multi-Speed Interactive Simulation Navigation Layout Control Deck
        c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([1.5, 1.5, 2, 3])
        
        with c_ctrl1:
            if st.button("➕ Advance 1 Single Day", use_container_width=True):
                if st.session_state.sim_current_day < res["max_days"]:
                    st.session_state.sim_current_day += 1
        with c_ctrl2:
            if st.button("⏪ Reset Timeline Index", use_container_width=True):
                st.session_state.sim_current_day = 1
        with c_ctrl3:
            jump_day = st.slider("Target Day Index Block Routing:", 1, int(res["max_days"]), int(st.session_state.sim_current_day))
            st.session_state.sim_current_day = jump_day
        with c_ctrl4:
            # Animation run option loop simulation
            if st.checkbox("⚙️ Trigger Automated Visual Pipeline Playback Stream Loop"):
                st.session_state.play_is_running = True
            else:
                st.session_state.play_is_running = False

        if st.session_state.play_is_running and st.session_state.sim_current_day < res["max_days"]:
            st.session_state.sim_current_day += 1
            time.sleep(0.08) # Short cycle break to display updating state transitions
            st.rerun()

        # Gather context state matrices relative to active operational day step view
        cd = st.session_state.sim_current_day
        day_data = logs[cd]
        
        st.markdown(f"#### 🛰️ Real-Time Line Metrics Framework Status Matrix &mdash; **DAY {cd} OF {res['max_days']}**")
        
        # Display Harvard Metric telemetry summary
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Simulated System Cycles Out", f"{int(day_data['cumulative_fg'])} Units")
        m_col2.metric("Instant Target Frame Processing Efficiency", f"{round((day_data['cumulative_fg']/cd), 2)} Units / Cycle Day")
        m_col3.metric("Current Backlog Footprint Status", f"{sum(day_data['wip_end'].values())} Units In-Line")
        
        st.markdown("---")
        st.markdown("### 🗺️ Harvard Analytics Process Flow Topology Model Visualizer")
        st.caption("Active capacity variables represent raw system potential. Realized Yield indicates actual throughput output constraint execution dynamics.")
        
        # Construct pipeline routing rendering maps dynamically using standard layout columns mapping layout blocks
        f_cols = st.columns([2, 1.2, 2, 1.2, 2, 1.2, 2, 1.2, 2, 1.2, 2, 1.2, 2])
        
        station_letters = [chr(65 + k) for k in range(7)]
        
        for idx, letter in enumerate(station_letters):
            col_pos = idx * 2
            
            # Processing Station Component Node Rendering Block Elements
            with f_cols[col_pos]:
                roll_val = day_data["rolls"][letter]
                flow_val = day_data["flows"][letter]
                
                # Highlight starved nodes if realized flow drops below roll potential
                is_starved = "border-top: 4px solid #EF4444; background: #FFF5F5;" if (flow_val < roll_val and idx > 0 and roll_val > 0) else ""
                
                st.markdown(f"""
                <div class='node-card' style='{is_starved}'>
                    <div class='node-name'>Station {letter}</div>
                    <hr style='margin:6px 0; border: 0; border-top: 1px solid #E5E7EB;'/>
                    <p style='margin:0; font-size:0.75rem; color:#4B5563;'>Capacity: <b>{roll_val}</b></p>
                    <p style='margin:2px 0 0 0; font-size:0.85rem; color:#A51C30;'><b>Yield: {flow_val}</b></p>
                </div>
                """, unsafe_allow_html=True)
            
            # Buffer Capacity Storage Render Elements
            if idx < len(station_letters) - 1:
                next_letter = station_letters[idx+1]
                b_key = f"WIP_{letter}{next_letter}"
                wip_val = day_data["wip_end"][b_key]
                
                # Check buffer asset constraints
                buffer_class = "queue-card-starved" if wip_val == 0 else "queue-card-normal"
                
                with f_cols[col_pos + 1]:
                    st.markdown(f"""
                    <div class='{buffer_class}'>
                        <div style='font-size:0.65rem; text-transform:uppercase; font-weight:700; color:#92400E;'>WIP {letter}➔{next_letter}</div>
                        <div style='font-size:1.2rem; font-weight:800; margin-top:2px;'>{wip_val}</div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📈 Micro-Trend Inventory Tracking Matrix Profile Lines")
        
        # Display localized micro charts mapping system accumulation indexes over time scales
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.caption("Historical Trendline Asset Footprint Log Line Allocation Matrix (Total Volume)")
            st.line_chart(res["results_df"]["Daily_Total_WIP"].iloc[:cd], height=180)
        with chart_col2:
            st.caption("System Run Cumulative Target Pipeline Throughput Metrics Processing Log Line")
            st.line_chart(res["results_df"]["FG"].cumsum().iloc[:cd], height=180)

with tab2:
    st.markdown("### 📋 Executive Cross-Scenario Strategy Ledger Analysis Matrix")
    if user_record["history"]:
        st.dataframe(pd.DataFrame(user_record["history"]).set_index("Scenarios"), use_container_width=True)
        st.markdown("---")
        st.markdown("### 🔬 Workstation Node Granular Micro-Diagnostics Data Ledger")
        st.dataframe(pd.DataFrame(user_record["stations"]).set_index(["Scenario"]), use_container_width=True)
    else:
        st.info("No recorded trial ledger blocks located in active storage buffer arrays.")

with tab3:
    st.markdown("### 📖 Mathematical Core Documentation Architecture")
    st.markdown("""
    This interactive analysis matrix implements operations diagnostics rules for sequential dependent networks governed under **The Theory of Constraints (TOC)** framework model.
    """)
    with st.container(border=True):
        st.markdown("#### Dependency Flow Bounds Governing Constraints")
        st.latex(r"\text{Realized Yield Output}_i = \min\left(\text{Node Design Capacity Capability}_i,\, \text{Input Asset Inventory Level Buffer}_{i-1 \to i}\right)")
        st.info("💡 **Harvard Business School Takeaway:** System variance within sequentially linked processes propagates downstream. System parameters cannot run smoothly without properly configured inventory safety buffers to protect against capacity starvation bottlenecks.")
