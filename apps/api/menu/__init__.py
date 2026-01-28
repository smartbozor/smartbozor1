from .stall import init_stall_menu, get_stall_data_by_type, save_stall, cancel_stall
from .shop import init_shop_menu, get_shop_data_by_type, save_shop, cancel_shop
from .rent import init_rent_menu, get_rent_data_by_type, save_rent, cancel_rent
from .parking import init_parking_menu, get_parking_data_by_type, save_parking, cancel_parking


def init_menu(bazaar, today):
    return [
        *init_stall_menu(bazaar, today),
        *init_shop_menu(bazaar, today),
        *init_rent_menu(bazaar, today),
        *init_parking_menu(bazaar, today),
    ]


__all__ = [
    "init_menu",

    "get_stall_data_by_type",
    "save_stall",
    "cancel_stall",

    "get_shop_data_by_type",
    "save_shop",
    "cancel_shop",

    "get_rent_data_by_type",
    "save_rent",
    "cancel_rent",

    "get_parking_data_by_type",
    "save_parking",
    "cancel_parking"
]