# This file is a deprecated copy of color-resetter.py, made by mistake. This file will be removed soon. 
try:
    import argparse
    import json
    import random
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    exit()

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', type=str, help='The input JSON file path for cadnano2 design.')
    parser.add_argument('-target', type=str, help='The target color to change from in hex color code.')
    parser.add_argument('-new', type=str, help='The new color to change to in hex color code.')
    return parser.parse_args()

def load_json_file(filename: str) -> dict: 
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print('Error: File not found.')
        return None

def write_json_file(filename: str, data: dict):
    with open(filename, 'w') as f:
        json.dump(data, f)

def hex_color_to_int(hex_color):
    # Remove the leading '#' if present
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    
    # Convert the hexadecimal string to an integer
    return int(hex_color, 16)

def color_change(blueprint: dict, output_file: str, from_color: int = None, to_color: int = None): 
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            # make random number between 0 and 255.
            rand_hex = lambda: int(16777215 * random.random())
            if from_color == None and to_color == None:
                new_color = rand_hex()
                blueprint['vstrands'][helix_id]['stap_colors'][strand_id][1] = new_color
            elif blueprint['vstrands'][helix_id]['stap_colors'][strand_id][1] == from_color:
                new_color = to_color
                blueprint['vstrands'][helix_id]['stap_colors'][strand_id][1] = new_color
    write_json_file(output_file, blueprint)

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    from_color = hex_color_to_int(args.target) if args.target else None
    to_color = hex_color_to_int(args.new) if args.new else None
    color_change(blueprint, 'output.json', from_color, to_color)
