#!/usr/bin/env python3
import json
import os
import re

with open('/Users/liuyixing/项目/OREP/ai-scoring/output/pipeline_result_full.json', 'r') as f:
    data = json.load(f)

html_pages = data.get('html_pages', [])
output_dir = '/Users/liuyixing/项目/OREP/ai-scoring/output/pipeline_html'
os.makedirs(output_dir, exist_ok=True)

total_pages = 0
for i, batch_str in enumerate(html_pages):
    # Remove markdown code block markers
    cleaned = re.sub(r'^```json\n', '', batch_str)
    cleaned = re.sub(r'\n```$', '', cleaned)

    try:
        batch = json.loads(cleaned)
        # Handle both batch format (with "pages" array) and single page format
        if 'pages' in batch:
            pages = batch['pages']
        else:
            # Single page format
            pages = [batch]

        for page in pages:
            page_num = page.get('page_number', 0)
            html = page.get('html', '')
            if html:
                filename = f'page_{page_num:02d}.html'
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html)
                total_pages += 1
                print(f'Saved: {filename} ({len(html)} chars)')
    except json.JSONDecodeError as e:
        print(f'Batch {i+1}: JSON decode error: {e}')

print(f'\nTotal pages saved: {total_pages}')
