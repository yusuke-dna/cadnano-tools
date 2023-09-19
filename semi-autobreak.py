try:
    import argparse
    import json
    import csv
    import os
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    exit()

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', type=str, help='The input JSON file path for cadnano2 design.')
    parser.add_argument('-max', '-long', '-l', dest='max', type=int, default=80, help='20 by default. Upper limit of staple length. Colored magenta if exceeds')
    parser.add_argument('-min', '-short', '-s', dest='min', type=int, default=20, help='80 by default. Lower limit of staple length. Colored yellow if the staple is shorter than this number')
    parser.add_argument('-optimal', '-opt', '-o', dest='optimal' , type=int, default=14, help='14 by default. Requirement of minimum continuous hybridization length per staple. Satisifying staples are colored blue')
    parser.add_argument('-acceptable', '-accept', '-a', dest='acceptable', type=int, default=12, help='12 by default. Loosen requirement of minimum continuous hybridization length per staple. Satisfying staples are colored cyan')
    parser.add_argument('-manual', '-m', dest='manual', action='store_true', help='Only staple color is updated and autobreak is skipped. The same behaviour as seeding-domain-tracer')
    parser.add_argument('-connect', '-reconnect' '-c', dest='connect', action='store_true', help='Reconnect all break point of staples, by halting autobreak script')
    parser.add_argument('-color', '-colour' '-intermediate' '-i', dest='color', action='store_true', help='Leave intermediate JSON file displaying autobroken staples in green')
    parser.add_argument('-limit', '-threshold', '-t', dest='limit', type=int, default=5000, help='5000 by default. Limiter to prevent combinatorial explosion. The threshold to apply filter (below) breaking pattern variation. For low restriction designs (long average domain length), weight (**(optimal_seed_len/average_domain_len)) is automatically applied to reduce wasteful calculation cost, resulting in no siginficant differences')
    parser.add_argument('-filter', '-f', dest='filter', type=int, default=100, help='100 by default. Filter to prevent combinatorial explosion. The pattern exceeding threshold (above) will be filtered to this number. For low restriction designs (long average domain length), weight (**(optimal_seed_len/average_domain_len)) is automatically applied to reduce wasteful calculation cost, resulting in no siginficant differences')
    parser.add_argument('-distance', '-d', dest='distance', type=int, default=3, help='3 by default (or 4 if square lattice, apart from the case path panel width is multiple of 672). Distance from 5-/3-end of staple and staple crossover (not considering scaffold crossover)')   
    return parser.parse_args()

def load_json_file(filename: str) -> dict: 
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print('Error: File not found.')
        return None

args = get_args()
min_length = args.min
max_length = args.max
if min_length > max_length:
    raise ValueError(f'max length {max_length} shuold be larger than min length {min_length}') 
optimal_seed_len = args.optimal
acceptable_seed_len = args.acceptable
if optimal_seed_len < acceptable_seed_len:
    raise ValueError(f'optimal seeding length {optimal_seed_len} shuold be larger than acceptable seed length {acceptable_seed_len}') 
blueprint = load_json_file(args.input_file)
if blueprint:
    single_array = True
    sorted_vstrands = sorted(blueprint['vstrands'], key=lambda x: x['col'])
    sorted_vstrands = sorted(sorted_vstrands, key=lambda x: x['row'])
    row = sorted_vstrands[0]['row']
    col = sorted_vstrands[0]['col']
    debug = []
    for i in range(len(sorted_vstrands)):
        if sorted_vstrands[i]['row'] == row ^ sorted_vstrands[i]['col'] == col:
            single_array = False
    if args.distance != 3:
        distance = args.distance
    elif len(blueprint['vstrands'][0]['scaf']) % 21 == 0:
        distance = args.distance + args.distance * single_array
    else:
        distance = 4 + 4 * single_array

    # reverse dict to convert num in json file to vstrands list index.
    num = {}
    for i in range(len(blueprint['vstrands'])):
        num.update({blueprint['vstrands'][i]['num']: i})

    print(num)

def trace_domain(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str, max_length=args.max, min_length=args.min, optimal_seed_len=args.optimal, acceptable_seed_len=args.acceptable) -> tuple [dict, list]:
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
        if blueprint['vstrands'][num[tracer_hel]]['scaf'][tracer_pos][0] == -1 and blueprint['vstrands'][num[tracer_hel]]['scaf'][tracer_pos][2] == -1: # Both end of scaffold is monitored. If scaffold is blank.
            staple_3_end = blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][2]
            count = 0
            domain_string += '^' # ssDNA region
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3]
        elif blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][2] == tracer_hel and blueprint['vstrands'][num[tracer_hel]]['scaf'][tracer_pos][0] == tracer_hel: # if domain continues
            staple_3_end = blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][2]
            count += 1
            max_count = max(count,max_count)
            domain_string += alphabet[domain_num]
            last_tracer_pos = tracer_pos
            tracer_pos = blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][3]
        else:  # domain broken
            staple_3_end = blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][2]
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
            tracer_hel = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3]
    if count < 8 and count > 1:
        hel_history.append(tracer_hel)
    end = str(last_tracer_hel) + '[' + str(last_tracer_pos) + '],'
    total_len = len(domain_string)
    if blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] == 0:         # black is left unprocessed.
        pass
    elif total_len < min_length:
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
        hel_dict = blueprint['vstrands'][num[i]]
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

def short_domain_counter(count_list,short_domain_list) -> list:
    # Count number of short domains in each helix
    for helix_id in short_domain_list:
        count_list[helix_id] += 1
    return count_list

def autobreak_search(input_seq: str, min_length=args.min, max_length=args.max, acceptable_seed_len=args.acceptable, optimal_seed_len=args.optimal, limit_num=args.limit, filter_num=args.filter, distance=distance) -> list:
    char_counts = {}
    middle_seq = input_seq.strip('^!')
    i = 0
    j = 0
    char_counts = {j: 0}
    char = 'a'
    while i < len(middle_seq):
        if middle_seq[i] == char:
            char_counts[j] += 1
        else:
            char = middle_seq[i]
            j += 1
            char_counts.update({j: 1})
        i += 1
    average_domain_length = sum(char_counts.values()) / (j + 1)
    output_string = f'limit/filter weight: ^({acceptable_seed_len/average_domain_length:.3f}) is applied.' if average_domain_length > acceptable_seed_len else ''
    print(f"average domain length is {average_domain_length:.3f}. {output_string}")
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
            if count >= optimal_seed_len or seeding_domain == 1:
                seeding_domain = 1
            elif count >= acceptable_seed_len:
                seeding_domain = 0.3        # 0.3 fold penalty to acceptable strand
        return seeding_domain * ( 2 - (len(sequence) - min_length) / (max_length - min_length) )    # length penalty: Max length gets half score than min length. Besides, shorter split gives more number of split strands each of them has score.

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
                if k + distance - 1 < len(remaining_seq) and remaining_seq[k - distance] == remaining_seq[k + distance - 1] and score_seq(remaining_seq[:k]) and score_seq(remaining_seq[k:]) and len(remaining_seq[k:]) >= min_length:
                    valid_split_found = True
                    split_length = pattern['split_length'] + [k]
                    score = pattern['score'] + score_seq(remaining_seq[:k])
                    new_patterns.append({'split_length': split_length, 'score': score, 'remaining': remaining_seq[k:]})
                    
            if not valid_split_found:
                final_patterns.append(pattern)
        weight_limit = int(limit_num ** (min(1, acceptable_seed_len/average_domain_length))) # if the strand is continuous sequence, apply weight to limit to reduce wasteful calculation
        weight_filter = int(filter_num ** (min(1, acceptable_seed_len/average_domain_length))) # if the strand is continuous sequence, apply weight to limit to reduce wasteful calculation
        if not new_patterns:  # No new patterns found in this iteration
            completed = True
        elif len(new_patterns) > weight_limit:  # for each cycle, if the pattern exceed limit, filtered to top 1000th score, with risk of listing local optimum.
            print(f'calculation is filtered to top {weight_filter} patterns as pattern limit reached: {len(new_patterns)}/{weight_limit}')
            print(f'found {len(final_patterns)} breaking patterns and still searching from rest {len(new_patterns)} patterns ...')
            top_scored_patterns = sorted(new_patterns, key=lambda x: x['score'], reverse=True)[:weight_filter]
            new_patterns = top_scored_patterns
        else:
            print(f'found {len(final_patterns)} breaking patterns and still searching from rest {len(new_patterns)} patterns ...')
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
            print(f"break to {highest_score_pattern['split_length']} score: {highest_score_pattern['score']:.4f}, highest among {len(final_patterns)} breaking patterns")
        else:
            print("left as " + str(highest_score_pattern['split_length']) + " score: " + str(highest_score_pattern['score']))
    else:
        highest_score_pattern = {'split_length': []}
        print("skipped as no patterns met given criteria. manual breaking required")
    return highest_score_pattern['split_length'][:-1]

def autobreak(blueprint: dict, report_path: str, color=False) -> dict:
    # get csv as list
    with open(report_path, 'r') as f:
        reader = csv.reader(f)
        csv_list = [row for row in reader]
    # remove header
    csv_list.pop(0)
    # for each line, get sequence and split it
    for line in csv_list:
        start, _, sequence, _ = line
        print("autobreaking staple: " + str(start) + " len=" + str(len(sequence)) + "...")
        split_length = autobreak_search(sequence)
        hel, pos = start.split('[')
        hel = int(hel)
        pos = int(pos[:-1])
        if split_length != []:
            for i in range(len(blueprint['vstrands'][num[hel]]['stap_colors'])):
                if blueprint['vstrands'][num[hel]]['stap_colors'][i][0] == pos:
                    blueprint['vstrands'][num[hel]]['stap_colors'][i][1] = 65280
            for i in range(len(split_length)):
                blueprint, hel, pos = break_3_end(blueprint, hel, pos, split_length[i])
    if color:   # if intermediate file kept or unsaved.
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
        tracer_hel = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][2]
        tracer_pos = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3]
        count += 1
    blueprint['vstrands'][num[tracer_hel]]['stap'][last_tracer_pos][2] = -1
    blueprint['vstrands'][num[tracer_hel]]['stap'][last_tracer_pos][3] = -1
    blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][0] = -1
    blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][1] = -1
    blueprint['vstrands'][num[tracer_hel]]['stap_colors'].append([tracer_pos,65280])
    # sort accending order 
    blueprint['vstrands'][num[tracer_hel]]['stap_colors'].sort(key=lambda x: x[0])
    return blueprint, tracer_hel, tracer_pos

def autoconnect(blueprint: dict) -> dict:
    staple_list = {}
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            if helix_id not in staple_list:
                staple_list[helix_id] = []
            staple_list[helix_id].append(strand[0])
    for helix_id in staple_list:
        for position in staple_list[helix_id]:
            blueprint = reconnect_breaks(blueprint, helix_id, position)
    return blueprint

def reconnect_breaks(blueprint: dict, hel_num: int, pos_num: int) -> dict:
    tracer_pos = pos_num
    tracer_hel = hel_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    # reverse tracing to 5'end to avoid loop creation
    while not(blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][0] == -1 and blueprint['vstrands'][num[tracer_hel]]['stap'][tracer_pos][1] == -1):
        last_tracer_hel = tracer_hel
        last_tracer_pos = tracer_pos
        tracer_hel = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][0]
        tracer_pos = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][1]
    start_hel = tracer_hel
    start_pos = tracer_pos
    tracer_pos = pos_num
    tracer_hel = hel_num
    last_tracer_pos = tracer_pos
    last_tracer_hel = tracer_hel
    end_flag = False
    while not end_flag:
        while tracer_pos != -1:
            last_tracer_hel = tracer_hel
            last_tracer_pos = tracer_pos
            tracer_hel = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][2]
            tracer_pos = blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3]
        # connect break if next position is filled
        if blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][1] != -1:
            direction = last_tracer_pos - blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][1]    # if pos num of 3' is larger, +1, if smaller, -1
        else:
            direction = - last_tracer_pos + blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3] 
        if blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][0] == -1 and blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][1] == -1 and \
           blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][2] != -1 and blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][3] != -1:
            if not (last_tracer_hel == start_hel and last_tracer_pos + direction == start_pos) :    # exclude circular connection
                # fill gap and remove the color of connected staple, only when the 3' strand is not black.
                for i in range(len(blueprint['vstrands'][num[last_tracer_hel]]['stap_colors'])):
                    if blueprint['vstrands'][num[last_tracer_hel]]['stap_colors'][i][0] == last_tracer_pos + direction and blueprint['vstrands'][num[last_tracer_hel]]['stap_colors'][i][1] == 0: # Black strand is left intact, for manual editing.
                        end_flag = True
                        print("Strand: " + str(start_hel) + "[" + str(start_pos) + "] was left broken as specified")
                    elif blueprint['vstrands'][num[last_tracer_hel]]['stap_colors'][i][0] == last_tracer_pos + direction:
                        blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][2] = last_tracer_hel
                        blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos][3] = last_tracer_pos + direction
                        blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][0] = last_tracer_hel
                        blueprint['vstrands'][num[last_tracer_hel]]['stap'][last_tracer_pos + direction][1] = last_tracer_pos
                        print("reconnected strand: " + str(start_hel) + "[" + str(start_pos) + "] at " + str(last_tracer_hel) + "[" + str(last_tracer_pos + direction) + "]")
                        blueprint['vstrands'][num[last_tracer_hel]]['stap_colors'].pop(i)
                        break
            else:
                print("Strand: " + str(start_hel) + "[" + str(start_pos) + "] was left broken to avold loop")
                end_flag = True              
        else:
            end_flag = True
    return blueprint

blueprint = load_json_file(args.input_file)
if blueprint:
    if args.manual:
        count_list = [0] * len(blueprint['vstrands'])
        short_domain_count = color_change(blueprint,'domain_report.csv', 'output.json')
        short_domain_list = short_domain_counter(count_list,short_domain_count)
        crossover_counter(blueprint, 'crossover_report.csv', short_domain_list)
    else:
        # below is for autobreak
        blueprint = autoconnect(blueprint)
        count_list = [0] * len(blueprint['vstrands'])
        short_domain_count = color_change(blueprint,'domain_report_autoconnect.csv', 'output_autoconnect.json')
        short_domain_list = short_domain_counter(count_list,short_domain_count)
        crossover_counter(blueprint, 'crossover_report_autoconnect.csv', short_domain_list)
        if not args.connect:
            blueprint = autobreak(blueprint,'domain_report_autoconnect.csv', color=args.color)
            # color change again and update report
            count_list = [0] * len(blueprint['vstrands'])
            short_domain_count = color_change(blueprint,'domain_report.csv', 'output.json') # overwrite colored blueprint
            short_domain_list = short_domain_counter(count_list,short_domain_count)
            crossover_counter(blueprint, 'crossover_report.csv', short_domain_list)
            # Cleaning directory
            if os.path.exists('crossover_report_autoconnect.csv'):
                os.remove('crossover_report_autoconnect.csv')
            if os.path.exists('domain_report_autoconnect.csv'):
                os.remove('domain_report_autoconnect.csv')
            if os.path.exists('output_autoconnect.json'):
                os.remove('output_autoconnect.json')
