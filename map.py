#!/usr/bin/env python3
"""
map.py — Plot GPS track on an interactive OpenStreetMap tile map using folium.

Generates an HTML file and opens it in the default browser.
Full zoom/pan/layer-switching available in the browser.

Usage:
    uv run python map.py
    uv run python map.py --input my_walk.yaml
    uv run python map.py --output map.html   # save to specific file (still opens it)
    uv run python map.py --no-open           # save HTML but don't launch browser
"""

import argparse
import colorsys
import math
import os
import sys
import webbrowser

import folium
import yaml


DEFAULT_INPUT = "gps_track.yaml"
DEFAULT_OUTPUT = "map.html"


def load_points(path: str) -> list[dict]:
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f"File not found: {path!r}. Run record.py first.")
    if not isinstance(data, list) or len(data) == 0:
        sys.exit(f"No GPS points found in {path!r}.")
    return data


def rainbow_hex(t: float) -> str:
    """Map t in [0,1] to a blue→green→yellow→red hex colour."""
    r, g, b = colorsys.hsv_to_rgb(0.66 * (1 - t), 0.9, 0.95)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def parse_args():
    p = argparse.ArgumentParser(description="Show GPS track on an interactive map.")
    p.add_argument("--input",   default=DEFAULT_INPUT,  help=f"YAML track file (default: {DEFAULT_INPUT})")
    p.add_argument("--output",  default=DEFAULT_OUTPUT, help=f"HTML output file (default: {DEFAULT_OUTPUT})")
    p.add_argument("--no-open", action="store_true",    help="Don't open the browser automatically")
    return p.parse_args()


def main():
    args = parse_args()
    points = load_points(args.input)
    n = len(points)

    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]

    center_lat = sum(lats) / n
    center_lon = sum(lons) / n

    # Pick a starting zoom that fits the bounding box
    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)
    span = max(lat_span, lon_span)
    if span < 0.001:
        zoom = 17
    elif span < 0.01:
        zoom = 15
    elif span < 0.1:
        zoom = 13
    elif span < 1.0:
        zoom = 11
    else:
        zoom = 9

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom,
        control_scale=True,
    )

    # Layer switcher: add satellite + topo alternatives
    folium.TileLayer("OpenStreetMap",         name="Street").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Satellite (Esri)",
    ).add_to(m)
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topo",
    ).add_to(m)

    # Track polyline
    if n > 1:
        folium.PolyLine(
            locations=list(zip(lats, lons)),
            color="#4a90d9",
            weight=2.5,
            opacity=0.7,
        ).add_to(m)

    # Scatter dots coloured by time (blue→red)
    for i, p in enumerate(points):
        t = i / max(n - 1, 1)
        color = rainbow_hex(t)

        speed = p.get("speed_knots")
        alt   = p.get("altitude_m")
        sats  = p.get("num_sats")
        tooltip_parts = [f"<b>#{i + 1}</b>  {p['timestamp']}"]
        tooltip_parts.append(f"lat {p['lat']:.6f} &nbsp; lon {p['lon']:.6f}")
        if speed is not None:
            tooltip_parts.append(f"speed: {speed:.1f} kn")
        if alt is not None:
            tooltip_parts.append(f"alt: {alt:.1f} m")
        if sats is not None:
            tooltip_parts.append(f"sats: {sats}")

        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            tooltip="<br>".join(tooltip_parts),
        ).add_to(m)

    # Start marker (green) and end marker (red)
    folium.Marker(
        location=[lats[0], lons[0]],
        tooltip=f"<b>Start</b><br>{points[0]['timestamp']}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m)
    if n > 1:
        folium.Marker(
            location=[lats[-1], lons[-1]],
            tooltip=f"<b>End</b><br>{points[-1]['timestamp']}",
            icon=folium.Icon(color="red", icon="stop", prefix="fa"),
        ).add_to(m)

    # Fit map to the actual track bounds
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    # Layer control (top-right tile switcher)
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(args.output)
    abs_path = os.path.abspath(args.output)
    print(f"Saved {n} points → {abs_path}")

    if not args.no_open:
        webbrowser.open(f"file://{abs_path}")
        print("Opened in browser.")


if __name__ == "__main__":
    main()
