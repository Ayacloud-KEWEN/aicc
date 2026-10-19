"""Demo restaurant data: trilingual menu, carts, orders and slot-based reservations.

Everything lives in memory and is mirrored to data/*.json so the kitchen board
survives a server restart. Prices are in euros.
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Paris")
DATA_DIR = Path(__file__).parent / "data"

RESTAURANT = {
    "name": "Restaurant Quimper",
    "address": "18 rue d'Odessa, 75014 Paris",
    "phone": "01 23 45 67 89",
    "hours": {
        "fr": "Du mardi au dimanche, 12h–14h30 et 19h–22h30. Fermé le lundi.",
        "en": "Tuesday to Sunday, 12:00–14:30 and 19:00–22:30. Closed on Mondays.",
        "zh": "周二至周日，12:00–14:30 和 19:00–22:30，周一休息。",
    },
}

# Each dish: id, names in fr/en/zh, aliases (for fuzzy speech), price, category, allergens.
# Galettes are buckwheat (sarrasin), naturally gluten-free; crêpes are wheat.
MENU = [
    {"id": "galette_complete", "fr": "Galette complète (jambon, œuf, emmental)", "en": "Galette complète (ham, egg, cheese)", "zh": "经典荞麦饼（火腿、鸡蛋、奶酪）", "aliases": ["complète", "complete", "jambon œuf fromage", "火腿鸡蛋", "经典荞麦饼"], "price": 11.5, "category": "galette", "allergens": ["egg", "milk"], "options": ["egg"]},
    {"id": "galette_forestiere", "fr": "Galette forestière (champignons, lardons, crème)", "en": "Forest galette (mushrooms, bacon, cream)", "zh": "森林荞麦饼（蘑菇、培根、奶油）", "aliases": ["forestière", "champignons", "mushroom", "蘑菇"], "price": 13.5, "category": "galette", "allergens": ["milk"]},
    {"id": "galette_saumon", "fr": "Galette au saumon fumé et crème citronnée", "en": "Smoked salmon galette with lemon cream", "zh": "烟熏三文鱼荞麦饼", "aliases": ["saumon", "salmon", "三文鱼"], "price": 14.5, "category": "galette", "allergens": ["fish", "milk"]},
    {"id": "galette_andouille", "fr": "Galette andouille de Guémené", "en": "Galette with Guémené andouille sausage", "zh": "布列塔尼香肠荞麦饼", "aliases": ["andouille", "guémené", "sausage", "香肠"], "price": 13.0, "category": "galette", "allergens": []},
    {"id": "galette_chevre", "fr": "Galette chèvre, miel et noix (végétarienne)", "en": "Goat cheese, honey and walnut galette (vegetarian)", "zh": "山羊奶酪蜂蜜核桃荞麦饼（素）", "aliases": ["chèvre", "goat cheese", "山羊奶酪", "素的"], "price": 12.5, "category": "galette", "allergens": ["milk", "nuts"]},
    {"id": "galette_saucisse", "fr": "Galette saucisse", "en": "Sausage galette (Breton street classic)", "zh": "布列塔尼香肠卷饼", "aliases": ["galette saucisse", "saucisse", "热狗", "香肠卷"], "price": 7.0, "category": "galette", "allergens": []},
    {"id": "moules_frites", "fr": "Moules marinières et frites", "en": "Mussels in white wine with fries", "zh": "白葡萄酒青口配薯条", "aliases": ["moules", "mussels", "青口", "贻贝"], "price": 18.0, "category": "plat", "allergens": ["molluscs", "sulphites"]},
    {"id": "cotriade", "fr": "Cotriade (soupe de poissons bretonne)", "en": "Cotriade (Breton fish stew)", "zh": "布列塔尼鱼汤", "aliases": ["cotriade", "fish stew", "soupe de poisson", "鱼汤"], "price": 19.5, "category": "plat", "allergens": ["fish", "milk"]},
    {"id": "kig_ha_farz", "fr": "Kig ha farz (pot-au-feu du Léon)", "en": "Kig ha farz (Breton pot-au-feu)", "zh": "布列塔尼炖肉配荞麦布丁", "aliases": ["kig ha farz", "pot-au-feu", "炖肉"], "price": 21.0, "category": "plat", "allergens": ["gluten", "egg", "milk"]},
    {"id": "crepe_beurre_sucre", "fr": "Crêpe beurre-sucre", "en": "Butter and sugar crêpe", "zh": "黄油白糖可丽饼", "aliases": ["beurre sucre", "butter sugar", "黄油糖"], "price": 5.0, "category": "crepe", "allergens": ["gluten", "egg", "milk"]},
    {"id": "crepe_caramel", "fr": "Crêpe caramel au beurre salé maison", "en": "Salted butter caramel crêpe", "zh": "咸黄油焦糖可丽饼", "aliases": ["caramel", "salted caramel", "焦糖"], "price": 7.0, "category": "crepe", "allergens": ["gluten", "egg", "milk"]},
    {"id": "crepe_chocolat", "fr": "Crêpe chocolat-banane", "en": "Chocolate and banana crêpe", "zh": "巧克力香蕉可丽饼", "aliases": ["chocolat", "banane", "chocolate", "巧克力", "香蕉"], "price": 7.5, "category": "crepe", "allergens": ["gluten", "egg", "milk"]},
    {"id": "crepe_suzette", "fr": "Crêpe Suzette flambée", "en": "Crêpe Suzette (flambéed)", "zh": "橙香火焰可丽饼", "aliases": ["suzette", "flambée", "橙子", "火焰"], "price": 9.0, "category": "crepe", "allergens": ["gluten", "egg", "milk"]},
    {"id": "kouign_amann", "fr": "Kouign-amann", "en": "Kouign-amann (Breton butter cake)", "zh": "布列塔尼黄油酥", "aliases": ["kouign amann", "kouign", "黄油酥", "黄油饼"], "price": 5.5, "category": "dessert", "allergens": ["gluten", "milk"]},
    {"id": "far_breton", "fr": "Far breton aux pruneaux", "en": "Far breton (prune flan)", "zh": "西梅布列塔尼布丁", "aliases": ["far", "far breton", "flan", "布丁"], "price": 5.0, "category": "dessert", "allergens": ["gluten", "egg", "milk"]},
    {"id": "cidre_bouteille", "fr": "Cidre fermier de Cornouaille (bouteille 75 cl)", "en": "Cornouaille farm cider (75 cl bottle)", "zh": "康沃伊农庄苹果酒（整瓶75cl）", "aliases": ["bouteille de cidre", "cider bottle", "一瓶苹果酒", "整瓶"], "price": 16.0, "category": "boisson", "allergens": ["sulphites"], "options": ["cider"]},
    {"id": "bolee_cidre", "fr": "Bolée de cidre", "en": "Bowl of cider", "zh": "一碗苹果酒", "aliases": ["bolée", "cidre", "cider", "苹果酒"], "price": 4.5, "category": "boisson", "allergens": ["sulphites"], "options": ["cider"]},
    {"id": "chouchen", "fr": "Chouchen (hydromel breton)", "en": "Chouchen (Breton mead)", "zh": "布列塔尼蜂蜜酒", "aliases": ["chouchen", "hydromel", "mead", "蜂蜜酒"], "price": 6.0, "category": "boisson", "allergens": []},
    {"id": "breizh_cola", "fr": "Breizh Cola (33 cl)", "en": "Breizh Cola (33 cl)", "zh": "布列塔尼可乐（33cl）", "aliases": ["breizh cola", "cola", "coca", "可乐"], "price": 3.5, "category": "boisson", "allergens": []},
    {"id": "jus_pomme", "fr": "Jus de pomme artisanal", "en": "Craft apple juice", "zh": "手工苹果汁", "aliases": ["jus de pomme", "apple juice", "苹果汁"], "price": 3.5, "category": "boisson", "allergens": []},
]
MENU_BY_ID = {d["id"]: d for d in MENU}

CATEGORY_NAMES = {
    "galette": {"fr": "Galettes de blé noir", "en": "Buckwheat galettes", "zh": "荞麦咸饼"},
    "plat": {"fr": "Spécialités bretonnes", "en": "Breton specialities", "zh": "布列塔尼特色菜"},
    "crepe": {"fr": "Crêpes sucrées", "en": "Sweet crêpes", "zh": "甜可丽饼"},
    "dessert": {"fr": "Desserts", "en": "Desserts", "zh": "甜品"},
    "boisson": {"fr": "Boissons", "en": "Drinks", "zh": "饮品"},
}

# Reservations: 30-minute slots, capacity counted in covers per slot.
SERVICES = [(time(12, 0), time(14, 0)), (time(19, 0), time(22, 0))]
SLOT_MINUTES = 30
MAX_COVERS_PER_SLOT = 20
CLOSED_WEEKDAYS = {0}  # Monday


def now_paris() -> datetime:
    return datetime.now(TZ)


def menu_for_prompt() -> str:
    lines = []
    for cat, names in CATEGORY_NAMES.items():
        lines.append(f"## {names['fr']} / {names['en']} / {names['zh']}")
        for d in MENU:
            if d["category"] != cat:
                continue
            extra = f" | allergens: {', '.join(d['allergens'])}" if d["allergens"] else ""
            if "egg" in d.get("options", []):
                extra += " | option: egg style (miroir/brouillé)"
            if "cider" in d.get("options", []):
                extra += " | option: cider type (brut/doux)"
            lines.append(f"- id={d['id']} | {d['fr']} | {d['en']} | {d['zh']} | €{d['price']:.2f}{extra}")
    return "\n".join(lines)


@dataclass
class CartLine:
    item_id: str
    quantity: int
    note: str = ""

    def to_dict(self, lang: str) -> dict:
        dish = MENU_BY_ID[self.item_id]
        return {
            "item_id": self.item_id,
            "name": dish[lang],
            "quantity": self.quantity,
            "unit_price": dish["price"],
            "line_total": round(dish["price"] * self.quantity, 2),
            "note": self.note,
        }


@dataclass
class Cart:
    lines: list[CartLine] = field(default_factory=list)

    def add(self, item_id: str, quantity: int, note: str = "") -> None:
        for line in self.lines:
            if line.item_id == item_id and line.note == note:
                line.quantity += quantity
                return
        self.lines.append(CartLine(item_id, quantity, note))

    def remove(self, item_id: str, quantity: int | None) -> bool:
        for line in self.lines:
            if line.item_id == item_id:
                if quantity is None or quantity >= line.quantity:
                    self.lines.remove(line)
                else:
                    line.quantity -= quantity
                return True
        return False

    def total(self) -> float:
        return round(sum(MENU_BY_ID[l.item_id]["price"] * l.quantity for l in self.lines), 2)

    def to_dict(self, lang: str) -> dict:
        return {"lines": [l.to_dict(lang) for l in self.lines], "total": self.total()}


class Store:
    """Thread-safe in-memory store for orders and reservations, persisted as JSON."""

    def __init__(self):
        self._lock = threading.Lock()
        DATA_DIR.mkdir(exist_ok=True)
        self.orders: list[dict] = self._load("orders.json")
        self.reservations: list[dict] = self._load("reservations.json")

    def _load(self, name: str) -> list[dict]:
        path = DATA_DIR / name
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return []
        return []

    def _save(self, name: str, rows: list[dict]) -> None:
        (DATA_DIR / name).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_order(self, order: dict) -> dict:
        with self._lock:
            order["id"] = f"CMD-{len(self.orders) + 1001}"
            order["created_at"] = now_paris().isoformat(timespec="seconds")
            order["status"] = "new"
            self.orders.append(order)
            self._save("orders.json", self.orders)
            return order

    def get_order(self, order_id: str) -> dict | None:
        return next((o for o in self.orders if o["id"] == order_id), None)

    def update_order(self, order_id: str, **fields) -> dict | None:
        with self._lock:
            order = self.get_order(order_id)
            if order:
                order.update(fields)
                self._save("orders.json", self.orders)
            return order

    def set_order_status(self, order_id: str, status: str) -> dict | None:
        with self._lock:
            for order in self.orders:
                if order["id"] == order_id:
                    order["status"] = status
                    self._save("orders.json", self.orders)
                    return order
            return None

    def covers_booked(self, day: date, slot: time) -> int:
        key_date, key_time = day.isoformat(), slot.strftime("%H:%M")
        return sum(
            r["party_size"]
            for r in self.reservations
            if r["date"] == key_date and r["time"] == key_time and r["status"] == "confirmed"
        )

    def add_reservation(self, reservation: dict) -> dict:
        with self._lock:
            reservation["id"] = f"RES-{len(self.reservations) + 501}"
            reservation["created_at"] = now_paris().isoformat(timespec="seconds")
            reservation["status"] = "confirmed"
            self.reservations.append(reservation)
            self._save("reservations.json", self.reservations)
            return reservation


store = Store()


def all_slots() -> list[time]:
    slots = []
    for start, end in SERVICES:
        t = datetime.combine(date.today(), start)
        while t.time() <= end:
            slots.append(t.time())
            t += timedelta(minutes=SLOT_MINUTES)
    return slots


def parse_slot(day_str: str, time_str: str) -> tuple[date, time] | str:
    """Validate a requested date/time; returns (date, slot) or an error code."""
    try:
        day = date.fromisoformat(day_str)
        hh, mm = time_str.strip().replace("h", ":").split(":")[:2]
        slot = time(int(hh), int(mm or 0))
    except (ValueError, TypeError):
        return "invalid_date_or_time"
    if day < now_paris().date():
        return "date_in_past"
    if day.weekday() in CLOSED_WEEKDAYS:
        return "closed_that_day"
    if slot not in all_slots():
        return "not_a_bookable_slot"
    return day, slot


def nearby_free_slots(day: date, slot: time, party_size: int, limit: int = 3) -> list[str]:
    slots = all_slots()
    ordered = sorted(slots, key=lambda s: abs((s.hour * 60 + s.minute) - (slot.hour * 60 + slot.minute)))
    free = [s for s in ordered if s != slot and store.covers_booked(day, s) + party_size <= MAX_COVERS_PER_SLOT]
    return [s.strftime("%H:%M") for s in free[:limit]]
