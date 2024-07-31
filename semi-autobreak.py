try:
    import argparse
    import json
    import csv
    import os
    import sys
    from typing import List, Tuple, Dict
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    sys.exit(1)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', type=str, help='The input JSON file path for CADNano2 design.')
    parser.add_argument('-max', '-long', '-l', dest='max', type=int, default=80, help='Upper limit of staple length. Colored magenta if it exceeds.')
    parser.add_argument('-min', '-short', '-s', dest='min', type=int, default=18, help='Lower limit of staple length excluding ssDNA region. Colored yellow if too short.')
    parser.add_argument('-optimal', '-opt', '-o', dest='optimal', type=int, default=14, help='Minimum continuous hybridization length per staple for optimal coloring.')
    parser.add_argument('-acceptable', '-accept', '-a', dest='acceptable', type=int, default=12, help='Minimum continuous hybridization length per staple for acceptable coloring.')
    parser.add_argument('-manual', '-m', dest='manual', action='store_true', help='Only updates staple color, skips autobreak.')
    parser.add_argument('-connect', '-reconnect', '-c', dest='connect', action='store_true', help='Reconnect all breakpoints of staples, halting autobreak script.')
    parser.add_argument('-color', '-colour', '-intermediate', '-i', dest='color', action='store_true', help='Leaves intermediate JSON file displaying autobroken staples in green.')
    parser.add_argument('-limit', '-threshold', '-t', dest='limit', type=int, default=5000, help='Limiter to prevent combinatorial explosion.')
    parser.add_argument('-filter', '-screen', '-f', dest='filter', type=int, default=100, help='Filter to prevent combinatorial explosion.')
    parser.add_argument('-distance', '-d', dest='distance', type=int, default=3, help='Distance from 5-/3-end of staple and staple crossover.')
    parser.add_argument('-penalty', '-rate', '-p', dest='penalty', type=float, default=0.3, help='Penalty for acceptable seed length vs optimal.')
    parser.add_argument('-extension', '-ext', '-modification', '-mod', '-e', dest='extension', type=int, default=0, help='Number to be added to the length of white strands during length evaluation.')
    return parser.parse_args()

def load_json_file(filename: str) -> dict: 
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print('Error: File not found.')
        sys.exit(1)

def validate_lengths(min_length, max_length, optimal_seed_len, acceptable_seed_len):
    if min_length > max_length:
        raise ValueError(f'max length {max_length} should be larger than min length {min_length}.')
    if optimal_seed_len < acceptable_seed_len:
        raise ValueError(f'optimal seeding length {optimal_seed_len} should be larger than acceptable seed length {acceptable_seed_len}.')

def determine_lattice_type(blueprint: dict, distance: int) -> int:
    single_array = True
    sorted_vstrands = sorted(blueprint['vstrands'], key=lambda x: (x['row'], x['col']))
    row, col = sorted_vstrands[0]['row'], sorted_vstrands[0]['col']

    for vstrand in sorted_vstrands:
        if vstrand['row'] != row and vstrand['col'] != col:
            single_array = False
            break

    lattice_distance = (distance if len(blueprint['vstrands'][0]['scaf']) % 21 == 0 else 4) + 4 * single_array
    return lattice_distance, single_array

def generate_mappings(blueprint: dict) -> Tuple[Dict[int, int], Dict[int, int]]:
    num2id, id2num = {}, {}
    for i, vstrand in enumerate(blueprint['vstrands']):
        num2id[vstrand['num']] = i
        id2num[i] = vstrand['num']
    return num2id, id2num

def trace_domains_and_color(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str, settings: dict) -> Tuple[dict, List[int]]:
    global acceptable_strand_count, optimal_strand_count, rest_strand_count, short_strand_count, long_strand_count, fixed_strand_count
    alphabet = [chr(i) for i in range(97, 123)] * 50 + ['!'] * 5000
    domain_num, count, max_count = 0, 0, 0
    domain_string, hel_history = '', []

    def update_position_and_count():
        nonlocal count, max_count, domain_string, domain_num, tracer_hel, tracer_pos, last_tracer_hel, last_tracer_pos
        count = 0
        domain_string += alphabet[domain_num]
        domain_num += 1
        last_tracer_hel = tracer_hel
        last_tracer_pos = tracer_pos
        tracer_hel = blueprint['vstrands'][num2id[last_tracer_hel]]['stap'][last_tracer_pos][2]
        tracer_pos = blueprint['vstrands'][num2id[last_tracer_hel]]['stap'][tracer_pos][3]

    tracer_pos, tracer_hel = pos_num, helix_num
    last_tracer_pos, last_tracer_hel = tracer_pos, tracer_hel
    staple_3_end, start = 0, f"{tracer_hel}[{tracer_pos}]"

    while staple_3_end != -1:
        scaf, stap = blueprint['vstrands'][num2id[tracer_hel]]['scaf'], blueprint['vstrands'][num2id[tracer_hel]]['stap']
        
        if scaf[tracer_pos][0] == -1 and scaf[tracer_pos][2] == -1:
            count = 0
            domain_string += '^'
        elif stap[tracer_pos][2] == tracer_hel and scaf[tracer_pos][0] == tracer_hel:
            count += 1
            max_count = max(count, max_count)
            domain_string += alphabet[domain_num]
        else:
            if count > 1:
                hel_history.append(tracer_hel)
            if count >= settings['acceptable_seed_len'] - 1:
                domain_string = domain_string[:-count] + alphabet[domain_num].upper() * count
            update_position_and_count()

        staple_3_end = stap[tracer_pos][2]
        last_tracer_hel, last_tracer_pos = tracer_hel, tracer_pos
        tracer_hel, tracer_pos = stap[tracer_pos][2], stap[tracer_pos][3]

    if count > 1:
        hel_history.append(tracer_hel)

    end, total_len = f"{last_tracer_hel}[{last_tracer_pos}]", len(domain_string)
    core_len = len(domain_string.strip("^"))
    color_helix(blueprint, helix_num, strand_id, core_len, total_len, max_count, domain_string, settings)
    return blueprint, hel_history

def color_helix(blueprint: dict, helix_num: int, strand_id: int, core_len: int, total_len: int, max_count: int, domain_string: str, settings: dict):
    color_key = blueprint['vstrands'][num2id[helix_num]]['stap_colors'][strand_id]
    
    if color_key[1] == 16777215:
        domain_string += '^' * settings["extension"]
        fixed_strand_count += 1
    elif core_len < settings['min_length']:
        color_key[1] = 16776960
        short_strand_count += 1
    elif total_len > settings['max_length']:
        color_key[1] = 16711935
        long_strand_count += 1
    elif max_count >= settings['optimal_seed_len'] - 1:
        color_key[1] = 255
        optimal_strand_count += 1
    elif max_count >= settings['acceptable_seed_len'] - 1:
        color_key[1] = 65535
        acceptable_strand_count += 1
    else:
        color_key[1] = 16711680
        rest_strand_count += 1

def print_color_summary():
    total_strands = (acceptable_strand_count + optimal_strand_count + rest_strand_count + short_strand_count + long_strand_count)
    if total_strands > 0:
        print(f"Total strands: {total_strands}")
        print(f"Acceptable strands: {acceptable_strand_count}")
        print(f"Optimal strands: {optimal_strand_count}")
        print(f"Rest strands: {rest_strand_count}")
        print(f"Short strands: {short_strand_count}")
        print(f"Long strands: {long_strand_count}")
        print(f"Fixed strands (excluded from total strand): {fixed_strand_count}")
        print(f"Optimal strand percentage: {(optimal_strand_count / total_strands) * 100:.2f}%")
        print(f"Optimal and Acceptable strand percentage: {((optimal_strand_count + acceptable_strand_count) / total_strands) * 100:.2f}%")

def load_and_process_blueprint(args):
    blueprint = load_json_file(args.input_file)
    if blueprint:
        settings = {
            "min_length": args.min,
            "max_length": args.max,
            "optimal_seed_len": args.optimal,
            "acceptable_seed_len": args.acceptable,
            "distance": args.distance,
            "penalty": args.penalty,
            "extension": args.extension
        }
        validate_lengths(args.min, args.max, args.optimal, args.acceptable)
        distance, single_array = determine_lattice_type(blueprint, args.distance)
        num2id, id2num = generate_mappings(blueprint)
        if args.manual:
            handle_manual_mode(blueprint, settings, 'domain_report.csv', 'output.json')
        else:
            handle_autobreak_mode(blueprint, args, settings, num2id, id2num, distance)
        print(f"Options: min_length: {args.min}, max_length: {args.max}, optimal_seed_len: {args.optimal}, acceptable_seed_len: {args.acceptable}, distance: {distance}, penalty_rate: {args.penalty}, filter: {args.filter}, limit: {args.limit}")
        print_color_summary()

def handle_manual_mode(blueprint, settings, report_file, output_file):
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_list = process_colors(blueprint, settings, report_file, output_file)
    update_report(count_list, blueprint, short_domain_list, 'crossover_report.csv')

def handle_autobreak_mode(blueprint, args, settings, num2id, id2num, distance):
    blueprint = autoconnect(blueprint)
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_list = process_colors(blueprint, settings, 'domain_report_autoconnect.csv', 'output_autoconnect.json')
    update_report(count_list, blueprint, short_domain_list, 'crossover_report_autoconnect.csv')
    if not args.connect:
        blueprint = autobreak(blueprint, 'domain_report_autoconnect.csv', settings, args.color)
        short_domain_list = update_color_and_report(count_list, blueprint, settings, 'domain_report.csv', 'crossover_report.csv')

def process_colors(blueprint, settings, report_file, output_file):
    global acceptable_strand_count, optimal_strand_count, rest_strand_count, short_strand_count, long_strand_count, fixed_strand_count
    short_domain_list = []
    init_report(report_file)
    reset_global_counts()
    for helix_id, helix in enumerate(blueprint['vstrands']):
        for strand_id, strand in enumerate(helix['stap_colors']):
            position = strand[0]
            blueprint, new_short_domains = trace_domains_and_color(blueprint, id2num[helix_id], position, strand_id, report_file, settings)
            short_domain_list.extend(new_short_domains)
    save_json(output_file, blueprint)
    return short_domain_list

def update_report(count_list, blueprint, short_domain_list, report_file):
    short_domain_counts = count_short_domains(count_list, short_domain_list)
    generate_crossover_report(blueprint, report_file, short_domain_counts)

def reset_global_counts():
    global acceptable_strand_count, optimal_strand_count, rest_strand_count, short_strand_count, long_strand_count, fixed_strand_count
    acceptable_strand_count = 0
    optimal_strand_count = 0
    rest_strand_count = 0
    short_strand_count = 0
    long_strand_count = 0
    fixed_strand_count = 0

def init_report(filename):
    with open(filename, 'w') as f:
        f.write('start,end,domains,length\n')

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

def update_color_and_report(count_list, blueprint, settings, domain_report_file, crossover_report_file):
    count_list = [0] * len(blueprint['vstrands'])
    short_domain_list = process_colors(blueprint, settings, domain_report_file, 'output.json')
    update_report(count_list, blueprint, short_domain_list, crossover_report_file)
    clean_intermediate_files()

def clean_intermediate_files():
    try_remove('crossover_report_autoconnect.csv')
    try_remove('domain_report_autoconnect.csv')
    try_remove('output_autoconnect.json')

def try_remove(filename):
    if os.path.exists(filename):
        os.remove(filename)

def main():
    args = get_args()
    load_and_process_blueprint(args)

if __name__ == "__main__":
    main()
