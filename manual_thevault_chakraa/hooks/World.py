# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from typing import Any
from worlds.AutoWorld import World
from BaseClasses import MultiWorld, CollectionState, Item

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value, format_state_prog_items_key, ProgItemsCat

# calling logging.info("message") anywhere below in this file will output the message to both console and log file
import logging, math
from worlds.generic.Rules import add_item_rule
from .Rules import vault_settings

# Bonus key items join the pool once the keys needed reach their threshold
BONUS_KEY_ITEMS = {
    20: ["Mind Goblin Deez (+5 Vault Keys)", "Zizzlecrank with the Drill! (+5 Vault Keys)"],
    40: ["Time is Money, Friend. (+5 Vault Keys)", "Snotgrub drops a Vial of Acid on the lock! (+5 Vault Keys)"],
    75: ["Lining up the Firing Squad and SHOOT IT TO OBLIVIION! (+10 Vault Keys)", "STRIKING IT WITH A HUGE FKIN' MACE! (+10 Vault Keys)"],
    100: ["Strapping The Vault with a Jetpack and sending it sky-high! (+10 Vault Keys)", "Bringing in the Explosives! (+10 Vault Keys)"],
}
KEY_ITEM_NAMES = {"Vault Key"} | {name for names in BONUS_KEY_ITEMS.values() for name in names}

# A Vault's key items can take at most this share of the other games' free locations
# (the ones not needed for their own progression items)
MAX_SHARE_OF_OTHER_LOCATIONS = 0.75

########################################################################################
## Order of method calls when the world generates:
##    1. create_regions - Creates regions and locations
##    2. create_items - Creates the item pool
##    3. set_rules - Creates rules for accessing regions and locations
##    4. generate_basic - Runs any post item pool options, like place item/category
##    5. pre_fill - Creates the victory location
##
## The create_item method is used by plando and start_inventory settings to create an item from an item name.
## The fill_slot_data method will be used to send data to the Manual client for later use, like deathlink.
########################################################################################



# Use this function to change the valid filler items to be created to replace item links or starting items.
# Default value is the `filler_item_name` from game.json
def hook_get_filler_item_name(world: World, multiworld: MultiWorld, player: int) -> str | bool:
    return False

def before_generate_early(world: World, multiworld: MultiWorld, player: int) -> None:
    """Works out the key thresholds for this player, and refuses to generate a Vault without another game to hold its keys."""
    world.vault = vault_settings(get_option_value(multiworld, player, "amount_of_keys"),
                                 get_option_value(multiworld, player, "amount_of_treasure_in_vault"),
                                 get_option_value(multiworld, player, "vault_stages"))
    world.vault_starting_keys = 0

    if hasattr(multiworld, "generation_is_fake"):  # Universal Tracker
        return
    if not [p for p in multiworld.player_ids if multiworld.game[p] != world.game]:
        raise Exception(f"The Vault ({multiworld.player_name[player]}) can't be played alone: its keys have to be hidden "
                        "in other games. Add at least one other game to the multiworld.")

# Called before regions and locations are created. Not clear why you'd want this, but it's here. Victory location is included, but Victory event is not placed yet.
def before_create_regions(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after regions and locations are created, in case you want to see or modify that information. Victory location is included.
def after_create_regions(world: World, multiworld: MultiWorld, player: int):
    # Locations above the amount_of_treasure_in_vault option are filtered out before creation,
    # in before_is_location_enabled (hooks/Helpers.py)
    pass

# This hook allows you to access the item names & counts before the items are created. Use this to increase/decrease the amount of a specific item in the pool
# Valid item_config key/values:
# {"Item Name": 5} <- This will create qty 5 items using all the default settings
# {"Item Name": {"useful": 7}} <- This will create qty 7 items and force them to be classified as useful
# {"Item Name": {"progression": 2, "useful": 1}} <- This will create 3 items, with 2 classified as progression and 1 as useful
# {"Item Name": {0b0110: 5}} <- If you know the special flag for the item classes, you can also define non-standard options. This setup
#       will create 5 items that are the "useful trap" class
# {"Item Name": {ItemClassification.useful: 5}} <- You can also use the classification directly
def before_create_items_all(item_config: dict[str, int|dict], world: World, multiworld: MultiWorld, player: int) -> dict[str, int|dict]:
    """Puts the keys needed plus extra_keys_percent more key value in the pool, using bonus key items where they unlock."""
    keys_required = world.vault["keys_required"]
    extra_percent = get_option_value(multiworld, player, "extra_keys_percent")
    values = {name: world.item_name_to_item[name]["value"]["key"] for name in KEY_ITEM_NAMES}

    bonus = [name for threshold, names in BONUS_KEY_ITEMS.items() if keys_required >= threshold for name in names]
    bonus_value = sum(values[name] for name in bonus)

    def single_keys(percent: int) -> int:
        return max(0, math.ceil(keys_required * (100 + percent) / 100) - bonus_value)

    # Fewest Vault Keys that still open The Vault, used if the other games turn out to lack room
    world.vault_min_single_keys = single_keys(0)
    world.vault_bonus_value = bonus_value

    item_config["Vault Key"] = single_keys(extra_percent)
    for names in BONUS_KEY_ITEMS.values():
        for bonus_name in names:
            item_config[bonus_name] = 1 if bonus_name in bonus else 0
    return item_config

def fit_keys_in_other_games(world: World, multiworld: MultiWorld, player: int):
    """Key items can only go in other games (Treasures are behind the keys), so keep them to a share of
    those games' locations, split between every Vault in the multiworld. Runs once every game has
    created its items, since some games only number their locations at that point."""
    if hasattr(multiworld, "generation_is_fake"):  # Universal Tracker
        return
    other_locations = sum(1 for region in multiworld.regions if multiworld.game[region.player] != world.game
                          for location in region.locations if location.address is not None)
    # Locations the other games need for their own progression items aren't free for keys
    other_progression = sum(1 for item in multiworld.itempool if multiworld.game[item.player] != world.game and item.advancement)
    vaults = sum(1 for p in multiworld.player_ids if multiworld.game[p] == world.game)
    room = int(max(0, other_locations - other_progression) * MAX_SHARE_OF_OTHER_LOCATIONS / vaults)

    key_items = [item for item in multiworld.itempool if item.player == player and item.name in KEY_ITEM_NAMES]
    single_keys = [item for item in key_items if item.name == "Vault Key"]
    if len(key_items) <= room:
        return

    name = multiworld.player_name[player]
    keys_required = world.vault["keys_required"]
    extra_percent = get_option_value(multiworld, player, "extra_keys_percent")

    def take_out(items: list):
        # Each key taken out of the pool is replaced by filler, so this world keeps as many items as locations
        for item in items:
            multiworld.itempool.remove(item)
            multiworld.itempool.append(world.create_filler())

    # First lower the extra keys
    extra_singles = len(single_keys) - world.vault_min_single_keys
    dropped = min(extra_singles, len(key_items) - room)
    if dropped > 0:
        take_out(single_keys[:dropped])
        single_keys = single_keys[dropped:]
        percent = max(0, (len(single_keys) + world.vault_bonus_value) * 100 // keys_required - 100)
        logging.warning(f"The Vault ({name}): extra keys lowered from {extra_percent}% to {percent}%, "
                        f"the other games don't have enough room to hide more keys.")

    # Still too many: hand out some Vault Keys at the start
    starting = min(len(single_keys), len(key_items) - dropped - room)
    if starting > 0:
        moved = single_keys[:starting]
        take_out(moved)
        for item in moved:
            multiworld.push_precollected(item)
        world.vault_starting_keys = starting
        logging.warning(f"The Vault ({name}): you start with {starting} Vault Keys, "
                        f"the other games don't have enough room to hide all of them.")

# The item pool before starting items are processed, in case you want to see the raw item pool at that stage
def before_create_items_starting(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The item pool after starting items are processed but before filler is added, in case you want to see the raw item pool at that stage
def before_create_items_filler(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def after_create_items(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: World, multiworld: MultiWorld, player: int):
    fit_keys_in_other_games(world, multiworld, player)

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: World, multiworld: MultiWorld, player: int):
    # keys_outside_vault: never put this player's keys in their own Treasures
    if is_option_enabled(multiworld, player, "keys_outside_vault"):
        for location in (location for region in multiworld.get_regions(player) for location in region.locations):
            if location.name.startswith("Treasure "):
                add_item_rule(location, lambda item: item.player != player or item.name not in KEY_ITEM_NAMES)

    def Example_Rule(state: CollectionState) -> bool:
        # Calculated rules take a CollectionState object and return a boolean
        # True if the player can access the location
        # CollectionState is defined in BaseClasses
        return True

    ## Common functions:
    # location = world.get_location(location_name, player)
    # location.access_rule = Example_Rule

    ## Combine rules:
    # old_rule = location.access_rule
    # location.access_rule = lambda state: old_rule(state) and Example_Rule(state)
    # OR
    # location.access_rule = lambda state: old_rule(state) or Example_Rule(state)

# The item name to create is provided before the item is created, in case you want to make changes to it
def before_create_item(item_name: str, world: World, multiworld: MultiWorld, player: int) -> str:
    return item_name

# The item that was created is provided after creation, in case you want to modify the item
def after_create_item(item: ManualItem, world: World, multiworld: MultiWorld, player: int) -> ManualItem:
    return item

# This method is run towards the end of pre-generation, before the place_item options have been handled and before AP generation occurs
def before_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is run every time an item is added to the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be cancelled/undone in after_remove_item
def after_collect_item(world: World, state: CollectionState, Changed: bool, item: Item):
    # the following let you add to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] += 1
    pass

# This method is run every time an item is removed from the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be first done in after_collect_item
def after_remove_item(world: World, state: CollectionState, Changed: bool, item: Item):
    # the following let you undo the addition to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] -= 1
    pass


# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called right at the end, in case you want to write stuff to the spoiler log
def before_write_spoiler(world: World, multiworld: MultiWorld, spoiler_handle) -> None:
    vault = world.vault
    spoiler_handle.write(f"\n\nThe Vault ({multiworld.player_name[world.player]}):\n")
    for stage in range(1, vault["stages"] + 1):
        treasures = [n for n in range(1, len(vault["treasure_stage"])) if vault["treasure_stage"][n] == stage]
        spoiler_handle.write(f"  Stage {stage}: {vault['stage_keys'][stage]} keys open Treasures {treasures[0]:02d}-{treasures[-1]:02d}\n")
    if world.vault_starting_keys:
        spoiler_handle.write(f"  Starting Vault Keys: {world.vault_starting_keys}\n")

# This is called when you want to add information to the hint text
def before_extend_hint_information(hint_data: dict[int, dict[int, str]], world: World, multiworld: MultiWorld, player: int) -> None:

    ### Example way to use this hook:
    # if player not in hint_data:
    #     hint_data.update({player: {}})
    # for location in multiworld.get_locations(player):
    #     if not location.address:
    #         continue
    #
    #     use this section to calculate the hint string
    #
    #     hint_data[player][location.address] = hint_string

    pass

def after_extend_hint_information(hint_data: dict[int, dict[int, str]], world: World, multiworld: MultiWorld, player: int) -> None:
    pass

def hook_interpret_slot_data(world: World, player: int, slot_data: dict[str, Any]) -> dict[str, Any]:
    """
        Called when Universal Tracker wants to perform a fake generation
        Use this if you want to use or modify the slot_data for passed into re_gen_passthrough
    """
    return slot_data
