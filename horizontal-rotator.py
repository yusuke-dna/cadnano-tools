import json
import copy
import argparse

def load_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def is_even_number_of_vstrands(vstrands):
    return len(vstrands) % 2 == 0

def has_horizontal_symmetry(vstrands, min_row, max_row):
    for vstrand in vstrands:
        symmetric_row = max_row - (vstrand["row"] - min_row)
        if not any(v["row"] == symmetric_row and v["col"] == vstrand["col"] for v in vstrands):
            return False
    return True

def validate(vstrands):
    if not vstrands:
        raise ValueError("No vstrands found in the file.")
    
    row_numbers = [vstrand["row"] for vstrand in vstrands]
    min_row, max_row = min(row_numbers), max(row_numbers)

    if not is_even_number_of_vstrands(vstrands):
        raise ValueError("The file does not have an even number of vstrands.")
    
    if not has_horizontal_symmetry(vstrands, min_row, max_row):
        raise ValueError("All vstrands do not have horizontally symmetric pairs as required.")

def create_symmetric_num_map(vstrands, min_row, max_row):
    symmetric_num_map = {}
    center_row = (min_row + max_row) / 2

    for vstrand in vstrands:
        symmetric_row = int(2 * center_row - vstrand["row"])
        symmetric_vstrand = next((v for v in vstrands if v["row"] == symmetric_row and v["col"] == vstrand["col"]), None)

        if symmetric_vstrand:
            symmetric_num_map[vstrand["num"]] = symmetric_vstrand["num"]
    
    return symmetric_num_map

def extend_empty_bp(vstrands, length):
    # insert empty bp to the end of vstrands
    for vstrand in vstrands:
        vstrand['scaf'].extend([[-1, -1, -1, -1]] * length)
        vstrand['stap'].extend([[-1, -1, -1, -1]] * length)
        vstrand['loop'].extend([0] * length)
        vstrand['skip'].extend([0] * length)

    return vstrands

def apply_symmetric_modifications(vstrands, symmetric_num_map):
    original_length = len(vstrands[0]['stap'])
    print(f"Initial position range is [0]-[{original_length}]. Applying modifications based on symmetric relationships...")
    original_vstrands = copy.deepcopy(vstrands)  # Deep copy to preserve the original data
    if original_length % 21 == 0:
        phase_adjust = 7
        vstrands = extend_empty_bp(vstrands, phase_adjust)
        if original_length % 32 == 0:
            raise ValueError("The length of the vstrands is both a multiple of 21 and 32. The code assume the file is honeycomb lattice.")
    else:
        phase_adjust = 0

    for vstrand in vstrands:
        symmetric_vstrand_num = symmetric_num_map[vstrand['num']]
        # Access the symmetric vstrand's original data from original_vstrands
        symmetric_vstrand = next((v for v in original_vstrands if v['num'] == symmetric_vstrand_num), None)

        if symmetric_vstrand:
            print(f"Modifying vstrand #{vstrand['num']} with data from its symmetric counterpart #{symmetric_vstrand_num}")
            
            # Handle items in scaf and stap arrays, correctly dealing with -1 values
            for key in ['scaf', 'stap']:
                modified_data = [
                    [symmetric_num_map[item[0]] if item[0] != -1 else -1, 
                     2 * original_length + phase_adjust - item[1] - 1 if item[1] != -1 else -1,
                     symmetric_num_map[item[2]] if item[2] != -1 else -1, 
                     2 * original_length + phase_adjust - item[3] - 1 if item[3] != -1 else -1
                    ]
                    for item in reversed(symmetric_vstrand[key])
                ]
                vstrand[key].extend(modified_data)
            
            # Reverse and append data for loop and skip directly
            vstrand['loop'].extend(reversed(symmetric_vstrand['loop']))
            vstrand['skip'].extend(reversed(symmetric_vstrand['skip']))
            
            # Append scafLoop and stapLoop directly without modifications
            vstrand['scafLoop'].extend(symmetric_vstrand['scafLoop'])
            vstrand['stapLoop'].extend(symmetric_vstrand['stapLoop'])
            
            # Adjust stap_colors using the specified equation
            adjusted_stap_colors = [
                [2 * original_length + phase_adjust - color[0] - 1, color[1]]
                for color in symmetric_vstrand['stap_colors']
            ]
            vstrand['stap_colors'].extend(adjusted_stap_colors)
    
    if phase_adjust:
        vstrands = extend_empty_bp(vstrands, 21-phase_adjust)

    print("Modifications applied.")


def main(file_path):
    data = load_data(file_path)
    vstrands = data["vstrands"]
    validate(vstrands)
    
    row_numbers = [vstrand["row"] for vstrand in vstrands]
    min_row, max_row = min(row_numbers), max(row_numbers)
    
    symmetric_num_map = create_symmetric_num_map(vstrands, min_row, max_row)
    print("Symmetric mapping:", symmetric_num_map)  # To visualize the symmetric mapping

    apply_symmetric_modifications(vstrands, symmetric_num_map)

    # If modifications to vstrands are made, save the modified data
    modified_file_path = file_path.replace('.json', '_modified.json')
    with open(modified_file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    print(f"Modified file saved to {modified_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Modify and validate DNA structure file based on symmetric relationships.')
    parser.add_argument('file_path', type=str, help='Path to the DNA structure file')
    args = parser.parse_args()

    main(args.file_path)
