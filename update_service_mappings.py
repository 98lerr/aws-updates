#!/usr/bin/env python3
import json
import glob
import re
import os

# Paths
root = os.path.dirname(__file__)
mapping_file = os.path.join(root, 'service_mappings.json')

# Load existing mappings
with open(mapping_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
category_mappings = data.get('category_mappings', {})
service_descriptions = data.get('service_descriptions', {})

# Scan markdown outputs for service names
services_in_files = set()
pattern = re.compile(r'^- サービス: (.+)')
for md in glob.glob(os.path.join(root, 'output', '*.md')):
    with open(md, 'r', encoding='utf-8') as f:
        for line in f:
            m = pattern.match(line)
            if m:
                svc = m.group(1).strip()
                services_in_files.add(svc)

# Identify missing mappings
missing = services_in_files - set(category_mappings.keys())
if not missing:
    print('No new services to add.')
    exit(0)

# Add missing with defaults
for svc in sorted(missing):
    category_mappings[svc] = 'その他'
    service_descriptions[svc] = ''
    print(f'Added mapping for: {svc}')

# Save updated JSON
data['category_mappings'] = category_mappings
data['service_descriptions'] = service_descriptions
with open(mapping_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('service_mappings.json updated.')
