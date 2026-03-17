import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="HiveNavigator — Colony State Analysis",
    page_icon="🐝",
    layout="wide"
)

st.title("🐝 HiveNavigator — Acoustic Colony State Dashboard")
st.markdown("*Unsupervised detection of queen removal events — March 2026*")

BASE = Path(__file__).parent.parent
DATA_PATH = BASE / 'data' / 'features_all_hives.csv'

if not DATA_PATH.exists():
    BASE = Path(__file__).parent
    DATA_PATH = BASE / 'data' / 'features_all_hives.csv'

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=['timestamp'])
    return df

df = load_data()

# ── SIDEBAR ──────────────────────────────────────────────
st.sidebar.header("Controls")

all_hives = sorted(df['hive'].unique().tolist())
selected_hives = st.sidebar.multiselect(
    "Select Hives", all_hives, default=all_hives
)

all_features = [c for c in df.columns
                if c not in ['timestamp', 'hive', 'filename', 'cluster', 'pca_1', 'pca_2']]
selected_feature = st.sidebar.selectbox(
    "Select Feature to Plot", all_features, index=all_features.index('rms_mean')
)

date_min = df['timestamp'].min().date()
date_max = df['timestamp'].max().date()
date_range = st.sidebar.date_input(
    "Date Range",
    value=[date_min, date_max],
    min_value=date_min,
    max_value=date_max
)

show_smoothed = st.sidebar.checkbox("Show smoothed trend", value=True)

# ── FILTER DATA ───────────────────────────────────────────
if len(date_range) == 2:
    mask = (
        df['hive'].isin(selected_hives) &
        (df['timestamp'].dt.date >= date_range[0]) &
        (df['timestamp'].dt.date <= date_range[1])
    )
    filtered = df[mask].copy()
else:
    filtered = df[df['hive'].isin(selected_hives)].copy()

# ── MAIN FEATURE PLOT ─────────────────────────────────────
st.subheader(f"📈 {selected_feature} over Time")

fig = go.Figure()
colors = {'hive_01': '#1f77b4', 'hive_03': '#d62728', 'hive_04': '#ff7f0e'}

for hive in selected_hives:
    hive_data = filtered[filtered['hive'] == hive].sort_values('timestamp')
    if hive_data.empty:
        continue
    
    # Raw data (faint)
    fig.add_trace(go.Scatter(
        x=hive_data['timestamp'],
        y=hive_data[selected_feature],
        mode='lines',
        name=f'{hive} (raw)',
        line=dict(color=colors.get(hive, 'gray'), width=0.8),
        opacity=0.3
    ))
    
    # Smoothed trend
    if show_smoothed:
        smoothed = hive_data[selected_feature].rolling(8, center=True).mean()
        fig.add_trace(go.Scatter(
            x=hive_data['timestamp'],
            y=smoothed,
            mode='lines',
            name=f'{hive} (smoothed)',
            line=dict(color=colors.get(hive, 'gray'), width=2.5)
        ))

# Mark suspected queenless windows
fig.add_vrect(
    x0="2026-03-07", x1="2026-03-10",
    fillcolor="red", opacity=0.08,
    annotation_text="Suspected queenless (H3+H4)",
    annotation_position="top left"
)

fig.update_layout(
    height=450,
    xaxis_title="Date",
    yaxis_title=selected_feature,
    hovermode='x unified',
    legend=dict(orientation='h', yanchor='bottom', y=1.02)
)
st.plotly_chart(fig, use_container_width=True)

# ── MULTI-FEATURE COMPARISON ──────────────────────────────
st.subheader("🔬 Key Features Comparison")

col1, col2 = st.columns(2)

key_features = ['rms_mean', 'centroid_mean', 'flatness_mean', 'zcr_mean']

with col1:
    feat1 = st.selectbox("Feature A", key_features, index=0)
with col2:
    feat2 = st.selectbox("Feature B", key_features, index=2)

fig2 = go.Figure()
fig2_b = go.Figure()

for hive in selected_hives:
    hive_data = filtered[filtered['hive'] == hive].sort_values('timestamp')
    if hive_data.empty:
        continue
    s1 = hive_data[feat1].rolling(8, center=True).mean()
    s2 = hive_data[feat2].rolling(8, center=True).mean()
    fig2.add_trace(go.Scatter(x=hive_data['timestamp'], y=s1,
                              name=hive, line=dict(color=colors.get(hive,'gray'), width=2)))
    fig2_b.add_trace(go.Scatter(x=hive_data['timestamp'], y=s2,
                                name=hive, line=dict(color=colors.get(hive,'gray'), width=2)))

for f in [fig2, fig2_b]:
    f.add_vrect(x0="2026-03-07", x1="2026-03-10",
                fillcolor="red", opacity=0.08)
    f.update_layout(height=300, hovermode='x unified',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02))

fig2.update_layout(title=feat1)
fig2_b.update_layout(title=feat2)

col1.plotly_chart(fig2, use_container_width=True)
col2.plotly_chart(fig2_b, use_container_width=True)

# ── SENSOR DATA PANEL ─────────────────────────────────────
st.subheader("🌡️ Environmental Sensors — Hive 03 & 04")

@st.cache_data
def load_sensors():
    dfs = {}
    for hive in ['hive_03', 'hive_04']:
        p = BASE / 'data' / 'sensors' / hive
        files = list(p.rglob('*sensors*.csv'))  
        if files:
            s = pd.read_csv(files[0], parse_dates=['timestamp'])
            s['hive'] = hive
            dfs[hive] = s
    return dfs

sensor_dfs = load_sensors()

if sensor_dfs:
    sensor_feat = st.selectbox(
        "Sensor feature",
        ['sht_t', 'sht_h', 'co2'],
        format_func=lambda x: {'sht_t':'Temperature (°C)',
                                'sht_h':'Humidity (%)',
                                'co2':'CO₂ (ppm)'}[x]
    )
    fig3 = go.Figure()
    for hive, sdf in sensor_dfs.items():
        if sensor_feat in sdf.columns:
            fig3.add_trace(go.Scatter(
                x=sdf['timestamp'], y=sdf[sensor_feat],
                name=hive, line=dict(color=colors.get(hive,'gray'), width=1.5)
            ))
    fig3.add_vrect(x0="2026-03-07", x1="2026-03-10",
                   fillcolor="red", opacity=0.08,
                   annotation_text="Queenless window")
    fig3.update_layout(height=300, hovermode='x unified')
    st.plotly_chart(fig3, use_container_width=True)

# ── FINDINGS SUMMARY ─────────────────────────────────────
st.subheader("📋 Key Findings")
col_a, col_b = st.columns(2)

with col_a:
    st.error("""
    **Hive 04 — Strong queenless signal**
    - 📅 Queenless: **March 7–9, 2026**
    - Spectral flatness: 10× above normal
    - ZCR elevated (0.055–0.075 vs 0.040)
    - Centroid shifted +100 Hz above control
    - All features normalise by March 10
    """)

with col_b:
    st.warning("""
    **Hive 03 — Weak signal**
    - 📅 Likely queenless: **March 7–9, 2026**
    - Small flatness elevation March 8–9
    - Tracks closely with control hive
    - Cold temperatures likely masking signal
    - No strong clustering separation found
    """)