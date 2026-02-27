#!/usr/bin/env python3
"""
visualize.py — Plot GPS points from a YAML track file as a scatterplot.

Usage:
    uv run python visualize.py                          # reads gps_track.yaml
    uv run python visualize.py --input track.yaml
    uv run python visualize.py --no-line               # dots only, no connecting line
    uv run python visualize.py --save map.png          # save instead of showing
"""

import argparse
import sys

import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import yaml


DEFAULT_INPUT = "gps_track.yaml"


def load_points(path: str) -> list[dict]:
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f"File not found: {path!r}. Run record.py first.")
    if not isinstance(data, list) or len(data) == 0:
        sys.exit(f"No GPS points found in {path!r}.")
    return data


def parse_args():
    p = argparse.ArgumentParser(description="Visualize GPS track from YAML.")
    p.add_argument("--input", default=DEFAULT_INPUT, help=f"YAML file (default: {DEFAULT_INPUT})")
    p.add_argument("--no-line", action="store_true", help="Show only scatter dots, no connecting line")
    p.add_argument("--save", metavar="FILE", help="Save figure to FILE instead of displaying")
    return p.parse_args()


def main():
    args = parse_args()
    points = load_points(args.input)

    lats = np.array([p["lat"] for p in points])
    lons = np.array([p["lon"] for p in points])
    n = len(points)

    # Color points by order: blue (start) → red (end)
    colors = cm.plasma(np.linspace(0, 1, n))

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    # Connecting track line
    if not args.no_line and n > 1:
        ax.plot(lons, lats, color="#4a4a8a", linewidth=1.2, zorder=1, alpha=0.6)

    # Scatter points colored by time
    sc = ax.scatter(lons, lats, c=np.linspace(0, 1, n), cmap="plasma",
                    s=20, zorder=2, edgecolors="none", alpha=0.9)

    # Start / end markers
    ax.scatter(lons[0], lats[0], s=120, marker="^", color="#00ff88",
               zorder=3, label="Start", edgecolors="white", linewidths=0.8)
    ax.scatter(lons[-1], lats[-1], s=120, marker="s", color="#ff4444",
               zorder=3, label="End", edgecolors="white", linewidths=0.8)

    cbar = fig.colorbar(sc, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Time (earlier → later)", color="white")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    # Speed overlay if available
    speeds = [p.get("speed_knots") for p in points]
    if any(s is not None for s in speeds):
        valid_speeds = [s for s in speeds if s is not None]
        avg_speed = np.mean(valid_speeds)
        max_speed = np.max(valid_speeds)
        ax.text(0.02, 0.04,
                f"Avg speed: {avg_speed:.1f} kn   Max: {max_speed:.1f} kn",
                transform=ax.transAxes, color="#aaaacc", fontsize=9)

    ax.set_xlabel("Longitude", color="white")
    ax.set_ylabel("Latitude", color="white")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444466")

    # Aspect ratio: 1 lon degree ≠ 1 lat degree; correct for latitude
    mid_lat = np.mean(lats)
    lon_scale = np.cos(np.radians(mid_lat))
    ax.set_aspect(1.0 / lon_scale)

    ax.set_title(f"GPS Track — {n} points", color="white", fontsize=14, pad=12)
    ax.legend(facecolor="#1a1a2e", edgecolor="#444466", labelcolor="white", fontsize=9)

    plt.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        print(f"Saved to {args.save!r}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
