import argparse
import tempfile
import pathlib
import zipfile
import errno
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict

import yaml
from bs4 import BeautifulSoup

from CardGenerator import ExistingFile


def noop(self, *args, **kw):
    pass


yaml.emitter.Emitter.process_tag = noop


def strip_tags(html):
    """Strip unwanted HTML tags"""
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a"):
        a.unwrap()

    return str(soup)


ASSET_DIR = pathlib.Path(__file__).parent.resolve() / "assets"


@dataclass
class MonsterCardData:
    title: str
    subtitle: str
    artist: str
    image_path: pathlib.Path
    armor_class: str
    max_hit_points: str
    speed: str
    strength: str
    dexterity: str
    constitution: str
    intelligence: str
    wisdom: str
    charisma: str
    challenge_rating: str
    experience_points: str
    source: str
    attributes: dict
    abilities: dict
    actions: dict
    legendary: list


@dataclass
class ItemCardData:
    title: str
    subtitle: str
    artist: str
    image_path: pathlib.Path
    description: str
    category: str
    subcategory: str


item_type_to_text = {
    "AA": "Armor",
    "WW": "Weapon",
    "LA": "Light armor",
    "MA": "Medium armor",
    "HA": "Heavy armor",
    "S": "Shield",
    "M": "Melee weapon",
    "R": "Ranged weapon",
    "A": "Ammunition",
    "RD": "Rod",
    "ST": "Staff",
    "WD": "Wand",
    "RG": "Ring",
    "P": "Potion",
    "SC": "Scroll",
    "W": "Woundrous item",
    "G": "Adventuring gear",
    "$": "Wealth",
}

cr_to_xp = {
    "0": "0 or 10",
    "1/8": "25",
    "1/4": "50",
    "1/2": "100",
    "1": "200",
    "2": "450",
    "3": "700",
    "4": "1,100",
    "5": "1,800",
    "6": "2,300",
    "7": "2,900",
    "8": "3,900",
    "9": "5,000",
    "10": "5,900",
    "11": "7,200",
    "12": "8,400",
    "13": "10,000",
    "14": "11,500",
    "15": "13,000",
    "16": "15,000",
    "17": "18,000",
    "18": "20,000",
    "19": "22,000",
    "20": "25,000",
    "21": "33,000",
    "22": "41,000",
    "23": "50,000",
    "24": "62,000",
    "25": "75,000",
    "26": "90,000",
    "27": "105,000",
    "28": "120,000",
    "29": "135,000",
    "30": "155,000",
}


def generate(args):
    print(args)


def convert(args):
    if args.output_path is None:
        args.output_path = pathlib.Path(args.input.stem)

    if args.overwrite:
        try:
            shutil.rmtree(args.output_path)
        except FileNotFoundError:
            pass

    # Create output directory
    args.output_path.mkdir()
    (args.output_path / "images").mkdir()
    (args.output_path / "images" / "items").mkdir()
    (args.output_path / "images" / "monsters").mkdir()

    if args.format == "encounterplus":
        results = convert_encounterplus(args)

    for entry_type, entries in results.items():
        if len(entries):
            with open(args.output_path / (entry_type + ".yaml"), "w") as f:
                yaml.dump(entries, f, sort_keys=False)


def convert_encounterplus(args):
    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = pathlib.Path(tempdir)

        # Extract module
        with zipfile.ZipFile(args.input, "r") as zip_ref:
            zip_ref.extractall(tempdir)

        compendium_path = tempdir / "compendium.xml"
        if not compendium_path.exists():
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), compendium_path.name
            )

        tree = ET.parse(compendium_path)
        root = tree.getroot()

        def move_image(xml, output_path):
            image = xml.findtext("image")
            if image is not None:
                image_path = tempdir / (xml.tag + "s") / image
                new_path = (
                    pathlib.Path("images")
                    / (xml.tag + "s")
                    / (xml.findtext("name") + image_path.suffix)
                )
                image_path.rename(output_path / new_path)
                return str(new_path)
            return None

        tags = {"item": process_item, "monster": process_monster}

        results = {}
        for tag, process in tags.items():
            entries = []
            for entry_xml in root.findall(tag):
                item = process(entry_xml)

                item.image_path = move_image(entry_xml, args.output_path)

                # Strip unused fields
                item_dict = asdict(
                    item, dict_factory=lambda x: {k: v for (k, v) in x if v is not None}
                )
                entries.append(item_dict)
            results[tag] = entries

        return results


def process_item(item_xml):
    item = {}

    # Construct subtitle
    subtitle = f'{item_xml.findtext("rarity")}'
    attune = item_xml.findtext("attune")
    if attune is not None:
        subtitle += f" ({attune})"

    # Clean description
    description = item_xml.findtext("text", default="")
    description = strip_tags(description)
    description = description.replace(
        f"<i>Source: {item_xml.findtext('source')}</i>", ""
    )
    description = description.replace("\u2013", "-")
    description = description.strip()

    item_data = ItemCardData(
        title=item_xml.findtext("name"),
        subtitle=subtitle,
        artist=None,  # Artist
        image_path=None,  # Image
        description=description,
        category=item_type_to_text[item_xml.findtext("type")],
        subcategory=None,
        # source=item_xml.findtext("source"),
        # source=item_xml.findtext("weight"),
        # source=item_xml.findtext("value"),
    )

    return item_data


def process_entry(monster, tag):
    entries = {}
    for entry in monster.findall(tag):
        name = entry.findtext("name").strip()
        if name.endswith("."):
            name = name[:-1]
        name = name.replace("\u2013", "-")
        text = ""
        for line in entry.findall("text"):
            line.text = line.text.replace("\n", "\n<br/>")
            text += (line.text or "") + "<br/>"
        entries[name] = text.strip()
    return entries


def process_monster(monster_xml):
    monster_name = monster_xml.findtext("name")
    attributes = {}

    tags = {
        "skill": "Skills",
        "resist": "Damage Resistances",
        "immune": "Damage Immunities",
        "vulnerable": "Damage Vulnerabilities",
        "conditionImmune": "Condition Immunities",
    }
    for tag, name in tags.items():
        text = monster_xml.findtext(tag)
        if text:
            attributes[name] = text

    senses = monster_xml.findtext("senses")
    passive_perception = monster_xml.findtext("passive")
    if senses:
        attributes["Senses"] = f"{senses}, Passive Perception {passive_perception}"
    else:
        attributes["Senses"] = f"Passive Perception {passive_perception}"

    languages = monster_xml.findtext("languages") or "-"
    attributes["Languages"] = languages

    # Legendary Actions:
    legendary_actions = []
    legendary_tags = monster_xml.findall("legendary")
    i = 0
    heading_map = {
        "REGIONAL EFFECTS": "Regional Effects",
        "LAIR ACTIONS": "Lair Actions",
    }

    while i < len(legendary_tags):
        name = legendary_tags[i].findtext("name").strip()

        if (name or "").upper() in heading_map:
            name = heading_map[name.upper()]
            i += 2
            continue

        text = ""
        for line in legendary_tags[i].findall("text"):
            text += (line.text or "") + "<br/>"
        text = text.strip()

        if not name:
            legendary_actions.append(text)
        else:
            if name.endswith("."):
                name = name[:-1]
            name = name.replace("\u2013", "")
            legendary_actions.append({name: text})

        i += 1

    # Source
    source = ""
    description = monster_xml.findtext("description")
    if description:
        last_line = description.splitlines()[-1]
        last_line = last_line.replace("<i>", "").replace("</i>", "")
        start_string = "Source: "
        if last_line.startswith(start_string):
            source = last_line[len(start_string) :].split(",")[0]

    actions = process_entry(monster_xml, "action")
    for key in list(actions.keys()):
        if key and key.startswith("Variant: "):
            del actions[key]
            continue
        text = actions[key].strip()
        text = text.replace("<i></i>", "")
        text = text.replace("<i> Ranged Weapon Attack:</i>", "")
        text = text.replace("<i> Melee Weapon Attack:</i>", "")
        text = text.replace(" <i>Hit:</i>", "")
        text = text.replace(" reach", "")
        text = text.replace(" one target.", "")
        text = text.replace("\u2013", "-")
        text = text.strip()
        actions[key] = text

    abilities = process_entry(monster_xml, "trait")
    for key in list(abilities.keys()):
        abilities[key] = abilities[key].replace("<i></i> ", "")

    monster_data = MonsterCardData(
        title=monster_name,
        subtitle=f"{monster_xml.findtext('type')}, {monster_xml.findtext('alignment')}",
        artist=None,
        image_path=None,
        armor_class=monster_xml.findtext("ac").strip(),
        max_hit_points=monster_xml.findtext("hp"),
        speed=monster_xml.findtext("speed"),
        strength=f"{monster_xml.findtext('str')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        dexterity=f"{monster_xml.findtext('dex')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        constitution=f"{monster_xml.findtext('con')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        intelligence=f"{monster_xml.findtext('int')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        wisdom=f"{monster_xml.findtext('wis')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        charisma=f"{monster_xml.findtext('cha')} ({(int(monster_xml.findtext('str'))-10 )//2:+d})",
        challenge_rating=monster_xml.findtext("cr"),
        experience_points=cr_to_xp[monster_xml.findtext("cr")]
        if monster_xml.findtext("cr")
        else "0",
        source=source or None,
        attributes=attributes,
        abilities=abilities,
        actions=actions,
        legendary=legendary_actions,
    )

    return monster_data


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Convert data into YAML from other formats"
    )
    parser.set_defaults(func=convert)
    parser.add_argument(
        "-o",
        "--out",
        help="Output directory",
        action="store",
        dest="output_path",
        metavar="output_path",
        type=lambda p: pathlib.Path(p).absolute(),
    )
    parser.add_argument(
        "--overwrite",
        help="Delete and overwrite converted data if it already exists",
        action="store_true",
    )
    parser.add_argument(
        "-f",
        "--format",
        help="What format the input is in",
        action="store",
        default="encounterplus",
        choices=["encounterplus"],
        dest="format",
    )
    parser.add_argument(
        "input",
        help="Path to input data file",
        action="store",
        type=ExistingFile,
    )
    args = parser.parse_args()
    args.func(args)
