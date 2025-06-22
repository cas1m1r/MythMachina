import os.path
import json
import sys

import os
from pathlib import Path
from markdown import markdown


def generate_graphic_novel_html(md_file, image_folder, output_file, title="Graphic Novel"):
    # Read markdown content
    with open(md_file, 'r', encoding='utf-8') as f:
        md_text = f.read()
    
    # Convert markdown to HTML
    html_body = markdown(md_text)
    
    # Find images in folder
    image_files = sorted([
        img for img in os.listdir(image_folder)
        if img.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    
    # Assemble HTML
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            background-color: #000;
            color: #f2f2f2;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
        }}
        .page {{
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            background-color: #111;
            border-radius: 10px;
        }}
        img {{
            width: 100%;
            border: 2px solid #333;
            border-radius: 6px;
            margin-bottom: 15px;
        }}
        h1, h2, h3 {{
            color: #e74c3c;
        }}
        p {{
            line-height: 1.6;
            white-space: pre-line;
        }}
    </style>
</head>
<body>
    <div class="page">
        <h1>{title}</h1>
        {html_body}
    </div>
"""
    
    # Embed images after the markdown body
    for img in image_files:
        html_template += f'''
    <div class="page">
        <img src="{img}" alt="{img}">
    </div>
'''
    
    html_template += "</body></html>"
    
    # Save HTML output
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(html_template)
    
    print(f"✅ HTML saved to {output_file}")


def format_entry(entry):
    """Format a single JSON entry into readable prose-style script."""
    if not isinstance(entry, dict):
        return ""

    # Narrator-style entry: {'The Synthesizer': "some narration"}
    narration = entry.get("Narration")
    # Structured character entry
    character = entry.get("Character")
    decision = entry.get("ImagePrompt").strip()

    return f"\nNarrator:\n{narration}\n{character}:\n{decision}\n"

def allegory_json_to_script(json_data, output_path="allegory_script_cleaned.txt"):
    """
    Converts a list of mixed narrator/dialogue entries into a readable prose-style script.
    """
    lines = ["\n=== Scene 1 ===\n"]
    idata = f'![img]('
    n = 1
    for entry in json_data[1:]:
        line = format_entry(entry)
        if line:
            lines.append(line)
        n+=1
        lines.append(f'\n{idata}{entry["ImageResult"]})\n\n')
        lines.append(f"\n=== Scene {n} ===\n")
    setup = json_data[0]['Initial Seed']
    full_text = f'Setup:\n{setup}\n' + "\n".join(lines).replace('\n\n','\n')
    # remove empty lines
    
    # Save output to file
    out_path =  output_path
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    return out_path


if __name__ == '__main__':
    file_in = 'conflict_President_Trump_has_deployed_t_06112025.json'
    if len(sys.argv) > 1:
        file_in = sys.argv[1]
    file_out = file_in.split('.')[0]+'_novelized.txt'
    data = allegory_json_to_script(json.loads(open(file_in,'r').read()), file_out)