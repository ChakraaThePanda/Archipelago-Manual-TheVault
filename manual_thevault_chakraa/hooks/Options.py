# Object classes from AP that represent different types of options that you can create
from Options import FreeText, NumericOption, Toggle, DefaultOnToggle, Choice, TextChoice, Range, NamedRange

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value

class AmountOfKeys(Range):
    """Select the amount of Keys you need to open The Vault"""
    display_name = "Amount of Keys you need to open The Vault"
    range_start = 1
    range_end = 100
    default = 10

class AmountOfTreasureInVault(Range):
    """Select the amount of Treasure items that are in The Vault"""
    display_name = "Amount of Treasure items that are in The Vault"
    range_start = 1
    range_end = 100
    default = 10


# This is called before any manual options are defined, in case you want to define your own with a clean slate or let Manual define over them
def before_options_defined(options: dict) -> dict:
    options["amount_of_keys"] = AmountOfKeys
    options["amount_of_treasure_in_vault"] = AmountOfTreasureInVault  
    return options

# This is called after any manual options are defined, in case you want to see what options are defined or want to modify the defined options
def after_options_defined(options: dict) -> dict:
    return options