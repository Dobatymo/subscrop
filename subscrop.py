import os
import os.path
import logging
from tempfile import gettempdir
from glob import iglob
from subprocess import check_call
from xml.etree import ElementTree
from pathlib import Path

from PIL import Image
from pycountry import languages

"""
todo:
- keep correct color palette

no easy fix:
- cannot handle multiple streams in input files, it just processes the first one.
"""

# argparse utils

import argparse

def arg_to_path(func):
	def inner(path):
		return func(Path(path))
	return inner

@arg_to_path
def is_dir(dirname):
	"""Checks if a path is an actual directory"""

	if not dirname.is_dir():
		msg = "{0} is not a directory".format(dirname)
		raise argparse.ArgumentTypeError(msg)

	return dirname

@arg_to_path
def is_file(filename):
	"""Checks if a path is an actual file"""

	if not filename.is_file():
		msg = "{0} is not a file".format(filename)
		raise argparse.ArgumentTypeError(msg)

	return filename

@arg_to_path
def future_file(filename):
	""" Tests if file can be created to catch errors early.
		Checks if directory is writable and file does not exist yet.
	"""

	head, tail = os.path.split(filename)

	if head and not os.access(head, os.W_OK):
		msg = "cannot access directory {0}".format(head)
		raise argparse.ArgumentTypeError(msg)
	if filename.is_file():
		msg = "file {0} already exists".format(filename)
		raise argparse.ArgumentTypeError(msg)

	return filename

# subscrop

def crop(file_in: Path, file_out, left=0, top=0, right=0, bottom=0, format=None, optimize=True, overwrite=False):

	if file_in.samefile(file_out) and not overwrite:
		raise RuntimeError("Cannot overwrite files without corresponding argument")

	with Image.open(file_in) as original:
		width, height = original.size

		l = left
		t = top
		r = width - right
		b = height - bottom

		valid_dimensions = l < r and t < b

		if not valid_dimensions:
			raise ValueError("Invalid dimensions for '{}': {}x{}".format(file_in.name, r-l, b-t))

		cropped = original.crop((l, t, r, b))
		cropped.save(file_out, format, optimize=optimize)
		return cropped.size

# unused
def batch_crop(path_in: Path, left=0, top=0, right=0, bottom=0, dir_out=None, postfix="", overwrite=False, optimize=True):
	""" crops all .png file in directory """

	for file_in in path_in.glob("*.png"):
		file_out = os.path.join(dir_out or file_in.parent, file_in.stem+postfix+file_in.suffix)
		try:
			crop(file_in, file_out, left, top, right, bottom, optimize=optimize, overwrite=overwrite)
		except ValueError:
			print("cannot crop file, skipping...")

def crop_subs_xml(xml_in: Path, left=0, top=0, right=0, bottom=0, dir_out=None, postfix="", overwrite=False, optimize=True):
	""" crops xml/png format subtitle file
	"""

	xml = ElementTree.parse(xml_in)
	bdn = xml.getroot()

	language = bdn.find("Description/Language").get("Code", "eng")
	events = bdn.find("Events")

	for event in events.iter("Event"):
		for graphic in event.iter("Graphic"):

			img_file = Path(graphic.text)
			file_in = xml_in.parent / img_file # / op, Path.joinpath?
			file_out = os.path.join(dir_out or xml_in.parent, img_file.stem+postfix+img_file.suffix)

			try:
				width, height = crop(file_in, file_out, left, top, right, bottom, optimize=optimize, overwrite=overwrite)
				graphic.set("Height", str(height))
				graphic.set("Width", str(width))
				x = int(graphic.get("X"))
				y = int(graphic.get("Y"))
				graphic.set("X", str(x+left))
				graphic.set("Y", str(y+top))
			except ValueError as e:
				logging.warning(e)
				#event.remove(graphic) # empty <Event>s seems to cause problems with bdsup2sub
				events.remove(event)

	xml_out = os.path.join(dir_out or xml_in.parent, xml_in.stem+postfix+xml_in.suffix)

	if xml_in.samefile(xml_out) and not overwrite:
		raise RuntimeError("Cannot overwrite files without corresponding argument")

	xml.write(xml_out, encoding="utf-8", xml_declaration=True)

	return language, Path(xml_out)

def crop_subfile(executable, file_in, file_out, left=0, top=0, right=0, bottom=0, tempdir=None):
	if tempdir is None:
		tempdir = Path(gettempdir())
	xml_file = tempdir / "subtitle-s847vfv.xml"

	check_call([os.fspath(executable), "--no-verbose", "-o", os.fspath(xml_file), os.fspath(file_in)])
	language, xml_file = crop_subs_xml(xml_file, left, top, right, bottom, overwrite=True, optimize=False)
	language = languages.get(alpha_3=language).alpha_2
	check_call([os.fspath(executable), "--no-verbose", "--language", language, "-o", os.fspath(file_out), os.fspath(xml_file)])

if __name__ == "__main__":
	import argparse

	parser = argparse.ArgumentParser(prog="subscrop",
		description="Crop picture based subtitle files. Expects 'bdsup2sub++' to be in path. Does not support multiple stream in one file.",
		epilog="Example: 'subscrop.py movie.sub movie.cropped.sub 0 10 0 0' to crop 10 pixels on the top of every subpicture.",
		formatter_class=argparse.ArgumentDefaultsHelpFormatter)
	parser.add_argument('file_in', type=is_file, help="input subtitle file to crop [*.sub, *.sup]")
	parser.add_argument('file_out', type=future_file, help="output cropped subtitle file [*.sub, *.sup]")
	parser.add_argument("-t", '--temppath', type=is_dir, help="temporary directory", default=gettempdir())
	parser.add_argument("-e", '--executable', type=is_file, help="bdsup2sub++ executable", default="bdsup2sub++1.0.2_Win32.exe")
	parser.add_argument('left', type=int, help="number of pixels to crop on the left")
	parser.add_argument('top', type=int, help="... on the top")
	parser.add_argument('right', type=int, help="... on the right")
	parser.add_argument('bottom', type=int, help="... on the bottom")
	args = parser.parse_args()

	crop_subfile(args.executable, args.file_in, args.file_out, args.left, args.top, args.right, args.bottom, tempdir=args.temppath)
