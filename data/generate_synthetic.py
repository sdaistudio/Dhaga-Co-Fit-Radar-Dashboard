"""Builds the stand-in data: 2,000 return comments and reviews, units sold, and 300 known answers.

Run:  python data/generate_synthetic.py
Writes: data/comments.csv, data/units_sold.csv, data/gold_labels.csv

Everything here is invented. The vendors and patterns are planted so the app has something true to find;
they are not findings about any real company. The seed makes the output identical on every run.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20261002
OUT = Path(__file__).parent
WEEKS = [date(2026, 8, 24) + timedelta(weeks=i) for i in range(6)]
ADULT = ["S", "M", "L", "XL"]
KIDS = ["2Y", "4Y", "6Y", "8Y"]

# How each vendor writes its sizes. The load step has to make these consistent.
SIZE_STYLES = {
    "plain": {"S": "S", "M": "M", "L": "L", "XL": "XL", "2Y": "2Y", "4Y": "4Y", "6Y": "6Y", "8Y": "8Y"},
    "words": {"S": "Small", "M": "Medium", "L": "Large", "XL": "X-Large", "2Y": "2-3 yrs", "4Y": "4-5 yrs", "6Y": "6-7 yrs", "8Y": "8-9 yrs"},
    "numbers": {"S": "36", "M": "38", "L": "40", "XL": "42", "2Y": "Age 2", "4Y": "Age 4", "6Y": "Age 6", "8Y": "Age 8"},
}

BACKGROUND_FIT = {"fit_small": .35, "fit_large": .30, "fit_short": .20, "fit_long": .10, "fit_other": .05}
EVEN = [1, 1, 1, 1]
FLAT = [1, 1, 1, 1, 1, 1]

# vendor, city, category, returns, fit share, fit mix, fit-return rate, size weights, week weights, size style
GROUPS = [
    ("V-07", "Tiruppur", "Kurtis", 212, .81, {"fit_small": .86, "fit_other": .08, "fit_short": .06}, .19, [.12, .22, .30, .36], [.75, .82, .9, 1.0, 1.1, 1.1], "numbers"),
    ("V-01", "Tiruppur", "Kurtis", 122, .53, BACKGROUND_FIT, .09, EVEN, FLAT, "plain"),
    ("V-02", "Jaipur", "Kurtis", 121, .53, BACKGROUND_FIT, .085, EVEN, FLAT, "words"),
    ("V-12", "Jaipur", "Dresses", 140, .74, {"fit_short": .85, "fit_small": .10, "fit_other": .05}, .16, [.18, .24, .28, .30], FLAT, "words"),
    ("V-05", "Tiruppur", "Dresses", 122, .53, BACKGROUND_FIT, .08, EVEN, FLAT, "plain"),
    ("V-06", "Jaipur", "Dresses", 121, .53, BACKGROUND_FIT, .075, EVEN, FLAT, "numbers"),
    ("V-03", "Tiruppur", "Kids tees", 96, .71, {"fit_large": .87, "fit_long": .08, "fit_other": .05}, .13, [.36, .30, .20, .14], [.7, .78, .86, .95, 1.0, 1.0], "words"),
    ("V-04", "Tiruppur", "Kids tees", 122, .53, BACKGROUND_FIT, .07, EVEN, FLAT, "plain"),
    ("V-08", "Jaipur", "Kids tees", 121, .53, BACKGROUND_FIT, .065, EVEN, FLAT, "numbers"),
    ("V-18", "Tiruppur", "Leggings", 88, .49, {"fit_small": .30, "fit_large": .35, "fit_short": .20, "fit_long": .15}, .08, EVEN, FLAT, "plain"),
    ("V-19", "Tiruppur", "Leggings", 122, .53, BACKGROUND_FIT, .07, EVEN, FLAT, "words"),
    ("V-20", "Jaipur", "Leggings", 121, .53, BACKGROUND_FIT, .065, EVEN, FLAT, "plain"),
    ("V-21", "Jaipur", "Palazzo", 6, .50, BACKGROUND_FIT, .05, EVEN, FLAT, "plain"),
    ("V-22", "Jaipur", "Palazzo", 122, .53, BACKGROUND_FIT, .08, EVEN, FLAT, "numbers"),
    ("V-23", "Tiruppur", "Palazzo", 121, .53, BACKGROUND_FIT, .075, EVEN, FLAT, "plain"),
    ("V-09", "Jaipur", "Kurtas", 122, .53, BACKGROUND_FIT, .08, EVEN, FLAT, "words"),
    ("V-11", "Tiruppur", "Kurtas", 0, .53, BACKGROUND_FIT, .078, EVEN, FLAT, "plain"),   # filled to reach 2,000
]

# (text, body area). {size} is replaced by the size bought.
T = {
    "fit_small": [("size chota hai, {size} bhi tight lag raha", "overall"), ("bust pe bahut tight, return kar diya", "bust"),
                  ("fitting sahi nahi, ek size bada lena padega", "overall"), ("kamar pe tight hai, saans nahi aati", "waist"),
                  ("shoulder se tight hai, haath nahi uthta", "shoulder"), ("too tight on the chest, had to return", "bust"),
                  ("साइज़ छोटा है, बहुत टाइट है", "overall"), ("baju bahut tight hai", "sleeve"), ("chest pe fit nahi aa raha, chhota hai", "bust")],
    "fit_large": [("bahut dheela hai, hang ho raha", "overall"), ("kamar pe loose hai, baaki theek", "waist"),
                  ("bacche ko bahut dheela hai", "overall"), ("size bada nikla, ek size chhota mangwana pada", "overall"),
                  ("too loose, looks like a sack", "overall"), ("बहुत ढीला है, बड़ा साइज़ आ गया", "overall"), ("shoulder se utar raha hai, bada hai", "shoulder")],
    "fit_short": [("length bahut kam hai, photo me lamba dikh raha tha", "length"), ("ghutne se upar aa raha hai", "length"),
                  ("short hai, function me nahi pehen sakti", "length"), ("baju chhoti hai, kalai tak nahi aati", "sleeve"),
                  ("length is too short for me", "length")],
    "fit_long": [("bahut lamba hai, zameen pe lag raha", "length"), ("baju lambi hai, mod ke pehenna padta", "sleeve"), ("length zyada hai, katwana padega", "length")],
    "fit_other": [("fitting ajeeb hai, shape theek nahi", "overall"), ("cut sahi nahi baithta body pe", "overall")],
    "quality": [("kapda patla hai, ek dhulai me kharab ho gaya", "not_applicable"), ("silai khul gayi pehle hi din", "not_applicable"),
                ("fabric cheap lagta hai, photo jaisa nahi", "not_applicable"), ("stitching is poor and thread coming out", "not_applicable"),
                ("कपड़ा बहुत पतला है, घटिया क्वालिटी", "not_applicable"), ("dhone pe rang nikal gaya aur sikud gaya", "not_applicable")],
    "colour": [("pic me maroon tha, ye to laal hai", "not_applicable"), ("colour alag hai photo se", "not_applicable"),
               ("rang halka hai, website pe dark tha", "not_applicable"), ("color is different from the picture", "not_applicable")],
    "late": [("late aaya, function nikal gaya", "not_applicable"), ("delivery bahut der se hui, ab zaroorat nahi", "not_applicable"),
             ("arrived after the wedding, no use now", "not_applicable")],
    "changed_mind": [("gift ke liye liya tha, zaroorat nahi rahi", "not_applicable"), ("dusra pasand aa gaya isliye wapas", "not_applicable"),
                     ("galti se order ho gaya tha", "not_applicable")],
    "other": [("galat product aaya, maine ye nahi mangwaya", "not_applicable"), ("tag nahi tha, used lag raha tha", "not_applicable"),
              ("packet khula hua aaya tha", "not_applicable")],
    "unclear": [("theek nahi laga", "not_applicable"), ("wapas kar diya bas", "not_applicable"), ("jaisa socha tha waisa nahi nikla", "not_applicable"),
                ("pasand nahi aaya mujhe", "not_applicable"), ("accha nahi hai ye", "not_applicable")],
}
TWO_REASON = [("colour alag tha aur size bhi chhota", "fit_small", "colour", "overall"),
              ("kapda patla hai aur dheela bhi hai", "fit_large", "quality", "overall"),
              ("late aaya aur length bhi kam hai", "fit_short", "late", "length"),
              ("rang alag hai, upar se bust pe tight", "fit_small", "colour", "bust")]
UNREADABLE = ["ok", "bad", ".", "", "nahi", "return", "no", "??"]
SPELLING = [("chota", ["chota", "chhota", "chotta"]), ("dheela", ["dheela", "dhila", "dheela"]), ("bahut", ["bahut", "bohot", "bhot"]),
            ("tight", ["tight", "tite", "tight"]), ("colour", ["colour", "color", "kalar"])]
TAILS = ["", "", "", " yaar", " return kar diya", " paisa waste", " refund chahiye", " 👎", " plz jaldi refund karo"]
COLOURS = ["maroon", "Maroon ", "mehroon", "MRN", "red", "laal", "navy", "Navy Blue", "nevy", "black", "blk", "Black", "pink", "peach", "mustard", "mustrd"]
NON_FIT = [("quality", 14), ("colour", 9), ("late", 5), ("changed_mind", 4), ("other", 4), ("unreadable", 3), ("unclear", 3)]


def pick(rng, weights: dict):
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys])[0]


def noisy(rng, text):
    for word, options in SPELLING:
        if word in text:
            text = text.replace(word, rng.choice(options))
    if rng.random() < .12:
        text = text.upper()
    return text + rng.choice(TAILS)


def main():
    rng = random.Random(SEED)
    groups = [list(g) for g in GROUPS]
    groups[-1][3] = 2000 - sum(g[3] for g in groups)   # fill the last vendor so the total is exactly 2,000
    comments, units, truth = [], [], {}
    n = 0
    for vendor, city, cat, returns, fit_share, fit_mix, rate, size_w, week_w, style in groups:
        sizes = KIDS if cat == "Kids tees" else ADULT
        fit_count = round(returns * fit_share)
        skus = [f"SKU-{vendor[2:]}{i:02d}" for i in range(1, 21)]
        fit_by_size = {s: 0 for s in sizes}
        for i in range(returns):
            n += 1
            cid = f"C-{n:05d}"
            is_fit = i < fit_count
            week = rng.choices(WEEKS, weights=week_w if is_fit else FLAT)[0]
            size = rng.choices(sizes, weights=size_w if is_fit else EVEN)[0]
            second = ""
            if is_fit and rng.random() < .07:
                text, reason, second, area = rng.choice(TWO_REASON)
            elif is_fit:
                reason = pick(rng, fit_mix)
                options = T[reason]
                if vendor == "V-07" and reason == "fit_small":      # planted: tight at the bust
                    options = [o for o in options if o[1] == "bust"] * 3 + options
                text, area = rng.choice(options)
            else:
                reason = rng.choices([r for r, _ in NON_FIT], weights=[w for _, w in NON_FIT])[0]
                if reason == "unreadable":
                    text, area = rng.choice(UNREADABLE), "not_applicable"
                else:
                    text, area = rng.choice(T[reason])
            if reason != "unreadable":
                text = noisy(rng, text.replace("{size}", size))
            if is_fit:
                fit_by_size[size] += 1
            source = "return" if rng.random() < .65 else "review"
            comments.append({
                "comment_id": cid, "source": source, "text": text,
                "order_id": f"ORD-{rng.randint(4_000_000, 4_999_999)}", "sku_id": rng.choice(skus),
                "vendor_id": vendor, "vendor_city": city, "category": cat,
                "size_bought": SIZE_STYLES[style][size], "colour_raw": rng.choice(COLOURS),
                "return_reason_code": "Other" if source == "return" else "",
                "star_rating": "" if source == "return" else rng.choice([1, 1, 2, 2, 3]),
                "created_at": (week + timedelta(days=rng.randint(0, 6))).isoformat(),
            })
            truth[cid] = (reason, second)
        # units sold, so that fit returns / units comes out at the planted rate
        total_units = max(40, round(fit_count / rate)) if returns > 6 else 60
        for s in sizes:
            for w in WEEKS:
                units.append({"vendor_id": vendor, "category": cat, "size": SIZE_STYLES[style][s], "week_start": w.isoformat(),
                              "units_sold": max(1, round(total_units / (len(sizes) * len(WEEKS)) * rng.uniform(.9, 1.1)))})
    # a few exact duplicates, as real exports have
    for row in rng.sample(comments, 30):
        dup = dict(row); n += 1; dup["comment_id"] = f"C-{n:05d}"; comments.append(dup); truth[dup["comment_id"]] = ("duplicate", "")
    rng.shuffle(comments)

    def write(name, rows):
        with open(OUT / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    write("comments.csv", comments)
    write("units_sold.csv", units)
    labelled = [c for c in comments if truth[c["comment_id"]][0] != "duplicate"]
    gold = [{"comment_id": c["comment_id"], "text": c["text"], "gold_reason": truth[c["comment_id"]][0], "gold_second_reason": truth[c["comment_id"]][1]}
            for c in rng.sample(labelled, 300)]
    write("gold_labels.csv", gold)
    print(f"comments.csv: {len(comments)} rows ({len(comments) - 30} unique + 30 duplicates)")
    print(f"units_sold.csv: {len(units)} rows · gold_labels.csv: {len(gold)} rows")


if __name__ == "__main__":
    main()
