import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

st.set_page_config(layout="wide")
st.title("EV Charger Economic Comparison: On-grid with SLB vs On-grid")

# -------------------- INPUTS --------------------
st.sidebar.header("General Parameters")
analysis_years = st.sidebar.slider("Analysis Horizon (years)", 5, 30, 15)
discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 20.0, 8.0) / 100
inflation_rate = st.sidebar.number_input("Electricity Inflation Rate (%/year)", 0.0, 15.0, 3.0) / 100
residual_value_percent = st.sidebar.number_input("Residual Value (% of SLB CAPEX)", 0.0, 100.0, 10.0) / 100

st.sidebar.subheader("EV Usage Parameters")
ev_battery_capacity = st.sidebar.number_input("EV Battery Capacity (kWh)", 10.0, 200.0, 40.0)
ev_charge_percent = st.sidebar.slider("Average Charge Level (%)", 10, 100, 80)
ev_charging_sessions = st.sidebar.number_input("Charging Sessions per Month", 1, 60, 10)
ev_days_no_charging = st.sidebar.number_input("Days Without Charging per Month", 0, 31, 10)
feed_in_efficiency = st.sidebar.slider("Feed-in Efficiency (%)", 50, 100, 90) / 100

monthly_consumption = ev_battery_capacity * (ev_charge_percent / 100) * ev_charging_sessions
st.sidebar.markdown(f"**Estimated Monthly EV Charging Demand:** `{monthly_consumption:.1f} kWh`")

st.sidebar.header("On-grid with SLB EV Charger")
slb_capex_pv = st.sidebar.number_input("CAPEX - PV System (USD)", 0.0, 100000.0, 15000.0)
slb_capex_battery = st.sidebar.number_input("CAPEX - Second-life Battery (USD)", 0.0, 100000.0, 10000.0)
slb_opex = st.sidebar.number_input("Annual OPEX - SLB System (USD)", 0.0, 10000.0, 500.0)

st.sidebar.header("On-grid EV Charger")
electricity_price = st.sidebar.number_input("Electricity Price (USD/kWh)", 0.0, 1.0, 0.25)

# -------------------- CALCULATIONS --------------------
years = np.arange(1, analysis_years + 1)
annual_energy = monthly_consumption * 12

feed_in_tariff = 0.7 * electricity_price
energy_for_sale_per_month = ev_battery_capacity * (1 - ev_charge_percent/100) * ev_days_no_charging * feed_in_efficiency
annual_revenue_from_feed_in = energy_for_sale_per_month * 12 * feed_in_tariff

results = pd.DataFrame({'Year': np.insert(years, 0, 0)})

# On-grid with SLB system calculations
slb_total_capex = slb_capex_pv + slb_capex_battery
fc_slb = [-slb_total_capex]
slb_cashflows = [-slb_total_capex]
for year in years:
    escalated_cost = (electricity_price * (1 + inflation_rate) ** (year - 1)) * annual_energy
    escalated_revenue = (feed_in_tariff * (1 + inflation_rate) ** (year - 1)) * energy_for_sale_per_month * 12
    cashflow = (escalated_cost + escalated_revenue) - slb_opex
    discounted_cashflow = cashflow / ((1 + discount_rate) ** year)
    fc_slb.append(discounted_cashflow)
    slb_cashflows.append(cashflow)
residual_value = residual_value_percent * slb_total_capex
fc_slb[-1] += residual_value / ((1 + discount_rate) ** analysis_years)
slb_cashflows[-1] += residual_value
results['On-grid with SLB'] = np.cumsum(fc_slb)

# On-grid system calculations
fc_ongrid = [0]
ongrid_cashflows = [0]
for year in years:
    escalated_cost = (electricity_price * (1 + inflation_rate) ** (year - 1)) * annual_energy
    discounted_cashflow = -escalated_cost / ((1 + discount_rate) ** year)
    fc_ongrid.append(discounted_cashflow)
    ongrid_cashflows.append(-escalated_cost)
results['On-grid'] = np.cumsum(fc_ongrid)

# -------------------- METRICS --------------------
def calculate_irr(cashflows):
    try:
        return npf.irr(cashflows)
    except:
        return None

def calculate_npv(cashflows, rate):
    return npf.npv(rate, cashflows)

def calculate_payback(cashflows):
    cumulative = 0
    for i, val in enumerate(cashflows):
        cumulative += val
        if cumulative >= 0:
            return i
    return None

def calculate_crossover(results_slb, results_ongrid):
    for year, (slb_value, ongrid_value) in enumerate(zip(results_slb, results_ongrid)):
        if slb_value > ongrid_value:
            return year
    return None

irr_slb = calculate_irr(slb_cashflows)
npv_slb = calculate_npv(slb_cashflows, discount_rate)
pb_slb = calculate_payback(slb_cashflows)

irr_ongrid = calculate_irr(ongrid_cashflows)
npv_ongrid = calculate_npv(ongrid_cashflows, discount_rate)
pb_ongrid = calculate_payback(ongrid_cashflows)

crossover_point = calculate_crossover(results['On-grid with SLB'], results['On-grid'])

# -------------------- OUTPUT --------------------
st.subheader("Cumulative Cash Flow - On-grid with SLB vs On-grid")
st.line_chart(results.set_index('Year'))

st.subheader("Financial Metrics")
st.markdown(f"**On-grid with SLB** → IRR: `{irr_slb:.2%}` | NPV: `${npv_slb:,.2f}` | Payback: `{pb_slb if pb_slb is not None else 'N/A'} years`")
st.markdown(f"**On-grid** → IRR: `{irr_ongrid:.2%}` | NPV: `${npv_ongrid:,.2f}` | Payback: `{pb_ongrid if pb_ongrid is not None else 'N/A'} years`")

if crossover_point is not None:
    st.markdown(f"**Crossover Point**: `{crossover_point} years`")
else:
    st.markdown("**Crossover Point**: `Not reached within analysis horizon`")

st.subheader("Results Table")
st.dataframe(results.style.format("{:.2f}").set_table_styles([
    {"selector": "th", "props": [("min-width", "80px"), ("text-align", "center")]},
    {"selector": "td", "props": [("min-width", "100px"), ("text-align", "right")]}]))
