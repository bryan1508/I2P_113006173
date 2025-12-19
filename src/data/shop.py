from dataclasses import dataclass
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.data.bag import Bag

@dataclass
class ShopItem:
    name: str
    price: int
    sprite_path: str

class Shop:
    def __init__(self, items_for_sale: List[ShopItem]):
        self.items_for_sale = items_for_sale

    def buy(self, bag: "Bag", index: int):
        if index < 0 or index >= len(self.items_for_sale):
            return

        item = self.items_for_sale[index]

        # check coins
        for i in bag._items_data:
            if i["name"].lower() == "coins" and i["count"] >= item.price:
                i["count"] -= item.price
                bag._add_or_increase(item.name, item.sprite_path)
                return

    def sell(self, bag: "Bag", name: str, price: int):
        for i in bag._items_data:
            if i["name"] == name and i["count"] > 0:
                i["count"] -= 1
                bag._add_or_increase("Coins", None, amount=price)
                return