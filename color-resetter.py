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

def color_change(blueprint: dict, output_file: str): 
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            # make random number between 0 and 255.
            rand_hex = lambda: int(16777215 * random.random())
            rand_color = rand_hex()
            blueprint['vstrands'][helix_id]['stap_colors'][strand_id][1] = rand_color
    write_json_file(output_file, blueprint)

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    color_change(blueprint, 'output.json')
