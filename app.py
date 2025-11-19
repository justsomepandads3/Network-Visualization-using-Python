# app.py

import io
import os
from datetime import datetime

from flask import Flask, render_template_string, request, send_file
import pandas as pd
import matplotlib.pyplot as plt

METRICS_FILE = "metrics.csv"
ALERTS_FILE = "alerts.csv"

app = Flask(__name__)


def load_metrics():
    if not os.path.exists(METRICS_FILE):
        return pd.DataFrame(columns=[
            "timestamp", "device", "ip", "ifIndex",
            "ifDescr", "inOctets", "outOctets", "operStatus"
        ])
    df = pd.read_csv(METRICS_FILE)
    # Convert timestamp to datetime for grouping/plotting
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return pd.DataFrame(columns=[
            "timestamp", "device", "ip", "severity", "message"
        ])
    df = pd.read_csv(ALERTS_FILE)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@app.route("/")
def index():
    df = load_metrics()
    if df.empty:
        devices_summary = []
    else:
        # Get latest timestamp per device
        latest = df.sort_values("timestamp").groupby("device").tail(1)
        devices_summary = latest[["device", "ip", "timestamp"]].to_dict(orient="records")

    template = """
    <html>
    <head><title>Network Monitor - Overview</title></head>
    <body>
      <h1>Network Monitor - Overview</h1>
      {% if devices %}
        <table border="1" cellpadding="5">
          <tr><th>Device</th><th>IP</th><th>Last Data</th></tr>
          {% for d in devices %}
            <tr>
              <td>{{ d.device }}</td>
              <td>{{ d.ip }}</td>
              <td>{{ d.timestamp }}</td>
            </tr>
          {% endfor %}
        </table>
      {% else %}
        <p>No metrics collected yet. Run collector.py first.</p>
      {% endif %}

      <p><a href="/interfaces">View Interfaces</a></p>
      <p><a href="/alerts">View Alerts</a></p>
    </body>
    </html>
    """
    return render_template_string(template, devices=devices_summary)


@app.route("/interfaces")
def interfaces():
    df = load_metrics()
    if df.empty:
        html = "<p>No interface data yet.</p>"
        return html

    # Show last known state per device/interface
    df_sorted = df.sort_values("timestamp")
    last_state = df_sorted.groupby(["device", "ifIndex"]).tail(1)

    # Convert operStatus to human readable
    def status_to_str(x):
        return "UP" if x == 1 else f"DOWN({x})"

    last_state["status"] = last_state["operStatus"].apply(status_to_str)

    table_html = last_state[[
        "device", "ip", "ifIndex", "ifDescr", "status", "inOctets", "outOctets", "timestamp"
    ]].to_html(index=False)

    template = """
    <html>
    <head><title>Interfaces</title></head>
    <body>
      <h1>Interfaces - Latest Status</h1>
      {{ table|safe }}

      <h2>Plot Bandwidth Over Time</h2>
      <form method="get" action="/plot">
        Device: <input type="text" name="device" placeholder="R1">
        Interface Index: <input type="text" name="ifIndex" placeholder="1">
        <input type="submit" value="Plot">
      </form>

      <p><a href="/">Back to Overview</a></p>
    </body>
    </html>
    """
    return render_template_string(template, table=table_html)


@app.route("/plot")
def plot_interface():
    device = request.args.get("device")
    if_index = request.args.get("ifIndex")

    if not device or not if_index:
        return "<p>Please provide 'device' and 'ifIndex' query parameters.</p>"

    df = load_metrics()
    if df.empty:
        return "<p>No data available.</p>"

    df_sel = df[(df["device"] == device) & (df["ifIndex"].astype(str) == str(if_index))]
    if df_sel.empty:
        return f"<p>No data for device={device}, ifIndex={if_index}</p>"

    # Sort by time
    df_sel = df_sel.sort_values("timestamp")
    # Compute deltas to approximate bandwidth
    df_sel["delta_in"] = df_sel["inOctets"].diff()
    df_sel["delta_out"] = df_sel["outOctets"].diff()
    df_sel["delta_time"] = df_sel["timestamp"].diff().dt.total_seconds()

    # Avoid division by zero / NaN
    df_sel = df_sel.dropna(subset=["delta_in", "delta_out", "delta_time"])
    df_sel["in_bps"] = (df_sel["delta_in"] * 8) / df_sel["delta_time"]
    df_sel["out_bps"] = (df_sel["delta_out"] * 8) / df_sel["delta_time"]

    # Plot using matplotlib
    fig, ax = plt.subplots()
    ax.plot(df_sel["timestamp"], df_sel["in_bps"], label="In (bps)")
    ax.plot(df_sel["timestamp"], df_sel["out_bps"], label="Out (bps)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Bandwidth (bps)")
    ax.set_title(f"{device} ifIndex {if_index} Bandwidth")
    ax.legend()

    # Save to PNG in memory
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)

    return send_file(buf, mimetype="image/png")


@app.route("/alerts")
def alerts():
    df = load_alerts()
    if df.empty:
        return "<p>No alerts yet.</p>"

    df_sorted = df.sort_values("timestamp", ascending=False)

    table_html = df_sorted.to_html(index=False)

    template = """
    <html>
    <head><title>Alerts</title></head>
    <body>
      <h1>Alerts</h1>
      {{ table|safe }}
      <p><a href="/">Back to Overview</a></p>
    </body>
    </html>
    """
    return render_template_string(template, table=table_html)


if __name__ == "__main__":
    print("Starting Flask app on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
