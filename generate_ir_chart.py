#!/usr/bin/env python3
import csv
import sys
import os

def generate_html(csv_file):
    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found.")
        return

    events = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # ts, code, val
            events.append({
                'ts': float(row['ts']),
                'code': int(row['code']),
                'val': int(row['val'])
            })

    if not events:
        print("No events found.")
        return

    # Process events into HOT/COLD ranges
    ranges = []
    start_ts = events[0]['ts']
    current_state = False
    last_change_ts = start_ts
    
    # Track which point IDs are active
    active_points = set()

    # Time-ordered state transitions
    for e in events:
        if 16 <= e['code'] <= 23:
            point_id = (e['code'] - 16) // 2
            if e['val'] == 1023:
                active_points.discard(point_id)
            else:
                active_points.add(point_id)
        
        is_hot = len(active_points) > 0
        if is_hot != current_state:
            ranges.append({
                'state': current_state,
                'start': last_change_ts - start_ts,
                'end': e['ts'] - start_ts
            })
            current_state = is_hot
            last_change_ts = e['ts']

    # Add final range
    ranges.append({
        'state': current_state,
        'start': last_change_ts - start_ts,
        'end': events[-1]['ts'] - start_ts
    })

    # Generate SVG/HTML
    pixels_per_second = 1000 # High res: 1ms = 1px
    duration = events[-1]['ts'] - start_ts
    if duration == 0: duration = 1.0
    
    width = int(duration * pixels_per_second)
    height = 200
    scale = width / duration

    svg_content = ""
    for r in ranges:
        if r['state']: # HOT
            x = r['start'] * scale
            w = (r['end'] - r['start']) * scale
            # Minimum 2px width to ensure visibility
            svg_content += f'<rect x="{x}" y="50" width="{max(2, w)}" height="100" fill="#ff4444" />\n'
        else: # COLD
            x = r['start'] * scale
            svg_content += f'<line x1="{x}" y1="150" x2="{r["end"] * scale}" y2="150" stroke="#888" stroke-width="2" />\n'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Wii IR Signal Chart - {csv_file}</title>
        <style>
            body {{ background: #1a1a1b; color: #eee; font-family: sans-serif; padding: 20px; }}
            .container {{ overflow-x: auto; background: #2b2d2e; padding: 20px; border-radius: 8px; }}
            .info {{ margin-bottom: 20px; }}
            h1 {{ color: #00e676; }}
        </style>
    </head>
    <body>
        <h1>Wii-Eye Signal Analysis</h1>
        <div class="info">
            File: <b>{csv_file}</b><br>
            Total Duration: <b>{duration:.2f} s</b>
        </div>
        <div class="container">
            <svg width="{width}" height="{height}">
                <!-- Background grid -->
                <line x1="0" y1="150" x2="{width}" y2="150" stroke="#444" stroke-dasharray="5,5" />
                {svg_content}
                
                <!-- Time Markers -->
                <text x="0" y="180" fill="#888" font-size="12">0s</text>
                <text x="{width-40}" y="180" fill="#888" font-size="12">{duration:.2f}s</text>
            </svg>
        </div>
        <p>Red blocks = IR Points Detected (HOT). Gray line = No signal (COLD).</p>
    </body>
    </html>
    """
    
    output_file = csv_file.replace(".csv", ".html")
    with open(output_file, 'w') as f:
        f.write(html)
    print(f"Chart generated: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Find latest raw csv
        files = [f for f in os.listdir('.') if f.startswith("wiieye_raw_") and f.endswith(".csv")]
        if not files:
            print("No raw csv files found.")
        else:
            files.sort()
            generate_html(files[-1])
    else:
        generate_html(sys.argv[1])
