# SubsCrop

This script can crop picture based subtitle files: VobSubs (.idx/.sub) and BDSups (.sup).

## Requirements
- Python 3.4+
- [Pillow](https://github.com/python-pillow/Pillow) `pip install pillow`
- [pycountry](https://pypi.python.org/pypi/pycountry) `pip install pycountry`
- [BDSup2Sub++ executable](https://forum.doom9.org/showthread.php?p=1613303)

## Usage:
`subscrop.py subtitle.sub subtitle.cropped.sub 0 10 0 10 -e "C:\bdsup2sub++1.0.2_Win32.exe"`
crops 10 pixel from the top and bottom of the subtitle.sub file using the executable on C drive and saves the output to subtitle.cropped.sub
