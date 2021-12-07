import argparse
import pathlib
import logging
import sys
import os
import re

import yaml
from fuzzywuzzy import fuzz

from CardGenerator import ExistingFile


logging.DETAILED = 15
logger = logging.getLogger(__name__)
logging.addLevelName(logging.DETAILED, "DETAILED")


def detailed(self, message, *args, **kws):
    if self.isEnabledFor(15):
        self._log(15, message, args, **kws)


logging.Logger.detailed = detailed


class Quit(Exception):
    pass


def threshold_value(arg):
    try:
        f = float(arg)
    except ValueError:
        raise argparse.ArgumentTypeError("Must be a floating point number")
    if f < 0 or f > 1:
        raise argparse.ArgumentTypeError(
            "Argument must be < " + str(0) + "and > " + str(1)
        )
    return f


def find_images(path):
    images = []
    for root_dir, dirs, files in os.walk(path):
        for f in files:
            if f.endswith((".jpg", ".jpeg", ".png")):
                found_image = (pathlib.Path(root_dir) / f).absolute()
                images.append(found_image)
                logging.debug("Image found: {}".format(found_image))
    return images


def find_best_match(images, name):
    # Calculate match ratios
    ratios = []
    for image_path in images:
        # Get just the name of the file without extension
        file_name = image_path.stem
        # Strip out non alphanumeric chatacters from file name to improve matching
        non_alphanumeric_regex = re.compile(r"[\W _]+")
        cleaned_file_name = non_alphanumeric_regex.sub("", file_name)
        # String fuzzy matching
        ratio = fuzz.ratio(cleaned_file_name, name)
        ratios.append((ratio, image_path))

    # return highest match ratio
    return max(ratios, key=lambda item: item[0])


def match(name, images, auto_percent, ask_percent):
    match_ratio, image_file = find_best_match(images, name)
    # Automatic Match
    if match_ratio >= auto_percent:
        logger.detailed(f"Found image for '{name}': {image_file}")

    # Partial Match
    elif match_ratio >= ask_percent:
        msg = f"Found potential image ({match_ratio}) for '{name}': {image_file}"
        logger.info(msg)

        # Ask user if partial match is correct
        choice = input("Use this file? y/n/q (default: y): ")
        while choice not in ["n", "y", "", "q"]:
            msg = "Invalid input `{}`, please use `n`, `y`, `q` (default: `y`): "
            choice = input(msg.format(choice))
        logging.debug("Choice: {}".format(choice))
        if choice in "q":
            raise Quit()
        if choice == "n":
            return
    # No Match
    else:
        logger.debug("No match found")
        return

    return image_file


def image_match(args):
    with open(args.input) as f:
        entries = yaml.load(f, Loader=yaml.BaseLoader)
    no_image_entries = [e for e in entries if "image_path" not in e]

    images = find_images(args.image_src_dir)
    for entry in no_image_entries:
        name = entry["title"]
        best_match = match(name, images, 90, 50)
        print(name, best_match)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Attempts to match images to YAML entries. Searches for images matching the title of each entry"
    )
    parser.set_defaults(func=image_match)
    parser.add_argument(
        "-t",
        "--threshold",
        help="String matching threshold. 1=Match only exact name, 0=Match any name",
        action="store",
        default="0.80",
        type=threshold_value,
    )
    parser.add_argument(
        "input",
        help="Path to input data file",
        action="store",
        type=ExistingFile,
    )
    parser.add_argument(
        "image_src_dir",
        help="Path containing images to search",
        action="store",
        type=ExistingFile,
    )
    parser.add_argument(
        "image_dest_dir",
        help="Path to copy images to",
        default=pathlib.Path("images"),
        action="store",
        type=lambda p: pathlib.Path(p).absolute(),
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="Verbosity (-v, -vv, etc)"
    )
    args = parser.parse_args()

    if args.verbose == 1:
        logging.basicConfig(stream=sys.stdout, level=logging.DETAILED)
    elif args.verbose == 2:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    args.func(args)
