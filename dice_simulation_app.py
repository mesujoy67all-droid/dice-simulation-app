 /* Fix metric label visibility */
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"] p {
        color: #BFDBFE !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 1.2px !important;
        opacity: 1 !important;
    }

    /* Fix number inputs in sidebar */
    section[data-testid="stSidebar"] input[type="number"] {
        background-color: #1E3A8A !important;
        color: #F1F5F9 !important;
        border: 1px solid #3B82F6 !important;
        border-radius: 6px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] input[type="number"]:focus {
        border: 1px solid #60A5FA !important;
        box-shadow: 0 0 0 2px rgba(96,165,250,0.3) !important;
    }

    /* Fix main background */
    [data-testid="stAppViewContainer"] {
        background-color: #EFF6FF !important;
    }
    [data-testid="stAppViewContainer"] > section.main {
        background-color: #EFF6FF !important;
    }

    /* Fix +/- buttons in sidebar number inputs */
    section[data-testid="stSidebar"] button[kind="secondary"] {
        background-color: #2563EB !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
    }

    /* Number input labels in sidebar */
    section[data-testid="stSidebar"] .stNumberInput label p {
        color: #93C5FD !important;
        font-size: 0.83rem !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
    }
