#!/usr/bin/env python3

import argparse
import json
import os
import requests
import re
from pathlib import Path


def json_load(path):
    with path.open(mode="r") as json_fp:
        return json.load(json_fp)


def json_store(path, obj):
    with path.open(mode="w") as json_fp:
        json.dump(obj, json_fp, indent=4, ensure_ascii=False)
        json_fp.write("\n")


TIME_MAP = {
    "Two Actions": "2",
    "Reaction": "reaction",
    "Single Action": "1",
    "Single Action to Three Actions": "1 to 3",
    "Single Action or Three Actions": "1 or 3",
    "Single Action to Two Actions": "1 to 2",
    "Single Action or Two Actions": "1 or 2",
    "Two Actions to Three Actions": "2 to 3",
    "Two Actions or Three Actions": "2 or 3",
    "Three Actions": "3",
    "Free Action": "free",
    "Two Actions to 2 rounds": "2 to 2 rounds",
    "Single Action or more": "1 to 3",
    "Single Action or more Actions": "1 to 3",
}

ABILITIES_MAP = {
    "Intelligence": "int",
    "Wisdom": "wis",
    "Strength": "str",
    "Charisma": "cha",
    "Constitution": "con",
    "Dexterity": "dex",
}


TRADITIONS_MAP = {
    "Arcane": "arcane",
    "Divine": "divine",
    "Occult": "occult",
    "Primal": "primal",
}

RARITY_MAP = {
    "Common": "common",
    "Rare": "rare",
    "Uncommon": "uncommon",
    "Unique": "unique",
}

TRAITS_SCHOOL_MAP = {
    "Abjuration": "abjuration",
    "Conjuration": "conjuration",
    "Divination": "divination",
    "Enchantment": "enchantment",
    "Evocation": "evocation",
    "Illusion": "illusion",
    "Necromancy": "necromancy",
    "Transmutation": "transmutation",
}


def no_uni(string):
    string = string.replace("\u2019", "'")  # Fix quotes
    string = string.replace(" ,", ",")  # NS: formatting error
    string = string.replace(" '", "'")  # NS: formatting error
    return string.encode("ascii").decode()


def get_nethys_items(url, force):
    # Store the search database next to this script
    index_filename = Path(__file__).parent / "nethys-fixer.json"

    if not index_filename.exists() or force:
        print(f"Downloading Nethys Search data...")
        # TODO Database is larger then max Elasticsearch query size. This is a
        # lazy hack to paginate the results by requesting all the Feats and
        # Items, and then all the not-Feats-and-Items, which splits database
        # almost down the middle. Really should use the Paginate API.
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#search-after
        # { "query" : { "match_all" : {} } }
        ra = requests.get(
            url,
            json={
                "query": {"bool": {"filter": [{"terms": {"type": ["Feat", "Item"]}}]}},
                "size": 10000,
                "_source": {"excludes": ["text"]},
            },
        )
        ra_data = ra.json()

        rb = requests.get(
            url,
            json={
                "query": {
                    "bool": {"must_not": [{"terms": {"type": ["Feat", "Item"]}}]}
                },
                "size": 10000,
                "_source": {"excludes": ["text"]},
            },
        )
        rb_data = rb.json()

        # Merge together the hits and discard everything else
        hits = ra_data["hits"]["hits"] + rb_data["hits"]["hits"]

        # Sort hits by ID using a natural sort
        hits.sort(
            key=lambda x: [
                int(t) if t.isdigit() else t.lower()
                for t in re.split(r"(\d+)", x["_id"])
            ]
        )

        json_store(index_filename, hits)

        print(f"Download complete")

    for hit in json_load(index_filename):
        yield hit


def _get_packs(item):
    src = item["_source"]
    name = src["name"]

    # fmt: off
    pack_override = ({
        "background-40": [("backgrounds.db", "refugee-fall-of-plaguestone.json")],  # Name collision
        "background-78": [("backgrounds.db", "purveyor-of-the-bizzare.json")],  # FVTT: typo Bizzare -> Bizarre
        "background-84": [("backgrounds.db", "press-ganged-lowg.json")],  # Name collision
        "background-174": [("backgrounds.db", "refugee-apg.json")],  # Name collision
        "background-196": [("backgrounds.db", "post-guard-of-all-trades.json")],  # FVTT: typo Trades -> Trade
        "background-284": [("backgrounds.db", "press-ganged-g-g.json")],  # Name collision
        "background-296": [("backgrounds.db", "framed-in-ferrous-quarter.json")],  # AoN: typo of feat name, Famed -> Framed (submitted)
        "deity-164": [("deities.db", "nyarlathotep-the-crawling-chaos.json")],  # Name collision
        "deity-222": [("deities.db", "nyarlathotep-haunter-in-the-dark.json")],  # Name collision
        "equipment-407-1": [("equipment.db", "aeon-stone-dull-grey.json")],  # FVTT: typo grey -> gray
        "equipment-652": [("equipment.db", "yellow-musk-poison.json")], # FVTT: typo Poison -> Vial
        "equipment-1103-1": [("equipment.db", "ablative-shield-plating-moderate.json")],  # AoN: typo Moderatre -> Moderate
        "heritage-64": [("heritages.db", "dragonscaled-kobold*.json")],  # FVTT: variants
        "heritage-121": [("heritages.db", "deep-fetchling*.json")],  # FVTT: variants
        "feat-477": [("feats.db", "tongue-of-sun-and-moon.json")],  # AoN: typo of feat name
        "feat-756": [("feats.db", "assurance*.json")],  # FVTT: variants
        "feat-844": [("feats.db", "specialty-crafting*.json")],  # FVTT: variants
        "feat-851": [("feats.db", "terrain-expertise*.json")],  # FVTT: variants
        "feat-862": [("feats.db", "virtuosic-performer*.json")],  # FVTT: variants
        "feat-868": [("feats.db", "wilderness-spotter*.json")],  # FVTT: variants
        "feat-884": [("feats.db", "necromantic-resistance.json")],  # Name collision
        "feat-915": [("feats.db", "warding-rune*.json")],  # FVTT: variants
        "feat-1803": [("feats.db", "bloody-debilitation.json")],  # AoN: typo of feat name
        "feat-2352": [("feats.db", "daywalker.json")],  # Name collision
        "feat-2499": [("feats.db", "animal-swiftness*.json")],  # FVTT: variants
        "feat-2558": [("feats.db", "heat-wave.json")],  # AoN: typo of feat name
        "feat-2635": [("feats.db", "sprites-spark*.json")],  # FVTT: variants
        "feat-2897": [("feats.db", "ranged-combatant*.json")],  # FVTT: variants
        "feat-3477": [("feats.db", "necromantic-resistance-undead-slayer.json")],
        "feat-3540": [("feats.db", "skeletal-resistance.json")],  # AoN: typo skeleton -> skeletal
        "feat-3549": [("feats.db", "daywalker-vampire.json")],  # Name collision
        "spell-499": [("spells.db", "dragon-breath*.json")],  # FVTT: variants
        "feat-3845": [("feats.db", "purge-of-moments.json")],  # AoN: typo, reported 8/1/22
        "spell-1168": [("spells.db", "euphoric-renewal.json")],  # AoN: typo, reported 8/1/22
#: [("feats.db", "aerial-pilerdriver.json")],
#: [("feats.db", "animal-companion-druid.json")],
#: [("feats.db", "animal-companion-ranger.json")],
        #("feats.db", "attack-of-opportunity-fighter.json"),  # AoN: Does not list as a feat
#: [("feats.db", "battle-medicine-forensic-medicine.json")],
#: [("feats.db", "blessed-blood-sorcerer.json")],
#: [("feats.db", "blessings-of-the-five.json")],
#: [("feats.db", "cantrip-expansion-magus.json")],
#: [("feats.db", "cantrip-expansion-prepared-caster.json")],
#: [("feats.db", "cantrip-expansion-spontaneous-caster.json")],
#: [("feats.db", "ceremony-of-strengthened-hand.json")],
#: [("feats.db", "claws-of-the-dragon-draconic-bloodline.json")],
#: [("feats.db", "counterspell-prepared.json")],
#: [("feats.db", "counterspell-sorcerer.json")],
#: [("feats.db", "counterspell-spontaneous.json")],
#: [("feats.db", "critical-debilitation.json")],
#: [("feats.db", "cunning-trickster-mask.json")],
#: [("feats.db", "dedication-to-the-five.json")],
#: [("feats.db", "deep-vision.json")],
#: [("feats.db", "devil-allies.json")],
        #("feats.db", "disillusionment.json"),  # AoN: sub-feat of Order of the Rack
#: [("feats.db", "dragonslayer-oath-liberator.json")],
#: [("feats.db", "dragonslayer-oath-paladin.json")],
#: [("feats.db", "dragonslayer-oath-redeemer.json")],
#: [("feats.db", "ensaring-wrappings.json")],
#: [("feats.db", "esoteric-oath-liberator.json")],
#: [("feats.db", "esoteric-oath-paladin.json")],
#: [("feats.db", "esoteric-oath-redeemer.json")],
#: [("feats.db", "fear-no-law-fear-no-one.json")],
#: [("feats.db", "festering-wounds.json")],
#: [("feats.db", "fiendsbane-oath-liberator.json")],
#: [("feats.db", "fiendsbane-oath-paladin.json")],
#: [("feats.db", "fiendsbane-oath-redeemer.json")],
#: [("feats.db", "first-revelation-ancestors-mystery.json")],
#: [("feats.db", "first-revelation-battle-mystery.json")],
#: [("feats.db", "first-revelation-bones-mystery.json")],
#: [("feats.db", "first-revelation-cosmos-mystery.json")],
#: [("feats.db", "first-revelation-flames-mystery.json")],
#: [("feats.db", "first-revelation-life-mystery.json")],
#: [("feats.db", "first-revelation-lore-mystery.json")],
#: [("feats.db", "first-revelation-tempest-mystery.json")],
#: [("feats.db", "form-of-the-fiend-claw.json")],
#: [("feats.db", "form-of-the-fiend-hoof.json")],
#: [("feats.db", "form-of-the-fiend-jaws.json")],
#: [("feats.db", "form-of-the-fiend-tail.json")],
#: [("feats.db", "gunpowder-gauntlet.json")],
#: [("feats.db", "harsh-judgement.json")],
#: [("feats.db", "impeccable-crafting.json")],
#: [("feats.db", "impossible-volley-eldritch-archer.json")],
#: [("feats.db", "impossible-volley-fighter.json")],
#: [("feats.db", "impossible-volley-ranger.json")],
#: [("feats.db", "incredible-beastmaster-companion.json")],
#: [("feats.db", "incredible-luck-swashbuckler.json")],
#: [("feats.db", "innate-magical-intuition.json")],
#: [("feats.db", "inner-fire-ifrit.json")],
#: [("feats.db", "inner-fire-monk.json")],
#: [("feats.db", "invoke-the-elements-brine-may.json")],
#: [("feats.db", "invoke-the-elements-snow-may.json")],
#: [("feats.db", "invoke-the-elements-veil-may.json")],
#: [("feats.db", "invoke-the-elements-virga-may.json")],
#: [("feats.db", "invulnerable-juggernaut.json")],
#: [("feats.db", "irrepressible-halfling.json")],
#: [("feats.db", "judgement-of-the-monolith.json")],
#: [("feats.db", "keep-pace-bounty-hunter.json")],
#: [("feats.db", "keep-pace-game-hunter.json")],
#: [("feats.db", "knight-vigilant-dedication.json")],
#: [("feats.db", "know-it-all-bard.json")],
#: [("feats.db", "know-it-all-eldritch-researcher.json")],
#: [("feats.db", "living-weapon-claws.json")],
#: [("feats.db", "living-weapon-horn.json")],
#: [("feats.db", "living-weapon-jaws.json")],
#: [("feats.db", "living-weapon-tail.json")],
#: [("feats.db", "living-weapon-tusk.json")],
#: [("feats.db", "locate-lawbreakers.json")],
#: [("feats.db", "magic-sense-magus.json")],
#: [("feats.db", "manifold-edge-flurry.json")],
#: [("feats.db", "manifold-edge-outwit.json")],
#: [("feats.db", "manifold-edge-precision.json")],
#: [("feats.db", "master-summoning-spellcasting.json")],
#: [("feats.db", "perfections-path-fortitude.json")],
#: [("feats.db", "perfections-path-reflex.json")],
#: [("feats.db", "perfections-path-will.json")],
#: [("feats.db", "precise-debilitations.json")],
#: [("feats.db", "quick-change-beastkin.json")],
#: [("feats.db", "quick-change-vigilante.json")],
#: [("feats.db", "reckless-abandon-barbarian.json")],
#: [("feats.db", "recycled-cogwheels.json")],
#: [("feats.db", "rejuvination-token.json")],
#: [("feats.db", "reveal-beasts.json")],
#: [("feats.db", "revivification-protocol.json")],
#: [("feats.db", "righteous-resistance.json")],
#: [("feats.db", "saber-teeth.json")],
#: [("feats.db", "seek-injustice.json")],
#: [("feats.db", "shackles-of-law.json")],
#: [("feats.db", "shared-attunement.json")],
#: [("feats.db", "shield-warden-champion.json")],
#: [("feats.db", "shield-warden-fighter.json")],
#: [("feats.db", "shining-oath-liberator.json")],
#: [("feats.db", "shining-oath-paladin.json")],
#: [("feats.db", "shining-oath-redeemer.json")],
        #("feats.db", "silence-heresy.json"),  # AoN: sub-feat of Order of the Rack
#: [("feats.db", "skillful-tail-tiefling.json")],
#: [("feats.db", "soulsight-bard.json")],
#: [("feats.db", "soulsight-sorcerer.json")],
#: [("feats.db", "specialized-companion-animal-trainer.json")],
#: [("feats.db", "spiritual-disruption.json")],
#: [("feats.db", "sturdy-bindings.json")],
#: [("feats.db", "superior-sight-darkvision.json")],
#: [("feats.db", "superior-sight-low-light-vision.json")],
#: [("feats.db", "symphony-of-the-muse.json")],
#: [("feats.db", "trailblazing-stride.json")],
#: [("feats.db", "tusks-half-orc.json")],
#: [("feats.db", "tusks-orc.json")],
    }.get(item["_id"], []))
    # fmt: on

    if pack_override:
        yield from pack_override
        return

    filename = name.lower()
    if src["type"] in {"Background", "Ancestry", "Deity"}:
        filename = re.sub(r"\s*\(.*\)\s*", "", filename, flags=re.DOTALL)
    filename = re.sub(r"[\n,'()+!?…]+", "", filename, flags=re.DOTALL)
    filename = re.sub(r" +", "-", filename, flags=re.DOTALL)

    # return string.encode("ascii").decode()
    # .replace("\n", "").replace(" ", "-").replace(",", "").replace("'", "")

    match src["type"]:
        case "Ancestry":
            yield ("ancestries.db", f"{filename}.json")
            yield ("heritages.db", f"{filename}.json")
        case "Background":
            yield ("backgrounds.db", f"{filename}.json")
            for skill_raw in set(src.get("skill", [])):
                skill = skill_raw.lower().replace(" ", "-")
                yield ("backgrounds.db", f"{filename}-{skill}.json")
        case "Deity":
            yield ("deities.db", f"{filename}.json")
        case "Feat":
            yield ("feats.db", f"{filename}.json")
        case "Heritage":
            yield ("heritages.db", f"{filename}.json")
        case "Cantrip" | "Focus" | "Spell" | "Ritual":
            yield ("spells.db", f"{filename}.json")
        case "Item" | "Weapon" | "Armor" | "Shield":
            yield ("equipment.db", f"{filename}.json")


class Pack:
    def __init__(self, path):
        self.path = path
        self.modified = False
        self.obj = json_load(path)

    def modify(self):
        self.modified = True

    def close(self):
        if self.modified:
            json_store(self.path, self.obj)


def get_packs(pf2e_dir, item, files):
    src = item["_source"]

    any_match = False
    for database, filename in _get_packs(item):
        db_dir = (pf2e_dir / "packs" / "data" / database).resolve()
        if "*" in filename:
            paths = db_dir.glob(filename)
        else:
            paths = [db_dir / filename]

        for path in paths:
            if path.is_file():
                any_match = True
            else:
                continue

            # Filter on only files user requested to check
            if path not in files:
                continue

            yield Pack(path)

    if not any_match and src["type"] in {
        "Ancestry",
        "Armor",
        "Background",
        "Cantrip",
        "Deity",
        "Feat",
        "Focus",
        "Item",
        "Ritual",
        "Shield",
        "Spell",
        "Weapon",
    }:
        print(f"No packs found for {src['type']}: {src['name']}")


def parse_feat(item, pack):
    src = item["_source"]
    pass


def parse_item(item, pack):
    src = item["_source"]
    name = src["name"]

    # # Bulk
    # # equippedBulk == "Worn Bulk", weight == "Carried Bulk, value "L" == Light,
    # # empty equippedBulk string == same as weight
    # # Armor bulk is the equippedBulk, carried is +1
    # ebulk = src.get("bulk_raw", "-")

    # if src["type"] == "Armor" or pack.obj["type"] == "armor":
    #     weight = str(int({"-": 0, "L": 0}.get(ebulk, ebulk)) + 1)
    # else:
    #     weight = ebulk

    # # An empty equippedBulk means "same as carried weight"
    # if ebulk == weight:
    #     ebulk = ""

    # if ebulk != pack.obj["data"]["equippedBulk"]["value"]:
    #     pack.obj["data"]["equippedBulk"]["value"] = ebulk
    #     pack.modify()

    # if weight != pack.obj["data"]["weight"]["value"]:
    #     pack.obj["data"]["weight"]["value"] = weight
    #     pack.modify()

    # Traits
    # Usage (held in x)
    # Hands (number of)


def parse_ancestry(item, pack):
    src = item["_source"]
    name = src["name"]

    if "Heritage" in name:
        return parse_heritage(
            item, pack
        )  # AoN: categorizes versatile heritages as ancestries

    # ability_boost = src["ability_boost"]

    # ability_boost = [
    #    ["str", "dex", "con", "int", "wis", "cha"]
    #    if x == "Free" else [ABILITIES_MAP[x]] for x in ability_boost
    # ]

    # for i, boost in enumerate(ability_boost):
    #     print(f"{i}: {boost}")
    #     if set(boost) != set(pack.obj["data"]["boosts"][str(i)]["value"]):
    #         pack.obj["data"]["boosts"][str(i)]["value"] = boost
    #         pack.modify()

    # print(f"{name}: {ability_boost}")

    # HP
    if src["hp"] != pack.obj["data"]["hp"]:
        pack.obj["data"]["hp"] = src["hp"]
        pack.modify()

    # Speed
    for speed_type, speed in src["speed"].items():
        if speed_type == "land":
            if speed and speed != pack.obj["data"]["speed"]:
                pack.obj["data"]["speed"] = speed
                pack.modify()
            break

    # TODO "language" field
    # TODO "vision" field


def parse_heritage(item, pack):
    src = item["_source"]
    pass  # TODO


def parse_background(item, pack):
    src = item["_source"]
    name = src["name"]

    # Lore (Lots of false-positives)
    # lore_arr = []
    # for skill in src.get("skill", []):
    #     if skill.endswith("Lore"):
    #         lore_arr.append(skill.strip())
    # lore = " and ".join(lore_arr)

    # if lore.removesuffix("Lore").strip() != pack.obj["data"]["trainedLore"].removesuffix("Lore").strip():
    #     pack.obj["data"]["trainedLore"] = lore
    #     pack.modify()

    # feat = { x.lower() for x in src.get("feat", []) }
    # pack_feat = { x["name"].lower() for x in pack.obj["data"]["items"].values()}
    # if feat != pack_feat:
    #    print(f"{name}: {pack_feat} -> {feat}")


def parse_deity(item, pack):
    src = item["_source"]
    name = src["name"]

    ALIGNMENT = {
        "all": None,
        "Any": None,
        "CE": "CE",
        "CG": "CG",
        "CN": "CN",
        "LE": "LE",
        "LG": "LG",
        "LN": "LN",
        "N": "N",
        "NE": "NE",
        "NG": "NG",
        "No Alignment": None,
        "CE plus N if following the Reaper of Reputation": "CE",
    }
    # Alignment
    alignment = ALIGNMENT[src["alignment"]]

    if alignment != pack.obj["data"]["alignment"]["own"]:
        pack.obj["data"]["alignment"]["own"] = alignment
        pack.modify()

    # Follower Alignment
    follower_alignment = [ALIGNMENT[x] for x in src.get("follower_alignment", [])]

    if name == "Atheism":
        follower_alignment = []

    if set(follower_alignment) != set(pack.obj["data"]["alignment"]["follower"]):
        pack.obj["data"]["alignment"]["follower"] = follower_alignment
        pack.modify()

    # Divine Ability
    if name == "Asmodeus (The Prince of Darkness)":
        ability = []  # It's complicated
    else:
        ability = [ABILITIES_MAP[x] for x in src.get("ability", [])]

    if set(ability) != set(pack.obj["data"]["ability"]):
        pack.obj["data"]["ability"] = ability
        pack.modify()

    # Divine Skills
    skill = [
        {
            "Acrobatics": "acr",
            "Arcana": "arc",
            "Athletics": "ath",
            "Crafting": "cra",
            "Deception": "dec",
            "Diplomacy": "dip",
            "Intimidation": "itm",
            "Medicine": "med",
            "Nature": "nat",
            "Occultism": "occ",
            "Performance": "prf",
            "Religion": "rel",
            "Society": "soc",
            "Stealth": "ste",
            "Survival": "sur",
            "Thievery": "thi",
        }[x]
        for x in src.get("skill", [])
    ]

    if pack.obj["data"]["skill"] not in skill:
        # TODO Multiple skills??
        pack.obj["data"]["skill"] = skill[0] if len(skill) else None
        pack.modify()

    # Favored Weapon
    weapon = src.get("favored_weapon", [])
    weapon = [
        {
            "heavy mace": "mace",
        }.get(x, x)
        for x in weapon
    ]

    weapon = [x.lower().replace(" ", "-") for x in weapon]

    if set(weapon) != set(pack.obj["data"]["weapons"]):
        pack.obj["data"]["weapons"] = weapon
        pack.modify()

    # Domains
    domain = src.get("domain", [])

    if set(domain) != set(
        pack.obj["data"]["domains"]["primary"]
        + pack.obj["data"]["domains"]["alternate"]
    ):
        # DOMAINS BROKEN, NS: merge Primary and Alt domains into one list
        # pack.obj["data"]["domains"] = domain
        # pack.modify()
        print(
            f"{pack.path}:{name}: Nethys domains ({domain}) do not match system ({pack.obj['data']['domains']['primary']}/{pack.obj['data']['domains']['alternate']})"
        )

    # Divine Font
    font = src.get("divine_font", [])
    font = [x.lower() for x in font]

    if set(font) != set(pack.obj["data"]["font"]):
        pack.obj["data"]["font"] = font
        pack.modify()

    # Cleric Spells
    # TODO Spell upcasting?
    # spells_raw = src.get("cleric_spell", "")
    # if spells_raw:
    #    spells_raw = re.sub(r"\(.*\)", "", spells_raw, flags=re.DOTALL)
    #    spells_raw_s = [ x.strip() for x in spells_raw.split(",") ]
    #    spells = {}
    #    for spell in spells_raw_s:
    #        spell_level_raw, spell_name_raw = spell.split(":")

    #        # Remove the postfix for 1st, 2nd, 3rd, 4th, ...
    #        spell_level = spell_level_raw.strip().replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
    #        _ = int(spell_level)  # Sanity check it's a valid integer

    #        # Translate spell name to a compendium reference
    #        spell_name = spell_name_raw.strip().replace(" ", "-").replace(",", "").replace("'", "")
    #        spell_pack = os.path.join(pf2e_path, "packs", "data", "spells.db", f"{spell_name}.json")
    #        spell_obj = json_load(spell_pack)
    #        spell_id = spell_obj["_id"]
    #        spell_comp = f"Compendium.pf2e.spells-srd.{spell_id}"

    #        # Paizo has a thing with granting spells at a level lower then the
    #        # spell allows, cap it
    #        if int(spell_level) < spell_obj["data"]["level"]["value"]:
    #            spell_level = str(spell_obj["data"]["level"]["value"])

    #        spells[spell_level] = spell_comp

    #    if spells != pack.obj["data"]["spells"]:
    #        pack.obj["data"]["spells"] = spells
    #        pack.modify()


def parse_spell(item, pack):
    src = item["_source"]
    name = src["name"]

    # Traditions
    traditions = [x.lower() for x in src.get("tradition", []) if x != "Elemental"]
    if name == "Mother's Blessing":
        # Pz: Rituals shouldn't have traditions, but printed with
        # Primal trait. AoN ignores it but we don't.
        traditions = ["primal"]

    # Ignore Dark Archive spell traditions, which didn't add traditions to a
    # bunch of spells but pathfinder-2e added them anyway.
    if traditions or src.get("source", ["NA"])[0] != "Dark Archive":
        if set(traditions) != set(pack.obj["data"]["traditions"]["value"]):
            pack.obj["data"]["traditions"]["value"] = traditions
            pack.modify()

    # Spell Category
    if src["type"] != "Cantrip":
        # Cantrip categories are weird. In the book, "Cantrip" and "Focus" use
        # the same field. Paizo publishes a Focus Cantrip as just Cantrip. But
        # in FVTT we track both.
        category = {
            "Cantrip": "spell",
            "Focus": "focus",
            "Ritual": "ritual",
            "Spell": "spell",
        }[src["type"]]

        if category != pack.obj["data"]["category"]["value"]:
            pack.obj["data"]["category"]["value"] = category
            pack.modify()

    # Spell School
    school = src.get("school")
    school = {
        "spell-738": "transmutation",  # Pz: Published without a school
        "ritual-24": "transmutation",  # Pz: Published without a school
    }.get(item["_id"], school)

    if school != pack.obj["data"]["school"]["value"]:
        pack.obj["data"]["school"]["value"] = school
        pack.modify()

    # Time
    time = TIME_MAP.get(src["actions"], src["actions"])

    time = {
        "Thoughtful Gift": "1 (up to 3 if heightened)",  # Weirdness
    }.get(name, time)

    if time.lower() != pack.obj["data"]["time"]["value"].lower():
        pack.obj["data"]["time"]["value"] = time
        pack.modify()

    # Components
    material = False
    somatic = False
    verbal = False
    if "component" in src:
        for component in src["component"]:
            if component == "material":
                material = True
            if component == "somatic":
                somatic = True
            if component == "verbal":
                verbal = True

    material, somatic, verbal = {
        "Familiar's Face": (True, True, False),  # Nethys error
        "Counter Performance": (False, True, True),  # Variable number of components
    }.get(name, (material, somatic, verbal))

    if material != pack.obj["data"]["components"]["material"]:
        pack.obj["data"]["components"]["material"] = material
        pack.modify()

    if somatic != pack.obj["data"]["components"]["somatic"]:
        pack.obj["data"]["components"]["somatic"] = somatic
        pack.modify()

    if verbal != pack.obj["data"]["components"]["verbal"]:
        pack.obj["data"]["components"]["verbal"] = verbal
        pack.modify()

    # Ritual Primary Check
    if src["type"] == "Ritual":
        pri_check = no_uni(src["primary_check"])
        pri_check = (
            pri_check.strip().replace("  ", " ").replace("  ", " ").replace(" )", ")")
        )  # Nethys Search bug

        pri_check = {
            "Empower Ley Line": "Arcana, Nature, Occultism, or Religion matching the ley line's tradition (legendary)",  # NS: error
            "Establish Nexus": "Arcana, Nature, Occultism, or Religion, matching the ley line's tradition (master)",  # NS: error
        }.get(name, pri_check)

        if pri_check != pack.obj["data"]["primarycheck"]["value"]:
            pack.obj["data"]["primarycheck"]["value"] = pri_check
            pack.modify()

    # # Ritual Secondary Casters
    # # TODO Pull request changes
    # if src["type"] == "Ritual":
    #     if "secondary_casters_raw" in src:
    #         sec_casters = src["secondary_casters_raw"]
    #     else:
    #         sec_casters = ""

    #     if sec_casters != pack.obj["data"]["secondarycasters"]["value"]:
    #         pack.obj["data"]["secondarycasters"]["value"] = sec_casters
    #         pack.modify()

    # # Spell target
    # # TODO there are lots of liberties taken with targets in Foundry pf2e
    # if "target" in src:
    #     target = no_uni(src["target"])
    # else:
    #     target = ""

    # if target.lower() != pack.obj["data"]["target"]["value"].lower():
    #     pack.obj["data"]["target"]["value"] = target
    #     pack.modify()

    # # Ritual Secondary Check
    # # TODO Pull request changes
    # if src["type"] == "Ritual":
    #     if "secondary_check" in src:
    #         sec_check = src["secondary_check"]
    #         sec_check = sec_check.replace(" ,", ",")
    #     else:
    #         sec_check = ""

    #     if sec_check != pack.obj["data"]["secondarycheck"]["value"]:
    #         pack.obj["data"]["secondarycheck"]["value"] = sec_check
    #         pack.modify()

    # TODO Ritual Cost/Materials
    # TODO Spell range
    # TODO Spell area
    # TODO Spell duration


def parse_source(item, pack):
    src = item["_source"]
    name = src["name"]
    source = src["source"]

    # fmt: off
    source = [(
        {
            "Abomination Vaults Player's Guide": "Pathfinder: Abomination Vaults Player's Guide",
            "Absalom, City of Lost Omens": "Pathfinder Lost Omens: Absalom, City of Lost Omens",
            "Advanced Player's Guide": "Pathfinder Advanced Player's Guide",
            "Age of Ashes Player's Guide": "Pathfinder: Age of Ashes Player's Guide",
            "Agents of Edgewatch Player's Guide": "Pathfinder: Agents of Edgewatch Player's Guide",
            "Battle of the Pantheons Winner Announcement": "Pathfinder Blog",
            "Bestiary 2": "Pathfinder Bestiary 2",
            "Bestiary 3": "Pathfinder Bestiary 3",
            "Bestiary": "Pathfinder Bestiary",
            "Blood Lords Player's Guide": "Pathfinder: Blood Lords Player's Guide",
            "Character Guide": "Pathfinder Lost Omens: Character Guide",
            "Core Rulebook": "Pathfinder Core Rulebook",
            "Dark Archive": "Pathfinder Dark Archive",
            "Extinction Curse Player's Guide": "Pathfinder: Extinction Curse Player's Guide",
            "Fists of the Ruby Phoenix Player's Guide": "Pathfinder: Fists of the Ruby Phoenix Player's Guide",
            "Friends in High Places": "Pathfinder Blog",
            "Gods & Magic": "Pathfinder Lost Omens: Gods & Magic",
            "Gods of the Expanse": "Pathfinder Blog",
            "Guns & Gears": "Pathfinder Guns & Gears",
            "Knights of Lastwall": "Pathfinder Lost Omens: Knights of Lastwall",
            "Legends": "Pathfinder Lost Omens: Legends",
            "Malevolence": "Pathfinder Adventure: Malevolence",
            "Little Trouble in Big Absalom": "Pathfinder Adventure: Little Trouble in Big Absalom",
            "Monsters of Myth": "Pathfinder Lost Omens: Monsters of Myth",
            "Night of the Gray Death": "Pathfinder Adventure: Night of the Gray Death",
            "PFS Guide": "Pathfinder Lost Omens: Pathfinder Society Guide",
            "Pathfinder #153: Life's Long Shadow": "Pathfinder #153: Life's Long Shadows",  # Nethys typo
            "Pathfinder #172: Secrets of the Temple City": "Pathfinder #172: Secrets of the Temple-City",
            "Quest for the Frozen Flame Player's Guide": "Pathfinder: Quest for the Frozen Flame Player's Guide",
            "Secrets of Magic": "Pathfinder Secrets of Magic",
            "Shadows at Sundown": "Pathfinder Adventure: Shadows at Sundown",
            "The Fall of Plaguestone": "Pathfinder Adventure: The Fall of Plaguestone",
            "The Mwangi Expanse": "Pathfinder Lost Omens: The Mwangi Expanse",
            "The Waters of Stone Ring Pond": "Pathfinder Blog: The Waters of Stone Ring Pond",
            "Threshold of Knowledge": "Pathfinder Adventure: Threshold of Knowledge",
            "World Guide": "Pathfinder Lost Omens: World Guide",
            "Grand Bazaar": "Pathfinder Lost Omens: The Grand Bazaar",
            "Troubles in Otari": "Pathfinder Adventure: Troubles in Otari",
            "Gamemastery Guide": "Pathfinder Gamemastery Guide",
            "Pathfinder Special: Fumbus": "Pathfinder Special: Fumbus!",
            "Pathfinder Beginner Box: Game Master's Guide": "Pathfinder Beginners Box",
            "Ancestry Guide": "Pathfinder Lost Omens: Ancestry Guide",
            "City of Absalom": "Pathfinder Lost Omens: Absalom, City of Lost Omens",
            "The Slithering": "Pathfinder Adventure: The Slithering",
            "Redpitch Alchemy": "Pathfinder Blog",
            "GM's Toolkit: Secret Keeper's Mask": "Pathfinder Blog",
            "Book of the Dead": "Pathfinder Book of the Dead",
            "March of the Dead": "Pathfinder Book of the Dead",  # An adventure inside of the BOTD
            "Outlaws of Alkenstar Player's Guide": "Pathfinder: Outlaws of Alkenstar Player's Guide",
            "Pathfinder #178: Punks in a Powderkeg": "Pathfinder #178: Punks in a Powder Keg",
        }
        .get(x, x)
        .replace("PFS", "Pathfinder Society")
    ) for x in source ]

    source = {
        "Ancestry": {
            "Azarketi": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
        },
        "Deity": {
            "Atheism": ["Pathfindier Core Rulebook, Pathfinder Lost Omens: Gods & Magic"],  # FVTT: weirdness
        },
        "Weapon": {
            "Gill Hook": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Boarding Axe": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
        },
        "Item": {
            "Archaic Wayfinder": ["Pathfinder Lost Omens: World Guide"],  # NS: error
            "Bi-Resonant Wayfinder": ["Pathfinder Lost Omens: Character Guide"],  # NS: error
            "Chronicler Wayfinder": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Elemental Wayfinder (Air)": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Elemental Wayfinder (Earth)": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Elemental Wayfinder (Fire)": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Elemental Wayfinder (Water)": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Fashionable Wayfinder": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Feather Token (Balloon)": ["Pathfinder Special: Fumbus!"],  # NS: error
            "Feather Token (Puddle)": ["Pathfinder Special: Fumbus!"],  # NS: error
            "Flawed Orb of Gold Dragonkind": ["Pathfinder #150: Broken Promises"],  # NS: error
            "Homeward Wayfinder": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Hummingbird Wayfinder": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Orb of Dragonkind": ["Pathfinder #150: Broken Promises"],  # Printed in multiple books
            "Orb Shard": ["Pathfinder #150: Broken Promises"],  # Printed in multiple books
            "Pathfinder Chronicle": ["Pathfinder Lost Omens: Character Guide"],  # NS: error
            "Razmiri Wayfinder": ["Pathfinder Lost Omens: Pathfinder Society Guide"],  # NS: error
            "Refined Pesh": ["Pathfinder Lost Omens: World Guide"],  # Printed in multiple books
            "Shining Wayfinder": ["Pathfinder Lost Omens: Character Guide"],  # NS: error
            "Vanishing Wayfinder": ["Pathfinder Lost Omens: Character Guide"],  # NS: error
            "Wayfinder of Rescue": ["Pathfinder Society Scenario #1-03: Escaping the Grave"],  # NS: error
            "Wondrous Figurine (Bismuth Leopards)": ["Pathfinder #170: Spoken on the Song Wind"],  # NS: error
            "Wondrous Figurine (Ruby Hippopotamus)": ["Pathfinder #170: Spoken on the Song Wind"],  # NS: error
            "Wondrous Figurine (Candy Constrictor)": ["Pathfinder #152: Legacy of the Lost God"],  # NS: error
            "Wondrous Figurine (Rubber Bear)": ["Pathfinder #152: Legacy of the Lost God"],  # NS: error
        },
        "Feat": {
            "Aboleth Transmutation": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Alghollthu Bound": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Azarketi Lore": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Azarketi Weapon Aptitude": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Azarketi Weapon Familiarity": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Azarketi Weapon Expertise": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Cynical": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Drag Down": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Perfect Dive": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Replenishing Hydration": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Riptide": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
            "Surface Skimmer": ["Pathfinder Lost Omens: Absalom, City of Lost Omens"],  # AoN: doesn't list re-print
        },
    }.get(src["type"], {}).get(name, source)
    # fmt: on

    if src["type"] == "Focus" and name == "Dragon Breath":
        # Nethys groups all Dragon Breath versions into one
        if pack.path.name in [
            "dragon-breath-cloud.json",
            "dragon-breath-crystal-or-forest.json",
            "dragon-breath-sea.json",
            "dragon-breath-sky.json",
            "dragon-breath-sovereign.json",
            "dragon-breath-umbral.json",
            "dragon-breath-underworld.json",
        ]:
            source = ["Pathfinder Lost Omens: The Mwangi Expanse"]

    if pack.obj["data"]["source"]["value"] not in source:
        pack.obj["data"]["source"]["value"] = source[0]
        pack.modify()


def parse_level(item, pack):
    src = item["_source"]

    if "level" not in pack.obj["data"]:
        return

    level = src.get("level", 0)
    level = {
        "equipment-1102-4": 19,  # NS: bug
        "spell-663": 6,  # AoN: error, reported 7/29/22
        "weapon-201": 1,  # AoN: error
        "spell-1154": 3,  # AoN: error, reported 7/29/22
        "spell-1108": 6,  # AoN: error, reported 7/29/22
    }.get(item["_id"], level)

    if int(level) != pack.obj["data"]["level"]["value"]:
        pack.obj["data"]["level"]["value"] = int(level)
        pack.modify()


def parse_rarity(item, pack):
    src = item["_source"]
    name = src["name"]

    if "traits" not in pack.obj["data"]:
        return

    rarity = src.get("rarity", "common")
    # fmt: off
    rarity = {
        "Background": {
            "Sponsored by Family": "uncommon",  # AoN: error
            "Sponsored by Teacher Ot": "uncommon",  # AoN: error
            "Sponsored by a Village": "uncommon",  # AoN: error
            "Sponsored by a Stranger": "uncommon",  # AoN: error
            "Unsponsored": "uncommon",  # AoN: error
        },
        "Weapon": {
            "Axe Musket": "uncommon",  # NS: bug
            "Black Powder Knuckle Dusters": "uncommon",  # NS: bug
            "Cane Pistol": "uncommon",  # NS: bug
            "Dagger Pistol": "uncommon",  # NS: bug
            "Explosive Dogslicer": "uncommon",  # NS: bug
            "Gnome Amalgam Musket": "uncommon",  # NS: bug
            "Gun Sword": "uncommon",  # NS: bug
            "Hammer Gun": "uncommon",  # NS: bug
            "Mace Multipistol": "uncommon",  # NS: bug
            "Piercing Wind": "uncommon",  # NS: bug
            "Rapier Pistol": "uncommon",  # NS: bug
            "Repeating Crossbow Magazine": "uncommon",  # NS: bug
            "Repeating Heavy Crossbow Magazine": "uncommon",  # NS: bug
            "Three Peaked Tree": "uncommon",  # NS: bug
        },
        "Item": {
            "Camouflage Suit": "uncommon",  # AoN: error
            "Camouflage Suit (Superb)": "uncommon",  # AoN: error
            "Concealed Holster": "uncommon",  # AoN: error
            "Crimson Fulcrum Lens": "unique",  # NS: bug
            "Disrupting": "common",  # NS: bug
            "Ebon Fulcrum Lens": "unique",  # NS: bug
            "Emerald Fulcrum Lens": "unique",  # NS: bug
            "Firearm Cleaning Kit": "uncommon",  # AoN: error
            "Mask (Plague)": "uncommon",  # AoN: error
            "Ochre Fulcrum Lens": "unique",  # NS: bug
            "Orb Shard": "rare",  # NS: bug
            "Silencer": "uncommon",  # AoN: error
            "Staff of Enchantment (Greater)": "common",  # NS: bug
            "Staff of Enchantment": "common",  # NS: bug
            "Thieves' Tools (Infiltrator)": "common",  # NS: bug
            "Thieves' Tools (Infiltrator Picks)": "common",  # NS: bug
            "Thieves' Tools (Replacement Picks)": "common",  # NS: bug
            "Thieves' Tools": "common",  # NS: bug
            "Tripod": "uncommon",  # AoN: error
            "Waffle Iron (Imprint)": "common",  # NS: bug
            "Waffle Iron": "common",  # NS: bug
            "Warding Tattoo": "common",  # NS: bug
            "Warding Tattoo (Trail)": "common",  # NS: bug
            "Warding Tattoo (Wave)": "common",  # NS: bug
            "Wondrous Figurine (Bismuth Leopards)": "uncommon",  # NS: bug
            "Wondrous Figurine (Golden Lions)": "common",  # NS: bug
            "Wondrous Figurine (Jade Serpent)": "common",  # NS: bug
            "Wondrous Figurine (Marble Elephant)": "common",  # NS: bug
            "Wondrous Figurine (Ruby Hippopotamus)": "uncommon",  # NS: bug
        },
        "Feat": {
            "Spellshot Dedication": "common",  # AoN: error
        },
    }.get(src["type"], {}).get(name, rarity)

    rarity = {
        "weapon-123": "uncommon", # NS: APGv2 update
        "feat-1376": "uncommon", # NS: APGv2 update
        "feat-1422": "uncommon", # NS: APGv2 update
        "feat-1406": "uncommon", # NS: APGv2 update
        "spell-661": "uncommon", # NS: APGv2 update
        "spell-662": "uncommon", # NS: APGv2 update
        "spell-663": "uncommon", # NS: APGv2 update
        "spell-664": "uncommon", # NS: APGv2 update
    }.get(item["_id"], rarity)
    # fmt: on

    # Rarity (Traits)
    if rarity != pack.obj["data"]["traits"]["rarity"]:
        pack.obj["data"]["traits"]["rarity"] = rarity
        pack.modify()


def parse_price(item, pack):
    src = item["_source"]
    name = src["name"]

    if "price" not in pack.obj["data"]:
        return

    price_raw = {
        "equipment-1150": "30 gp",  # AoN: error
        "equipment-1174": "100 gp",  # FVTT: uses base item value
        "equipment-1175": "1000 gp",  # FVTT: uses base item value
        "equipment-1176": "260 gp",  # FVTT: uses base item value
        "equipment-1177": "4700 gp",  # FVTT: uses base item value
        "equipment-1178": "35 gp",  # FVTT: uses base item value
        "equipment-1179": "2500 gp",  # FVTT: uses base item value
        "equipment-1180": "100 gp",  # FVTT: uses base item value
        "equipment-1181": "2000 gp",  # FVTT: uses base item value
        "equipment-1183": "2000 gp",  # FVTT: uses base item value
        "equipment-1184": "1000 gp",  # FVTT: uses base item value
        "equipment-1185": "14000 gp",  # FVTT: uses base item value
        "equipment-1395": "1 gp",  # NS: bug
        "equipment-1544": "20 gp",  # AoN: wrong price (submitted)
        "equipment-595": "24000 gp",  # FVTT: uses base item value
    }.get(item["_id"], src.get("price_raw", ""))

    match = re.match(
        r"(([0-9 ]+)\s*gp)?[\s,]*(([0-9 ]+)\s*sp)?[\s,]*(([0-9 ]+)\s*cp)?", price_raw
    )
    price = {}

    if match:
        # if m := match.group(3):
        #    price["pp"] = int(m)
        if m := match.group(2):
            price["gp"] = int(m.replace(" ", ""))
        if m := match.group(4):
            price["sp"] = int(m.replace(" ", ""))
        if m := match.group(6):
            price["cp"] = int(m.replace(" ", ""))

    print(
        f"{name}: raw price = {price_raw}, new price = {price}, old price = {pack.obj['data']['price']['value']}"
    )
    for metal in ["pp", "gp", "sp", "cp"]:
        if metal not in price and metal in pack.obj["data"]["price"]["value"]:
            del pack.obj["data"]["price"]["value"][metal]
            pack.modify()

        elif (
            (metal in price and metal not in pack.obj["data"]["price"]["value"])
            or metal in price
            and price[metal] != pack.obj["data"]["price"]["value"][metal]
        ):
            pack.obj["data"]["price"]["value"][metal] = price[metal]
            pack.modify()


def parse_traits(item, pack):
    src = item["_source"]
    name = src["name"]

    if "traits" not in pack.obj["data"]:
        return

    trait_raw = src.get("trait_raw", [])

    # Scan Traits
    traits = []
    for traits_item in trait_raw:
        if traits_item in RARITY_MAP:
            pass
        elif traits_item == "Legacy - Age of Ashes":
            pass  # NS: error
        elif traits_item in TRAITS_SCHOOL_MAP:
            pass
        elif traits_item == "Druid" or traits_item == "Cleric":
            pass  # Traits for Druids and Clerics are a mess, ignore them
        elif traits_item in TRADITIONS_MAP:
            # Nethys normally doesn't put traditions in the traits list, but
            # for some spells with publishing errors they will. We ignore
            # them.
            pass
        else:
            traits.append(traits_item.lower().replace(" ", "-"))

    # Traits for Druids and Clerics are a mess, just match FVTT
    if "druid" in pack.obj["data"]["traits"]["value"]:
        traits.append("druid")
    if "cleric" in pack.obj["data"]["traits"]["value"]:
        traits.append("cleric")

    if set(traits) != set(pack.obj["data"]["traits"]["value"]):
        pack.obj["data"]["traits"]["value"] = traits
        pack.modify()


def check_missing(data_dir, files, jsons):
    """
    Check we aren't missing any FVTT json objects that we should have
    found
    """

    # Build list of jsons we expect to find
    must_check = files.copy()

    # Remove jsons that had at least one match
    for key in sorted(jsons):
        must_check.discard(key)

    # Remove jsons that are missing for a known reason
    must_check -= {
        (data_dir / x / y).resolve()
        for x, y in [
            # fmt: off
            ("backgrounds.db", "reclaimer-investigator.json"),  # Nethys is missing this, Pathfinder Lost Omens: Knights of Lastwall
            ("backgrounds.db", "almas-clerk.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("backgrounds.db", "glorianas-fixer.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("backgrounds.db", "gold-falls-regular.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("backgrounds.db", "guest-of-sedeq-lodge.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("backgrounds.db", "sandswept-survivor.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("backgrounds.db", "friend-of-greensteeples.json"),  # Nethys is missing this, Pathfinder Blog: Pathfinder Society Year 4 Rule Updates
            ("deities.db", "alocer.json"),  # Nethys is missing this, Pathfinder One-Shot #2: Dinner at Lionlodge
            ("spells.db", "lay-on-hands-vs-undead.json"),  # Variant of lay-on-hands spell
            ("spells.db", "unfettered-mark.json"),  # Nethys is missing this, Pathfinder #161: Belly of the Black Whale
            ("spells.db", "touch-of-corruption-healing.json"),  # No idea, some sort of FVTT alternate spell
            ("spells.db", "anima-invocation-modified.json"), # Nethys is missing this, Age of Ashes - 06 - Broken Promises (75)
            ("spells.db", "aspirational-state.json"), # Nethys is missing this, Pathfinder Society Scenario #2-22: Breaking the Storm: Excising Ruination
            ("spells.db", "savants-curse.json"), # Nethys is missing this, Pathfinder #164: Hands of the Devil
            # fmt: on
        ]
    }

    for missed_file in sorted(must_check):
        print(f"Missed json: {missed_file.relative_to(Path.cwd())}")


def main():
    parser = argparse.ArgumentParser(description="TODO, sorry")
    parser.add_argument(
        "files",
        nargs="*",
        help="List of packs/data/*/*.json files to run on, if none are supplied run on all of them",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Print extra debug",
    )
    parser.add_argument(
        "-p", "--pf2e", default=".", help="Path to root of pathfinder-2e repo"
    )
    parser.add_argument(
        "-u",
        "--url",
        default="https://2e.aonprd.com:9200/aon-test/_search",
        help="URL of the ElasticSearch endpoint to download Nethys Search data from",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force new download of Nethys Search data",
    )
    args = parser.parse_args()

    pf2e_dir = Path(args.pf2e).resolve()
    data_dir = pf2e_dir / "packs" / "data"

    if not data_dir.exists():
        raise RuntimeError(
            f"Path to pathfinder-2e repo does not look valid ({pf2e_dir})"
        )

    files = {Path(file).resolve() for file in args.files} if args.files else {data_dir}

    def expand_dirs(files):
        for file in files:
            if file.is_dir():
                yield from file.glob("**/*.json")
            else:
                yield file

    files = set(expand_dirs(files))

    json_to_names = {}

    for item in get_nethys_items(args.url, args.force):
        src = item["_source"]

        if args.debug:
            print(f"Parsing Nethys object {src['name']}")
        for pack in get_packs(pf2e_dir, item, files):
            if args.debug:
                print(f"Matched {src['name']} to {pack.path}")

            if pack.path not in json_to_names:
                json_to_names[pack.path] = [src["name"]]
            else:
                json_to_names[pack.path].append(src["name"])

            parse_source(item, pack)
            parse_level(item, pack)
            parse_rarity(item, pack)
            parse_price(item, pack)

            match src["type"]:
                case "Ancestry":
                    parse_ancestry(item, pack)
                case "Heritage":
                    parse_heritage(item, pack)
                case "Background":
                    parse_background(item, pack)
                case "Deity":
                    parse_deity(item, pack)
                case "Feat":
                    parse_feat(item, pack)
                case "Cantrip" | "Focus" | "Spell" | "Ritual":
                    parse_traits(item, pack)
                    parse_spell(item, pack)
                case "Item" | "Weapon" | "Armor" | "Shield":
                    parse_item(item, pack)

            pack.close()

    # for key, value in json_to_names.items():
    #    if len(value) > 1:
    #        print(f"Multiple hits for: {key}, {value}")

    check_missing(data_dir, files, json_to_names.keys())


if __name__ == "__main__":
    main()
