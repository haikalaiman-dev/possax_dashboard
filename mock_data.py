import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

# -------------------------
# Helpers
# -------------------------
CITIES = [
    "Jakarta", "Bandung", "Surabaya", "Medan", "Makassar",
    "Yogyakarta", "Denpasar", "Semarang", "Palembang", "Balikpapan",
    "Bekasi", "Tangerang", "Depok"
]

CITY_COORDS = {
    "Jakarta": (-6.2, 106.8),
    "Bandung": (-6.9, 107.6),
    "Surabaya": (-7.25, 112.75),
    "Medan": (3.59, 98.67),
    "Makassar": (-5.15, 119.43),
    "Yogyakarta": (-7.8, 110.37),
    "Denpasar": (-8.65, 115.22),
    "Semarang": (-6.99, 110.42),
    "Palembang": (-2.99, 104.76),
    "Balikpapan": (-1.27, 116.83),
    "Bekasi": (-6.24, 106.99),
    "Tangerang": (-6.18, 106.63),
    "Depok": (-6.4, 106.82),
}

ROLES = ["Owner", "Kasir", "Manager", "Supervisor"]
DEVICE_TYPES = ["Android", "iOS"]
STORE_TYPES = ["Retail", "F&B", "Service", "Cafe", "Restaurant", "Bakery"]
SUB_TYPES = ["Pro", "Basic", "Trial", "Non-Paid"]
REF_CODES = ["REF123", "JOIN2025", "PROMO50", "DISCOUNT10", "VIP", "FREEMONTH", "HELLO", "TRYME", "BONUS", "SUPER"]

def jitter(coord: float, spread: float = 0.15) -> float:
    return coord + random.uniform(-spread, spread)

# -------------------------
# Users
# -------------------------
NUM_USERS = 120
users = []
for uid in range(1, NUM_USERS + 1):
    city = random.choice(CITIES)
    base_lat, base_lon = CITY_COORDS[city]
    created_at = datetime.now() - timedelta(days=random.randint(0, 365))
    last_activity = datetime.now() - timedelta(days=random.randint(0, 7))
    user = {
        "UserID": uid,
        "Name": f"User {uid}",
        "CreatedAt": created_at,
        "LastActivity": last_activity,
        "Role": random.choice(ROLES),
        "DeviceType": random.choice(DEVICE_TYPES),
        "Phone": f"+62{random.randint(8110000000, 8999999999)}",
        "Email": f"user{uid}@example.com",
        "ReferralCode": random.choice(REF_CODES + [None, None]),  # some Nones
        "City": city,
        "Latitude": jitter(base_lat, 0.2),
        "Longitude": jitter(base_lon, 0.2),
        "TotalTransactions": random.randint(0, 1000),
    }
    users.append(user)

df_users = pd.DataFrame(users)

# -------------------------
# Stores
# -------------------------
NUM_STORES = 80
stores = []
for sid in range(1, NUM_STORES + 1):
    city = random.choice(CITIES)
    owner_id = random.randint(1, NUM_USERS)
    created_at = datetime.now() - timedelta(days=random.randint(0, 540))
    current_type = random.choice(SUB_TYPES)
    stores.append({
        "StoreID": sid,
        "StoreName": f"Store {sid}",
        "StoreType": random.choice(STORE_TYPES),
        "OwnerUserID": owner_id,
        "City": city,
        "CreatedAt": created_at,
        "SubscriptionType": current_type,  # current tier
        "Is_Branch": random.choice([True, False])
    })

df_stores = pd.DataFrame(stores)

# -------------------------
# Subscriptions (history, per store)
# -------------------------
sub_records = []
sub_id = 1
for _, s in df_stores.iterrows():
    # 1 to 5 historical records, last one defines current EndDate
    n_rec = random.randint(1, 5)
    start = s["CreatedAt"] - timedelta(days=random.randint(0, 60))
    for i in range(n_rec):
        sub_type = s["SubscriptionType"] if i == n_rec - 1 else random.choice(SUB_TYPES)
        duration = random.choice([30, 90, 180])
        s_start = start + timedelta(days=sum(random.choice([30, 90, 180]) for _ in range(i)))
        s_end = s_start + timedelta(days=duration)
        paid = 0
        if sub_type == "Pro":
            paid = 400_000
        elif sub_type == "Basic":
            paid = 200_000
        sub_records.append({
            "SubscriptionID": sub_id,
            "StoreID": s["StoreID"],
            "Type": sub_type,
            "StartDate": s_start,
            "EndDate": s_end,
            "AmountPaid": paid,
        })
        sub_id += 1

df_subscriptions = pd.DataFrame(sub_records)

# Aggregate back onto stores: current Start/End, recurring count, total spent
agg = (
    df_subscriptions.sort_values(["StoreID", "EndDate"])
    .groupby("StoreID")
    .agg(
        CurrentStart=("StartDate", "last"),
        CurrentEnd=("EndDate", "last"),
        ReoccuringSubs=("SubscriptionID", "count"),
        TotalMoneySpent=("AmountPaid", "sum"),
    )
    .reset_index()
)
df_stores = df_stores.merge(agg, on="StoreID", how="left")

# -------------------------
# Users → store membership (for "Stores" column in Users table)
# -------------------------
# Randomly assign each user 0–3 associated stores
store_ids = df_stores["StoreID"].tolist()
user_stores_map = {}
for uid in df_users["UserID"]:
    k = random.choice([0, 1, 2, 3])
    user_stores_map[uid] = sorted(random.sample(store_ids, k)) if k > 0 else []

df_users["Stores"] = df_users["UserID"].map(user_stores_map)

# -------------------------
# Derived: UserSubscriptionType (highest tier across their stores)
# Ranking: Pro > Basic > Trial > Non-Paid
# -------------------------
rank = {"Pro": 3, "Basic": 2, "Trial": 1, "Non-Paid": 0}

store_type_map = df_stores.set_index("StoreID")["SubscriptionType"].to_dict()

def user_tier(store_list):
    if not store_list:
        return "Non-Paid"
    tiers = [store_type_map.get(sid, "Non-Paid") for sid in store_list]
    return sorted(tiers, key=lambda t: rank[t], reverse=True)[0]

df_users["UserSubscriptionType"] = df_users["Stores"].apply(user_tier)

# -------------------------
# Trend scaffolds (we’ll compute from CreatedAt / CreatedAt)
# -------------------------

__all__ = ["df_users", "df_stores", "df_subscriptions"]
