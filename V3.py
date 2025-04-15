import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")
st.title("EV Charger Economic Comparison: Off-grid SLB vs On-grid")

# -------------------- GENERAL PARAMETERS --------------------
st.sidebar.header("General Parameters")
analysis_years = st.sidebar.slider("Analysis Horizon (years)", 5, 30, 15)
discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 20.0, 8.0) / 100
inflation_rate = st.sidebar.number_input("Electricity Inflation Rate (%/year)", 0.0, 15.0, 3.0) / 100
residual_value_percent = st.sidebar.number_input("Residual Value (% of SLB CAPEX)", 0.0, 100.0, 10.0) / 100

st.sidebar.subheader("EV Usage Parameters")
ev_battery_capacity = st.sidebar.number_input("EV Battery Capacity (kWh)", 10.0, 200.0, 40.0)
ev_charge_percent = st.sidebar.slider("Average Charge Level (%)", 10, 100, 80)
ev_charging_sessions = st.sidebar.number_input("Charging Sessions per Month", 1, 60, 10)

monthly_consumption = ev_battery_capacity * (ev_charge_percent / 100) * ev_charging_sessions
st.sidebar.markdown(f"**Estimated Monthly EV Charging Demand:** `{monthly_consumption:.1f} kWh`")

# -------------------- OFF-GRID SLB EV CHARGER --------------------
st.sidebar.header("Off-grid EV Charger (with SLB)")
slb_capex_pv = st.sidebar.number_input("CAPEX - PV System (USD)", 0.0, 100000.0, 15000.0)
slb_capex_battery = st.sidebar.number_input("CAPEX - Second-life Battery (USD)", 0.0, 100000.0, 10000.0)
slb_opex = st.sidebar.number_input("Annual OPEX - SLB System (USD)", 0.0, 10000.0, 500.0)

# -------------------- ON-GRID EV CHARGER --------------------
st.sidebar.header("On-grid EV Charger")
electricity_price = st.sidebar.number_input("Electricity Price (USD/kWh)", 0.0, 1.0, 0.25)

# -------------------- SIMULATION --------------------
years = np.arange(1, analysis_years + 1)
annual_energy = monthly_consumption * 12

results = pd.DataFrame({'Year': np.insert(years, 0, 0)})

# Off-grid SLB calculation
slb_total_capex = slb_capex_pv + slb_capex_battery
fc_slb = [-slb_total_capex]
for year in years:
    escalated_cost = (electricity_price * (1 + inflation_rate) ** (year - 1)) * annual_energy
    cashflow = escalated_cost / ((1 + discount_rate) ** year) - slb_opex / ((1 + discount_rate) ** year)
    fc_slb.append(cashflow)
# Add residual value in final year
residual_value = residual_value_percent * slb_total_capex
fc_slb[-1] += residual_value / ((1 + discount_rate) ** analysis_years)
results['Off-grid SLB'] = np.cumsum(fc_slb)

# On-grid calculation (no CAPEX, only escalating energy cost)
fc_ongrid = [0]
for year in years:
    escalated_cost = (electricity_price * (1 + inflation_rate) ** (year - 1)) * annual_energy
    cashflow = -escalated_cost / ((1 + discount_rate) ** year)
    fc_ongrid.append(cashflow)
results['On-grid'] = np.cumsum(fc_ongrid)

# -------------------- OUTPUT --------------------
st.subheader("Cumulative Cash Flow")
st.line_chart(results.set_index('Year'))

st.subheader("Results Table")
st.dataframe(results.style.format("{:.2f}").set_table_styles([
    {"selector": "th", "props": [("min-width", "80px"), ("text-align", "center")]},
    {"selector": "td", "props": [("min-width", "100px"), ("text-align", "right")]}]))

