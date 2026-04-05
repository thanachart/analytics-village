"""
Analytics Village — Business and SKU catalogue.
Seeds the village with businesses, owners, households, SKUs, and suppliers.
All data uses Thai context with realistic THB pricing.
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime
from typing import TYPE_CHECKING

from .world import (
    DAYS_OF_WEEK, CalendarDay, HouseholdState, BusinessState, SKUState,
    SupplierState, SimConfig, LifecycleState,
)
from .physics import INCOME_BRACKETS, DWELLING_STORAGE
from .database import VillageDB

if TYPE_CHECKING:
    pass

# ══════════════════════════════════════════════════════════════
# Business templates
# ══════════════════════════════════════════════════════════════

BUSINESS_TEMPLATES = [
    {
        "business_id": "supermarket",
        "business_name": "Village Fresh",
        "business_type": "retail_grocery",
        "owner_id": "khun_somchai",
        "location_zone": "central",
        "episode_primary": 1,
    },
    {
        "business_id": "pharmacy",
        "business_name": "P'Noi Pharmacy",
        "business_type": "pharmacy",
        "owner_id": "pnoi",
        "location_zone": "central",
        "episode_primary": 3,
    },
    {
        "business_id": "coffee_shop",
        "business_name": "Village Coffee & Bakery",
        "business_type": "food_beverage",
        "owner_id": "ajarn_malee",
        "location_zone": "central",
        "episode_primary": 5,
    },
    {
        "business_id": "wet_market",
        "business_name": "Village Wet Market",
        "business_type": "fresh_market",
        "owner_id": "khun_dao",
        "location_zone": "market_area",
        "episode_primary": 2,
    },
    {
        "business_id": "clinic",
        "business_name": "Village Health Clinic",
        "business_type": "healthcare",
        "owner_id": "dr_wichai",
        "location_zone": "central",
        "episode_primary": None,
    },
    {
        "business_id": "hardware",
        "business_name": "Village Hardware",
        "business_type": "hardware",
        "owner_id": "khun_prayut",
        "location_zone": "north_cluster",
        "episode_primary": None,
    },
    {
        "business_id": "convenience",
        "business_name": "Quick Stop Mini Mart",
        "business_type": "convenience",
        "owner_id": "khun_nong",
        "location_zone": "south_cluster",
        "episode_primary": None,
    },
]

OWNER_TEMPLATES = [
    {
        "owner_id": "khun_somchai",
        "name": "Khun Somchai",
        "age": 52,
        "background": "Former government employee, opened Village Fresh 8 years ago with family savings. Proud of his store's range and freshness.",
        "personality_traits": json.dumps(["proud", "anxious_about_competition", "trusts_gut_over_data"]),
        "known_blind_spots": json.dumps(["underestimates_wet_market", "overestimates_loyal_customers"]),
        "communication_style": "warm_and_chatty",
        "hidden_goal": "Plans to open a second branch in the nearby town within 2 years",
    },
    {
        "owner_id": "pnoi",
        "name": "P'Noi Jaruwan",
        "age": 48,
        "background": "Former hospital pharmacist, opened village pharmacy 4 years ago. Only pharmacy in the village.",
        "personality_traits": json.dumps(["proud_of_service", "anxious_about_waste", "trusts_supplier_relationships"]),
        "known_blind_spots": json.dumps(["underestimates_waste_scale", "overestimates_supplier_reliability"]),
        "communication_style": "warm_and_detailed",
        "hidden_goal": "Wants to expand to a second location in the city within 3 years",
    },
    {
        "owner_id": "ajarn_malee",
        "name": "Ajarn Malee",
        "age": 35,
        "background": "Former university lecturer, opened coffee shop as lifestyle business. Known for quality coffee and homemade bakery.",
        "personality_traits": json.dumps(["creative", "quality_focused", "impatient_with_numbers"]),
        "known_blind_spots": json.dumps(["ignores_cost_control", "overvalues_ambiance_vs_value"]),
        "communication_style": "enthusiastic_and_creative",
        "hidden_goal": "Wants to franchise the concept to 3 university towns",
    },
    {
        "owner_id": "khun_dao",
        "name": "Khun Dao",
        "age": 60,
        "background": "Market vendor family for 3 generations. Runs the village wet market stalls with her children.",
        "personality_traits": json.dumps(["traditional", "price_competitive", "early_morning_person"]),
        "known_blind_spots": json.dumps(["dismisses_convenience_shoppers", "underestimates_hygiene_concerns"]),
        "communication_style": "blunt_and_direct",
        "hidden_goal": "Wants one of her children to take over so she can retire",
    },
    {
        "owner_id": "dr_wichai",
        "name": "Dr. Wichai",
        "age": 45,
        "background": "Village doctor who expanded from home visits to a small clinic. Provides basic healthcare and referrals.",
        "personality_traits": json.dumps(["caring", "systematic", "cautious_about_expansion"]),
        "known_blind_spots": json.dumps(["underestimates_demand_for_wellness"]),
        "communication_style": "formal_and_cautious",
        "hidden_goal": "Considering adding a small dental service",
    },
    {
        "owner_id": "khun_prayut",
        "name": "Khun Prayut",
        "age": 55,
        "background": "Former construction foreman. Opened hardware store when village started growing.",
        "personality_traits": json.dumps(["practical", "no_nonsense", "loyal_to_regulars"]),
        "known_blind_spots": json.dumps(["slow_to_stock_new_products"]),
        "communication_style": "blunt_and_direct",
        "hidden_goal": "Content with current size, focused on stability",
    },
    {
        "owner_id": "khun_nong",
        "name": "Khun Nong",
        "age": 28,
        "background": "Young entrepreneur running a convenience store. Extended hours, higher prices, limited range.",
        "personality_traits": json.dumps(["ambitious", "tech_savvy", "price_aggressive"]),
        "known_blind_spots": json.dumps(["overestimates_demand_for_premium_items"]),
        "communication_style": "casual_and_modern",
        "hidden_goal": "Looking at online delivery options",
    },
]

# ══════════════════════════════════════════════════════════════
# SKU catalogue per business type
# ══════════════════════════════════════════════════════════════

# Format: (sku_suffix, name, name_th, category, subcategory, unit_desc,
#          shelf_life, storage, vol_L, weight_kg, cost, price,
#          elastic, impulse, consume_person, consume_hh)

SUPERMARKET_SKUS = [
    # Dairy
    ("MILK_1L", "Fresh Milk 1L", "นมสด 1 ลิตร", "dairy", "milk", "1 litre", 7, "cold", 1.0, 1.0, 28, 42, 0, 0, 0.15, None),
    ("MILK_UHT", "UHT Milk 1L", "นม UHT 1 ลิตร", "dairy", "milk", "1 litre", 180, "ambient", 1.0, 1.0, 22, 35, 1, 0, 0.10, None),
    ("YOGURT_4PK", "Yogurt 4-pack", "โยเกิร์ต 4 ถ้วย", "dairy", "yogurt", "4 pack", 14, "cold", 0.5, 0.5, 32, 49, 1, 0, 0.05, None),
    ("BUTTER_200G", "Butter 200g", "เนย 200 กรัม", "dairy", "butter", "200g", 30, "cold", 0.2, 0.2, 45, 65, 0, 0, None, 0.02),
    ("CHEESE_SLICE", "Cheese Slices 10pk", "ชีสแผ่น 10 แผ่น", "dairy", "cheese", "10 slices", 21, "cold", 0.2, 0.2, 55, 79, 1, 0, None, 0.03),
    # Fresh produce
    ("VEG_MORNING_GLORY", "Morning Glory", "ผักบุ้ง", "fresh_produce", "vegetables", "1 bunch", 3, "cold", 0.3, 0.3, 8, 15, 0, 0, 0.05, None),
    ("VEG_CABBAGE", "Cabbage", "กะหล่ำปลี", "fresh_produce", "vegetables", "1 head", 7, "cold", 1.5, 1.0, 12, 22, 0, 0, 0.03, None),
    ("VEG_TOMATO", "Tomatoes 500g", "มะเขือเทศ 500g", "fresh_produce", "vegetables", "500g", 5, "cold", 0.5, 0.5, 15, 25, 0, 0, 0.04, None),
    ("VEG_ONION", "Onions 500g", "หัวหอม 500g", "fresh_produce", "vegetables", "500g", 14, "ambient", 0.3, 0.5, 10, 18, 0, 0, None, 0.03),
    ("FRUIT_BANANA", "Bananas", "กล้วย", "fresh_produce", "fruits", "1 bunch", 5, "ambient", 0.5, 0.5, 15, 25, 0, 0, 0.08, None),
    ("FRUIT_ORANGE", "Oranges 1kg", "ส้ม 1 กก.", "fresh_produce", "fruits", "1 kg", 10, "cold", 0.8, 1.0, 30, 49, 1, 0, 0.04, None),
    # Meat & protein
    ("CHICKEN_BREAST", "Chicken Breast 500g", "อกไก่ 500g", "meat", "poultry", "500g", 3, "cold", 0.5, 0.5, 45, 69, 0, 0, 0.04, None),
    ("PORK_LOIN", "Pork Loin 500g", "สันนอกหมู 500g", "meat", "pork", "500g", 3, "cold", 0.5, 0.5, 55, 85, 0, 0, 0.03, None),
    ("EGGS_10PK", "Eggs 10-pack", "ไข่ไก่ 10 ฟอง", "meat", "eggs", "10 pack", 21, "cold", 0.6, 0.6, 35, 52, 0, 0, 0.10, None),
    ("FISH_TILAPIA", "Tilapia fillet 400g", "ปลานิลแล่ 400g", "meat", "fish", "400g", 2, "cold", 0.4, 0.4, 40, 65, 1, 0, 0.02, None),
    # Dry goods
    ("RICE_5KG", "Jasmine Rice 5kg", "ข้าวหอมมะลิ 5 กก.", "dry_goods", "rice", "5 kg", None, "ambient", 4.0, 5.0, 95, 139, 0, 0, None, 0.15),
    ("NOODLE_INSTANT", "Instant Noodles 5pk", "มาม่า 5 ซอง", "dry_goods", "noodles", "5 pack", 180, "ambient", 0.5, 0.4, 25, 38, 1, 0, 0.05, None),
    ("COOKING_OIL_1L", "Cooking Oil 1L", "น้ำมันพืช 1 ลิตร", "dry_goods", "cooking", "1 litre", 365, "ambient", 1.0, 0.9, 35, 49, 0, 0, None, 0.03),
    ("FISH_SAUCE", "Fish Sauce 700ml", "น้ำปลา 700 มล.", "dry_goods", "condiments", "700ml", 365, "ambient", 0.7, 0.7, 18, 29, 0, 0, None, 0.01),
    ("SOY_SAUCE", "Soy Sauce 500ml", "ซีอิ๊ว 500 มล.", "dry_goods", "condiments", "500ml", 365, "ambient", 0.5, 0.5, 15, 25, 0, 0, None, 0.01),
    ("SUGAR_1KG", "Sugar 1kg", "น้ำตาล 1 กก.", "dry_goods", "baking", "1 kg", 365, "ambient", 0.8, 1.0, 18, 28, 0, 0, None, 0.02),
    ("FLOUR_1KG", "All-Purpose Flour 1kg", "แป้งสาลี 1 กก.", "dry_goods", "baking", "1 kg", 180, "ambient", 0.8, 1.0, 22, 35, 0, 0, None, 0.01),
    # Beverages
    ("WATER_6PK", "Water 6-pack 1.5L", "น้ำดื่ม 6 ขวด", "beverage", "water", "6 × 1.5L", 365, "ambient", 9.0, 9.0, 30, 45, 0, 0, None, 0.10),
    ("COFFEE_3IN1", "3-in-1 Coffee 10pk", "กาแฟ 3in1 10 ซอง", "beverage", "coffee", "10 sachets", 365, "ambient", 0.3, 0.2, 35, 55, 1, 0, 0.08, None),
    ("SODA_CAN_6PK", "Cola 6-pack cans", "โคล่า 6 กระป๋อง", "beverage", "soft_drink", "6 × 325ml", 180, "ambient", 2.0, 2.0, 55, 79, 1, 1, 0.03, None),
    ("GREEN_TEA_500ML", "Green Tea 500ml", "ชาเขียว 500 มล.", "beverage", "tea", "500ml", 180, "cold", 0.5, 0.5, 12, 20, 1, 1, 0.04, None),
    # Snacks
    ("CHIPS_LAY", "Lay's Chips 75g", "เลย์ 75g", "snacks", "chips", "75g", 120, "ambient", 0.3, 0.1, 12, 22, 1, 1, None, 0.02),
    ("BISCUIT_OREO", "Oreo Biscuits", "โอรีโอ", "snacks", "biscuits", "1 pack", 180, "ambient", 0.2, 0.15, 15, 25, 1, 1, None, 0.01),
    ("CHOCOLATE_BAR", "Chocolate Bar", "ช็อกโกแลต", "snacks", "chocolate", "1 bar", 180, "ambient", 0.1, 0.05, 18, 30, 1, 1, None, 0.01),
    # Household
    ("TISSUE_6PK", "Tissue Paper 6-roll", "กระดาษทิชชู 6 ม้วน", "household", "paper", "6 rolls", None, "ambient", 2.0, 0.8, 45, 65, 0, 0, None, 0.02),
    ("DETERGENT_1L", "Laundry Detergent 1L", "น้ำยาซักผ้า 1 ลิตร", "household", "cleaning", "1 litre", None, "ambient", 1.0, 1.0, 35, 55, 0, 0, None, 0.01),
    ("DISH_SOAP", "Dish Soap 500ml", "น้ำยาล้างจาน 500 มล.", "household", "cleaning", "500ml", None, "ambient", 0.5, 0.5, 18, 29, 0, 0, None, 0.01),
    ("GARBAGE_BAGS", "Garbage Bags 20pk", "ถุงขยะ 20 ใบ", "household", "bags", "20 bags", None, "ambient", 0.3, 0.2, 15, 25, 0, 0, None, 0.01),
    # Frozen
    ("FROZEN_SHRIMP", "Frozen Shrimp 500g", "กุ้งแช่แข็ง 500g", "frozen", "seafood", "500g", 90, "frozen", 0.5, 0.5, 85, 129, 1, 0, 0.01, None),
    ("FROZEN_DUMPLINGS", "Frozen Dumplings 20pk", "เกี๊ยวซ่าแช่แข็ง 20 ชิ้น", "frozen", "ready_meal", "20 pieces", 90, "frozen", 0.5, 0.4, 45, 69, 1, 1, None, 0.02),
    ("ICE_CREAM_1L", "Ice Cream 1L", "ไอศกรีม 1 ลิตร", "frozen", "dessert", "1 litre", 180, "frozen", 1.0, 0.6, 55, 89, 1, 1, None, 0.01),
]

PHARMACY_SKUS = [
    ("PARACETAMOL_500", "Paracetamol 500mg 10tab", "พาราเซตามอล 10 เม็ด", "medicine", "pain_relief", "10 tablets", 730, "controlled", 0.05, 0.02, 5, 15, 0, 0, None, 0.01),
    ("IBUPROFEN_400", "Ibuprofen 400mg 10tab", "ไอบูโพรเฟน 10 เม็ด", "medicine", "pain_relief", "10 tablets", 730, "controlled", 0.05, 0.02, 8, 22, 0, 0, None, 0.005),
    ("ANTACID_LIQUID", "Antacid Liquid 200ml", "ยาลดกรด 200 มล.", "medicine", "digestive", "200ml", 365, "controlled", 0.2, 0.2, 25, 55, 0, 0, None, 0.005),
    ("VITAMIN_C_1000", "Vitamin C 1000mg 30tab", "วิตามินซี 30 เม็ด", "supplement", "vitamins", "30 tablets", 365, "ambient", 0.1, 0.05, 45, 95, 1, 0, 0.02, None),
    ("MULTIVITAMIN_30", "Multivitamin 30tab", "วิตามินรวม 30 เม็ด", "supplement", "vitamins", "30 tablets", 365, "ambient", 0.1, 0.05, 55, 120, 1, 0, 0.01, None),
    ("ANTIHISTAMINE_10", "Antihistamine 10tab", "ยาแก้แพ้ 10 เม็ด", "medicine", "allergy", "10 tablets", 730, "controlled", 0.05, 0.02, 12, 35, 0, 0, None, 0.003),
    ("ANTIFUNGAL_CREAM", "Antifungal Cream 15g", "ครีมต้านเชื้อรา 15g", "medicine", "skin", "15g tube", 730, "controlled", 0.05, 0.02, 18, 45, 0, 0, None, 0.002),
    ("BANDAGE_ROLL", "Bandage Roll", "ผ้าพันแผล", "first_aid", "wound_care", "1 roll", None, "ambient", 0.1, 0.05, 8, 20, 0, 0, None, 0.002),
    ("PLASTER_10PK", "Adhesive Plasters 10pk", "พลาสเตอร์ 10 ชิ้น", "first_aid", "wound_care", "10 pieces", None, "ambient", 0.05, 0.02, 10, 25, 0, 0, None, 0.003),
    ("ALCOHOL_GEL", "Hand Sanitizer 250ml", "เจลล้างมือ 250 มล.", "hygiene", "sanitizer", "250ml", 365, "ambient", 0.25, 0.25, 25, 49, 0, 0, None, 0.005),
    ("FACE_MASK_50", "Face Masks 50pk", "หน้ากากอนามัย 50 ชิ้น", "hygiene", "protection", "50 masks", None, "ambient", 0.3, 0.15, 35, 69, 0, 0, None, 0.005),
    ("BLOOD_PRESSURE_MED", "BP Medicine 30tab", "ยาความดัน 30 เม็ด", "medicine", "cardiovascular", "30 tablets", 365, "controlled", 0.1, 0.05, 120, 250, 0, 0, 0.03, None),
    ("DIABETES_MED", "Diabetes Medicine 30tab", "ยาเบาหวาน 30 เม็ด", "medicine", "endocrine", "30 tablets", 365, "controlled", 0.1, 0.05, 150, 320, 0, 0, 0.03, None),
    ("COUGH_SYRUP", "Cough Syrup 120ml", "ยาแก้ไอ 120 มล.", "medicine", "respiratory", "120ml", 365, "controlled", 0.12, 0.12, 30, 65, 0, 0, None, 0.003),
    ("THERMOMETER", "Digital Thermometer", "ที่วัดไข้ดิจิตอล", "device", "monitoring", "1 unit", None, "ambient", 0.1, 0.05, 45, 99, 0, 0, None, 0.001),
]

COFFEE_SHOP_SKUS = [
    ("LATTE_HOT", "Hot Latte", "ลาเต้ร้อน", "beverage", "coffee", "1 cup", 0, "ambient", 0.3, 0.3, 15, 55, 1, 0, 0.10, None),
    ("AMERICANO_HOT", "Hot Americano", "อเมริกาโน่ร้อน", "beverage", "coffee", "1 cup", 0, "ambient", 0.3, 0.3, 10, 45, 1, 0, 0.08, None),
    ("ICED_COFFEE", "Iced Coffee", "กาแฟเย็น", "beverage", "coffee", "1 cup", 0, "cold", 0.4, 0.4, 12, 50, 1, 0, 0.12, None),
    ("GREEN_TEA_LATTE", "Green Tea Latte", "ชาเขียวลาเต้", "beverage", "tea", "1 cup", 0, "ambient", 0.3, 0.3, 15, 55, 1, 0, 0.04, None),
    ("CROISSANT", "Butter Croissant", "ครัวซองต์", "bakery", "pastry", "1 piece", 1, "ambient", 0.1, 0.1, 12, 35, 1, 1, 0.03, None),
    ("BANANA_CAKE", "Banana Cake Slice", "เค้กกล้วยหอม", "bakery", "cake", "1 slice", 2, "ambient", 0.1, 0.1, 15, 45, 1, 1, 0.02, None),
    ("SANDWICH_HAM", "Ham & Cheese Sandwich", "แซนวิชแฮมชีส", "food", "sandwich", "1 piece", 1, "cold", 0.2, 0.2, 20, 55, 1, 0, 0.03, None),
    ("BROWNIE", "Chocolate Brownie", "บราวนี่", "bakery", "dessert", "1 piece", 3, "ambient", 0.1, 0.1, 10, 35, 1, 1, 0.02, None),
]


def _make_skus(business_id: str, prefix: str, sku_tuples: list) -> list[dict]:
    """Convert SKU tuples to dicts ready for DB insertion."""
    skus = []
    for t in sku_tuples:
        (suffix, name, name_th, cat, subcat, unit, shelf, storage,
         vol, weight, cost, price, elastic, impulse, cons_p, cons_h) = t
        skus.append({
            "sku_id": f"{prefix}_{suffix}",
            "business_id": business_id,
            "sku_name": name,
            "sku_name_th": name_th,
            "category": cat,
            "subcategory": subcat,
            "unit_description": unit,
            "shelf_life_days": shelf if shelf and shelf > 0 else None,
            "storage_type": storage,
            "unit_volume_L": vol,
            "unit_weight_kg": weight,
            "base_cost_thb": cost,
            "base_price_thb": price,
            "is_elastic": elastic,
            "is_impulse": impulse,
            "typical_daily_consume_per_person": cons_p,
            "typical_daily_consume_per_household": cons_h,
            "is_active": 1,
        })
    return skus


# ══════════════════════════════════════════════════════════════
# Seed functions
# ══════════════════════════════════════════════════════════════


def seed_businesses(db: VillageDB, config: SimConfig) -> list[dict]:
    """Create all businesses and owners. Returns business dicts."""
    now = datetime.utcnow().isoformat()
    businesses = []
    for tmpl in BUSINESS_TEMPLATES:
        biz = {
            **tmpl,
            "opened_day": -(config.history_days + 365),  # opened well before sim
            "is_active": 1,
        }
        businesses.append(biz)
        db.insert("businesses", biz)

    for owner in OWNER_TEMPLATES:
        db.insert("owners", {**owner, "llm_persona_prompt": None, "created_at": now})

    db.commit()
    return businesses


def seed_skus(db: VillageDB) -> list[dict]:
    """Create all SKUs for all businesses. Returns SKU dicts."""
    all_skus = []
    all_skus.extend(_make_skus("supermarket", "SUP", SUPERMARKET_SKUS))
    all_skus.extend(_make_skus("pharmacy", "PHM", PHARMACY_SKUS))
    all_skus.extend(_make_skus("coffee_shop", "COF", COFFEE_SHOP_SKUS))
    db.insert_many("skus", all_skus)
    db.commit()
    return all_skus


def seed_households(db: VillageDB, config: SimConfig) -> list[dict]:
    """Create N households with Dirichlet-sampled persona weights."""
    rng = random.Random(config.random_seed)
    now = datetime.utcnow().isoformat()
    households = []

    zones = ["central", "north_cluster", "south_cluster", "market_area"]
    zone_weights = [0.35, 0.25, 0.25, 0.15]

    for i in range(config.num_households):
        hh_id = f"HH_{i+1:03d}"

        # Household size distribution
        r = rng.random()
        if r < config.household_size_small_pct:
            size = rng.randint(1, 2)
            dwelling = rng.choice(["studio", "apartment_small"])
        elif r < config.household_size_small_pct + config.household_size_medium_pct:
            size = rng.randint(3, 4)
            dwelling = rng.choice(["apartment_small", "apartment_large"])
        else:
            size = rng.randint(5, 6)
            dwelling = rng.choice(["apartment_large", "house"])

        # Income bracket
        r2 = rng.random()
        if r2 < config.income_low_pct:
            income = "low"
        elif r2 < config.income_low_pct + config.income_medium_pct:
            income = "medium"
        else:
            income = "high"

        bracket = INCOME_BRACKETS[income]
        weekly_budget = rng.uniform(bracket["weekly_min"], bracket["weekly_max"])
        budget_var = rng.uniform(0.05, 0.25)

        # Zone
        zone = rng.choices(zones, weights=zone_weights, k=1)[0]

        # Storage
        storage = DWELLING_STORAGE[dwelling]

        # Persona weights: Dirichlet-like sampling
        raw = [rng.gammavariate(2.0, 1.0) for _ in range(6)]
        total = sum(raw)
        weights = [w / total for w in raw]

        # LLM temperature derived from routine_strength
        routine = weights[1]
        llm_temp = 0.3 + (1.0 - routine) * 0.6  # low routine → higher temp

        hh = {
            "household_id": hh_id,
            "household_size": size,
            "dwelling_type": dwelling,
            "location_zone": zone,
            "income_bracket": income,
            "weekly_budget_thb": round(weekly_budget, 2),
            "budget_variance_pct": round(budget_var, 3),
            "move_in_day": -(config.history_days + rng.randint(30, 365)),
            "move_out_day": None,
            "is_active": 1,
            "fridge_capacity_L": storage["fridge_L"],
            "pantry_capacity_units": storage["pantry_units"],
            "freezer_capacity_L": storage["freezer_L"],
            "price_sensitivity": round(weights[0], 4),
            "routine_strength": round(weights[1], 4),
            "health_orientation": round(weights[2], 4),
            "brand_loyalty": round(weights[3], 4),
            "stock_anxiety": round(weights[4], 4),
            "social_timing": round(weights[5], 4),
            "llm_temperature": round(llm_temp, 3),
            "persona_narrative": None,
            "created_at": now,
        }
        households.append(hh)

    db.insert_many("households", households)
    db.commit()
    return households


def seed_suppliers(db: VillageDB, config: SimConfig) -> list[dict]:
    """Create suppliers for each business type."""
    suppliers = [
        {
            "supplier_id": "sup_grocery_main",
            "supplier_name": "Central Grocery Supply",
            "reliability_score": config.primary_fill_rate,
            "base_lead_time_days": 2,
            "max_lead_time_days": 5,
            "min_order_qty": 10,
            "price_tier": "standard",
            "supplies_skus": json.dumps([s["sku_id"] for s in _make_skus("supermarket", "SUP", SUPERMARKET_SKUS)]),
            "is_backup": 0,
            "adaptive_price_threshold": 3,
        },
        {
            "supplier_id": "sup_grocery_backup",
            "supplier_name": "Express Wholesale",
            "reliability_score": config.backup_fill_rate,
            "base_lead_time_days": 1,
            "max_lead_time_days": 3,
            "min_order_qty": 5,
            "price_tier": "premium",
            "supplies_skus": json.dumps([s["sku_id"] for s in _make_skus("supermarket", "SUP", SUPERMARKET_SKUS)]),
            "is_backup": 1,
            "adaptive_price_threshold": 2,
        },
        {
            "supplier_id": "sup_pharma_main",
            "supplier_name": "National Pharma Distribution",
            "reliability_score": 0.92,
            "base_lead_time_days": 3,
            "max_lead_time_days": 7,
            "min_order_qty": 5,
            "price_tier": "standard",
            "supplies_skus": json.dumps([s["sku_id"] for s in _make_skus("pharmacy", "PHM", PHARMACY_SKUS)]),
            "is_backup": 0,
            "adaptive_price_threshold": 3,
        },
        {
            "supplier_id": "sup_coffee_main",
            "supplier_name": "Bean & Flour Co.",
            "reliability_score": 0.90,
            "base_lead_time_days": 2,
            "max_lead_time_days": 4,
            "min_order_qty": 10,
            "price_tier": "standard",
            "supplies_skus": json.dumps([s["sku_id"] for s in _make_skus("coffee_shop", "COF", COFFEE_SHOP_SKUS)]),
            "is_backup": 0,
            "adaptive_price_threshold": 3,
        },
    ]
    db.insert_many("suppliers", suppliers)
    db.commit()
    return suppliers


def seed_calendar(db: VillageDB, config: SimConfig) -> list[dict]:
    """Generate calendar events for the simulation period."""
    rng = random.Random(config.random_seed + 1)
    events = []
    day_start = -config.history_days
    day_end = config.live_days

    for day in range(day_start, day_end + 1):
        dom = CalendarDay.compute_day_of_month(day)
        dow = CalendarDay.compute_day_of_week(day)
        month = CalendarDay.compute_month(day)

        # Payday (25-30 of month)
        if 25 <= dom <= 30:
            events.append({
                "cal_id": f"CAL_PAYDAY_{day:+05d}",
                "day": day,
                "event_name": "Payday period",
                "event_type": "payday",
                "demand_multiplier": 1.3,
                "category_effects": json.dumps({"snacks": 1.4, "beverage": 1.3}),
            })

        # Weekends
        if dow in ("saturday", "sunday"):
            events.append({
                "cal_id": f"CAL_WEEKEND_{day:+05d}",
                "day": day,
                "event_name": f"Weekend ({dow})",
                "event_type": "weekend",
                "demand_multiplier": 1.15 if dow == "saturday" else 1.05,
                "category_effects": None,
            })

        # Random weather (tropical: mostly fine, some rain)
        if config.enable_weather:
            r = rng.random()
            if r < 0.15:
                events.append({
                    "cal_id": f"CAL_WEATHER_{day:+05d}",
                    "day": day,
                    "event_name": "Rainy day",
                    "event_type": "weather_rain",
                    "demand_multiplier": 0.85,
                    "category_effects": json.dumps({"fresh_produce": 0.7, "frozen": 1.2}),
                })
            elif r < 0.20:
                events.append({
                    "cal_id": f"CAL_WEATHER_HOT_{day:+05d}",
                    "day": day,
                    "event_name": "Very hot day",
                    "event_type": "weather_hot",
                    "demand_multiplier": 1.05,
                    "category_effects": json.dumps({"beverage": 1.4, "frozen": 1.3}),
                })

        # Thai holidays (approximate — scattered through the year)
        if month == 4 and 13 <= dom <= 15:
            events.append({
                "cal_id": f"CAL_SONGKRAN_{day:+05d}",
                "day": day,
                "event_name": "Songkran Festival",
                "event_type": "public_holiday",
                "demand_multiplier": 0.7,
                "category_effects": json.dumps({"beverage": 1.5, "snacks": 1.3}),
            })

    if events:
        db.insert_many("calendar_events", events)
        db.commit()
    return events


def seed_initial_stock(db: VillageDB, skus: list[dict], day: int) -> None:
    """Create initial stock_ledger entries for all SKUs."""
    rng = random.Random(42)
    ledger_entries = []
    for sku in skus:
        # Initial stock: 30-150 units depending on expected demand
        base_stock = rng.randint(30, 150)
        shelf = int(base_stock * 0.6)
        warehouse = base_stock - shelf
        ledger_entries.append({
            "ledger_id": f"STK_{sku['sku_id']}_{day:+05d}",
            "business_id": sku["business_id"],
            "sku_id": sku["sku_id"],
            "day": day,
            "shelf_open": shelf,
            "warehouse_open": warehouse,
            "shelf_replenished": 0,
            "units_sold": 0,
            "units_expired": 0,
            "units_shrinkage": 0,
            "units_delivered": 0,
            "shelf_close": shelf,
            "warehouse_close": warehouse,
            "total_stock_close": base_stock,
            "stockout_occurred": 0,
            "near_expiry_flag": 0,
            "near_expiry_units": 0,
            "reorder_triggered": 0,
        })
    db.insert_many("stock_ledger", ledger_entries)
    db.commit()
