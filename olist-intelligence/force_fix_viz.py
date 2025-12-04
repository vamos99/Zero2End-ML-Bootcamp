import json
import os
import glob

# Get all .ipynb files in notebooks directory
notebook_files = glob.glob("notebooks/*.ipynb")

if not notebook_files:
    print("❌ No notebooks found in notebooks/ directory!")
    exit(1)

print(f"Found {len(notebook_files)} notebooks.")

for nb_path in notebook_files:
    print(f"Processing {nb_path}...")
    
    with open(nb_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)
    
    # Find first code cell
    first_code_cell = None
    for cell in nb['cells']:
        if cell['cell_type'] == 'code':
            first_code_cell = cell
            break
    
    if first_code_cell:
        source = "".join(first_code_cell['source'])
        if "pio.renderers.default" not in source:
            # Prepend the config
            config_lines = [
                "\n",
                "# GitHub'da grafiklerin görünmesi için statik render (png) kullanıyoruz\n",
                "import plotly.io as pio\n",
                "pio.renderers.default = \"png\"\n",
                "\n"
            ]
            # Insert at the beginning of the cell source
            first_code_cell['source'] = config_lines + first_code_cell['source']
            
            with open(nb_path, 'w', encoding='utf-8') as f:
                json.dump(nb, f, indent=1, ensure_ascii=False)
            print(f"✅ Injected PNG config into {nb_path}")
        else:
            print(f"ℹ️ {nb_path} already has PNG config.")
    else:
        print(f"⚠️ No code cell found in {nb_path}")
