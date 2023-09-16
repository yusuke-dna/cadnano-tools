try:
    import argparse
    import json
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    exit()

def trace_domain(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str) -> tuple [dict, list]:
    # Change color of specific helices according to domain composition.
    tracer_pos = pos_num
    tracer_hel = helix_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    length_max = 80    # configure as you like
    length_min = 20    # configure as you like
    optimal_seed_len = 14
    acceptable_seeding_len = 12
    alphabet = [chr(i) for i in range(97,123)]
    alphabet.extend(['E'] * 100)
    domain_num = 0
    count = 0
    max_count = 0
    hel_history = []
    start = str(tracer_hel) + '[' + str(tracer_pos) + '],'
    staple_3_end = 0
    domain_string = ''

    while staple_3_end != -1:
        if blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == -1 and blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][2] == -1: # Both end of scaffold is monitored. If scaffold is blank.
            staple_3_end = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]
            count = 0
            domain_string += 'S' # ssDNA region
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3]
        elif blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2] == tracer_hel and blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == tracer_hel: # if domain continues
            staple_3_end = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]
            count += 1
            max_count = max(count,max_count)
            domain_string += alphabet[domain_num]
            last_tracer_pos = tracer_pos
            tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
        else:  # domain broken
            staple_3_end = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]
            if count < 8 and count > 1:
                hel_history.append(tracer_hel)
            count = 0
            domain_string += alphabet[domain_num]
            domain_num += 1
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3]
    if count < 8 and count > 1:
        hel_history.append(tracer_hel)
    end = str(last_tracer_hel) + '[' + str(last_tracer_pos) + '],'
    total_len = len(domain_string)
    if total_len < length_min:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16776960  # Yellow when the sequence is too short.
    elif total_len > length_max:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711935  # Magenta when the sequence is too long.
    elif max_count >= optimal_seed_len - 1 :
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 255 # optimal strand is painted blue.
        hel_history = []                                                    # short domains in optimal strand is not counted
    elif max_count >= acceptable_seeding_len - 1 :
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 65535 # Acceptable strand is painted cyan.
        hel_history = []                                                      # short domains in acceptable strand is not counted
    else:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711680 # Rest bad strands are painted red
    write_report(report_path, start + end + domain_string + ',' + str(total_len)) 
    return blueprint, hel_history

def crossover_counter(blueprint: dict, report_path: str, short_domain_list: list):
    with open(report_path, 'w') as f:
        f.write('hel,total,scaf,stap,len,short_domain\n') # Initialize report file with empty content
    summary = ''
    for i in range(len(blueprint['vstrands'])):
        neighbours = get_neighbour_helix(blueprint, i)
        hel_dict = blueprint['vstrands'][i]
        filled_len = len(hel_dict['scaf'])
        for j in range(len(neighbours)):
            summary = summary + str(hel_dict['num']) + '-' + str(neighbours[j]) + ','
            count = 0
            count_stap = 0
            count_scaf = 0
            for k in range(len(hel_dict['scaf'])):
                if hel_dict['scaf'][k][0] == neighbours[j] and hel_dict['scaf'][k][1] == k and not (hel_dict['stap'][k][0] == -1 and hel_dict['stap'][k][2] == -1):  # Second equotion excludes spacer (bridged positons unmatch). Latter two equations exclude external loop. If accept loose connection as crossover, remove them
                    count += 1
                    count_scaf += 1
                elif hel_dict['scaf'][k][2] == neighbours[j] and hel_dict['scaf'][k][3] == k and not (hel_dict['stap'][k][0] == -1 and hel_dict['stap'][k][2] == -1):
                    count += 1
                    count_scaf += 1
                elif hel_dict['stap'][k][0] == neighbours[j] and hel_dict['stap'][k][1] == k and not (hel_dict['scaf'][k][0] == -1 and hel_dict['scaf'][k][2] == -1):
                    count += 1
                    count_stap += 1
                elif hel_dict['stap'][k][2] == neighbours[j] and hel_dict['stap'][k][3] == k and not (hel_dict['scaf'][k][0] == -1 and hel_dict['scaf'][k][2] == -1):
                    count += 1
                    count_stap += 1
                if j == 0 and hel_dict['scaf'][k][0] == -1 and hel_dict['scaf'][k][2] == -1 and hel_dict['stap'][k][0] == -1 and hel_dict['stap'][k][2] == -1:   # If both scaffold and staple are empty, it is subtracted from length of the helix
                    filled_len -= 1
            summary = summary + f"{count},{count_scaf},{count_stap},{filled_len},{short_domain_list[i]}\n"
    write_report(report_path, summary)

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

def color_change(blueprint: dict, filename: str) -> list: 
    short_domain_list = []
    with open(filename, 'w') as f:
        f.write('start,end,domains,length\n') # Initialize report file with empty content
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            position = strand[0]
            blueprint, new_short_domains = trace_domain(blueprint, helix_id, position, strand_id, filename)
            short_domain_list.extend(new_short_domains)
    write_json_file('output.json', blueprint)
    return short_domain_list

def is_empty_helix(vstrands: list) -> bool:
    empty = True
    for i in range(len(vstrands['scaf'])):
        if not (vstrands['scaf'][i][0] == -1 and vstrands['scaf'][i][1] == -1 and vstrands['scaf'][i][2] == -1 and vstrands['scaf'][i][3] == -1 and vstrands['stap'][i][0] == -1 and vstrands['stap'][i][1] == -1 and vstrands['stap'][i][2] == -1 and vstrands['stap'][i][3] == -1) :
            empty = False
    return empty

def get_neighbour_helix(blueprint: dict, helix_id: int) -> list:
    # Get helix id of neighbours
    neighbour_list = []
    if not is_empty_helix(blueprint['vstrands'][helix_id]):
        # if neibour is triangle (row + col is odd) arrangement
        if (blueprint['vstrands'][helix_id]['row'] + blueprint['vstrands'][helix_id]['col']) % 2 == 0:
            for helix_num in range(len(blueprint['vstrands'])):
                candidate = -1
                if blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] - 1 and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row']:
                    candidate = helix_num
                elif blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] + 1 and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row']:
                    candidate = helix_num
                elif blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row'] - 1:
                    candidate = helix_num
                if candidate != -1 and not is_empty_helix(blueprint['vstrands'][candidate]):
                    neighbour_list.append(candidate)
        # if neibour is reverse triangle arrangement
        else:
            for helix_num in range(len(blueprint['vstrands'])):
                candidate = -1
                if blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] - 1 and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row']:
                    candidate = helix_num
                elif blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] + 1 and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row']:
                    candidate = helix_num
                elif blueprint['vstrands'][helix_num]['col'] == blueprint['vstrands'][helix_id]['col'] and blueprint['vstrands'][helix_num]['row'] == blueprint['vstrands'][helix_id]['row'] + 1:
                    candidate = helix_num
                if candidate != -1 and not is_empty_helix(blueprint['vstrands'][candidate]):
                    neighbour_list.append(candidate)
    return neighbour_list

def count_short_domain(count_list,short_domain_list) -> list:
    # Count number of short domains in each helix
    for helix_id in short_domain_list:
        count_list[helix_id] += 1
    return count_list

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_count = color_change(blueprint,'domain_report.csv')
    short_domain_list = count_short_domain(count_list,short_domain_count)
    crossover_counter(blueprint, 'crossover_report.csv', short_domain_list)
