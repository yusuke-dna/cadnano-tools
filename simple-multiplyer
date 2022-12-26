#Set variables
#Path to cadnano2 json file
cadnano2_input_path = '/content/PATH_TO_FILE'

#Path to output json file (optional)
cadnano2_output_path = '/content/output.json'

def periodic_copy(json_path,output_path):

  #To be automatically calculated
  #Helices number (vertical size) of one domain
  unit_size = 22

  #Max helix number (repeat number * unit_size - 1)
  n_max = 65

  #horisontal size in base position (the most right base positon) 
  m_max = 1983

  import json
  import sys
  from collections import OrderedDict
  with open(json_path) as json_text:
    dic_text = json.load(json_text, object_pairs_hook=OrderedDict)

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
          m = m + 1
      n = n + 1

  if len(sys.argv)==2 :
    output = open(output_path, 'w')
    output.write(json.dumps(dic_text))
  else :
    return json.dumps(dic_text)

periodic_copy(cadnano2_input_path,cadnano2_output_path)
