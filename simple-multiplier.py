try:
    import json
    from collections import OrderedDict
    import sys
except ImportError as e:
    missing_module = str(e).split(" ")[-1].replace("'", "")
    print(f"Error: The required module {missing_module} is not installed.")
    print(f"Please install it by running 'pip install {missing_module}' and then run the script again.")
    exit()

def validation(dic_text):
    n_max = len(dic_text['vstrands']) - 1              
    m_max = len(dic_text['vstrands'][0]['scaf']) - 1    
    n = 0
    while n <= n_max:
        m = 0
        while m <= m_max:
            if dic_text['vstrands'][n]['scaf'][m][0] != -1:
                unit_size = n + 1
            m += 1
        n += 1
    if (n_max + 1) % unit_size == 0:  
        return [n_max, m_max, unit_size]
    else:
        return 'error'
    
def write_json_file(filename: str, data: dict):
    with open(filename, 'w') as f:
        json.dump(data, f)

def periodic_copy(json_path):
    try:
        with open(json_path) as json_text:
            dic_text = json.load(json_text, object_pairs_hook=OrderedDict)
    except:
        raise Exception('There has been an error in input file or filepath')
    try:
        [n_max, m_max, unit_size] = validation(dic_text)
    except:
        raise Exception('JSON file is not in appropriate format. Follow README.')
    print('The basic unit with '+ str(unit_size) + ' helices has copied and is being pasted to ' + str(n_max + 1) + ' helices lattice')
    n = unit_size
    while n <= n_max:
        ref_h = n - unit_size
        dic_text['vstrands'][n]['loop'] = dic_text['vstrands'][ref_h]['loop']
        dic_text['vstrands'][n]['skip'] = dic_text['vstrands'][ref_h]['skip']
        dic_text['vstrands'][n]['stap_colors'] = dic_text['vstrands'][ref_h]['stap_colors']
        m = 0
        while m <= m_max:
            dic_text['vstrands'][n]['scaf'][m][1] = dic_text['vstrands'][ref_h]['scaf'][m][1]
            dic_text['vstrands'][n]['scaf'][m][3] = dic_text['vstrands'][ref_h]['scaf'][m][3]
            if dic_text['vstrands'][ref_h]['scaf'][m][0] != -1:
                dic_text['vstrands'][n]['scaf'][m][0] = dic_text['vstrands'][ref_h]['scaf'][m][0] + unit_size
            if dic_text['vstrands'][ref_h]['scaf'][m][2] != -1:
                dic_text['vstrands'][n]['scaf'][m][2] = dic_text['vstrands'][ref_h]['scaf'][m][2] + unit_size
            dic_text['vstrands'][n]['stap'][m][1] = dic_text['vstrands'][ref_h]['stap'][m][1]
            dic_text['vstrands'][n]['stap'][m][3] = dic_text['vstrands'][ref_h]['stap'][m][3]
            if dic_text['vstrands'][ref_h]['stap'][m][0] != -1:
                dic_text['vstrands'][n]['stap'][m][0] = dic_text['vstrands'][ref_h]['stap'][m][0] + unit_size
            if dic_text['vstrands'][ref_h]['stap'][m][2] != -1:
                dic_text['vstrands'][n]['stap'][m][2] = dic_text['vstrands'][ref_h]['stap'][m][2] + unit_size
            m += 1
        n += 1

        write_json_file(filename='output.json', data=dic_text)


if __name__ == "__main__":
    cadnano2_input_path = sys.argv[1]
    periodic_copy(cadnano2_input_path)
