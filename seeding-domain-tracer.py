try:
    import argparse
    import json
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

def count_crossover(blueprint: dict, report_path: str):
    with open(report_path, 'w') as f:
        f.write('hel,total,scaf,stap,len\n') # Initialize report file with empty content
    summary = ''
    for i in range(len(blueprint['vstrands'])):
        hel_dict = blueprint['vstrands'][i]
        count_scaf = 0
        count_stap = 0
        count = 0
        filled_len = len(hel_dict['scaf'])
        summary = summary + str(hel_dict['num']) + ','
        for j in range(len(hel_dict['scaf'])):
            if hel_dict['scaf'][j][0] != i and hel_dict['scaf'][j][0] != -1 and hel_dict['stap'][j][0] != -1 and hel_dict['stap'][j][2] != -1:  # Latter two equation exclude external loop. If accept loose connection as crossover, remove them
                count += 1
                count_scaf += 1
            elif hel_dict['scaf'][j][2] != i and hel_dict['scaf'][j][2] != -1 and hel_dict['stap'][j][0] != -1 and hel_dict['stap'][j][2] != -1:
                count += 1
                count_scaf += 1
            elif hel_dict['stap'][j][0] != i and hel_dict['stap'][j][0] != -1 and hel_dict['scaf'][j][0] != -1 and hel_dict['scaf'][j][2] != -1:
                count += 1
                count_stap += 1
            elif hel_dict['stap'][j][2] != i and hel_dict['stap'][j][2] != -1 and hel_dict['scaf'][j][0] != -1 and hel_dict['scaf'][j][2] != -1:
                count += 1
                count_stap += 1
            if hel_dict['scaf'][j][0] == -1 and hel_dict['scaf'][j][2] == -1 and hel_dict['stap'][j][0] == -1 and hel_dict['stap'][j][2] == -1:   # If both scaffold and staple are empty, it is subtracted from length of the helix
                filled_len -= 1
        summary = summary + f"{count},{count_scaf},{count_stap},{filled_len}\n"
    write_report(report_path, summary)

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    color_change(blueprint,'domain_report.csv')
    count_crossover(blueprint, 'crossover_report.csv')
