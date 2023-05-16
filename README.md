# cadnano-tools
Microtools for cadnano
## Seeding domain tracer
Staple colors are adopted according to staple status:
* Staples without ends: no color, default dark grey
* Staples with length above 80 nt: Magenta
* Staples with > 13 nt continuous hybridization to scaffold: Blue
* Staples with > 11 nt continuous hybridization to scaffold: Cyan
* Staples without seeding domains: Red

### How to Use
Run below.
```
$ seeding-domain-tracer.py file/path/to/json/file.json
```
The two output files will be generated. output.json is the json file to open by cadnano2, while report.txt is a list of staples to show domain property. a-z represents continuous base pairs with incremental domain naming, S indicates the base is not hybridized to scaffold, and E is error above 26th domains. 
Keep in mind that this script does not consider domain breakage due to scaffold side, that would be supported in future update.
## Simple Multiplier
Documents to be made.
