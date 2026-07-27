# Cadnano Tools
This repository contains several microtools designed to enhance the functionality of cadnano, a popular software for designing DNA nanostructures.

## Setup Script
`setup.py` installs `cadnano2` into an isolated environment managed by [uv](https://docs.astral.sh/uv/). uv supplies its own Python interpreter, so the installation does not depend on which `python3` happens to be first on your PATH — pyenv, conda and Homebrew installations no longer interfere with it.

### How to Use

1. **Run the Setup Script**: Navigate to the directory containing the `setup.py` script and execute the following command:

    ```bash
    $ python3 setup.py
    ```
    This command will:
    - Install uv if it is not already present, after asking for confirmation.
    - Download a uv-managed Python 3.12 and install `cadnano2` and PyQt6 into an isolated environment.
    - On macOS and Linux, add uv's executable directory to your PATH if it is not already there, using the configuration file that matches your login shell.
    - On Windows, create a `cadnano2` shortcut on your desktop.

    Re-running the script is safe: it repairs an existing installation rather than rebuilding it.

2. **Using the Tools**: Once the setup is complete, **open a new terminal** and start cadnano2 by typing `cadnano2`. On Windows, double-click the `cadnano2` shortcut on the desktop instead — see below to enable the command line.

    A new terminal is required, not optional. PATH is read once when a shell starts, so a terminal that was already open when you ran the installer will still report that `cadnano2` is not found. Run `python3 setup.py --check` to see how PATH is currently configured.

### Running `cadnano2` from the Command Prompt on Windows

On Windows the installer creates the desktop shortcut but does **not** change your PATH. PATH lives in the registry there rather than in a file you edit, so a change reaches every program your account starts; the script reports what is needed and leaves the decision to you.

The desktop shortcut works without any of this. To type `cadnano2` in Command Prompt or PowerShell as well, run **one** of the following, then open a new Command Prompt:

```
uv tool update-shell
```

```
setx PATH "%PATH%;%USERPROFILE%\.local\bin"
```

Both add uv's executable directory to your user PATH. `setx` writes the value permanently but does not affect windows that are already open, which is why a new one is needed. If you would rather not change PATH at all, run cadnano2 by its full path:

```
%USERPROFILE%\.local\bin\cadnano2.exe
```

`python3 setup.py --check` reports the exact directory and whether it is registered.

    If you installed cadnano2 with an older version of this script, it added an alias to your shell configuration file. **An alias takes precedence over the newly installed command**, so delete any `alias cadnano2=...` lines before opening a new terminal. The script reports the exact files and line numbers; it does not edit them for you. The old environment at `~/venv/cn2` can be deleted once the new one works.

### Options

| Option | Purpose |
|---|---|
| `--check` | Report what is installed and what needs attention, changing nothing. |
| `--upgrade` | Upgrade an existing installation to the latest `cadnano2`. |
| `--reinstall` | Rebuild the environment from scratch if it is broken. |
| `--python VERSION` | Use a different Python version (default 3.12). |
| `--system-certs` | Use the operating system's certificate store. Try this first if your institution intercepts TLS traffic. |
| `--allow-insecure-host` | Last resort if `--system-certs` is not enough. Skips certificate verification for pypi.org only. |
| `--uninstall` | Remove cadnano2 and report anything left to clean up by hand. |
| `--yes` | Answer yes to prompts, for unattended installation. |

The old `-unsafe` flag is deprecated. It disabled certificate verification to work around Python builds without working SSL; uv bundles its own TLS stack, so that problem no longer arises. If you are behind a TLS-inspecting proxy, use `--system-certs`.

### Requirements

- Python 3.8 or later, only to run the installer itself. uv provides the Python that cadnano2 actually runs on, so no particular version needs to be installed beforehand.
- Note for Windows users: python.org stopped shipping binary installers for Python 3.12 after 3.12.10, but uv installs 3.12.13 on Windows just as it does on macOS and Linux.

## Semi-Autobreak
A Python script that supports users' semi-automatic optimisation of the breaking points of staples in DNA origami design. It removes existing staple breaks and introduces breaks with the following criteria if possible. If not possible, or if the user colour the staple in white (#FFFFFF), the strand is left intact. Users will attempt to rearrange the crossover position referring to the generated reports and repeatedly run the script to turn all strands blue (or cyan). Merged with `Seeding Domain Tracer` on 19th Sept 2023.

### Criteria
- All staples should have a seeding domain, continuous hybridisation to the scaffold without staple/scaffold crossover, ≥ 12 nt or, preferably, ≥ 14 nt. (configurable by optional arguments `-acceptable` and `-optimal`)
- All ends of staples are at least three base away from staple crossover. (configurable by optional arguments `-distance`)
- The length of all split staples should be within the specified range, ≥ 18 and ≤ 80 by default. (configurable by optional arguments `-min` and `-max`)
- The most preferable breaking point is selected from all possible combinations based on its `score`. The score represents the quality of split staples. A shorter staple is preferable (minimum length staple has twice the score as maximum length staple), a higher split number is preferable (score is the sum of individual split staple scores), and a seeding domain above 13 is more preferable than one above 11 (1:0.3).
- Calculation is limited up to 5 000 patterns per cycle. If exceed, top 100 (by score) patterns are filtered to next breaking point search. (configurable by optional arguments `-limit` and `-filter`) Note that a weight is applied to both to reduce calculation cost for staples with low sequence divesity.
  
_See the reference at the bottom for the theoretical/experimental background about `seeding domain`._

### Colour Code
- **Staples without ends:** These remain uncoloured, appearing as the default dark grey.
- **Staples with a length above 80 nt:** These are coloured magenta. (Adjust the number according to your policy -max option.)
- **Staples with a length below 18 nt (excluding ssDNA region):** These are coloured yellow. (Adjust the number according to your policy -min option.)
- **Staples with ≥ 14 nt continuous hybridisation to the scaffold:** These are coloured blue. (Adjust the number according to your policy -optimal option.)
- **Staples with ≥ 12 nt continuous hybridisation to the scaffold:** These are coloured cyan. (Adjust the number according to your policy -acceptable option.)
- **Staples without seeding domains:** These are coloured red.

### How to Use

To use Semi-Autobreak, navigate to the directory containing the script and run the following command:

```
$ python3 semi-autobreak.py file/path/to/json/file.json
```

The script will generate several output files: `output.json`, `crossover_report.csv`, `domain_report.csv`, and optionally `output_connected.json`, `output_autobreak.json`, `crossover_report_connected.csv`, `domain_report_connected.csv`.
- The `output.json` file is compatible with cadnano2. Open the file with cadnano2 as usual. Colour codes are written above.
- `crossover_report.csv` summarises the crossover frequency of every adjacent helix pair (by num in slice panel), in ascending order of the central helix number. So, e.g. 0-1 and 1-0 appear twice. From left to right: helix pair number, total count of crossover, crossover count by scaffold, crossover count by staple, filled length of the focused helix, count of short domains of invalid (neither blue nor cyan) strands.
- `domain_report.csv` lists the staples to display domain properties. In this list, the first and the second column shows the locations of the 5' end and 3' end of the strand, similarly to the staple export file of cadnano2. In the third column, the domain structure is printed as follows: `a-z` represents continuous base pairings with incremental domain naming. If the domain length is or is above 12 nt (or user-specified `acceptable` length), the domain is shown by the upper letter `A-Z`; `^` indicates a base not hybridised to the scaffold (ssDNA), and `!` is an error catcher for situations like the presence of more than 1300 domains in a single staple. Note that the domain label circulates between a-z (a is next to z). Length of each staple is provided in the last column for reference.

### Arguments
- `[File path]`: Mandatory argument. Input path to cadnano json file.
- `-min [number]`: 18 by default. Lower limit of staple length excluding ssDNA region. Coloured yellow if the staple is shorter than this number.
- `-max [number]`: 80 by default. Upper limit of staple length. Coloured magenta if exceeded.
- `-optimal [number]`: 14 by default. Requirement for minimum continuous hybridisation length per staple. Staples meeting this requirement are coloured blue.
- `-acceptable [number]`: 12 by default. A more lenient requirement for minimum continuous hybridisation length per staple. Staples that meet this requirement are coloured cyan.
- `-manual`: Only the staple colour is updated and autobreak is skipped. This behaviour is the same as the seeding-domain-tracer.
- `-connect`: Reconnect all breakpoints of staples, by halting the autobreak script. Generated file: `output_connected.json`, `crossover_report_connected.csv`, `domain_report_connected.csv`.
- `-color`: Retain an intermediate JSON file `output_autobreak.json` displaying autobroken staples in green.
- `-limit [number]`: 5000 by default. Limiter to prevent combinatorial explosion. The threshold to apply pruning filter (below) breaking pattern variation. For low restriction design (long average domain length), weight (**(optimal_seed_len/average_domain_len)) is automatically applied to reduce wasteful calculation cost, resulting in no siginficant difference.
- `-filter [number]`: 100 by default. Filter to prevent combinatorial explosion. The pattern exceeding threshold (above) will be pruned to this number. For low restriction design (long average domain length), weight (**(optimal_seed_len/average_domain_len)) is automatically applied to reduce wasteful calculation cost, resulting in no siginficant difference.
- `-distance [number]`: 3 by default. Distance from 5-/3-end of staple and staple crossover (not considering scaffold crossover).
- `-extension [number]`: 0 by default. Specified number of ssDNA (^) is added to the white staples. This is useful to introduce modifications to the DNA nanostructure.

### Staple Optimisation Workflow Semi-Autobreak

_Updated on 2023-09-19_

**SAVE intermediate files at every step:**
1. Run the script and review coloured staples by opening `output.json` from cadnano2. The goal is to make all staples blue (or cyan).
2. If a staple loop exists, break them and run the script again to colour all strands. (I recommend introducing a break in one of the short domains)
3. Run the script and ensure all staples are coloured.
4. Correct yellow (too short) strands by extending staple ends at edges or relocating crossovers.
5. Run the script and ensure there are no yellow staples.
6. Review the crossover frequency (refer to `crossover_report.csv`) to ensure every adjacent helix pair has crossovers.
7. Correct red strands in high-restriction areas (edges, modifying sites, etc.) by removing excess crossovers or relocating them. `crossover_report.csv` informs you which strands have sufficient crossovers, while `domain_report.csv` indicates which part of the strand lacks seeding domains, making it the target for crossover removal.
8. Run the script and repeat steps 7-8 until all target staples are coloured blue or cyan.
9. Correct the remaining red strands and magenta strands by efficiently removing excess crossovers or relocating them. `crossover_report.csv` and `domain_report.csv` aid this step.
10. Run the script and repeat steps 9-10 until all staples are blue or cyan.
11. At last, review once more to ensure all adjacent helices have proper crossover frequency (`crossover_report.csv`) and location (`output.json`).
12. Optionally, some edge staples extended at step 4 could be trimmed to minimum length limit. (this would be included in script in future update.)

### Known issues
- Inserts and skips (for curvature and twist) are not counted for now.
- The script recognises crossover only when the base positions of two ends are kept same (e.g. 1[118] to 10[118]).
- Short limit `min` only consider hybridisation (bp) length while long limit `max` includes ssDNA length, resulted in unexpected behaviour when ssDNA is too long.

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

## Simple Slider

The `Simple Slider` is a script that automate the process of moving DNA origami design to right (+) or left (-) free space. Moving right extend path panel width while moving left remove specific bases from left side of the path panel, if nothing are written in the deleting zone.

### How to Use

To use the Simple Slider, navigate to the directory containing the script, and run the following command:
```   
$ python3 simple-slider.py file/path/to/json/file.json [sliding number]
```
Both file path and number are required. The sliding number should be multiple of 32 (square lattice) or 21 (honeycomb lattice).

## Color Resetter

The `Color Resetter` is a simple script to assign random staple colour, which is default of cadnano.

### How to Use

To use the Color Resetter, navigate to the directory containing the script, and run the following command:
```   
$ python3 color-resetter.py file/path/to/json/file.json
```
It generate output.json file which the staple colours are updated.

## Horizontal Rotator

The `Horizontal Rotator` is a script designed to create a mirrored copy of a DNA origami design, placing the flipped version to the right of the original within the same JSON file. This tool requires the input JSON file to describe a symmetrically arranged lattice for accurate processing. Running the script effectively doubles the path panel width, with the left-side paths (including both scaffold and staples) being mirrored upside down and left to right alongside the original design. The script returns an error if the lattice design lacks symmetric helix arrangements.
<img width="4032" alt="image" src="https://github.com/yusuke-dna/cadnano-tools/assets/70700401/92fe4e39-2cb3-4f51-a2da-d5206009a265">

### How to Use

To utilise the Horizontal Rotator, first navigate to the directory where the script is located. Then, execute the following command:

```bash
python3 horizontal-rotator.py /path/to/your/input_file.json
```

This command generates a new file named `[input_file_name]_modified.json`, which contains both the original design and its mirrored version.

---
### References
Cadnano2 is developped by Douglas group:

Douglas et al. 'Rapid prototyping of 3D DNA-origami shapes with caDNAno' Nucleic Acids Res: 37(15):5001–6 (2009) https://doi.org/10.1093/nar/gkp436
https://github.com/douglaslab/cadnano2

The Seeding Domain Tracer/Semi-Autobreak scripts are based on the following research:

Ke, Y., G. Bellot, N. V. Voigt, E. Fradkov, and W. M. Shih. 'Two Design Strategies for Enhancement of Multilayer-DNA-Origami Folding: Underwinding for Specific Intercalator Rescue and Staple-Break Positioning'. Chem Sci 3, no. 8 (1 August 2012): 2587–97. [https://doi.org/10.1039/C2SC20446K](https://doi.org/10.1039/C2SC20446K).

DNA origami regular tile is derived from:

Tikhomirov, G., Petersen, P. & Qian, L. Fractal assembly of micrometre-scale DNA origami arrays with arbitrary patterns. Nature 552, 67–71 (2017). https://doi.org/10.1038/nature24655
