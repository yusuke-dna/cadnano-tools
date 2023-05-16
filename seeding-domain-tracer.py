import argparse
parser = argparse.ArgumentParser()
parser.add_argument('arg1', type=str, help='The input JSON file path for cadnano2 design.')
args = parser.parse_args()

def color_change(filename: str) -> str: 
    import json
    try:
        with open(filename, 'r') as f:
            blueprint = json.load(f)
    except FileNotFoundError:
        return 'Error: File not found.'
    with open('report.txt', 'w') as g:
        g.write('')
    for i in range(len(blueprint['vstrands'])):
        for j in range(len(blueprint['vstrands'][i]['stap_colors'])):
            pos = blueprint['vstrands'][i]['stap_colors'][j][0]
#            print('staple starts from helix ' + str(i) + ' position ' + str(pos) + ' is ' + str(blueprint['vstrands'][i]['stap_colors'][j][1]))
            blueprint = trace_domain(blueprint,i,pos,j,'report.txt')
    with open('output.json', 'w') as h:
        json.dump(blueprint, h)
                
def trace_domain(blueprint: dict, helix_num: int, pos_num: int, strand_id: int, report_path: str) -> dict:
    # change color of specific helices according to domain composition.
    tracer_pos = pos_num
    tracer_hel = helix_num
    alphabet = [chr(i) for i in range(97,123)]
    alphabet.extend(['E'] * 100)
    domain_num = 0
    count = 0
    max_count = 0
    if blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == -1:
        domain_string = 'S'
    else:
        domain_string = 'a'

    while blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2] != -1 and domain_num < 26:
#        print(str(tracer_pos) + ' pos and helix ' + str(tracer_hel))
        if blueprint['vstrands'][tracer_hel]['scaf'][tracer_pos][0] == -1:
            count = 0
            domain_string += 'S' # ssDNA region
            new_tracer_hel = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]
            new_tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
            tracer_hel = new_tracer_hel
            tracer_pos = new_tracer_pos
        elif blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2] == tracer_hel: # if domain continues
#            print('domain continues')
            count += 1
            max_count = max(count,max_count)
            domain_string += alphabet[domain_num]
            tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
        else:  # domain broken
#            print('domain broken')
            count = 0
            domain_num += 1
            domain_string += alphabet[domain_num]
            tracer_pos = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][3]
            tracer_hel = blueprint['vstrands'][tracer_hel]['stap'][tracer_pos][2]        

    if max_count > 13:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 255 # OK strand is paineted blue.
    elif max_count > 11:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 65535 # acceptable strand is paineted cyan.
    else:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711680            
    with open(report_path, 'a') as f:
        f.write(domain_string + '\n')
    if len(domain_string) > 80:
        blueprint['vstrands'][helix_num]['stap_colors'][strand_id][1] = 16711935  # magenta when the sequence is too long.
    return blueprint

color_change(args.arg1)
