# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from worlds.AutoWorld import World
from BaseClasses import MultiWorld, CollectionState

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation
from .Options import AmountOfKeys, AmountOfTreasureInVault

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value

# calling logging.info("message") anywhere below in this file will output the message to both console and log file
import logging

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

# Called before regions and locations are created. Not clear why you'd want this, but it's here. Victory location is included, but Victory event is not placed yet.
def before_create_regions(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after regions and locations are created, in case you want to see or modify that information. Victory location is included.
def after_create_regions(world: World, multiworld: MultiWorld, player: int):
    # Use this hook to remove locations from the world
    locationNamesToRemove = []  # List of location names to remove
    items_in_vault = get_option_value(multiworld, player, "amount_of_treasure_in_vault")

    # Iterate through all regions in the multiworld
    for region in multiworld.regions:
        if region.player == player:  # Only process regions for the current player
            for location in list(region.locations):  # Copy of the locations list for safe iteration
                if location.name.startswith("Treasure "):  # Check if the location name starts with "Treasure "
                    try:
                        item_number = int(location.name.split(" ")[1])  # Extract Treasure number
                        if item_number > items_in_vault:  # Compare with the limit
                            region.locations.remove(location)  # Remove the location
                    except ValueError:
                        # If parsing fails, skip this entry
                        continue

    # Clear the location cache if the multiworld has this method
    if hasattr(multiworld, "clear_location_cache"):
        multiworld.clear_location_cache()

# The item pool before starting items are processed, in case you want to see the raw item pool at that stage
def before_create_items_starting(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

def before_create_items_filler(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    # Use this hook to remove items from the item pool
    number_of_keys = get_option_value(multiworld, player, "amount_of_keys")  # Define how many keys we want

    # Define items to remove for each breakpoint (thresholds are <10, <20, ..., <100)
    items_to_remove = {
        10: ["Mind Goblin Deez (+5 Vault Keys)", "It's Goblin-Engineered! (+5 Vault Keys)"],
        20: ["Zizzlecrank with the Drill! (+10 Vault Keys)", "Time is Money, Friend. (+10 Vault Keys)"],
        30: ["Found a Shiny Rock! (Totally Not a Diamond) (+15 Vault Keys)", "Snotgrub drops a Vial of Acid on the lock! (+15 Vault Keys)"],
        40: ["STRIKING IT WITH A HUGE FKIN' MACE! (+20 Vault Keys)", "Strapping The Vault with a Jetpack and sending it sky-high! (+20 Vault Keys)"],
        50: ["Lining up the Firing Squad and SHOOT IT TO OBLIVIION! (+25 Vault Keys)","Bringing in the Explosives! (+25 Vault Keys)"]
    }

    # Iterate through breakpoints in ascending order
    for breakpoint, item_names in sorted(items_to_remove.items()):
        if number_of_keys < breakpoint:
            # Remove items in the item_names list from the pool
            for item_name in item_names:
                item_pool = [item for item in item_pool if item.name != item_name]

    # Filter "Vault Key" items
    vault_keys = [item for item in item_pool if item.name == "Vault Key"]

    # Remove extra "Vault Key" items if there are more than allowed
    if len(vault_keys) > number_of_keys:
        excess_keys = len(vault_keys) - number_of_keys
        for _ in range(excess_keys):
            vault_key = vault_keys.pop()  # Pop a Vault Key from the list
            multiworld.push_precollected(vault_key)  # Mark it as a precollected item
            item_pool.remove(vault_key)  # Remove the Vault Key from the item pool

    item_pool = world.add_filler_items(item_pool, [])  # Add filler items

    return item_pool  # Give the modified pool back to the multiworld

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def after_create_items(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: World, multiworld: MultiWorld, player: int):
    # Use this hook to modify the access rules for a given location

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
def before_generate_basic(world: World, multiworld: MultiWorld, player: int) -> list:
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called right at the end, in case you want to write stuff to the spoiler log
def before_write_spoiler(world: World, multiworld: MultiWorld, spoiler_handle) -> None:
    pass

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