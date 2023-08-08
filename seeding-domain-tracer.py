import argparse
import json

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

def write_report(filename: str, content: str):
    with open(filename, 'a') as f:
        f.write(content + '\n')

def color_change(blueprint: dict, filename: str): 
    with open(filename, 'w') as f:
        f.write('start,end,domains\n') # Initialize report file with empty content
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            position = strand[0]
            blueprint = trace_domain(blueprint, helix_id, position, strand_id, filename)
    write_json_file('output.json', blueprint)
                
def trace_domain(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str) -> dict:
    # Change color of specific helices according to domain composition.
    tracer_pos = pos_num
    tracer_hel = helix_num
    alphabet = [chr(i) for i in range(97,123)]
    alphabet.extend(['E'] * 100)
    domain_num = 0
    count = 0
    max_count = 0
    start = str(tracer_hel) + '[' + str(tracer_pos) + '],'
    if blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == -1:
        domain_string = 'S'
    else:
        domain_string = 'a'

    while blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2] != -1:
        if blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == -1:
            count = 0
            domain_string += 'S' # ssDNA region
            new_tracer_hel = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]
            new_tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
            tracer_hel = new_tracer_hel
            tracer_pos = new_tracer_pos
        elif blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2] == tracer_hel and blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == tracer_hel: # if domain continues
            count += 1
            max_count = max(count,max_count)
            domain_string += alphabet[domain_num]
            tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
        else:  # domain broken
            count = 0
            domain_num += 1
            domain_string += alphabet[domain_num]
            tracer_pos_break = tracer_pos
            tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
            tracer_hel = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos_break][2]        
    end = str(tracer_hel) + '[' + str(tracer_pos) + '],'
    if max_count >= 13:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 255 # OK strand is painted blue.
    elif max_count >= 11:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 65535 # Acceptable strand is painted cyan.
    else:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711680 # Rest bad strands are painted red
    write_report(report_path, start + end + domain_string)
    if len(domain_string) > 80:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711935  # Magenta when the sequence is too long.
    return blueprint

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    color_change(blueprint,'report.txt')
