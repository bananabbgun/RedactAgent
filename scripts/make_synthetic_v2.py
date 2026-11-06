"""Synthetic corpus v2: held-out document types + phone-photo capture.

v1 (make_synthetic.py) was used while developing prompts and rules. v2 is a held-out set:
five document types never seen during development, quasi-identifier phrasings that do not
appear in any prompt, and half of the pages "photographed with a phone" (perspective,
uneven light, blur, heavy JPEG) instead of scanned.

    python scripts/make_synthetic_v2.py --n-per-template 6 --out data/synthetic_v2
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np
from faker import Faker
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_synthetic import (  # noqa: E402
    F_EN, F_EN_B, F_SERIF, F_SERIF_B, F_ZH, H, MARGIN, W, Page, bank_account, en_address, en_date, font,
    mrn, rand_date, roc_date, roman_name, scan, slash_date, tw_landline, tw_mobile, tw_national_id, zh_address,
)

# Quasi-identifiers that appear in no prompt and no v1 document.
QUASI_EN_V2 = [
    "the only harbour pilot licensed for Hualien port",
    "the principal of the sole elementary school on Dongyin island",
    "the youngest member of the national para-fencing squad",
    "the last blacksmith still working in Lukang old street",
]
QUASI_ZH_V2 = [
    "為金門唯一的手語翻譯員",
    "是臺東縣唯一的女性熱氣球駕駛",
    "現任國家帕拉桌球隊隊長",
    "為該部落唯一領有執照的狩獵者",
]
LABS = ["Northbridge Clinical Laboratory", "Lakeside Diagnostics Centre", "Pinewood Medical Laboratory"]
PHARMACIES = ["和平社區藥局", "仁愛健保藥局", "安泰大藥局"]
BANKS = ["Formosa Harbour Bank", "Pacific Union Savings Bank", "Jade River Commercial Bank"]
COURTS = ["臺灣濱海地方法院", "臺灣東嶺地方法院"]
CLINICS = ["Maple Family Medicine Clinic", "Seaside Internal Medicine Clinic"]


def t_lab_report_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "lab_report_en", "en")
    name, surname = roman_name(rng)
    sex = rng.choice("MF")
    doctor, _ = roman_name(rng)
    tech, _ = roman_name(rng)
    rel, _ = roman_name(rng)
    dob = rand_date(rng, 1945, 2005)
    col = rand_date(rng, 2025, 2026)
    rep = (col[0], col[1], min(28, col[2] + 1))
    hb, r = font(F_EN_B, 25), font(F_EN, 24)
    p.text(MARGIN, 70, rng.choice(LABS), font(F_EN_B, 36), fill=(110, 30, 30))
    p.text(MARGIN, 118, "CAP-accredited  |  Tel (04) 2311-0000  |  www.example-lab.test", font(F_EN, 20), fill=(110, 110, 110))
    p.text(W - MARGIN - 330, 76, "LABORATORY REPORT", font(F_EN_B, 30))
    p.hline(160, w=3)
    y, c2 = 185, 660
    p.field(MARGIN, y, "Patient:", name, hb, r, "PERSON_NAME", "subject")
    p.field(c2, y, "Sex / DOB:", ("M" if sex == "M" else "F") + " / ", hb, r)
    p.text(c2 + 210, y, en_date(dob, 2), r, cat="DATE_OF_BIRTH")
    y += 44
    p.field(MARGIN, y, "Chart No.:", f"CH-{rng.randint(100000, 999999)}", hb, r, "MEDICAL_RECORD_NO")
    p.field(c2, y, "Accession:", f"SP{rng.randint(10, 99)}-{rng.randint(100000, 999999)}", hb, r, "MEDICAL_RECORD_NO")
    y += 44
    p.field(MARGIN, y, "Collected:", en_date(col, 1) + f" {rng.randint(7, 11):02d}:{rng.randint(0, 59):02d}", hb, r, "DATE")
    p.field(c2, y, "Reported:", en_date(rep, 1), hb, r, "DATE")
    y += 44
    p.field(MARGIN, y, "Ordering physician:", f"Dr. {doctor}", hb, r, "PERSON_NAME", "professional")
    y += 70
    p.box([MARGIN, y, W - MARGIN, y + 46], w=0, fill=(235, 238, 245), outline=(235, 238, 245))
    for x, h in zip((MARGIN + 12, 520, 720, 900), ("Test", "Result", "Unit", "Reference range")):
        p.text(x, y + 10, h, font(F_EN_B, 22))
    y += 56
    rows = [("Haemoglobin", f"{rng.uniform(10.5, 16.5):.1f}", "g/dL", "12.0 - 16.0"),
            ("WBC", f"{rng.uniform(3.5, 12.5):.1f}", "10^3/uL", "4.0 - 10.0"),
            ("Platelets", f"{rng.randint(120, 420)}", "10^3/uL", "150 - 400"),
            ("Creatinine", f"{rng.uniform(0.5, 1.9):.2f}", "mg/dL", "0.60 - 1.20"),
            ("HbA1c", f"{rng.uniform(5.0, 9.8):.1f}", "%", "4.0 - 5.6"),
            ("ALT", f"{rng.randint(10, 95)}", "U/L", "7 - 56")]
    for row in rows:
        for x, v in zip((MARGIN + 12, 520, 720, 900), row):
            p.text(x, y, v, font(F_EN, 22))
        y += 40
    y += 30
    p.text(MARGIN, y, "Clinical note", hb)
    y += 42
    for ln in [["Specimen from ", (name, "PERSON_NAME", "subject"), ", who is ", (rng.choice(QUASI_EN_V2), "QUASI_IDENTIFIER", "subject"), "."],
               ["Critical HbA1c value phoned to ", (rel, "PERSON_NAME", "family"), " (daughter) at ", (tw_mobile(rng), "PHONE"), "."],
               ["Repeat testing recommended in three months."]]:
        p.segs(MARGIN, y, ln, font(F_EN, 23))
        y += 38
    y = 1450
    p.hline(y, w=1)
    bb = p.field(MARGIN, y + 30, "Verified by:", tech + ", MT", hb, r, "PERSON_NAME", "professional")
    p.signature(MARGIN + 20, y + 80, tech, rng, role="professional", size=40)
    p.text(MARGIN, 1680, "Synthetic held-out sample (v2) - all data fictitious.", font(F_EN, 18), fill=(130, 130, 130))
    return p


def t_prescription_zh(doc_id, rng, fzh) -> Page:
    p = Page(doc_id, "prescription_label_zh", "zh")
    sex = rng.choice("MF")
    name = fzh.name_male() if sex == "M" else fzh.name_female()
    doctor, pharm = fzh.name(), fzh.name()
    dob = rand_date(rng, 1940, 2010)
    day = rand_date(rng, 2025, 2026)
    t, r, lb = font(F_ZH, 40), font(F_ZH, 27), font(F_ZH, 27)
    pharmacy = rng.choice(PHARMACIES)
    p.text(MARGIN, 70, pharmacy + "　藥袋", t, fill=(20, 90, 60))
    p.text(MARGIN, 125, f"地址：{zh_address(rng)}　電話：{tw_landline(rng)}", font(F_ZH, 21), fill=(100, 100, 100))
    p.hline(170, w=3)
    y = 195
    p.field(MARGIN, y, "姓名：", name, lb, r, "PERSON_NAME", "subject")
    p.field(560, y, "性別：", "男" if sex == "M" else "女", lb, r)
    y += 52
    p.field(MARGIN, y, "出生日期：", roc_date(dob), lb, r, "DATE_OF_BIRTH")
    p.field(640, y, "病歷號：", f"{rng.randint(10000000, 99999999)}", lb, r, "MEDICAL_RECORD_NO")
    y += 52
    p.field(MARGIN, y, "調劑日期：", roc_date(day), lb, r, "DATE")
    p.field(640, y, "領藥號：", f"{rng.randint(1, 300):03d}", lb, r)
    y += 80
    p.box([MARGIN, y, W - MARGIN, y + 360], w=2)
    drug = rng.choice([("Metformin 500mg", "降血糖", "每日兩次，早晚飯後各一顆"),
                       ("Amlodipine 5mg", "降血壓", "每日一次，早餐後一顆"),
                       ("Atorvastatin 20mg", "降血脂", "每日一次，睡前一顆")])
    yy = y + 25
    for label, val in [("藥品名稱：", drug[0]), ("用途：", drug[1]), ("用法：", drug[2]), ("數量：", f"{rng.choice([28, 56, 84])} 顆")]:
        p.field(MARGIN + 25, yy, label, val, lb, r)
        yy += 60
    p.text(MARGIN + 25, yy, "注意：服藥期間如有不適，請立即回診或洽詢藥師。", font(F_ZH, 23), fill=(150, 40, 40))
    y += 400
    p.text(MARGIN, y, "藥師叮嚀：", lb)
    y += 50
    p.segs(MARGIN + 30, y, ["病人", (name, "PERSON_NAME", "subject"), "　", (rng.choice(QUASI_ZH_V2), "QUASI_IDENTIFIER", "subject"), "，"], r)
    y += 46
    p.text(MARGIN + 30, y, "因需長時間戶外工作，請注意補充水分並按時服藥。", r)
    y = 1440
    p.hline(y, w=1)
    p.field(MARGIN, y + 35, "處方醫師：", doctor, lb, r, "PERSON_NAME", "professional")
    bb = p.field(640, y + 35, "調劑藥師：", pharm, lb, r, "PERSON_NAME", "professional")
    p.seal(bb[2] + 25, y + 5, (pharm + "印")[:4], size=100, rng=rng)
    p.text(MARGIN, 1680, "本文件為 RedactAgent v2 保留測試集合成樣本，所有資料皆為隨機產生。", font(F_ZH, 18), fill=(130, 130, 130))
    return p


def t_bank_statement_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "bank_statement_en", "en")
    holder, _ = roman_name(rng)
    period = rand_date(rng, 2025, 2026)
    hb, r = font(F_EN_B, 24), font(F_EN, 23)
    p.text(MARGIN, 70, rng.choice(BANKS), font(F_SERIF_B, 38), fill=(15, 60, 100))
    p.text(W - MARGIN - 330, 82, "ACCOUNT STATEMENT", font(F_EN_B, 28))
    p.hline(150, w=3)
    y = 175
    p.text(MARGIN, y, holder.upper(), font(F_EN_B, 26), cat="PERSON_NAME", role="subject")
    p.text(MARGIN, y + 38, en_address(rng), r, cat="ADDRESS")
    p.field(MARGIN, y + 84, "Account:", bank_account(rng), hb, r, "FINANCIAL_ACCOUNT")
    bb = p.field(660, y + 84, "Period:", f"{period[0]}-{period[1]:02d}-01", hb, r, "DATE")
    bb = p.text(bb[2] + 12, y + 84, "to ", r)
    p.text(bb[2] + 4, y + 84, f"{period[0]}-{period[1]:02d}-28", r, cat="DATE")
    y += 150
    p.box([MARGIN, y, W - MARGIN, y + 44], w=0, fill=(228, 236, 245), outline=(228, 236, 245))
    cols = (MARGIN + 10, 280, 860, 1020)
    for x, h in zip(cols, ("Date", "Description", "Amount", "Balance")):
        p.text(x, y + 10, h, font(F_EN_B, 21))
    y += 56
    bal = rng.randint(30, 400) * 1000
    descr = [("Salary - Starfield Technology Co.", None), ("ATM withdrawal - Zhongshan branch", None),
             ("Transfer to {}", "other"), ("Rent payment to {}", "other"), ("Card purchase - City Supermarket", None),
             ("Transfer from {}", "family"), ("Utility bill - Taipower", None), ("Insurance premium - Harbor Mutual", None)]
    rng.shuffle(descr)
    for i, (d, role) in enumerate(descr):
        day = (period[0], period[1], min(28, 2 + i * 3))
        p.text(cols[0], y, f"{day[0]}-{day[1]:02d}-{day[2]:02d}", font(F_EN, 21), cat="DATE")
        if role:
            nm, _ = roman_name(rng)
            nm = nm.upper()
            pre, post = d.split("{}")
            p.segs(cols[1], y, [pre, (nm, "PERSON_NAME", role), post], font(F_EN, 21))
        else:
            p.text(cols[1], y, d, font(F_EN, 21))
        amt = rng.randint(-60, 60) * 500 or 1500
        bal += amt
        p.text(cols[2], y, f"{amt:+,}", font(F_EN, 21))
        p.text(cols[3], y, f"{bal:,}", font(F_EN, 21))
        y += 46
    y += 40
    p.text(MARGIN, y, "Messages", hb)
    y += 40
    for ln in [["Dear customer, your registered mobile ", (tw_mobile(rng), "PHONE"), " will receive one-time passwords."],
               ["Report lost cards immediately via our 24-hour hotline (02) 2181-0000."]]:
        p.segs(MARGIN, y, ln, r)
        y += 38
    p.text(MARGIN, 1680, "Synthetic held-out sample (v2) - all data fictitious.", font(F_EN, 18), fill=(130, 130, 130))
    return p


def t_judgment_zh(doc_id, rng, fzh) -> Page:
    p = Page(doc_id, "court_judgment_zh", "zh")
    a_sex, b_sex = rng.choice("MF"), rng.choice("MF")
    a = fzh.name_male() if a_sex == "M" else fzh.name_female()
    b = fzh.name_male() if b_sex == "M" else fzh.name_female()
    lawyer, judge, clerk = fzh.name(), fzh.name(), fzh.name()
    sign = rand_date(rng, 2023, 2025)
    issue = rand_date(rng, 2026, 2026)
    t, r, lb = font(F_ZH, 40), font(F_ZH, 26), font(F_ZH, 26)
    p.text(W // 2 - 250, 70, rng.choice(COURTS) + "民事判決", t)
    p.text(W // 2 - 160, 130, f"{issue[0] - 1911}年度訴字第{rng.randint(100, 2999)}號", font(F_ZH, 24), fill=(80, 80, 80))
    y = 200
    p.field(MARGIN, y, "原　　告　", a, lb, r, "PERSON_NAME", "party")
    p.field(560, y, "身分證統一編號：", tw_national_id(rng, a_sex), lb, r, "GOV_ID")
    y += 46
    p.field(MARGIN + 140, y, "住：", zh_address(rng), lb, r, "ADDRESS")
    y += 46
    p.field(MARGIN, y, "訴訟代理人　", lawyer + "律師", lb, r, "PERSON_NAME", "professional")
    y += 56
    p.field(MARGIN, y, "被　　告　", b, lb, r, "PERSON_NAME", "party")
    y += 46
    p.field(MARGIN + 140, y, "住：", zh_address(rng), lb, r, "ADDRESS")
    y += 80
    p.text(W // 2 - 40, y, "主　文", font(F_ZH, 30))
    y += 56
    amt = rng.randint(20, 300) * 10000
    p.text(MARGIN + 30, y, f"被告應給付原告新臺幣{amt:,}元，及自起訴狀繕本送達翌日起至清償日止，", r)
    y += 44
    p.text(MARGIN + 30, y, "按週年利率百分之五計算之利息。訴訟費用由被告負擔。", r)
    y += 70
    p.text(W // 2 - 90, y, "事實及理由", font(F_ZH, 30))
    y += 56
    lines = [["原告主張：兩造於", (roc_date(sign), "DATE"), "簽訂借款契約，"],
             ["被告", (b, "PERSON_NAME", "party"), (rng.choice(QUASI_ZH_V2), "QUASI_IDENTIFIER", "party"), "，"],
             ["向原告借款後屆期未還，經原告多次催告仍置之不理。"],
             ["被告經合法通知，未於言詞辯論期日到場，亦未提出書狀作何聲明或陳述。"]]
    for ln in lines:
        p.segs(MARGIN + 30, y, ln, r)
        y += 46
    y = 1420
    p.text(MARGIN, y, "中華民國", r)
    p.text(MARGIN + 120, y, f"{issue[0] - 1911}年{issue[1]}月{issue[2]}日", r, cat="DATE")
    y += 60
    p.field(MARGIN, y, "民事庭　法　官　", judge, lb, r, "PERSON_NAME", "professional")
    y += 52
    p.field(MARGIN, y, "書記官　", clerk, lb, r, "PERSON_NAME", "professional")
    p.seal(W - MARGIN - 210, y - 110, COURTS[0][2:6] + "法院印", size=190, round_=True, rng=rng)
    p.text(MARGIN, 1680, "本文件為 RedactAgent v2 保留測試集合成樣本，所有資料皆為隨機產生。", font(F_ZH, 18), fill=(130, 130, 130))
    return p


def t_referral_en(doc_id, rng, fen) -> Page:
    p = Page(doc_id, "referral_letter_en", "en")
    pat, surname = roman_name(rng)
    to_dr, _ = roman_name(rng)
    from_dr, _ = roman_name(rng)
    wife, _ = roman_name(rng)
    dob = rand_date(rng, 1950, 1995)
    seen = rand_date(rng, 2026, 2026)
    r, hb = font(F_SERIF, 26), font(F_SERIF_B, 26)
    p.text(MARGIN, 70, rng.choice(CLINICS), font(F_SERIF_B, 36), fill=(30, 70, 60))
    p.text(MARGIN, 118, en_address(rng) + "  |  (02) 2700-1234", font(F_SERIF, 20), fill=(110, 110, 110))
    p.hline(160, w=2)
    y = 200
    p.text(MARGIN, y, en_date(seen, 0), r, cat="DATE")
    y += 60
    p.segs(MARGIN, y, ["Dear ", (f"Dr. {to_dr}", "PERSON_NAME", "professional"), ","], r)
    y += 60
    body = [
        ["Re: ", (pat, "PERSON_NAME", "subject"), ", born ", (en_date(dob, 0), "DATE_OF_BIRTH"), ", chart ", (mrn(rng), "MEDICAL_RECORD_NO")],
        [],
        ["Thank you for seeing this patient, who is ", (rng.choice(QUASI_EN_V2), "QUASI_IDENTIFIER", "subject"), "."],
        ["Mr./Ms. ", (surname, "PERSON_NAME", "subject"), " presented on ", (en_date(seen, 0), "DATE"), " with exertional chest pain"],
        ["for two weeks. ECG showed non-specific ST changes; troponin was negative."],
        ["I would be grateful for your assessment regarding stress testing."],
        [],
        ["The patient prefers appointments in the afternoon and can be reached at"],
        [(tw_mobile(rng), "PHONE"), " or via the spouse, ", (wife, "PERSON_NAME", "family"), ", at ", (tw_mobile(rng), "PHONE"), "."],
        ["Home address: ", (en_address(rng), "ADDRESS"), "."],
    ]
    for ln in body:
        if ln:
            p.segs(MARGIN, y, ln, r)
        y += 44
    y += 60
    p.text(MARGIN, y, "Sincerely,", r)
    p.signature(MARGIN, y + 45, from_dr, rng, role="professional")
    p.text(MARGIN, y + 140, f"Dr. {from_dr}", hb, cat="PERSON_NAME", role="professional")
    p.text(MARGIN, 1680, "Synthetic held-out sample (v2) - all data fictitious.", font(F_SERIF, 18), fill=(130, 130, 130))
    return p


TEMPLATES_V2 = [
    ("lab_report_en", t_lab_report_en, "en"),
    ("prescription_label_zh", t_prescription_zh, "zh"),
    ("bank_statement_en", t_bank_statement_en, "en"),
    ("court_judgment_zh", t_judgment_zh, "zh"),
    ("referral_letter_en", t_referral_en, "en"),
]


def _homography(src, dst):
    """3x3 H with dst ~ H @ src (4 point pairs)."""
    a = []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        a.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.asarray(a, dtype=float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def phone_capture(p: Page, rng: random.Random) -> tuple[Image.Image, list[dict]]:
    """Simulate a phone photo of the page on a desk: perspective, shading, blur, noise."""
    jit = lambda s: rng.uniform(0.015, 0.05) * s  # noqa: E731
    src = [(0, 0), (W, 0), (W, H), (0, H)]
    dst = [(jit(W), jit(H)), (W - jit(W), jit(H)), (W - jit(W), H - jit(H)), (jit(W), H - jit(H))]
    h_fwd = _homography(src, dst)          # page -> photo
    h_inv = np.linalg.inv(h_fwd)           # photo -> page (PIL wants output->input)
    coeffs = (h_inv / h_inv[2, 2]).flatten()[:8]
    desk = tuple(rng.randint(60, 110) for _ in range(3))
    img = p.img.transform((W, H), Image.PERSPECTIVE, tuple(coeffs), resample=Image.BICUBIC, fillcolor=desk)

    def fwd(x, y):
        v = h_fwd @ np.array([x, y, 1.0])
        return v[0] / v[2], v[1] / v[2]

    items = []
    for it in p.items:
        x0, y0, x1, y1 = it["bbox"]
        pts = [fwd(x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        items.append({**it, "bbox": [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]})
    arr = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    gx, gy = rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)
    light = 0.92 + gx * (xx / W - 0.5) + gy * (yy / H - 0.5)
    light -= 0.18 * (((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2) * 2)  # vignette
    arr *= np.clip(light, 0.55, 1.05)[..., None]
    arr *= np.array([1.0, rng.uniform(0.96, 1.0), rng.uniform(0.88, 0.96)])  # warm indoor light
    arr += np.random.default_rng(rng.randint(0, 10**9)).normal(0, 7, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rng.uniform(0.6, 1.1)))
    return img, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-per-template", type=int, default=6)
    ap.add_argument("--out", default="data/synthetic_v2")
    ap.add_argument("--seed", type=int, default=4242)
    a = ap.parse_args()
    out = Path(a.out)
    (out / "images").mkdir(parents=True, exist_ok=True)
    (out / "gt").mkdir(parents=True, exist_ok=True)
    index = []
    for ti, (tname, fn, lang) in enumerate(TEMPLATES_V2):
        for k in range(a.n_per_template):
            seed = a.seed * 1000 + ti * 100 + k
            rng = random.Random(seed)
            fk = Faker("zh_TW" if lang == "zh" else "en_US")
            fk.seed_instance(seed)
            doc_id = f"{tname}_{k:02d}"
            page = fn(doc_id, rng, fk)
            capture = "phone" if k % 2 else "scan"
            img, items = phone_capture(page, rng) if capture == "phone" else scan(page, rng)
            img.save(out / "images" / f"{doc_id}.jpg", quality=60 if capture == "phone" else 88)
            gt = {"id": doc_id, "template": tname, "lang": lang, "capture": capture, "width": W, "height": H, "items": items}
            (out / "gt" / f"{doc_id}.json").write_text(json.dumps(gt, ensure_ascii=False, indent=1))
            index.append({"id": doc_id, "template": tname, "lang": lang, "capture": capture, "n_pii": len(items)})
            print(f"{doc_id} ({capture}): {len(items)} PII items")
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    print(f"\n{len(index)} documents, {sum(i['n_pii'] for i in index)} PII items -> {out}")


if __name__ == "__main__":
    main()
