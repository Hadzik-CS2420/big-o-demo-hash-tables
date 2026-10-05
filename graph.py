#!/usr/bin/env python3
"""Build, run the Big O demo, and generate Plotly charts -- one command."""

import csv
import subprocess
import sys
import webbrowser
from pathlib import Path

try:
    import plotly.graph_objects as go
except ImportError:
    print("plotly not found -- installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.graph_objects as go

REPO_DIR = Path(__file__).resolve().parent
BUILD_DIR = REPO_DIR / "out" / "build" / "x64-debug"
CSV_FILE = REPO_DIR / "results.csv"
OUTPUT_HTML = REPO_DIR / "charts.html"


# ── Build & Run ──────────────────────────────────────────────────────────────

def find_executable():
    """Locate the compiled executable across common build layouts."""
    out_build = REPO_DIR / "out" / "build"
    if out_build.exists():
        for exe in out_build.rglob("big-o-demo-hash-tables.exe"):
            if "CompilerId" not in str(exe):
                return exe

    candidates = [
        REPO_DIR / "build" / "big-o-demo-hash-tables.exe",
        REPO_DIR / "build" / "Debug" / "big-o-demo-hash-tables.exe",
        REPO_DIR / "build" / "Release" / "big-o-demo-hash-tables.exe",
        REPO_DIR / "build" / "big-o-demo-hash-tables",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def build_and_run():
    exe = find_executable()
    if exe is None:
        print("No executable found -- building with CMake...")
        build_dir = REPO_DIR / "build"
        subprocess.run(["cmake", "-B", str(build_dir), str(REPO_DIR)], check=True)
        subprocess.run(["cmake", "--build", str(build_dir)], check=True)
        exe = find_executable()
        if exe is None:
            sys.exit("ERROR: build succeeded but executable not found")

    print(f"Running {exe.name}...\n")
    subprocess.run([str(exe)], cwd=str(REPO_DIR), check=True)


# ── Parse CSV ─────────────────────────────────────────────────────────────────

def read_results():
    with open(CSV_FILE) as f:
        return list(csv.DictReader(f))


def group_by_operation(rows):
    """Return {operation: {structure: {n: [...], time: [...], complexity: str}}}"""
    ops = {}
    for row in rows:
        op = row["operation"]
        struct = row["structure"]
        if op not in ops:
            ops[op] = {}
        if struct not in ops[op]:
            ops[op][struct] = {"n": [], "time": [], "complexity": ""}
        ops[op][struct]["n"].append(int(row["n"]))
        ops[op][struct]["time"].append(float(row["time_us"]))
        ops[op][struct]["complexity"] = row["complexity"]
    return ops


# ── Chart Generation ──────────────────────────────────────────────────────────

COLORS = {
    "Chaining": "#2563eb",  # blue
    "Probing":  "#dc2626",  # red
}


def build_chart(op_name, structures):
    fig = go.Figure()

    for struct_name, data in structures.items():
        fig.add_trace(go.Scatter(
            x=data["n"],
            y=data["time"],
            mode="lines+markers",
            name=f"{struct_name} -- {data['complexity']}",
            line=dict(color=COLORS.get(struct_name, "#3b82f6"), width=3),
            marker=dict(size=10),
        ))

    fig.update_layout(
        title=dict(text=op_name, font=dict(size=22)),
        xaxis_title="n (input size)",
        yaxis_title="Time per operation (\u00b5s)",
        yaxis=dict(rangemode="tozero"),
        template="plotly_white",
        font=dict(size=14),
        legend=dict(font=dict(size=14)),
        margin=dict(t=60, b=60),
        height=450,
    )
    return fig


def generate_html(operations):
    chart_divs = []
    img_dir = REPO_DIR / "images"
    img_dir.mkdir(exist_ok=True)

    for i, (op_name, structures) in enumerate(operations.items()):
        fig = build_chart(op_name, structures)
        chart_divs.append(
            fig.to_html(full_html=False, include_plotlyjs=(i == 0))
        )
        # Export static SVG for Canvas page embedding
        svg_name = op_name.lower().replace(" ", "_").replace("/", "_") + ".svg"
        try:
            fig.write_image(str(img_dir / svg_name), format="svg", width=900, height=450)
            print(f"  SVG: images/{svg_name}")
        except Exception:
            pass  # kaleido not installed -- skip SVG export

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Big O Demo: Hash Tables</title>
<style>
  body {{ background: #ffffff; color: #1a1a1a; font-family: system-ui, sans-serif;
         max-width: 960px; margin: 0 auto; padding: 2rem; }}
  h1 {{ text-align: center; margin-bottom: 0.25rem; }}
  p.sub {{ text-align: center; color: #666; margin-top: 0; }}
  .chart {{ margin-bottom: 2rem; }}
</style>
</head>
<body>
<h1>Big O Demo: Hash Tables</h1>
<p class="sub">Chaining vs. Linear Probing operation timing</p>
{"".join(f'<div class="chart">{div}</div>' for div in chart_divs)}
</body>
</html>"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"\nCharts written to {OUTPUT_HTML}")
    webbrowser.open(OUTPUT_HTML.as_uri())


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--graph-only" not in sys.argv:
        build_and_run()
    else:
        if not CSV_FILE.exists():
            sys.exit(f"ERROR: {CSV_FILE} not found -- run without --graph-only first")
        print("Skipping build/run -- using existing results.csv")
    rows = read_results()
    operations = group_by_operation(rows)
    generate_html(operations)
