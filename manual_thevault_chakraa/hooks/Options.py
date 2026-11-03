# Object classes from AP that represent different types of options that you can create
from Options import Option, FreeText, NumericOption, Toggle, DefaultOnToggle, Choice, TextChoice, Range, NamedRange, OptionGroup, PerGameCommonOptions
# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, get_option_value
from typing import Type, Any


####################################################################
# NOTE: At the time that options are created, Manual has no concept of the multiworld or its own world.
#       Options are defined before the world is even created.
#
# Example of creating your own option:
#
#   class MakeThePlayerOP(Toggle):
#       """Should the player be overpowered? Probably not, but you can choose for this to do... something!"""
#       display_name = "Make me OP"
#
#   options["make_op"] = MakeThePlayerOP
#
#
# Then, to see if the option is set, you can call is_option_enabled or get_option_value.
#####################################################################


# To add an option, use the before_options_defined hook below and something like this:
#   options["total_characters_to_win_with"] = TotalCharactersToWinWith
#
class AmountOfKeys(Range):
    """Select the amount of Keys you need to open The Vault"""
    display_name = "Keys to open The Vault"
    range_start = 1
    range_end = 100
    default = 10

class ExtraKeysPercent(Range):
    """Adds this percentage of extra key value to the multiworld, on top of the keys needed to open The Vault,
    so you don't have to find every single one. Bonus key items (worth 5 or 10 keys) count towards this."""
    display_name = "Extra keys (%)"
    range_start = 0
    range_end = 100
    default = 20

class AmountOfTreasureInVault(Range):
    """Select the amount of Treasure items that are in The Vault"""
    display_name = "Treasures in The Vault"
    range_start = 1
    range_end = 100
    default = 10

class VaultStages(Range):
    """Opens The Vault in stages instead of all at once. With 4 stages, every 25% of the keys opens a quarter
    of the Treasures. 1 opens everything at once when you have all the keys."""
    display_name = "Vault stages"
    range_start = 1
    range_end = 10
    default = 1

class KeysOutsideVault(DefaultOnToggle):
    """Your own keys are never placed inside your own Treasures, so other worlds always hold them,
    spare keys included."""
    display_name = "Keys outside The Vault"

# This is called before any manual options are defined, in case you want to define your own with a clean slate or let Manual define over them
def before_options_defined(options: dict[str, Type[Option[Any]]]) -> dict[str, Type[Option[Any]]]:
    options["amount_of_keys"] = AmountOfKeys
    options["extra_keys_percent"] = ExtraKeysPercent
    options["amount_of_treasure_in_vault"] = AmountOfTreasureInVault
    options["vault_stages"] = VaultStages
    options["keys_outside_vault"] = KeysOutsideVault
    return options

# This is called after any manual options are defined, in case you want to see what options are defined or want to modify the defined options
def after_options_defined(options: Type[PerGameCommonOptions]):
    # To access a modifiable version of options check the dict in options.type_hints
    # For example if you want to change DLC_enabled's display name you would do:
    # options.type_hints["DLC_enabled"].display_name = "New Display Name"

    #  Here's an example on how to add your aliases to the generated goal
    # options.type_hints['goal'].aliases.update({"example": 0, "second_alias": 1})
    # options.type_hints['goal'].options.update({"example": 0, "second_alias": 1})  #for an alias to be valid it must also be in options

    pass

# Use this Hook if you want to add your Option to an Option group (existing or not)
def before_option_groups_created(groups: dict[str, list[Type[Option[Any]]]]) -> dict[str, list[Type[Option[Any]]]]:
    # Uses the format groups['GroupName'] = [TotalCharactersToWinWith]
    return groups

def after_option_groups_created(groups: list[OptionGroup]) -> list[OptionGroup]:
    return groups
