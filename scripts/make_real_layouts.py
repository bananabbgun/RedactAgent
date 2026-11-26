"""Real-layout check: public government forms filled with synthetic people.

The forms are real (published by Taiwan's Ministry of Health and Welfare, the US Department of Veterans Affairs and
the US Centers for Medicare & Medicaid Services); every person, number, address and date written into them is
randomly generated. Neither the forms nor these fill-ins were seen while RedactAgent was developed, so this corpus
checks whether the engine generalises beyond the layouts of our own generators. Ground truth is recorded while
drawing, in the same format as data/synthetic*.

Backgrounds: data/real_layouts/templates/*.png, rendered at 150 dpi from data/real_layouts/raw/ (see the README there).

    python scripts/make_real_layouts.py --out data/real_layouts/corpus
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from faker import Faker
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_synthetic import F_HAND, F_ZH, Page, font, tw_mobile, tw_national_id  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "data" / "real_layouts" / "templates"
F_TYPE = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"
INK = (25, 35, 120)      # handwriting
TYPED = (20, 20, 20)

# Quasi-identifiers that appear in no prompt and in none of the v1/v2/v3 corpora.
QUASI_ZH_RL = ["為馬祖東引唯一的中醫師", "是澎湖七美鄉唯一的獸醫", "為該校唯一的視障物理教師"]

ZH_HOSP = [("康寧紀念醫院", "臺北市內湖區成功路二段312號", "(02)2799-1100"),
           ("仁和綜合醫院", "新北市板橋區文化路一段188號", "(02)2963-5200"),
           ("安心聯合醫院", "臺中市西屯區台灣大道四段966號", "(04)2358-3300")]
US_FACILITY = [("VA Riverside Health Care Facility", "1200 Lakeview Dr, Springfield, IL 62702"),
               ("VA Northbridge Medical Center", "88 Commonwealth Ave, Bedford, MA 01730")]
US_CLINIC = [("Lakeshore Orthopedics", "455 Harbor St, Racine, WI 53403"),
             ("Brightwater Family Practice", "2101 Elm Ave, Dayton, OH 45402")]


def page_on(template: str, doc_id: str, lang: str) -> Page:
    img = Image.open(TPL / f"{template}.png").convert("RGB")
    return Page(doc_id, template, lang, img=img)


def check(p: Page, x, y, size=24):
    p.d.text((x, y), "✓", font=font(F_ZH, size), fill=INK)


def union(p: Page, start: int, cat: str, role=None):
    """Merge the items drawn since `start` (e.g. year, month, day written into separate blanks) into one item."""
    parts = p.items[start:]
    del p.items[start:]
    x0 = min(i["bbox"][0] for i in parts); y0 = min(i["bbox"][1] for i in parts)
    x1 = max(i["bbox"][2] for i in parts); y1 = max(i["bbox"][3] for i in parts)
    p.items.append({"cat": cat, "text": " ".join(i["text"] for i in parts), "bbox": [x0, y0, x1, y1], "role": role})


def ymd_blanks(p: Page, xs, y, d, f, cat, role=None, roc=True, fill=TYPED):
    start = len(p.items)
    yy, mm, dd = d
    for x, v in zip(xs, [yy - 1911 if roc else yy, mm, dd]):
        p.text(x, y, str(v), f, cat="TMP", fill=fill)
    union(p, start, cat, role)


def rdate(rng, y0, y1):
    return rng.randint(y0, y1), rng.randint(1, 12), rng.randint(1, 28)


def zh_name(fk: Faker) -> str:
    while True:
        n = fk.name()
        if 2 <= len(n) <= 3:
            return n


# ----------------------------------------------------------------------------------------------------------------
# Taiwan NHI referral form (MOHW, 全民健康保險院(所)轉診單)
# ----------------------------------------------------------------------------------------------------------------

def nhi_referral(doc_id, rng, fk, k) -> Page:
    p = page_on("nhi_referral_zh", doc_id, "zh")
    f, fs = font(F_ZH, 22), font(F_ZH, 19)
    sex = rng.choice("MF")
    name, relative, doctor, doctor2 = zh_name(fk), zh_name(fk), zh_name(fk), zh_name(fk)
    hosp, hosp_addr, hosp_tel = ZH_HOSP[k % 3]
    to_hosp = ZH_HOSP[(k + 1) % 3][0]
    p.text(405, 158, f"{rng.randint(1101000000, 1199999999)}", f)               # facility code (organisation)
    p.text(840, 100, to_hosp[:4], font(F_ZH, 26))
    p.text(186, 233, name, f, cat="PERSON_NAME", role="subject")
    check(p, 354 if sex == "M" else 438, 230)
    ymd_blanks(p, [622, 703, 778], 233, rdate(rng, 1940, 2005), f, "DATE_OF_BIRTH", "subject")
    p.text(893, 233, tw_national_id(rng, sex), f, cat="GOV_ID", role="subject")
    p.text(186, 305, relative, f, cat="PERSON_NAME", role="relative")
    p.text(333, 307, tw_mobile(rng), fs, cat="PHONE")
    addr = f"{fk.city()}{fk.street_name()}{rng.randint(1, 300)}號{rng.randint(2, 15)}樓"
    p.text(516, 307, addr, fs, cat="ADDRESS")
    p.text(186, 405, "主訴：右膝疼痛三個月，上下樓梯困難，夜間加劇。", fs)
    if k % 2 == 0:
        p.segs(186, 438, ["病人", (rng.choice(QUASI_ZH_RL), "QUASI_IDENTIFIER", "subject"), "，工作需久站。"], fs)
    else:
        p.text(186, 438, "保守治療六週效果不佳，建議進一步評估。", fs)
    p.text(870, 405, rng.choice(["無", "Penicillin", "NSAIDs"]), fs)
    p.text(420, 528, "M17.11", fs); p.text(700, 528, "右側原發性膝關節炎", fs)
    p.text(215, 560, "M25.561", fs); p.text(700, 560, "右膝疼痛", fs)
    ex = rdate(rng, 2025, 2026)
    p.text(250, 688, f"{ex[0] - 1911}/{ex[1]:02d}/{ex[2]:02d}", fs, cat="DATE")
    p.text(250, 706, "X光：右膝內側關節腔狹窄，骨刺形成。", fs)
    p.text(930, 655, "Celecoxib 200mg", fs)
    md = rdate(rng, 2025, 2026)
    p.text(715, 688, f"{md[0] - 1911}/{md[1]:02d}/{md[2]:02d}", fs, cat="DATE")
    check(p, 418, 744); p.text(692, 738, "MRI", fs)
    p.text(186, 835, hosp_addr, fs)                                             # organisation address
    p.text(852, 835, hosp_tel[:-2] + "99", fs)
    p.text(852, 862, "referral@" + ["kangning", "renhe", "anxin"][k % 3] + "-hosp.org.tw", font(F_ZH, 16))
    p.text(220, 912, doctor, f, cat="PERSON_NAME", role="professional")
    p.text(392, 912, "骨科", fs)
    p.text(603, 896, hosp_tel, font(F_ZH, 15)); p.text(603, 920, f"#{rng.randint(1000, 8999)}", font(F_ZH, 15))
    p.seal(860, 884, doctor + "印", size=58, rng=rng)
    od = rdate(rng, 2026, 2026)
    ymd_blanks(p, [212, 318, 418], 970, od, f, "DATE")
    ap = rdate(rng, 2026, 2026)
    ymd_blanks(p, [728, 868, 1018], 962, ap, fs, "DATE")
    p.text(226, 1020, to_hosp[:4], fs); p.text(455, 1020, "骨科", fs)
    p.text(608, 1020, doctor2, fs, cat="PERSON_NAME", role="professional")
    to_addr = ZH_HOSP[(k + 1) % 3][1]; p.text(950, 1020, to_addr[:9], font(F_ZH, 15)); p.text(950, 1040, to_addr[9:], font(F_ZH, 15))
    p.text(950, 1070, ZH_HOSP[(k + 1) % 3][2], fs)
    p.text(232, 1098, f"{od[0] - 1911 + 0}/{min(12, od[1] + 3):02d}/{od[2]:02d}", fs, cat="DATE")
    if k % 3 == 2:   # the receiving hospital has filled in its reply
        check(p, 243, 1188); p.text(455, 1203, "7B", fs)
        p.text(400, 1350, "M17.11", fs); p.text(290, 1382, "右膝退化性關節炎，已安排全膝置換術。", fs)
        p.text(225, 1415, to_hosp, fs); p.text(865, 1415, ZH_HOSP[(k + 1) % 3][2], fs)
        p.text(250, 1505, doctor2, f, cat="PERSON_NAME", role="professional")
        p.seal(650, 1474, doctor2 + "印", size=54, rng=rng)
        ymd_blanks(p, [840, 935, 1020], 1500, rdate(rng, 2026, 2026), fs, "DATE")
    return p


# ----------------------------------------------------------------------------------------------------------------
# US VA Form 10-5345 (Request for and authorization to release health information), pages 1 and 2
# ----------------------------------------------------------------------------------------------------------------

def us_person(fk: Faker):
    first, last, mid = fk.first_name(), fk.last_name(), fk.random_uppercase_letter()
    return first, last, mid


def us_date(d):
    return f"{d[1]:02d}/{d[2]:02d}/{d[0]}"


def va_p1(doc_id, rng, fk, k) -> Page:
    p = page_on("va_release_p1_en", doc_id, "en")
    h, hs = font(F_HAND, 30), font(F_HAND, 26)
    first, last, mid = us_person(fk)
    fac, fac_addr = US_FACILITY[k % 2]
    p.text(100, 372, f"{fac}, {fac_addr}", hs, fill=INK)
    p.text(100, 486, f"{last}, {first} {mid}", h, cat="PERSON_NAME", role="subject", fill=INK)
    p.text(928, 486, us_date(rdate(rng, 1942, 1990)), h, cat="DATE_OF_BIRTH", role="subject", fill=INK)
    p.text(100, 560, fk.street_address(), h, cat="ADDRESS", fill=INK)
    p.text(100, 594, f"{fk.city()}, {fk.state_abbr()} {fk.zipcode()}", h, cat="ADDRESS", fill=INK)
    clinic, clinic_addr = US_CLINIC[k % 2]
    dr_first, dr_last, _ = us_person(fk)
    x = p.segs(100, 655, [("Dr. ", None, None), (f"{dr_first} {dr_last}", "PERSON_NAME", "professional"),
                          (f", {clinic}, {clinic_addr}", None, None)], hs, fill=INK)
    check(p, 97, 740, 28)
    a, b = rdate(rng, 2024, 2025), rdate(rng, 2025, 2026)
    check(p, 97, 890, 28)
    p.segs(462, 885, [(us_date(a), "DATE"), " - ", (us_date(b), "DATE")], hs, fill=INK)
    check(p, 134, 1040, 28)
    p2_first, p2_last, _ = us_person(fk)
    p.segs(552, 1035, [("Dr. ", None, None), (f"{p2_first} {p2_last}", "PERSON_NAME", "professional"),
                       (", ", None, None), (us_date(rdate(rng, 2025, 2025)), "DATE")], hs, fill=INK)
    if k % 2:
        check(p, 97, 1153, 28); check(p, 134, 1190, 28)
        p.segs(445, 1185, [("HbA1c, lipid panel, ", None, None), (us_date(rdate(rng, 2025, 2026)), "DATE")], hs, fill=INK)
    return p


def va_p2(doc_id, rng, fk, k) -> Page:
    p = page_on("va_release_p2_en", doc_id, "en")
    h, hs, t = font(F_HAND, 30), font(F_HAND, 26), font(F_TYPE, 20)
    first, last, mid = us_person(fk)
    p.text(100, 104, f"{last}, {first} {mid}", h, cat="PERSON_NAME", role="subject", fill=INK)
    p.text(928, 104, us_date(rdate(rng, 1942, 1990)), h, cat="DATE_OF_BIRTH", role="subject", fill=INK)
    if k % 2 == 0:
        check(p, 97, 682, 28)
    else:
        check(p, 97, 718, 28)
        p.text(358, 706, us_date(rdate(rng, 2027, 2027)), hs, cat="DATE", fill=INK)
    signed = rdate(rng, 2026, 2026)
    if k % 2 == 0:   # the patient signs
        p.signature(110, 838, f"{first} {last}", rng, role="subject", size=40)
        p.text(915, 848, us_date(signed), h, cat="DATE", fill=INK)
    else:            # a legal representative signs for the patient
        rf, rl, _ = us_person(fk)
        p.signature(110, 912, f"{rf} {rl}", rng, role="relative", size=40)
        p.text(915, 922, us_date(signed), h, cat="DATE", fill=INK)
        p.text(100, 990, f"{rf} {last if rng.random() < 0.6 else rl}", h, cat="PERSON_NAME", role="relative", fill=INK)
        p.text(752, 990, rng.choice(["Daughter", "Son", "Spouse", "Guardian"]), h, fill=INK)
    p.text(100, 1090, "Inpatient discharge summary and progress notes, 18 pages.", t)
    p.text(360, 1514, us_date(rdate(rng, 2026, 2026)), t, cat="DATE")
    sf, sl, _ = us_person(fk)
    p.text(700, 1514, f"{sf[0]}. {sl}, ROI Unit", t)
    p.items.append({"cat": "PERSON_NAME", "text": f"{sf[0]}. {sl}",
                    "bbox": list(p.d.textbbox((700, 1514), f"{sf[0]}. {sl}", font=t)), "role": "professional"})
    return p


# ----------------------------------------------------------------------------------------------------------------
# US CMS-1500 health insurance claim form (the public copy carries a SAMPLE watermark; it is kept as published)
# ----------------------------------------------------------------------------------------------------------------

def cms1500(doc_id, rng, fk, k) -> Page:
    p = page_on("cms1500_en", doc_id, "en")
    t = font(F_TYPE, 21)
    first, last, mid = us_person(fk)
    mbi = f"{rng.randint(1, 9)}{rng.choice('ACDEFGHJKMNPQRTUVWXY')}{rng.choice('ACDEFGHJKMNPQRTUVWXY0123456789')}{rng.randint(0, 9)}" \
          f"{rng.choice('ACDEFGHJKMNPQRTUVWXY')}{rng.choice('ACDEFGHJKMNPQRTUVWXY0123456789')}{rng.randint(0, 9)}" \
          f"{rng.choice('ACDEFGHJKMNPQRTUVWXY')}{rng.choice('ACDEFGHJKMNPQRTUVWXY')}{rng.randint(0, 9)}{rng.randint(0, 9)}"
    p.text(868, 298, mbi, t, cat="HEALTH_INSURANCE_NO", role="subject")
    p.text(133, 344, f"{last.upper()}, {first.upper()}, {mid}", t, cat="PERSON_NAME", role="subject")
    b = rdate(rng, 1940, 1960)
    p.text(578, 348, f"{b[1]:02d}  {b[2]:02d}  {b[0]}", t, cat="DATE_OF_BIRTH", role="subject")
    p.text(746 if rng.random() < 0.5 else 820, 346, "X", t)
    p.text(868, 344, f"{last.upper()}, {first.upper()}", t, cat="PERSON_NAME", role="subject")
    p.text(133, 392, fk.street_address().upper(), t, cat="ADDRESS")
    p.text(133, 444, fk.city().upper(), t, cat="ADDRESS"); p.text(512, 444, fk.state_abbr(), t)
    p.text(133, 497, fk.zipcode(), t, cat="ADDRESS")
    ph = f"{rng.randint(201, 989)}"
    p.segs(345, 497, [(ph, "PHONE"), ("  ", None), (f"{rng.randint(200, 999)}-{rng.randint(1000, 9999)}", "PHONE")], t)
    union(p, len(p.items) - 2, "PHONE")
    p.text(612, 396, "X", t)
    p.text(210, 846, "SIGNATURE ON FILE", t); p.text(950, 846, "SIGNATURE ON FILE", t)
    a = rdate(rng, 2026, 2026)
    p.text(925, 955, f"{a[1]:02d} {a[2]:02d} {a[0] % 100:02d}", t, cat="DATE")
    p.text(1135, 955, f"{a[1]:02d} {min(28, a[2] + 3):02d} {a[0] % 100:02d}", t, cat="DATE")
    for i, (cpt, chg) in enumerate([("99223", "450 00"), ("99232", "180 00")]):
        y = 1204 + 50 * i
        p.text(130, y, f"{a[1]:02d} {min(28, a[2] + i):02d} {a[0] % 100:02d}", t, cat="DATE")
        p.text(395, y, "21", t); p.text(500, y, cpt, t); p.text(800, y, "A", t)
        p.text(880, y, chg, t); p.text(1015, y, "1", t); p.text(1135, y, f"{rng.randint(10**9, 2 * 10**9 - 1)}", t)
    p.text(135, 1498, f"{rng.randint(10, 99)}-{rng.randint(1000000, 9999999)}", t); p.text(410, 1500, "X", t)
    p.text(462, 1498, f"PT{rng.randint(100000, 999999)}", t, cat="MEDICAL_RECORD_NO", role="subject")
    p.text(690, 1500, "X", t); p.text(890, 1498, "630 00", t)
    df, dl, _ = us_person(fk)
    p.signature(140, 1588, f"{df} {dl} MD", rng, role="professional", size=34)
    p.text(410, 1628, f"{a[1]:02d}/{min(28, a[2] + 4):02d}/{a[0]}", font(F_TYPE, 17), cat="DATE")
    clinic, clinic_addr = US_CLINIC[k % 2]
    p.text(462, 1555, clinic.upper(), font(F_TYPE, 17)); p.text(462, 1578, clinic_addr.upper(), font(F_TYPE, 15))
    p.text(868, 1555, clinic.upper(), font(F_TYPE, 17)); p.text(868, 1578, clinic_addr.upper(), font(F_TYPE, 15))
    p.text(1105, 1527, f"{rng.randint(201, 989)} {rng.randint(200, 999)}-{rng.randint(1000, 9999)}", font(F_TYPE, 17))
    return p


TEMPLATES = [("nhi_referral_zh", nhi_referral, "zh", 6), ("va_release_p1_en", va_p1, "en", 4),
             ("va_release_p2_en", va_p2, "en", 4), ("cms1500_en", cms1500, "en", 4)]


def scan(p: Page, rng: random.Random) -> tuple[Image.Image, list[dict]]:
    """Same light 'scanner' as the other corpora: small rotation, paper tint, noise, slight blur."""
    W, H = p.img.size
    angle = rng.uniform(-0.8, 0.8)
    img = p.img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=(255, 255, 255))
    cx, cy, a = W / 2, H / 2, math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    items = []
    for it in p.items:
        x0, y0, x1, y1 = it["bbox"]
        pts = [(cx + (x - cx) * ca + (y - cy) * sa, cy - (x - cx) * sa + (y - cy) * ca) for x, y in [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]]
        items.append({**it, "bbox": [round(min(q[0] for q in pts)), round(min(q[1] for q in pts)),
                                     round(max(q[0] for q in pts)), round(max(q[1] for q in pts))]})
    arr = np.asarray(img).astype(np.float32)
    arr = arr * (np.array([rng.uniform(244, 252), rng.uniform(240, 248), rng.uniform(228, 240)]) / 255.0)
    arr += np.random.default_rng(rng.randint(0, 10**9)).normal(0, 6, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))
    return img, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "real_layouts" / "corpus"))
    ap.add_argument("--seed", type=int, default=1127)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "gt").mkdir(parents=True, exist_ok=True)
    index = []
    for ti, (tname, fn, lang, n) in enumerate(TEMPLATES):
        for k in range(n):
            seed = args.seed * 1000 + ti * 100 + k
            rng = random.Random(seed)
            fk = Faker("zh_TW" if lang == "zh" else "en_US")
            fk.seed_instance(seed)
            doc_id = f"{tname}_{k:02d}"
            page = fn(doc_id, rng, fk, k)
            assert all(i["cat"] != "TMP" for i in page.items), doc_id
            img, items = scan(page, rng)
            img.save(out / "images" / f"{doc_id}.jpg", quality=88)
            gt = {"id": doc_id, "template": tname, "lang": lang, "capture": "scan",
                  "width": img.width, "height": img.height, "items": items}
            (out / "gt" / f"{doc_id}.json").write_text(json.dumps(gt, ensure_ascii=False, indent=1))
            index.append({"id": doc_id, "template": tname, "lang": lang, "capture": "scan", "n_pii": len(items)})
            print(f"{doc_id}: {len(items)} PII items")
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(f"\n{len(index)} pages, {sum(i['n_pii'] for i in index)} PII items -> {out}")


if __name__ == "__main__":
    main()
