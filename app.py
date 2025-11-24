# app.py

import base64
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
    if "sysUpTimeCentisecs" not in df.columns:
        df["sysUpTimeCentisecs"] = pd.NA
    return df


def fig_to_base64(fig):
    """Convert a matplotlib figure to a base64 string."""
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def format_uptime(centisecs):
    if pd.isna(centisecs):
        return "unknown"
    try:
        total_seconds = int(centisecs) / 100
    except (ValueError, TypeError):
        return "unknown"

    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{int(days)}d")
    if hours or days:
        parts.append(f"{int(hours)}h")
    parts.append(f"{int(minutes)}m")
    parts.append(f"{int(seconds)}s")
    return " ".join(parts)


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
    charts = {"uptime": None, "bandwidth": None, "traffic": None}
    devices_summary = []

    if not df.empty:
        # Get latest timestamp per device
        latest = df.sort_values("timestamp").groupby("device").tail(1)
        latest["uptime"] = latest["sysUpTimeCentisecs"].apply(format_uptime)
        latest["status"] = latest["operStatus"].apply(lambda x: "Yes" if x == 1 else "No")
        devices_summary = latest[["device", "ip", "timestamp", "uptime", "status"]].to_dict(orient="records")

        # Uptime visualization (bar)
        if not latest.empty:
            uptime_hours = latest.copy()
            uptime_hours["uptime_hours"] = (
                pd.to_numeric(uptime_hours["sysUpTimeCentisecs"], errors="coerce").fillna(0) / 100 / 3600
            )
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(uptime_hours["device"], uptime_hours["uptime_hours"], color="#2e86de")
            ax.set_title("Device Uptime (hours)")
            ax.set_ylabel("Hours")
            ax.set_xlabel("Device")
            ax.set_ylim(bottom=0)
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            charts["uptime"] = fig_to_base64(fig)

        # Prepare bandwidth/traffic data
        df_sorted = df.sort_values(["device", "ifIndex", "timestamp"]).copy()
        for col in ["inOctets", "outOctets"]:
            df_sorted[col] = pd.to_numeric(df_sorted[col], errors="coerce")
        df_sorted["delta_in"] = df_sorted.groupby(["device", "ifIndex"])["inOctets"].diff()
        df_sorted["delta_out"] = df_sorted.groupby(["device", "ifIndex"])["outOctets"].diff()
        df_sorted["delta_time"] = (
            df_sorted.groupby(["device", "ifIndex"])["timestamp"].diff().dt.total_seconds()
        )
        df_bps = df_sorted.dropna(subset=["delta_in", "delta_out", "delta_time"]).copy()
        df_bps = df_bps[df_bps["delta_time"] > 0]
        df_bps["in_bps"] = (df_bps["delta_in"] * 8) / df_bps["delta_time"]
        df_bps["out_bps"] = (df_bps["delta_out"] * 8) / df_bps["delta_time"]
        df_bps = df_bps[(df_bps["in_bps"] >= 0) & (df_bps["out_bps"] >= 0)]

        if not df_bps.empty:
            # Bandwidth per device (avg bps)
            by_device = df_bps.groupby("device")[["in_bps", "out_bps"]].mean().sort_values("in_bps", ascending=False)
            fig, ax = plt.subplots(figsize=(6, 3))
            x = range(len(by_device))
            ax.bar(x, by_device["in_bps"], width=0.4, label="Inbound", color="#27ae60")
            ax.bar([i + 0.4 for i in x], by_device["out_bps"], width=0.4, label="Outbound", color="#e67e22")
            ax.set_xticks([i + 0.2 for i in x])
            ax.set_xticklabels(by_device.index, rotation=15)
            ax.set_ylabel("Average bps")
            ax.set_title("Average Bandwidth by Device")
            ax.legend()
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            charts["bandwidth"] = fig_to_base64(fig)

            # Traffic flow over time (sum)
            over_time = df_bps.groupby("timestamp")[["in_bps", "out_bps"]].sum().tail(25)
            if not over_time.empty:
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(over_time.index, over_time["in_bps"], label="Inbound", color="#27ae60")
                ax.plot(over_time.index, over_time["out_bps"], label="Outbound", color="#e67e22")
                ax.fill_between(over_time.index, over_time["in_bps"], alpha=0.1, color="#27ae60")
                ax.fill_between(over_time.index, over_time["out_bps"], alpha=0.1, color="#e67e22")
                ax.set_title("Network Traffic Flow (recent samples)")
                ax.set_ylabel("bps")
                ax.set_xlabel("Time")
                ax.legend()
                ax.grid(True, linestyle="--", alpha=0.4)
                fig.autofmt_xdate()
                charts["traffic"] = fig_to_base64(fig)

    template = """
    <html>
    <head>
      <title>Network Monitor - Overview</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 30px; background: #f6f8fb; color: #1f2a37; }
        h1 { margin-bottom: 10px; }
        table { border-collapse: collapse; width: 100%; background: #fff; margin-bottom: 20px; }
        th, td { border: 1px solid #d0d7e2; padding: 8px 10px; text-align: left; }
        th { background: #e9eef6; }
        .status-yes { color: #1e8449; font-weight: bold; }
        .status-no { color: #c0392b; font-weight: bold; }
        .charts { display: flex; flex-wrap: wrap; gap: 20px; }
        .card { background: #fff; border: 1px solid #d0d7e2; border-radius: 8px; padding: 15px; flex: 1 1 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .card img { width: 100%; height: auto; }
        .links { margin-top: 20px; }
        .links a { margin-right: 15px; color: #2e86de; text-decoration: none; }
      </style>
    </head>
    <body>
      <h1>Network Monitor - Overview</h1>
      {% if devices %}
        <table border="1" cellpadding="5">
          <tr><th>Device</th><th>IP</th><th>Last Data</th><th>Uptime</th><th>Status</th></tr>
          {% for d in devices %}
            <tr>
              <td>{{ d.device }}</td>
              <td>{{ d.ip }}</td>
              <td>{{ d.timestamp }}</td>
              <td>{{ d.uptime }}</td>
              <td class="status-{{ d.status|lower }}">{{ d.status }}</td>
            </tr>
          {% endfor %}
        </table>
        <div class="charts">
          {% if charts.uptime %}
          <div class="card">
            <h3>Uptime Snapshot</h3>
            <img src="data:image/png;base64,{{ charts.uptime }}" alt="Uptime chart">
          </div>
          {% endif %}
          {% if charts.bandwidth %}
          <div class="card">
            <h3>Bandwidth Averages</h3>
            <img src="data:image/png;base64,{{ charts.bandwidth }}" alt="Bandwidth chart">
          </div>
          {% endif %}
          {% if charts.traffic %}
          <div class="card">
            <h3>Traffic Flow</h3>
            <img src="data:image/png;base64,{{ charts.traffic }}" alt="Traffic chart">
          </div>
          {% endif %}
        </div>
      {% else %}
        <p>No metrics collected yet. Run collector.py first.</p>
      {% endif %}

      <div class="links">
        <a href="/interfaces">View Interfaces</a>
        <a href="/alerts">View Alerts</a>
      </div>
    </body>
    </html>
    """
    return render_template_string(template, devices=devices_summary, charts=charts)


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
    last_state["uptime"] = last_state["sysUpTimeCentisecs"].apply(format_uptime)

    table_html = last_state[[
        "device",
        "ip",
        "ifIndex",
        "ifDescr",
        "status",
        "uptime",
        "inOctets",
        "outOctets",
        "timestamp"
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
