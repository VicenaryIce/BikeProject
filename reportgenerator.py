import sqlite3
import base64
import os
from datetime import datetime

conn = sqlite3.connect("/home/sid/Desktop/BikeProject/table3.db")
cursor = conn.cursor()
cursor.execute("SELECT id, timestamp, description, image_path, latitude, longitude FROM photos")
rows = cursor.fetchall()
conn.close()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>Road Infrastructure Report</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; }
        h1 { color: #333; }
        .meta { color: #888; font-size: 14px; margin-bottom: 40px; }
        .entry { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 30px; overflow: hidden; }
        .entry img { width: 100%; max-height: 400px; object-fit: cover; }
        .entry-content { padding: 16px; }
        .timestamp { font-size: 12px; color: #999; margin-bottom: 8px; }
        .coords { font-size: 12px; color: #666; margin-bottom: 8px; }
        .coords a { color: #4a90e2; text-decoration: none; }
        p { margin: 0; color: #555; white-space: pre-line; }
    </style>
</head>
<body>
    <h1>Road Infrastructure Monitoring Report</h1>
    <p class="meta">Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" &nbsp;|&nbsp; Total entries: {len(rows)}</p>"

for row in rows:
    id, timestamp, description, image_path, latitude, longitude = row

    img_tag = ""
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        img_tag = f'<img src="data:image/jpeg;base64,{img_data}" alt="Road photo">'

    if latitude and longitude:
        maps_url = f"https://www.google.com/maps?q={latitude},{longitude}"
        coords_html = f'<div class="coords">📍 <a href="{maps_url}" target="_blank">{latitude:.6f}, {longitude:.6f} — View on Google Maps</a></div>'
    else:
        coords_html = '<div class="coords">📍 No GPS data</div>'

    html += f"""
    <div class="entry">
        {img_tag}
        <div class="entry-content">
            <div class="timestamp">{timestamp}</div>
            {coords_html}
            <p>{description}</p>
        </div>
    </div>
    """

html += "</body></html>"

with open("/home/sid/Desktop/BikeProject/report.html", "w") as f:
    f.write(html)

print("Report saved to report.html")