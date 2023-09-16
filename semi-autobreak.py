try:
    import argparse
    import json
    import csv
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    exit()

max_length = 60    # configure as you like
min_length = 22    # configure as you like
optimal_seed_len = 14    # configure as you like
acceptable_seed_len = 12    # configure as you like

def trace_domain(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str, max_length=max_length, min_length=min_length, optimal_seed_len=optimal_seed_len, acceptable_seed_len=acceptable_seed_len) -> tuple [dict, list]:
    # Change color of specific helices according to domain composition.
    tracer_pos = pos_num
    tracer_hel = helix_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    alphabet = [chr(i) for i in range(97,123)] * 10 # loops 10 times if alphabet is not enough 
    alphabet.extend(['!'] * 100)
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
            domain_string += '^' # ssDNA region
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
            if count >= acceptable_seed_len - 1:
                domain_string = domain_string[:- 1 * ( count )] + alphabet[domain_num].upper() * ( count + 1 )
            else:
                domain_string += alphabet[domain_num]
            count = 0
            domain_num += 1
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3]
    if count < 8 and count > 1:
        hel_history.append(tracer_hel)
    end = str(last_tracer_hel) + '[' + str(last_tracer_pos) + '],'
    total_len = len(domain_string)
    if total_len < min_length:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16776960  # Yellow when the sequence is too short.
    elif total_len > max_length:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711935  # Magenta when the sequence is too long.
    elif max_count >= optimal_seed_len - 1 :
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 255 # optimal strand is painted blue.
        hel_history = []                                                    # short domains in optimal strand is not counted
    elif max_count >= acceptable_seed_len - 1 :
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

def color_change(blueprint: dict, filename: str, output_file: str) -> list: 
    short_domain_list = []
    with open(filename, 'w') as f:
        f.write('start,end,domains,length\n') # Initialize report file with empty content
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            position = strand[0]
            blueprint, new_short_domains = trace_domain(blueprint, helix_id, position, strand_id, filename)
            short_domain_list.extend(new_short_domains)
    write_json_file(output_file, blueprint)
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

def autobreak_search(input_seq: str, min_length=min_length, max_length=max_length, acceptable_seed=acceptable_seed_len, optimal_seed=optimal_seed_len) -> list:
    def score_seq(sequence: str) -> float:  # at present the location of seeding domain is not considered
        seeding_domain = 0
        count = 0
        last_letter = '!'
        for i in range(len(sequence)):
            # check if i-th letter is upper case
            if last_letter != sequence[i]:
                count = 0
                last_letter = sequence[i]
            if sequence[i].isupper():
                count += 1
            if last_letter != sequence[i]:
                count = 0
                last_letter = sequence[i]
            if count >= optimal_seed or seeding_domain == 1:
                seeding_domain = 1
            elif count >= acceptable_seed:
                seeding_domain = 0.3        # 0.3 fold penalty to acceptable strand  
        return seeding_domain * ( 2 - (len(sequence) - min_length) / (max_length - min_length) )    # length penalty: Max length get half score than min length. Besides, shorter split gives more number of split strands each of them has score.

    patterns = [{'split_length': [], 'score': 0, 'remaining': input_seq}]
    completed = False
    final_patterns = []

    while not completed:
        new_patterns = []
        for pattern in patterns:
            remaining_seq = pattern['remaining']
            
            # If the remaining sequence is less than min_length, consider this pattern completed
            if len(remaining_seq) < min_length:
                final_patterns.append(pattern)
                continue
            
            # If there's no valid split for this pattern, also consider it completed
            valid_split_found = False
            for k in range(min_length, min(max_length + 1, len(remaining_seq) - 6)):
                if k + 3 < len(remaining_seq) and remaining_seq[k - 3] == remaining_seq[k + 3] and score_seq(remaining_seq[:k]) and score_seq(remaining_seq[k:]) and len(remaining_seq[k:]) >= min_length:
                    valid_split_found = True
                    split_length = pattern['split_length'] + [k]
                    score = pattern['score'] + score_seq(remaining_seq[:k]) # shorter split has higher score. Minimum 0.5.
                    new_patterns.append({'split_length': split_length, 'score': score, 'remaining': remaining_seq[k:]})
                    
            if not valid_split_found:
                final_patterns.append(pattern)
                    
        if not new_patterns:  # No new patterns found in this iteration
            completed = True
            
        patterns = new_patterns

    # Filtering out patterns with 'remaining' longer than max_length, add score from their individual remaining sequence
    final_patterns = [pattern for pattern in final_patterns if len(pattern['remaining']) <= max_length]
    for pattern in final_patterns:
        if score_seq(pattern['remaining']):
            pattern['score'] += score_seq(pattern['remaining'])
            pattern['split_length'].append(len(pattern['remaining']))   # for easy debugging

    if len(final_patterns) > 0:
        highest_score_pattern = max(final_patterns, key=lambda x: x['score'])
        if len(highest_score_pattern['split_length']) > 1:
            print("break to " + str(highest_score_pattern['split_length']) + " score: " + str(highest_score_pattern['score']) + ", highest among " + str(len(final_patterns)) + " breaking patterns")
        else:
            print("left as " + str(highest_score_pattern['split_length']) + " score: " + str(highest_score_pattern['score']))
    else:
        highest_score_pattern = {'split_length': []}
        print("skipped as no patterns met given criteria. manual breaking required")
    return highest_score_pattern['split_length'][:-1]

def autobreak(blueprint: dict, report_path: str) -> dict:
    # get csv as list
    with open(report_path, 'r') as f:
        reader = csv.reader(f)
        csv_list = [row for row in reader]
    # remove header
    csv_list.pop(0)
    # for each line, get sequence and split it
    for line in csv_list:
        start, _, sequence, _ = line
        print("autobreaking staple: " + str(start) + " ...")
        split_length = autobreak_search(sequence)
        hel, pos = start.split('[')
        hel = int(hel)
        pos = int(pos[:-1])
        if split_length != []:
            for i in range(len(blueprint['vstrands'][hel]['stap_colors'])):
                if blueprint['vstrands'][hel]['stap_colors'][i][0] == pos:
                    blueprint['vstrands'][hel]['stap_colors'][i][1] = 65280
            for i in range(len(split_length)):
                blueprint, hel, pos = break_3_end(blueprint, hel, pos, split_length[i])
    write_json_file('output_autobreak.json', blueprint)
    return blueprint

def break_3_end(blueprint: dict, hel_num: int, pos_num: int, split_length: int) -> tuple[dict, int, int]:
    tracer_pos = pos_num
    tracer_hel = hel_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    count = 0
    while count < split_length:
        last_tracer_hel = tracer_hel
        last_tracer_pos = tracer_pos
        tracer_hel = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2]
        tracer_pos = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3]
        count += 1
    blueprint['vstrands'][tracer_hel]['stap'][last_tracer_pos][2] = -1
    blueprint['vstrands'][tracer_hel]['stap'][last_tracer_pos][3] = -1
    blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][0] = -1
    blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][1] = -1
    blueprint['vstrands'][tracer_hel]['stap_colors'].append([tracer_pos,65280])
    # sort accending order 
    blueprint['vstrands'][tracer_hel]['stap_colors'].sort(key=lambda x: x[0])
    return blueprint, tracer_hel, tracer_pos

def autoconnect(blueprint: dict) -> dict:
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            position = strand[0]
            blueprint = reconnect_breaks(blueprint, helix_id, position)
    return blueprint

def reconnect_breaks(blueprint: dict, hel_num: int, pos_num: int) -> dict:
    tracer_pos = pos_num
    tracer_hel = hel_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    start_hel = tracer_hel
    start_pos = tracer_pos
    end_flag = False
    while not end_flag:
        while tracer_pos != -1:
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3]
        # connect break if next position is filled
        direction = last_tracer_pos - blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][1]    # if pos num of 3' is larger, +1, if smaller, -1
        if blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][0] == -1 and blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][1] == -1 and \
           blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][2] != -1 and blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][3] != -1 and \
           not (last_tracer_hel == start_hel and last_tracer_pos + direction == start_pos) :    # exclude circular connection
            blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][2] = last_tracer_hel
            blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos][3] = last_tracer_pos + direction
            blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][0] = last_tracer_hel
            blueprint['vstrands'][last_tracer_hel]['stap'][last_tracer_pos + direction][1] = last_tracer_pos
            # remove color
            for i in range(len(blueprint['vstrands'][last_tracer_hel]['stap_colors'])):
                if blueprint['vstrands'][last_tracer_hel]['stap_colors'][i][0] == last_tracer_pos + direction:
                    blueprint['vstrands'][last_tracer_hel]['stap_colors'].pop(i)
                    break
        else:
            end_flag = True
    return blueprint

args = get_args()
blueprint = load_json_file(args.input_file)
if blueprint:
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_count = color_change(blueprint,'domain_report.csv', 'output.json')
    short_domain_list = count_short_domain(count_list,short_domain_count)
    crossover_counter(blueprint, 'crossover_report.csv', short_domain_list)
    # below is for autobreak
    blueprint = autoconnect(blueprint)
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_count = color_change(blueprint,'domain_report_temp.csv', 'output_autoconnect.json')
    short_domain_list = count_short_domain(count_list,short_domain_count)
    crossover_counter(blueprint, 'crossover_report_temp.csv', short_domain_list)
    blueprint = autobreak(blueprint,'domain_report_temp.csv')
    # color change again and update report (comment out if you don't want to update autobreak color and report)
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_count = color_change(blueprint,'domain_report_autobreak.csv', 'output_autobreak.json') # overwrite colored blueprint
    short_domain_list = count_short_domain(count_list,short_domain_count)
    crossover_counter(blueprint, 'crossover_report_autobreak.csv', short_domain_list)
