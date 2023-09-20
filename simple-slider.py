import json, argparse
# simple slide specified number to right. -n to right.

argperser = argparse.ArgumentParser(description='slide specified number to right. -n to right.')
argperser.add_argument('file_path', type=str, help='cadnano file path')
argperser.add_argument('number', type=int, help='number to slide')
args = argperser.parse_args()

# get cadnano json file as dict.
with open(args.file_path, 'r') as f:
    cadnano_dict = json.load(f)
    if cadnano_dict:
        if len(cadnano_dict['vstrands'][0]['scaf'])%21 == 0 and args.number == 0:
            slide_num = 21
        elif len(cadnano_dict['vstrands'][0]['scaf'])%32 == 0 and args.number == 0:
            slide_num = 32
        else:
            slide_num = args.number
            if slide_num % 21 != 0 and slide_num % 32 != 0:
                raise Exception('slide number must be multiple of 21 or 32.')
    else:
        raise Exception('cadnano file is empty.')

def left_empty(vstrands, num):
    isempty = True
    for i in range(num):
        if vstrands['scaf'][i] != [-1,-1,-1,-1]:
            isempty = False
        if vstrands['stap'][i] != [-1,-1,-1,-1]:
            isempty = False
        if vstrands['loop'][i] != 0:
            isempty = False
        if vstrands['skip'][i] != 0:
            isempty = False
    return isempty

if slide_num >= 0:
    for i in range(len(cadnano_dict['vstrands'])):
        for j in range(len(cadnano_dict['vstrands'][i]['scaf'])):
            cadnano_dict['vstrands'][i]['scaf'][j][1] = -1 if cadnano_dict['vstrands'][i]['scaf'][j][1] == -1 else cadnano_dict['vstrands'][i]['scaf'][j][1] + slide_num
            cadnano_dict['vstrands'][i]['scaf'][j][3] = -1 if cadnano_dict['vstrands'][i]['scaf'][j][3] == -1 else cadnano_dict['vstrands'][i]['scaf'][j][3] + slide_num
        cadnano_dict['vstrands'][i]['scaf'] = [[-1,-1,-1,-1]] * slide_num + cadnano_dict['vstrands'][i]['scaf']
        for j in range(len(cadnano_dict['vstrands'][i]['stap'])):
            cadnano_dict['vstrands'][i]['stap'][j][1] = -1 if cadnano_dict['vstrands'][i]['stap'][j][1] == -1 else cadnano_dict['vstrands'][i]['stap'][j][1] + slide_num
            cadnano_dict['vstrands'][i]['stap'][j][3] = -1 if cadnano_dict['vstrands'][i]['stap'][j][3] == -1 else cadnano_dict['vstrands'][i]['stap'][j][3] + slide_num
        cadnano_dict['vstrands'][i]['stap'] = [[-1,-1,-1,-1]] * slide_num + cadnano_dict['vstrands'][i]['stap']
        cadnano_dict['vstrands'][i]['loop'] = [0] * slide_num + cadnano_dict['vstrands'][i]['loop']
        cadnano_dict['vstrands'][i]['skip'] = [0] * slide_num + cadnano_dict['vstrands'][i]['skip']
        for j in range(len(cadnano_dict['vstrands'][i]['stap_colors'])):
            cadnano_dict['vstrands'][i]['stap_colors'][j][0] = cadnano_dict['vstrands'][i]['stap_colors'][j][0] + slide_num

elif left_empty(cadnano_dict['vstrands'], -slide_num):
    for i in range(len(cadnano_dict['vstrands'])):
        cadnano_dict['vstrands'][i]['scaf'] = cadnano_dict['vstrands'][i]['scaf'][slide_num:]
        for j in range(len(cadnano_dict['vstrands'][i]['scaf'])):
            cadnano_dict['vstrands'][i]['scaf'][j][1] = -1 if cadnano_dict['vstrands'][i]['scaf'][j][1] == -1 else cadnano_dict['vstrands'][i]['scaf'][j][1] + slide_num
            cadnano_dict['vstrands'][i]['scaf'][j][3] = -1 if cadnano_dict['vstrands'][i]['scaf'][j][3] == -1 else cadnano_dict['vstrands'][i]['scaf'][j][3] + slide_num
        cadnano_dict['vstrands'][i]['stap'] = cadnano_dict['vstrands'][i]['stap'][slide_num:]
        for j in range(len(cadnano_dict['vstrands'][i]['stap'])):
            cadnano_dict['vstrands'][i]['stap'][j][1] = -1 if cadnano_dict['vstrands'][i]['stap'][j][1] == -1 else cadnano_dict['vstrands'][i]['stap'][j][1] + slide_num
            cadnano_dict['vstrands'][i]['stap'][j][3] = -1 if cadnano_dict['vstrands'][i]['stap'][j][3] == -1 else cadnano_dict['vstrands'][i]['stap'][j][3] + slide_num
        cadnano_dict['vstrands'][i]['loop'] = cadnano_dict['vstrands'][i]['loop'][slide_num:]
        cadnano_dict['vstrands'][i]['skip'] = cadnano_dict['vstrands'][i]['skip'][slide_num:]
        for j in range(len(cadnano_dict['vstrands'][i]['stap_colors'])):
            cadnano_dict['vstrands'][i]['stap_colors'][j][0] = cadnano_dict['vstrands'][i]['stap_colors'][j][0] + slide_num
else:
    raise Exception('left empty space is not enough.')

# write cadnano json file as output.json
with open('output.json', 'w') as f:
    json.dump(cadnano_dict, f)
