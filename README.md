# Cadnano Tools
This repository contains several microtools designed to enhance the functionality of cadnano, a popular software for designing DNA nanostructures.

## Seeding Domain Tracer

The Seeding Domain Tracer is a Python script that assists users in the manual optimization of the breaking points of staples in a DNA origami design. It assigns staple colors based on their status:

- **Staples without ends:** These are left uncolored, appearing as the default dark grey.
- **Staples with a length above 80 nt:** These are colored magenta.
- **Staples with > 13 nt continuous hybridization to the scaffold:** These are colored blue.
- **Staples with > 11 nt continuous hybridization to the scaffold:** These are colored cyan.
- **Staples without seeding domains:** These are colored red.

### Usage

To use the Seeding Domain Tracer, navigate to the directory containing the script and run the following command:
```
$ python3 seeding-domain-tracer.py file/path/to/json/file.json
```
The script will generate two output files: `output.json` and `report.txt`. The `output.json` file is compatible with cadnano2, while `report.txt` lists the staples to display domain properties. In this list, the first column shows the location of 5' end of the strand, in the same way as staple export file of cadnano2. In the second column, domain structure is printed in following way: `a-z` represents continuous base pairings with incremental domain naming; `S` indicates a base not hybridized to the scaffold; and `E` is an error catcher for situations such as the presence of more than 26 domains in single staple.

### References

The Seeding Domain Tracer script is based on the following research:

Ke, Y., G. Bellot, N. V. Voigt, E. Fradkov, and W. M. Shih. 'Two Design Strategies for Enhancement of Multilayer-DNA-Origami Folding: Underwinding for Specific Intercalator Rescue and Staple-Break Positioning'. Chem Sci 3, no. 8 (1 August 2012): 2587–97. [https://doi.org/10.1039/C2SC20446K](https://doi.org/10.1039/C2SC20446K).

## Simple Multiplier

The `Simple Multiplier` is a script that automates the process of copying and pasting repetitive DNA origami designs from a unique unit. This can significantly reduce the time required to create symmetric structures.

Documentation for this tool is currently under development and will be available in future.
