import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta

st.set_page_config(
    page_title="NSE Trade Data Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
        color: #ffffff;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #00d4ff !important;
    }
    .stButton>button {
        background: linear-gradient(to right, #00d4ff, #00a3ff) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 24px !important;
        font-weight: bold !important;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 14px rgba(0, 212, 255, 0.3);
    }
    [data-testid="stSidebar"] {
        background: rgba(15, 32, 39, 0.85) !important;
        border-right: 1px solid #00d4ff;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    cols = ["S.No", "Symbol", "Series", "Timestamp", "Price", "Quantity Traded"]
    data = pd.read_csv("20090803.csv", names=cols, header=None)
    data["Timestamp"] = pd.to_datetime(data["Timestamp"], format="%H:%M:%S").dt.time
    return data

df = load_data()

st.title("NSE Trade Data Analyzer")
st.markdown("#### Explore and analyze trade-level stock exchange data with ease")
st.markdown("---")

with st.sidebar:
    st.header("Settings")
    
    symbols = st.multiselect(
        "Choose Symbol(s)", 
        sorted(df["Symbol"].unique())
    )

    bin_seconds = st.number_input(
        "Specify Time Bin (in seconds)",
        min_value=1,
        max_value=21600,
        step=1
    )

    st.markdown("---")
    st.markdown("#### Sample of Trade Records")
    st.dataframe(df.sample(10), use_container_width=True)

if symbols:
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("Filter by Time Range")
        
        filtered_df = df[df["Symbol"].isin(symbols)].copy()
        filtered_df["Timestamp"] = pd.to_datetime(filtered_df["Timestamp"].astype(str))

        min_time = filtered_df["Timestamp"].min().to_pydatetime()
        max_time = filtered_df["Timestamp"].max().to_pydatetime()

        time_range = st.slider(
            "Pick Start and End Time",
            min_value=min_time,
            max_value=max_time,
            value=(min_time, max_time),
            format="HH:mm:ss"
        )

        final_df = filtered_df[
            (filtered_df["Timestamp"] >= pd.to_datetime(time_range[0])) &
            (filtered_df["Timestamp"] <= pd.to_datetime(time_range[1]))
        ].copy()

        if final_df.empty:
            st.warning("No data found for the selected time window. Try adjusting it.")
        else:
            start_time = pd.to_datetime(time_range[0])

            def assign_time_bin(ts):
                delta = (ts - start_time).total_seconds()
                bin_start = int(delta // bin_seconds) * bin_seconds
                return start_time + timedelta(seconds=bin_start)

            final_df["Time Bin"] = final_df["Timestamp"].apply(assign_time_bin)

            summary = final_df.groupby(["Symbol", "Time Bin"], as_index=False).agg({
                "Price": "mean",
                "Quantity Traded": "sum"
            })

            st.subheader("Aggregated Stats")
            stat1, stat2 = st.columns(2)
            stat1.metric("Total Trades", f"{final_df.shape[0]:,}")
            stat2.metric("Average Price", f"₹{final_df['Price'].mean():,.2f}")
    
    with col2:
        st.subheader("Export Reports")

        if not final_df.empty:
            with st.expander("View Aggregated Results", expanded=True):
                display_df = summary.copy()
                display_df["Time Bin"] = display_df["Time Bin"].dt.strftime("%H:%M:%S")
                display_df.rename(columns={
                    "Time Bin": "Timestamp"
                }, inplace=True)
                st.dataframe(display_df, use_container_width=True)

            if st.button("Generate Excel File"):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for symbol in symbols:
                        temp = summary[summary["Symbol"] == symbol].copy()
                        temp["Time Bin"] = temp["Time Bin"].dt.strftime("%H:%M:%S")
                        temp.rename(columns={
                            "Time Bin": "Timestamp",
                            "Price": "Average Price"
                        }, inplace=True)
                        temp.to_excel(writer, sheet_name=symbol[:25], index=False)
                output.seek(0)
                st.download_button(
                    label="Download Excel File",
                    data=output,
                    file_name=f"Trade_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
else:
    st.info("Start by selecting one or more symbols from the sidebar.")
