# Cadnano Tools
This repository contains several microtools designed to enhance the functionality of cadnano, a popular software for designing DNA nanostructures.

## Semi-Autobreak
Derived from `Seeding Domain Tracer`. A python script that support users' semi-automatic optimisation of the breaking points of staples in DNA origami design. It removes exiting staple break and introduce breaks with following criteria if possible. If impossible, the strand is left intact. The user will try to rearrange crossover position refering generated reports, and repeat running the script to make all strands blue.
### Criteria
- All staple should have seeding domain, continuous hybridisation to the scaffold, with longer than 11 nt, or preferably > 13 nt. (configurable in the script)
- The length of all split staple should be within the specified range, ≥ 20 and ≤ 80 as default. (configurable in the script)
- Most optimal breaking point is selected among all possible combination, according to its `score`. The score represents the quality of split staples. Shorter staple is preferable (min length:max length = 2:1), higher split number is preferable (score is total of individual split staple score), and seeding domain above 13 is prefarable than one above 11 (1:0.3).
### Colour Code
- **Staples without ends:** These are left uncoloured, appearing as the default dark grey.
- **Staples with a length above 80 nt:** These are coloured magenta. (adjust to your policy by modifying length_max in trace_domain().)
- **Staples with a length below 20 nt:** These are coloured yellow. (adjust to your policy by modifying length_min in trace_domain().)
- **Staples with > 13 nt continuous hybridisation to the scaffold:** These are coloured blue.
- **Staples with > 11 nt continuous hybridisation to the scaffold:** These are coloured cyan.
- **Staples without seeding domains:** These are coloured red.
### How to Use

To use the Semi-Autobreak, navigate to the directory containing the script and run the following command:
```
$ python3 semi-autobreak.py file/path/to/json/file.json
```
The script will generate five output files: `output.json`, `crossover_report.csv`, `domain_report.csv`, `output_connected.json`, `output_autobreak.json`, `crossover_report_autobreak.csv`, `domain_report_autobreak.csv`, and `domain_report_temp.csv`. 
- The `output.json` file is compatible with cadnano2. Open the file by cadnano2 as usual. Colour code are wrtten above.
- `crossover_report.csv` summarises crossover frequency of every adjacent helices pair, in accending order of central helix number. So e.g. 0-1 and 1-0 appears twice. From left to right, helix number, total count of crossover, crossover count by scaffold, crossover count by staple, filled length of focusing helix, count of short domain of invalid (not either blue nor cyan) strands.
- `domain_report.csv` lists the staples to display domain properties. In this list, the first and the second column shows the location of 5' end and 3' end of the strand, in the same way as staple export file of cadnano2. In the third column, domain structure is printed in following way: `a-z` represents continuous base pairings with incremental domain naming. If the domain is longer than 13 nt, the domain is shown by upper letter `A-Z`; `^` indicates a base not hybridised to the scaffold; and `!` is an error catcher for situations such as the presence of more than 26 domains in single staple (too long in practice). Length at the last column for reference.
- `output_connected.json` is a cadnano2 compatible file with all staple break reconnected.
- `output_autobreak.json` is a cadnano2 compatible file after autobreak. The color code follows as output.json file.
- `crossover_report_autobreak.csv` is equivalent file of domain_report but after autobreak. 
- `domain_report_autobreak.csv` is equivalent file of domain_report but after autobreak.
- `domain_report_temp.csv` is temporal file to be used in autobreak script.

### Staple Optimisation Workflow with Seeding Domain Tracer

_Updated 2023-09-17_

**SAVE intermediate file every step**
1. Run the script and review coloured staples by opening `output_autobreak.json` from cadnano2. The goal is to make all staples blue (or cyan).
2. If loop exists, break them and run the script again to make all strands coloured. (I recommend introducing one break in one of short domain)
3. Correct yellow strands (too short)
4. Review crossover frequency (`crossover_report_autobreak.csv`) to make sure all adjacent helices pair has crossovers
5. Correct red strands in high restriction area (edge, modifying sites etc) by removing excess crossovers or relocate crossovers. `crossover_report_autobreak.csv` let you know which strands has enough crossover, while `domain_report_autobreak.csv` tells which part of domain should be extended by removing crossover.
6. Correct rest red strands and magenta strand by EFFICIENTLY removing excess crossovers or relocate crossovers. `crossover_report_autobreak.csv` and `domain_report_autobreak` support this step. Repeat rearranging crossover and running the script, until all staples become blue or cyan.
7. At the end, review again to make sure all adjacent helices have crossover in proper frequency (`crossover_report_autobreak.csv`) and location (output_autobreak.json).

## Seeding Domain Tracer

The `Seeding Domain Tracer` is a Python script that assists users in the manual optimisation of the breaking points of staples in a DNA origami design. It assigns staple colours based on their status:

- **Staples without ends:** These are left uncoloured, appearing as the default dark grey.
- **Staples with a length above 80 nt:** These are coloured magenta. (adjust to your policy by modifying length_max in trace_domain().)
- **Staples with a length below 20 nt:** These are coloured yellow. (adjust to your policy by modifying length_min in trace_domain().)
- **Staples with > 13 nt continuous hybridisation to the scaffold:** These are coloured blue.
- **Staples with > 11 nt continuous hybridisation to the scaffold:** These are coloured cyan.
- **Staples without seeding domains:** These are coloured red.

### How to Use

To use the Seeding Domain Tracer, navigate to the directory containing the script and run the following command:
```
$ python3 seeding-domain-tracer.py file/path/to/json/file.json
```
The script will generate three output files: `output.json`, `crossover_report.csv` and `domain_report.csv`. 
- The `output.json` file is compatible with cadnano2. Open the file by cadnano2 as usual. Colour code are wrtten above.
- `crossover_report.csv` summarises crossover frequency of every adjacent helices pair, in accending order of central helix number. So e.g. 0-1 and 1-0 appears twice. From left to right, helix number, total count of crossover, crossover count by scaffold, crossover count by staple, filled length of focusing helix, count of short domain of invalid (not either blue nor cyan) strands.
- `domain_report.csv` lists the staples to display domain properties. In this list, the first and the second column shows the location of 5' end and 3' end of the strand, in the same way as staple export file of cadnano2. In the third column, domain structure is printed in following way: `a-z` represents continuous base pairings with incremental domain naming. If the domain is longer than 13 nt, the domain is shown by upper letter `A-Z`; `^` indicates a base not hybridised to the scaffold; and `!` is an error catcher for situations such as the presence of more than 26 domains in single staple (too long in practice). Length at the last column for reference.

### Staple Optimisation Workflow with Seeding Domain Tracer

_Updated 2023-09-16_

**SAVE intermediate file every step**
1. Run the script and review coloured staples by opening `output.json` from cadnano2. The goal is to make all staples blue (or cyan).
2. If loop exists, break them and run the script again to make all strands coloured. (I recommend introducing one break in one of short domain)
3. Correct yellow strands (too short)
4. Review crossover frequency (`crossover_report.csv`) to make sure all adjacent helices pair has crossovers
5. Correct red strands in high restriction area (edge, modifying sites etc) by removing excess crossovers. `crossover_report.csv` supports this step.
6. Correct magenta strands, primary by splitting the strand keeping both halves have seeding domain. If a magenta strand can not be split keeping at least one seeding domain strand included, leave it to next step. `domain_report.csv` supports this step.
7. Correct rest red strands and magenta strand by EFFICIENTLY removing excess crossovers. `crossover_report.csv` supports this step.
8. At the end, review again if all adjacent helices have proper crossover (`crossover_report.csv`).

## Simple Multiplier

The `Simple Multiplier` is a script that automates the process of copying and pasting repetitive DNA origami designs from a unique unit. This can significantly reduce the time required to create symmetric structures.

### How to Use

To use the Simple Multiplier, prepare the json file as following instruction, navigate to the directory containing the script, and run the following command:
```   
$ python3 simple-multiplier.py file/path/to/json/file.json  
```   

1. Draw a design of **basic unit** desired to be multiplied. Ensure the first helix # is 0 and the last helix # is odd number (otherwise the output file can not be recognised by cadnano). The last helix should have scaffold to spacify it is the last helix of the basic unit.
<img width="2168" alt="image" src="https://github.com/yusuke-dna/cadnano-tools/assets/70700401/7f21252f-01ad-46cc-aaa6-d876436b8000">
2. Add blank helices to arrange lattice for the copies. The arrangement of the helices (copied units) is recommended to be regular (periodical) and separated to each other to make future simulations and visualisation easy. The unit should start from odd number and finish with even number. Keep in mind the `Basic unit` is defined as a scaffold/staple pathes/colours in consecutive helices from helix #0 to the largest # containing scaffold. The unit is copied and pasted to following blank helices.
<img width="2168" alt="image" src="https://github.com/yusuke-dna/cadnano-tools/assets/70700401/5ad050ff-8875-4997-bfbf-ee84a7eb9053">
3. Save the file, run the script as above and you'll get the multiplied design as `output.json` saved in the same directory as the script.
  
<img width="2168" alt="image" src="https://github.com/yusuke-dna/cadnano-tools/assets/70700401/a5a6d52b-7c3d-40c1-88c3-a57831821743">

---
### References
Cadnano2 is developped by Douglas group:

Douglas et al. 'Rapid prototyping of 3D DNA-origami shapes with caDNAno' Nucleic Acids Res: 37(15):5001–6 (2009) https://doi.org/10.1093/nar/gkp436
https://github.com/douglaslab/cadnano2

The Seeding Domain Tracer script is based on the following research:

Ke, Y., G. Bellot, N. V. Voigt, E. Fradkov, and W. M. Shih. 'Two Design Strategies for Enhancement of Multilayer-DNA-Origami Folding: Underwinding for Specific Intercalator Rescue and Staple-Break Positioning'. Chem Sci 3, no. 8 (1 August 2012): 2587–97. [https://doi.org/10.1039/C2SC20446K](https://doi.org/10.1039/C2SC20446K).
