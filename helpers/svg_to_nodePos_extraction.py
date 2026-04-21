# This script extracts node positions from an SVG file and saves them in a JSON file.

import json
import os
import xml.etree.ElementTree as ET

svg_file = os.path.join(os.path.dirname(__file__), "network.svg")
tree = ET.parse(svg_file)
root = tree.getroot()

positions = {}

# Handle namespace if present
ns = ''
if '}' in root.tag:
    ns = root.tag.split('}')[0].strip('{')
    ns_map = {'svg': ns}
else:
    ns_map = {}

# Find all <text> elements
for text_elem in root.findall('.//svg:text', ns_map):
    node_id = text_elem.text.strip() if text_elem.text else None
    if not node_id:
        continue
    x = round(float(text_elem.get('x', '0')))
    y = round(float(text_elem.get('y', '0')))
    positions[node_id] = (x, y)

positions = dict(sorted(positions.items(), key=lambda item: int(item[0])))

print("Positions dictionary (chronological):")
for node, pos in positions.items():
    print(f"{node}: {pos}")


with open("data/positions.json", 'w') as f:
    json.dump(positions, f, indent=4)