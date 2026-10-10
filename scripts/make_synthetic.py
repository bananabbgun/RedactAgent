"""Generate a synthetic, fully fictional document corpus with pixel-exact PII ground truth.

Every person, ID number, address and organisation below is randomly generated.
Documents are rendered as A4 pages at 150 dpi, then "scanned" (slight rotation,
noise, blur, paper tint) so that OCR and vision models face realistic input.

Usage:
    python scripts/make_synthetic.py --n-per-template 6 --out data/synthetic
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from faker import Faker
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1240, 1754  # A4 @ 150 dpi
MARGIN = 90

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
F_EN = str(FONT_DIR / "Arial.ttf")
F_EN_B = str(FONT_DIR / "Arial Bold.ttf")
F_SERIF = str(FONT_DIR / "Times New Roman.ttf")
F_SERIF_B = str(FONT_DIR / "Times New Roman Bold.ttf")
F_ZH = str(FONT_DIR / "Arial Unicode.ttf")
F_HAND = str(FONT_DIR / "Bradley Hand Bold.ttf")
F_SIGN = str(FONT_DIR / "SnellRoundhand.ttc")

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# --------------------------------------------------------------------------------------
# Fake identity generators (Taiwan-specific formats with valid checksums)
# --------------------------------------------------------------------------------------

TW_ID_LETTERS = {
    "A": 10, "B": 11, "C": 12, "D": 13, "E": 14, "F": 15, "G": 16, "H": 17, "I": 34,
    "J": 18, "K": 19, "L": 20, "M": 21, "N": 22, "O": 35, "P": 23, "Q": 24, "R": 25,
    "S": 26, "T": 27, "U": 28, "V": 29, "W": 32, "X": 30, "Y": 31, "Z": 33,
}


def tw_national_id(rng: random.Random, sex: str) -> str:
    letter = rng.choice("ABEFHJKLOPT")
    code = TW_ID_LETTERS[letter]
    digits = [1 if sex == "M" else 2] + [rng.randint(0, 9) for _ in range(7)]
    total = (code // 10) * 1 + (code % 10) * 9 + sum(d * w for d, w in zip(digits, [8, 7, 6, 5, 4, 3, 2, 1]))
    check = (10 - total % 10) % 10
    return letter + "".join(map(str, digits)) + str(check)


def luhn_card(rng: random.Random) -> str:
    body = [4] + [rng.randint(0, 9) for _ in range(14)]
    total = 0
    for i, d in enumerate(reversed(body)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    digits = body + [(10 - total % 10) % 10]
    s = "".join(map(str, digits))
    return " ".join(s[i:i + 4] for i in range(0, 16, 4))


def tw_mobile(rng: random.Random) -> str:
    return f"09{rng.randint(10, 89)}-{rng.randint(100, 999)}-{rng.randint(100, 999)}"


def tw_landline(rng: random.Random) -> str:
    return f"(0{rng.choice([2, 2, 3, 4, 6, 7])}) {rng.randint(2000, 2999)}-{rng.randint(1000, 9999)}"


def bank_account(rng: random.Random) -> str:
    return f"({rng.choice([700, 812, 822, 808, 13])}) {rng.randint(1000, 9999)}-{rng.randint(100, 999)}-{rng.randint(100000, 999999)}"


def nhi_card(rng: random.Random) -> str:
    return f"0000 {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"


def mrn(rng: random.Random) -> str:
    return f"MRN-{rng.randint(10, 99)}{rng.randint(10000, 99999)}"


def plate(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    if rng.random() < 0.5:
        return "".join(rng.choice(letters) for _ in range(3)) + "-" + f"{rng.randint(0, 9999):04d}"
    return f"{rng.randint(100, 999)}-" + "".join(rng.choice(letters) for _ in range(3))


ROMAN_SURNAMES = ["Chen", "Lin", "Huang", "Chang", "Lee", "Wang", "Wu", "Liu", "Tsai", "Yang", "Hsu", "Cheng", "Hsieh", "Kuo", "Lai"]
ROMAN_GIVEN = ["Wei", "Ting", "Yu", "Hsin", "Chih", "Ming", "Chia", "Hao", "Yi", "Jung", "Shu", "Pei", "Kuan", "Tzu", "Han", "Chun", "Yen", "Po"]


def roman_name(rng: random.Random) -> tuple[str, str]:
    """Returns (full name, surname), e.g. ("Chen Yu-Ting", "Chen")."""
    s = rng.choice(ROMAN_SURNAMES)
    g = f"{rng.choice(ROMAN_GIVEN)}-{rng.choice(ROMAN_GIVEN).lower()}"
    return f"{s} {g}", s


ZH_CITIES = {
    "臺北市": ["大安區", "信義區", "中山區", "士林區", "北投區"],
    "新北市": ["板橋區", "新店區", "中和區", "三重區"],
    "臺中市": ["西屯區", "北區", "南屯區"],
    "高雄市": ["苓雅區", "左營區", "三民區"],
    "臺南市": ["東區", "安平區"],
    "新竹市": ["東區", "北區"],
}
ZH_ROADS = ["中山路", "民生東路", "復興南路", "和平東路", "忠孝東路", "文化路", "光復路", "自由路", "建國路", "中正路"]
ZH_SEC = ["", "一段", "二段", "三段"]
ZH_NUM = "一二三四五六七八九"

EN_CITIES = {
    "Taipei City": ["Da'an Dist.", "Xinyi Dist.", "Zhongshan Dist.", "Shilin Dist."],
    "New Taipei City": ["Banqiao Dist.", "Xindian Dist."],
    "Taichung City": ["Xitun Dist.", "Nantun Dist."],
    "Kaohsiung City": ["Lingya Dist.", "Zuoying Dist."],
}
EN_ROADS = ["Zhongshan Rd.", "Minsheng E. Rd.", "Fuxing S. Rd.", "Heping E. Rd.", "Zhongxiao E. Rd.", "Wenhua Rd.", "Guangfu Rd.", "Ziyou Rd."]


def zh_address(rng: random.Random) -> str:
    city = rng.choice(list(ZH_CITIES))
    dist = rng.choice(ZH_CITIES[city])
    sec = rng.choice(ZH_SEC)
    lane = f"{rng.randint(2, 300)}巷" if rng.random() < 0.3 else ""
    floor = f"{rng.choice(ZH_NUM)}樓" if rng.random() < 0.7 else ""
    return f"{city}{dist}{rng.choice(ZH_ROADS)}{sec}{lane}{rng.randint(1, 399)}號{floor}"


def en_address(rng: random.Random) -> str:
    city = rng.choice(list(EN_CITIES))
    dist = rng.choice(EN_CITIES[city])
    sec = f", Sec. {rng.randint(1, 4)}" if rng.random() < 0.5 else ""
    floor = f"{rng.randint(2, 15)}F., " if rng.random() < 0.6 else ""
    return f"{floor}No. {rng.randint(1, 399)}, {rng.choice(EN_ROADS)}{sec}, {dist}, {city}"


def rand_date(rng: random.Random, y0: int, y1: int) -> tuple[int, int, int]:
    return rng.randint(y0, y1), rng.randint(1, 12), rng.randint(1, 28)


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def en_date(d: tuple[int, int, int], style: int = 0) -> str:
    y, m, dd = d
    if style == 0:
        return f"{MONTHS[m - 1]} {dd}, {y}"
    if style == 1:
        return f"{y}-{m:02d}-{dd:02d}"
    return f"{m:02d}/{dd:02d}/{y}"


def roc_date(d: tuple[int, int, int]) -> str:
    y, m, dd = d
    return f"民國{y - 1911}年{m}月{dd}日"


def slash_date(d: tuple[int, int, int]) -> str:
    y, m, dd = d
    return f"{y}/{m:02d}/{dd:02d}"


QUASI_EN = [
    "the only licensed ferry captain on Green Island",
    "the head coach of the national women's curling team",
    "the sole veterinarian serving Orchid Island",
    "the only female lighthouse keeper in Penghu",
]
QUASI_ZH = [
    "為該村唯一的排灣族語教師",
    "是蘭嶼唯一的牙醫師",
    "現任國家女子冰壺隊總教練",
    "為綠島唯一領有執照的渡輪船長",
]

HOSPITALS_EN = ["Riverside Memorial Hospital", "Harborview Union Hospital", "Greenfield General Hospital"]
HOSPITALS_ZH = ["仁和綜合醫院", "康寧紀念醫院", "安心聯合醫院"]
COMPANIES_ZH = ["星河科技股份有限公司", "曜光精密工業股份有限公司", "藍海數位服務有限公司"]

# --------------------------------------------------------------------------------------
# Page canvas that records ground truth while drawing
# --------------------------------------------------------------------------------------


@dataclass
class Page:
    doc_id: str
    template: str
    lang: str
    img: Image.Image = field(default_factory=lambda: Image.new("RGB", (W, H), "white"))
    items: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.d = ImageDraw.Draw(self.img)

    # -- primitives -----------------------------------------------------------------
    def text(self, x, y, s, f, fill=(20, 20, 20), cat=None, role=None):
        self.d.text((x, y), s, font=f, fill=fill)
        bb = self.d.textbbox((x, y), s, font=f)
        if cat:
            self.items.append({"cat": cat, "text": s, "bbox": list(bb), "role": role})
        return bb

    def segs(self, x, y, segments, f, **kw):
        """Draw consecutive text segments on one line; (text, cat, role) tuples or plain str."""
        for seg in segments:
            if isinstance(seg, str):
                seg = (seg, None, None)
            s, cat, role = (list(seg) + [None, None])[:3]
            self.text(x, y, s, f, cat=cat, role=role, **kw)
            # advance by the font's advance width so trailing spaces are kept
            x += f.getlength(s)
        return x

    def field(self, x, y, label, value, f_label, f_value, cat=None, role=None, gap=12, fill=(20, 20, 20)):
        bb = self.text(x, y, label, f_label, fill=(60, 60, 60))
        return self.text(bb[2] + gap, y, value, f_value, cat=cat, role=role, fill=fill)

    def hline(self, y, x0=MARGIN, x1=W - MARGIN, w=2, fill=(60, 60, 60)):
        self.d.line([(x0, y), (x1, y)], fill=fill, width=w)

    def box(self, xy, w=2, fill=None, outline=(80, 80, 80)):
        self.d.rectangle(xy, outline=outline, width=w, fill=fill)

    # -- visual PII -----------------------------------------------------------------
    def signature(self, x, y, name, rng, role=None, size=46):
        f = font(F_SIGN, size)
        s = name.replace("-", " ")
        self.d.text((x, y), s, font=f, fill=(15, 30, 110))
        bb = list(self.d.textbbox((x, y), s, font=f))
        # an underline flourish
        y2 = bb[3] - 4
        pts = [(bb[0] - 6 + i * 12, y2 + int(5 * math.sin(i / 1.7 + rng.random()))) for i in range((bb[2] - bb[0]) // 12 + 2)]
        self.d.line(pts, fill=(15, 30, 110), width=2)
        bb = [bb[0] - 8, bb[1] - 4, max(bb[2], pts[-1][0]) + 4, y2 + 12]
        self.items.append({"cat": "SIGNATURE", "text": name, "bbox": bb, "role": role})
        return bb

    def seal(self, x, y, chars: str, size=120, round_=False, rng=None):
        """Red seal stamp (square personal seal or round organisation seal)."""
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        red = (200, 30, 35, 210)
        if round_:
            ld.ellipse([3, 3, size - 4, size - 4], outline=red, width=6)
            f = font(F_ZH, size // 6)
            # arrange characters around a circle
            n = len(chars)
            for i, ch in enumerate(chars):
                a = math.pi * (1.15 + 0.7 * i / max(1, n - 1))
                cx = size / 2 + (size / 2 - size * 0.2) * math.cos(a)
                cy = size / 2 + (size / 2 - size * 0.2) * math.sin(a)
                ld.text((cx, cy), ch, font=f, fill=red, anchor="mm")
            ld.text((size / 2, size / 2), "★", font=font(F_ZH, size // 4), fill=red, anchor="mm")
        else:
            ld.rectangle([3, 3, size - 4, size - 4], outline=red, width=7)
            f = font(F_ZH, int(size * 0.36))
            grid = [chars[i] if i < len(chars) else "" for i in range(4)]
            # traditional seal order: right column top-to-bottom, then left column
            pos = [(0.72, 0.30), (0.72, 0.72), (0.30, 0.30), (0.30, 0.72)]
            for ch, (px, py) in zip(grid, pos):
                ld.text((size * px, size * py), ch, font=f, fill=red, anchor="mm")
        if rng is not None:
            layer = layer.rotate(rng.uniform(-12, 12), resample=Image.BICUBIC, expand=False)
        self.img.paste(layer, (x, y), layer)
        bb = [x, y, x + size, y + size]
        self.items.append({"cat": "SEAL_STAMP", "text": chars, "bbox": bb, "role": None})
        return bb

    def photo(self, x, y, w=210, h=270, rng=None):
        """ID-style portrait (cartoon face; no real person)."""
        rng = rng or random.Random(0)
        bg = rng.choice([(196, 220, 240), (225, 228, 232), (210, 232, 214)])
        self.d.rectangle([x, y, x + w, y + h], fill=bg, outline=(90, 90, 90), width=2)
        skin = rng.choice([(241, 204, 170), (224, 180, 140), (198, 150, 110)])
        hair = rng.choice([(30, 25, 20), (60, 40, 25), (90, 80, 70)])
        cx, cy = x + w // 2, y + int(h * 0.42)
        # shoulders
        self.d.pieslice([x + 10, y + int(h * 0.70), x + w - 10, y + int(h * 1.35)], 180, 360, fill=rng.choice([(40, 60, 110), (70, 70, 70), (120, 30, 40)]))
        self.d.rectangle([cx - 18, cy + 50, cx + 18, cy + 80], fill=skin)  # neck
        self.d.ellipse([cx - 62, cy - 80, cx + 62, cy + 75], fill=skin)  # face
        self.d.chord([cx - 68, cy - 95, cx + 68, cy + 10], 180, 360, fill=hair)  # hair
        for ex in (-25, 25):
            self.d.ellipse([cx + ex - 8, cy - 8, cx + ex + 8, cy + 6], fill=(255, 255, 255))
            self.d.ellipse([cx + ex - 4, cy - 5, cx + ex + 4, cy + 4], fill=(30, 30, 30))
            self.d.line([cx + ex - 12, cy - 20, cx + ex + 12, cy - 22], fill=hair, width=4)
        self.d.line([cx, cy + 2, cx - 6, cy + 25, cx + 4, cy + 27], fill=(150, 100, 80), width=2)
        self.d.arc([cx - 22, cy + 28, cx + 22, cy + 52], 20, 160, fill=(150, 60, 60), width=3)
        bb = [x, y, x + w, y + h]
        self.items.append({"cat": "FACE_PHOTO", "text": "portrait", "bbox": bb, "role": "subject"})
        return bb


# --------------------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------------------


def t_discharge_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "discharge_summary_en", "en")
    sex = rng.choice("MF")
    name, surname = roman_name(rng)
    doctor, _ = roman_name(rng)
    contact, _ = roman_name(rng)
    hosp = rng.choice(HOSPITALS_EN)
    adm = rand_date(rng, 2024, 2026)
    dis = (adm[0], adm[1], min(28, adm[2] + rng.randint(2, 9)))
    dob = rand_date(rng, 1950, 2000)
    style = rng.randint(0, 2)
    b, r, hb = font(F_EN_B, 40), font(F_EN, 25), font(F_EN_B, 27)

    p.text(MARGIN, 70, hosp, b, fill=(20, 50, 110))
    p.text(MARGIN, 122, "Department of Internal Medicine  |  Tel (02) 2700-0000", font(F_EN, 22), fill=(90, 90, 90))
    p.text(W - MARGIN - 330, 78, "DISCHARGE SUMMARY", font(F_EN_B, 30))
    p.hline(170, w=3)

    y = 200
    col2 = 660
    p.field(MARGIN, y, "Patient Name:", name, hb, r, "PERSON_NAME", "subject")
    p.field(col2, y, "MRN:", mrn(rng), hb, r, "MEDICAL_RECORD_NO")
    y += 48
    p.field(MARGIN, y, "National ID:", tw_national_id(rng, sex), hb, r, "GOV_ID")
    p.field(col2, y, "Date of Birth:", en_date(dob, style), hb, r, "DATE_OF_BIRTH")
    y += 48
    p.field(MARGIN, y, "Sex:", "Male" if sex == "M" else "Female", hb, r)
    p.field(col2, y, "NHI Card No.:", nhi_card(rng), hb, r, "HEALTH_INSURANCE_NO")
    y += 48
    p.field(MARGIN, y, "Phone:", tw_mobile(rng), hb, r, "PHONE")
    first = name.split(" ")[1].replace("-", "").lower()
    p.field(col2, y, "Email:", f"{first}.{surname.lower()}{rng.randint(1, 99)}@mail.example.tw", hb, r, "EMAIL")
    y += 48
    p.field(MARGIN, y, "Address:", en_address(rng), hb, r, "ADDRESS")
    y += 48
    p.field(MARGIN, y, "Admission:", en_date(adm, style), hb, r, "DATE")
    p.field(col2, y, "Discharge:", en_date(dis, style), hb, r, "DATE")
    y += 48
    p.field(MARGIN, y, "Attending Physician:", f"Dr. {doctor}", hb, r, "PERSON_NAME", "professional")
    y += 48
    bb = p.field(MARGIN, y, "Emergency Contact:", contact, hb, r, "PERSON_NAME", "family")
    rel = rng.choice(["spouse", "daughter", "son", "sister"])
    bb = p.text(bb[2] + 10, y, f"({rel}),", r)
    p.text(bb[2] + 10, y, tw_mobile(rng), r, cat="PHONE")
    y += 70
    p.hline(y, w=1)

    y += 25
    p.text(MARGIN, y, "Diagnosis", hb)
    dx = rng.choice([
        "Community-acquired pneumonia, right lower lobe (J18.1)",
        "Acute pyelonephritis without obstruction (N10)",
        "Type 2 diabetes mellitus with hyperglycemia (E11.65)",
        "Cellulitis of left lower limb (L03.116)",
    ])
    p.text(MARGIN, y + 42, dx, r)
    y += 110
    p.text(MARGIN, y, "Hospital Course", hb)
    y += 45
    title = "Mr." if sex == "M" else "Ms."
    age = adm[0] - dob[0]
    lines = [
        [f"{title} ", (surname, "PERSON_NAME", "subject"), f" is a {age}-year-old patient who works as"],
        [(rng.choice(QUASI_EN), "QUASI_IDENTIFIER", "subject"), ". The patient was admitted on "],
        [(en_date(adm, style), "DATE"), " with fever, malaise and productive cough for three days."],
        ["Empirical intravenous antibiotics were started and the patient improved steadily."],
        ["Inflammatory markers normalised and oral therapy was tolerated before discharge."],
        ["Follow-up with ", (f"Dr. {doctor}", "PERSON_NAME", "professional"), " at the outpatient clinic in two weeks."],
    ]
    for ln in lines:
        p.segs(MARGIN, y, ln, r)
        y += 40
    y += 30
    p.text(MARGIN, y, "Discharge Medications", hb)
    y += 45
    for med in rng.sample(["Amoxicillin-clavulanate 875 mg PO BID x 5 days", "Acetaminophen 500 mg PO Q6H PRN",
                           "Metformin 500 mg PO BID", "Omeprazole 20 mg PO QD"], 3):
        p.text(MARGIN + 20, y, "- " + med, r)
        y += 38

    y = 1440
    p.hline(y, w=1)
    p.text(MARGIN, y + 40, "Physician Signature:", hb)
    p.signature(MARGIN + 290, y + 25, doctor, rng, role="professional")
    p.text(col2 + 120, y + 40, "Date:", hb)
    p.text(col2 + 200, y + 40, en_date(dis, style), r, cat="DATE")
    p.seal(W - MARGIN - 170, y + 110, "".join(rng.sample("仁心醫院專用章", 4)), size=130, rng=rng)
    p.text(MARGIN, 1680, "CONFIDENTIAL MEDICAL RECORD - Generated synthetic sample for RedactAgent evaluation",
           font(F_EN, 18), fill=(130, 130, 130))
    return p


def t_certificate_zh(doc_id, rng, fzh) -> Page:
    p = Page(doc_id, "medical_certificate_zh", "zh")
    sex = rng.choice("MF")
    name = fzh.name_male() if sex == "M" else fzh.name_female()
    doctor = fzh.name()
    hosp = rng.choice(HOSPITALS_ZH)
    dob = rand_date(rng, 1950, 2002)
    visit = rand_date(rng, 2025, 2026)
    issue = (visit[0], visit[1], min(28, visit[2] + rng.randint(0, 3)))
    t, r, lb = font(F_ZH, 44), font(F_ZH, 28), font(F_ZH, 28)

    p.text(W // 2 - 260, 80, f"{hosp}　診斷證明書", t)
    p.text(W - MARGIN - 300, 150, f"字號：{rng.randint(113, 115)}診字第{rng.randint(10000, 99999)}號", font(F_ZH, 22), fill=(90, 90, 90))
    p.hline(190, w=3)
    # form table
    x0, x1, y0 = MARGIN, W - MARGIN, 210
    rows = 5
    rh = 66
    for i in range(rows + 1):
        p.hline(y0 + i * rh, x0, x1, w=2)
    p.d.line([(x0, y0), (x0, y0 + rows * rh)], fill=(60, 60, 60), width=2)
    p.d.line([(x1, y0), (x1, y0 + rows * rh)], fill=(60, 60, 60), width=2)
    mid = 640
    for i in range(rows - 1):
        p.d.line([(mid, y0 + i * rh), (mid, y0 + (i + 1) * rh)], fill=(60, 60, 60), width=2)
    ty = y0 + 17
    p.field(x0 + 15, ty, "姓　　名：", name, lb, r, "PERSON_NAME", "subject")
    p.field(mid + 15, ty, "性　　別：", "男" if sex == "M" else "女", lb, r)
    ty += rh
    p.field(x0 + 15, ty, "出生日期：", roc_date(dob), lb, r, "DATE_OF_BIRTH")
    p.field(mid + 15, ty, "身分證字號：", tw_national_id(rng, sex), lb, r, "GOV_ID")
    ty += rh
    p.field(x0 + 15, ty, "病歷號碼：", f"{rng.choice('ABCK')}{rng.randint(1000000, 9999999)}", lb, r, "MEDICAL_RECORD_NO")
    p.field(mid + 15, ty, "聯絡電話：", tw_mobile(rng), lb, r, "PHONE")
    ty += rh
    p.field(x0 + 15, ty, "應診日期：", roc_date(visit), lb, r, "DATE")
    p.field(mid + 15, ty, "科　　別：", rng.choice(["新陳代謝科", "骨科", "家庭醫學科", "神經內科"]), lb, r)
    ty += rh
    p.field(x0 + 15, ty, "住　　址：", zh_address(rng), lb, r, "ADDRESS")

    y = y0 + rows * rh + 40
    p.text(MARGIN, y, "診斷病名：", lb)
    dx = rng.choice(["第二型糖尿病併周邊神經病變", "腰椎椎間盤突出併坐骨神經痛", "右側踝關節扭傷", "偏頭痛，無預兆"])
    p.text(MARGIN + 160, y, dx, r)
    y += 80
    p.text(MARGIN, y, "醫師囑言：", lb)
    y += 55
    lines = [
        ["病人", (name, "PERSON_NAME", "subject"), "於", (roc_date(visit), "DATE"), "至本院門診就診，"],
        ["經檢查後診斷如上。病人", (rng.choice(QUASI_ZH), "QUASI_IDENTIFIER", "subject"), "，"],
        ["因工作性質需長時間站立，建議休養十四日，並於兩週後回診追蹤。"],
        ["期間宜避免負重與長時間行走，如症狀加劇應立即返院就醫。"],
        ["（以下空白）"],
    ]
    for ln in lines:
        p.segs(MARGIN + 30, y, ln, r)
        y += 52
    y = 1180
    p.text(MARGIN, y, "上述病人經本院醫師診斷屬實，特此證明。", r)
    y += 90
    bb = p.field(MARGIN, y, "診治醫師：", doctor, lb, r, "PERSON_NAME", "professional")
    p.seal(bb[2] + 30, y - 40, (doctor + "印")[:4], size=118, rng=rng)
    p.text(MARGIN, y + 90, "醫師證書字號：", lb)
    p.text(MARGIN + 210, y + 90, f"醫字第{rng.randint(10000, 99999)}號", r)
    p.seal(W - MARGIN - 230, y - 60, hosp[:4] + "證明專用", size=200, round_=True, rng=rng)
    p.text(W // 2 - 260, 1560, "中華民國", r)
    p.text(W // 2 - 140, 1560, f"{issue[0] - 1911}年{issue[1]}月{issue[2]}日", r, cat="DATE")
    p.text(MARGIN, 1680, "本文件為 RedactAgent 測試用合成樣本，所有人名、編號與地址皆為隨機產生。", font(F_ZH, 18), fill=(130, 130, 130))
    return p


def t_lease_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "lease_agreement_en", "en")
    landlord, _ = roman_name(rng)
    tenant = fen.name()
    witness, _ = roman_name(rng)
    made = rand_date(rng, 2025, 2026)
    start = (made[0], made[1], 1)
    end = (made[0] + 1, made[1], 1)
    style = rng.randint(0, 2)
    t, r, hb = font(F_SERIF_B, 40), font(F_SERIF, 27), font(F_SERIF_B, 27)

    p.text(W // 2 - 300, 80, "RESIDENTIAL LEASE AGREEMENT", t)
    p.hline(140, w=2)
    y = 175
    lines = [
        ["This Lease Agreement is made on ", (en_date(made, style), "DATE"), " by and between:"],
        ["LANDLORD: ", (landlord, "PERSON_NAME", "party"), ", National ID No. ", (tw_national_id(rng, rng.choice("MF")), "GOV_ID"), ","],
        ["residing at ", (en_address(rng), "ADDRESS"), ";"],
        ["TENANT: ", (tenant, "PERSON_NAME", "party"), ", Passport No. ", (f"{rng.choice('ABCX')}{rng.randint(10000000, 99999999)}", "GOV_ID"), ","],
        ["phone ", (tw_mobile(rng), "PHONE"), ", e-mail ", (f"{tenant.split()[0].lower()}.{tenant.split()[-1].lower()}@example.com", "EMAIL"), "."],
    ]
    for ln in lines:
        p.segs(MARGIN, y, ln, r)
        y += 46
    y += 20
    clauses = [
        ("1. PREMISES.", [["The Landlord leases to the Tenant the apartment located at"], [(en_address(rng), "ADDRESS"), " (the \"Premises\")."]]),
        ("2. TERM.", [["The lease begins on ", (en_date(start, style), "DATE"), " and ends on ", (en_date(end, style), "DATE"), "."]]),
        ("3. RENT.", [[f"Monthly rent is NT$ {rng.choice([18, 22, 25, 28, 32, 36])},000, payable on the 5th day of each month"],
                      ["by wire transfer to the Landlord's account ", (bank_account(rng), "FINANCIAL_ACCOUNT"), "."]]),
        ("4. DEPOSIT.", [["A security deposit equal to two months' rent is due upon signing and will be returned"],
                         ["within 30 days after the Tenant vacates, less any lawful deductions for damage."]]),
        ("5. USE.", [["The Premises shall be used solely as a private residence. No subletting without the"],
                     ["prior written consent of the Landlord. Pets are not permitted."]]),
        ("6. GOVERNING LAW.", [["This Agreement is governed by the laws of Taiwan (R.O.C.). Disputes shall be submitted"],
                               ["to the district court having jurisdiction over the Premises."]]),
    ]
    for head, body in clauses:
        p.text(MARGIN, y, head, hb)
        y += 42
        for ln in body:
            p.segs(MARGIN + 30, y, ln, r)
            y += 40
        y += 14
    y = 1330
    p.hline(y, w=1)
    y += 30
    p.text(MARGIN, y, "LANDLORD", hb)
    p.text(660, y, "TENANT", hb)
    p.signature(MARGIN, y + 45, landlord, rng, role="party")
    p.signature(660, y + 45, tenant, rng, role="party")
    p.text(MARGIN, y + 140, "Signature", font(F_SERIF, 22), fill=(110, 110, 110))
    p.text(660, y + 140, "Signature", font(F_SERIF, 22), fill=(110, 110, 110))
    y += 200
    bb = p.text(MARGIN, y, "WITNESS: ", hb)
    p.text(bb[2] + 8, y, witness, r, cat="PERSON_NAME", role="witness")
    p.text(MARGIN, 1680, "Synthetic sample generated for RedactAgent evaluation - all names and numbers are fictitious.",
           font(F_SERIF, 18), fill=(130, 130, 130))
    return p


def t_police_zh(doc_id, rng, fzh) -> Page:
    p = Page(doc_id, "accident_report_zh", "zh")
    a_sex, b_sex = rng.choice("MF"), rng.choice("MF")
    a = fzh.name_male() if a_sex == "M" else fzh.name_female()
    b = fzh.name_male() if b_sex == "M" else fzh.name_female()
    wit = fzh.name()
    officer = fzh.name()
    when = rand_date(rng, 2025, 2026)
    hh, mm = rng.randint(6, 22), rng.randint(0, 59)
    pa, pb = plate(rng), plate(rng)
    t, r, lb = font(F_ZH, 40), font(F_ZH, 26), font(F_ZH, 26)

    p.text(W // 2 - 330, 70, "濱海市政府警察局　道路交通事故登記聯單", t)
    p.text(MARGIN, 140, f"案號：{when[0] - 1911}交字第{rng.randint(1000, 9999)}號", font(F_ZH, 22), fill=(90, 90, 90))
    p.hline(180, w=3)
    y = 205
    bb = p.text(MARGIN, y, "發生時間：", lb)
    p.text(bb[2] + 8, y, f"{roc_date(when)} {hh:02d}時{mm:02d}分", r, cat="DATE")
    y += 50
    p.field(MARGIN, y, "發生地點：", f"{rng.choice(ZH_ROADS)}與{rng.choice(ZH_ROADS)}交岔路口", lb, r)
    y += 70

    def party(y, label, nm, sx, pl):
        p.box([MARGIN, y, W - MARGIN, y + 250], w=2)
        p.text(MARGIN + 15, y + 15, label, font(F_ZH, 28))
        yy = y + 65
        p.field(MARGIN + 15, yy, "姓名：", nm, lb, r, "PERSON_NAME", "party")
        p.field(560, yy, "身分證字號：", tw_national_id(rng, sx), lb, r, "GOV_ID")
        yy += 45
        p.field(MARGIN + 15, yy, "出生日期：", slash_date(rand_date(rng, 1960, 2004)), lb, r, "DATE_OF_BIRTH")
        p.field(560, yy, "聯絡電話：", tw_mobile(rng), lb, r, "PHONE")
        yy += 45
        p.field(MARGIN + 15, yy, "車牌號碼：", pl, lb, r, "LICENSE_PLATE")
        p.field(560, yy, "車種：", rng.choice(["自用小客車", "普通重型機車", "營業小貨車"]), lb, r)
        yy += 45
        p.field(MARGIN + 15, yy, "住址：", zh_address(rng), lb, r, "ADDRESS")
        return y + 270

    y = party(y, "當事人（甲）", a, a_sex, pa)
    y = party(y, "當事人（乙）", b, b_sex, pb)
    bb = p.field(MARGIN, y, "目擊證人：", wit, lb, r, "PERSON_NAME", "witness")
    p.field(bb[2] + 40, y, "電話：", tw_landline(rng), lb, r, "PHONE")
    y += 70
    p.text(MARGIN, y, "事故經過摘要：", lb)
    y += 50
    lines = [
        ["甲車（", (pa, "LICENSE_PLATE"), "）由", (a, "PERSON_NAME", "party"), "駕駛，沿幹道直行，"],
        ["行經路口時與自支線道左轉之乙車（", (pb, "LICENSE_PLATE"), "）發生碰撞。"],
        ["乙車駕駛", (b, "PERSON_NAME", "party"), "表示當時號誌為綠燈，甲車駕駛則稱其未注意來車。"],
        ["雙方均無明顯外傷，車輛前保險桿受損，現場已拍照存證並繪製現場圖。"],
    ]
    for ln in lines:
        p.segs(MARGIN + 30, y, ln, r)
        y += 46
    y = 1450
    p.hline(y, w=1)
    bb = p.field(MARGIN, y + 40, "處理員警：", officer, lb, r, "PERSON_NAME", "professional")
    p.seal(bb[2] + 30, y + 10, (officer + "印")[:4], size=110, rng=rng)
    bb = p.text(700, y + 40, "填單日期：", lb)
    p.text(bb[2] + 8, y + 40, roc_date(when), r, cat="DATE")
    p.text(MARGIN, 1680, "本文件為 RedactAgent 測試用合成樣本，所有人名、編號與地址皆為隨機產生。", font(F_ZH, 18), fill=(130, 130, 130))
    return p


def t_claim_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "insurance_claim_en", "en")
    name, surname = roman_name(rng)
    sex = rng.choice("MF")
    dob = rand_date(rng, 1955, 2003)
    tx = rand_date(rng, 2025, 2026)
    signed = (tx[0], tx[1], min(28, tx[2] + rng.randint(1, 6)))
    t, lbl, hand = font(F_EN_B, 36), font(F_EN, 21), font(F_HAND, 32)
    ink = (20, 35, 120)

    p.text(MARGIN, 70, "HARBOR MUTUAL LIFE & HEALTH", font(F_EN_B, 24), fill=(20, 80, 60))
    p.text(MARGIN, 105, "MEDICAL EXPENSE CLAIM FORM", t)
    p.field(W - MARGIN - 300, 112, "Policy No.", f"HM-{rng.randint(1000000, 9999999)}", font(F_EN, 24), font(F_EN, 24),
            "FINANCIAL_ACCOUNT", gap=8)
    p.hline(165, w=3)
    p.text(MARGIN, 180, "PART A - CLAIMANT DETAILS (please print clearly)", font(F_EN_B, 22))

    def cell(x, y, w, label, value, cat=None, role=None, h=88):
        p.box([x, y, x + w, y + h], w=2, outline=(120, 120, 120))
        p.text(x + 10, y + 6, label, lbl, fill=(90, 90, 90))
        if value:
            p.text(x + 14, y + 38, value, hand, fill=ink, cat=cat, role=role)

    y = 220
    full = W - 2 * MARGIN
    half = full // 2
    cell(MARGIN, y, half, "Full name of claimant", name, "PERSON_NAME", "subject")
    cell(MARGIN + half, y, half, "Date of birth (DD/MM/YYYY)", f"{dob[2]:02d}/{dob[1]:02d}/{dob[0]}", "DATE_OF_BIRTH")
    y += 88
    cell(MARGIN, y, half, "National ID / ARC No.", tw_national_id(rng, sex), "GOV_ID")
    cell(MARGIN + half, y, half, "Mobile phone", tw_mobile(rng), "PHONE")
    y += 88
    first = name.split(" ")[1].split("-")[0].lower()
    cell(MARGIN, y, full, "E-mail", f"{first}{surname.lower()}{rng.randint(10, 99)}@mail.example.tw", "EMAIL")
    y += 88
    cell(MARGIN, y, full, "Residential address", en_address(rng), "ADDRESS")
    y += 120
    p.text(MARGIN, y, "PART B - TREATMENT DETAILS", font(F_EN_B, 22))
    y += 40
    cell(MARGIN, y, half, "Hospital / clinic", rng.choice(HOSPITALS_EN))
    cell(MARGIN + half, y, half, "Date of treatment", en_date(tx, 1), "DATE")
    y += 88
    cell(MARGIN, y, half, "Diagnosis", rng.choice(["Fractured wrist", "Appendicitis", "Dengue fever", "Kidney stones"]))
    cell(MARGIN + half, y, half, "Amount claimed (NT$)", f"{rng.randint(8, 95)},{rng.randint(100, 999)}")
    y += 120
    p.text(MARGIN, y, "PART C - PAYMENT", font(F_EN_B, 22))
    y += 40
    cell(MARGIN, y, full, "Reimburse to credit card number", luhn_card(rng), "FINANCIAL_ACCOUNT")
    y += 120
    p.text(MARGIN, y, "PART D - DECLARATION", font(F_EN_B, 22))
    y += 40
    decl = [
        "I declare that the information given in this form is true and complete. I authorise any",
        "physician, hospital or other provider to release to the insurer information about my",
        "medical history and treatment that is relevant to this claim.",
    ]
    for ln in decl:
        p.text(MARGIN, y, ln, font(F_EN, 23))
        y += 36
    y += 40
    p.box([MARGIN, y, MARGIN + half, y + 130], w=2, outline=(120, 120, 120))
    p.text(MARGIN + 10, y + 6, "Signature of claimant", lbl, fill=(90, 90, 90))
    p.signature(MARGIN + 30, y + 40, name, rng, role="subject")
    cell(MARGIN + half, y, half, "Date", en_date(signed, 1), "DATE", h=130)
    p.text(MARGIN, 1680, "Synthetic sample generated for RedactAgent evaluation - all names and numbers are fictitious.",
           font(F_EN, 18), fill=(130, 130, 130))
    return p


def t_hr_zh(doc_id, rng, fzh) -> Page:
    p = Page(doc_id, "employee_form_zh", "zh")
    sex = rng.choice("MF")
    name = fzh.name_male() if sex == "M" else fzh.name_female()
    en_name, _ = roman_name(rng)
    mom = fzh.name_female()
    dob = rand_date(rng, 1975, 2003)
    join = rand_date(rng, 2025, 2026)
    company = rng.choice(COMPANIES_ZH)
    t, r, lb = font(F_ZH, 42), font(F_ZH, 27), font(F_ZH, 26)

    p.text(MARGIN, 80, company, font(F_ZH, 28), fill=(20, 60, 120))
    p.text(MARGIN, 125, "新進員工基本資料表", t)
    p.hline(195, w=3)
    p.photo(W - MARGIN - 220, 220, rng=rng)
    y = 230
    rows = [
        ("中文姓名：", name, "PERSON_NAME", "subject"),
        ("英文姓名：", en_name, "PERSON_NAME", "subject"),
        ("身分證字號：", tw_national_id(rng, sex), "GOV_ID", None),
        ("出生日期：", slash_date(dob), "DATE_OF_BIRTH", None),
        ("行動電話：", tw_mobile(rng), "PHONE", None),
        ("電子郵件：", f"{en_name.split()[1].replace('-', '').lower()}.{en_name.split()[0].lower()}@mail.example.tw", "EMAIL", None),
    ]
    for label, val, cat, role in rows:
        p.field(MARGIN, y, label, val, lb, r, cat, role)
        p.hline(y + 44, MARGIN, W - MARGIN - 250, w=1, fill=(170, 170, 170))
        y += 58
    y += 30
    p.field(MARGIN, y, "戶籍地址：", zh_address(rng), lb, r, "ADDRESS")
    p.hline(y + 44, w=1, fill=(170, 170, 170))
    y += 58
    p.field(MARGIN, y, "通訊地址：", zh_address(rng), lb, r, "ADDRESS")
    p.hline(y + 44, w=1, fill=(170, 170, 170))
    y += 58
    p.field(MARGIN, y, "薪資轉帳帳戶：", bank_account(rng), lb, r, "FINANCIAL_ACCOUNT")
    p.hline(y + 44, w=1, fill=(170, 170, 170))
    y += 58
    bb = p.field(MARGIN, y, "緊急聯絡人：", mom, lb, r, "PERSON_NAME", "family")
    bb = p.field(bb[2] + 30, y, "關係：", "母親", lb, r)
    p.field(bb[2] + 30, y, "電話：", tw_mobile(rng), lb, r, "PHONE")
    p.hline(y + 44, w=1, fill=(170, 170, 170))
    y += 58
    p.field(MARGIN, y, "到職日期：", slash_date(join), lb, r, "DATE")
    p.field(640, y, "部門：", rng.choice(["研發部", "業務部", "財務部", "製造部"]), lb, r)
    p.hline(y + 44, w=1, fill=(170, 170, 170))
    y += 100
    p.text(MARGIN, y, "學經歷摘要：", lb)
    y += 50
    for ln in [
        "國立大學資訊工程學系畢業，曾任軟體工程師三年，熟悉後端系統開發與雲端部署。",
        "具備專案管理經驗，曾帶領五人團隊完成企業內部系統導入。",
    ]:
        p.text(MARGIN + 30, y, ln, r)
        y += 46
    y += 50
    p.text(MARGIN, y, "本人保證以上資料均屬實，並同意公司依個人資料保護法蒐集、處理及利用。", r)
    y += 90
    p.text(MARGIN, y + 20, "本人簽名：", lb)
    p.signature(MARGIN + 160, y, en_name, rng, role="subject")
    bb = p.text(700, y + 20, "填表日期：", lb)
    p.text(bb[2] + 8, y + 20, slash_date(join), r, cat="DATE")
    p.text(MARGIN, 1680, "本文件為 RedactAgent 測試用合成樣本，所有人名、編號與地址皆為隨機產生。", font(F_ZH, 18), fill=(130, 130, 130))
    return p


TEMPLATES = [
    ("discharge_summary_en", t_discharge_en, "en"),
    ("medical_certificate_zh", t_certificate_zh, "zh"),
    ("lease_agreement_en", t_lease_en, "en"),
    ("accident_report_zh", t_police_zh, "zh"),
    ("insurance_claim_en", t_claim_en, "en"),
    ("employee_form_zh", t_hr_zh, "zh"),
]

# --------------------------------------------------------------------------------------
# "Scanner" degradation with ground-truth box transform
# --------------------------------------------------------------------------------------


def scan(p: Page, rng: random.Random, strength: float = 1.0) -> tuple[Image.Image, list[dict]]:
    angle = rng.uniform(-0.8, 0.8) * strength
    img = p.img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    # transform boxes: PIL rotates counter-clockwise around the centre
    cx, cy = W / 2, H / 2
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    items = []
    for it in p.items:
        x0, y0, x1, y1 = it["bbox"]
        pts = []
        for x, y in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]:
            dx, dy = x - cx, y - cy
            pts.append((cx + dx * ca + dy * sa, cy - dx * sa + dy * ca))
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        items.append({**it, "bbox": [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]})
    arr = np.asarray(img).astype(np.float32)
    tint = np.array([rng.uniform(244, 252), rng.uniform(240, 248), rng.uniform(228, 240)]) / 255.0
    arr = arr * tint
    arr += np.random.default_rng(rng.randint(0, 10**9)).normal(0, 6 * strength, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(0.5 * strength))
    return img, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-template", type=int, default=6)
    ap.add_argument("--out", default="data/synthetic")
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()

    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "gt").mkdir(parents=True, exist_ok=True)
    index = []
    for ti, (tname, fn, lang) in enumerate(TEMPLATES):
        for k in range(args.n_per_template):
            seed = args.seed * 1000 + ti * 100 + k
            rng = random.Random(seed)
            fk = Faker("zh_TW" if lang == "zh" else "en_US")
            fk.seed_instance(seed)
            doc_id = f"{tname}_{k:02d}"
            page = fn(doc_id, rng, fk)
            img, items = scan(page, rng)
            img.save(out / "images" / f"{doc_id}.jpg", quality=88)
            gt = {"id": doc_id, "template": tname, "lang": lang, "width": W, "height": H, "items": items}
            (out / "gt" / f"{doc_id}.json").write_text(json.dumps(gt, ensure_ascii=False, indent=1))
            index.append({"id": doc_id, "template": tname, "lang": lang, "n_pii": len(items)})
            print(f"{doc_id}: {len(items)} PII items")
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(f"\n{len(index)} documents, {sum(i['n_pii'] for i in index)} PII items -> {out}")


if __name__ == "__main__":
    main()
