# Under construction

import json

# load the cadnano2 file
with open('filename.json', 'r') as f:
    data = json.load(f)

# modify the color of a strand
helix_id = 1  # replace with the desired helix ID
strand_id = 1  # replace with the desired strand ID
new_color = 65280  # replace with the desired color in number
data['vstrands'][strand_id]['stap_colors'][strand_id][1] = new_color

# save the modified cadnano2 file
with open('filename_modified.json', 'w') as f:
    json.dump(data, f)
