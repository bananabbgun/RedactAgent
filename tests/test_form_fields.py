"""Form conventions handled by the rule layer: values split over several OCR fragments on one row, ROC slash dates,
Taiwan landlines without parentheses, North American numbers, and institution contacts identified by their field label."""

from redactagent.detectors import rules
from redactagent.schema import OcrLine


def line(i, text, x0, y0, w_char=20, h=30):
    boxes = [[x0 + k * w_char, y0, x0 + (k + 1) * w_char, y0 + h] for k in range(len(text))]
    return OcrLine(f"L{i}", text, [x0, y0, x0 + w_char * len(text), y0 + h], boxes, 0.9)


def cats(hits):
    return sorted({h.category for h in hits})


def test_date_written_into_year_month_day_blanks():
    ls = [line(1, "開單日期", 100, 500), line(2, "115", 220, 502), line(3, "年", 290, 500), line(4, "2", 340, 503),
          line(5, "月", 380, 500), line(6, "28", 430, 502), line(7, "日", 490, 500)]
    hits = [h for h in rules.detect(ls) if h.category == "DATE"]
    carrier = next(h for h in hits if h.bbox is not None)
    assert carrier.bbox[0] <= 220 and carrier.bbox[2] >= 510      # one box from the year to 日
    assert {h.line_id for h in hits} >= {"L2", "L4", "L6"}          # every fragment gets a text span too


def test_date_of_birth_across_blanks():
    ls = [line(1, "出生日期", 100, 300), line(2, "民國", 200, 300), line(3, "54", 260, 302), line(4, "年", 310, 300),
          line(5, "6", 350, 301), line(6, "月", 390, 300), line(7, "18", 430, 302), line(8, "日", 480, 300)]
    assert "DATE_OF_BIRTH" in cats(rules.detect(ls))


def test_characters_one_per_box_with_label_on_the_left():
    ls = [line(1, "身分證統一編號", 50, 200)] + [line(i + 2, ch, 400 + 55 * i, 205) for i, ch in enumerate("A123456789")]
    hits = [h for h in rules.detect(ls) if h.category == "GOV_ID" and h.bbox is not None]
    assert hits and hits[0].bbox[0] <= 400 and hits[0].bbox[2] >= 400 + 55 * 9


def test_boxes_partly_unread_are_still_covered_under_a_label_above():
    # the OCR read only two of five postcode boxes; the label above spans all of them
    ls = [line(1, "郵遞區號", 200, 600, w_char=40), line(2, "5", 250, 650), line(3, "3", 330, 650)]
    hit = next(h for h in rules.detect(ls) if h.category == "ADDRESS" and h.bbox is not None)
    assert hit.bbox[0] <= 200 and hit.bbox[2] >= 360


def test_single_digits_without_a_known_label_are_ignored():
    ls = [line(1, "數量", 50, 200)] + [line(i + 2, ch, 300 + 55 * i, 205) for i, ch in enumerate("1234")]
    assert not [h for h in rules.detect(ls) if h.bbox is not None]


def test_roc_slash_dates():
    for s in ["日期：114/06/06", "有效期限115/05/22", "54/6/18"]:
        assert "DATE" in cats(rules.detect_line(line(1, s, 0, 0)))
    assert "DATE" not in cats(rules.detect_line(line(1, "血壓 120/80", 0, 0)))


def test_landline_without_parentheses_and_north_american_numbers():
    assert "PHONE" in cats(rules.detect_line(line(1, "04-24873952", 0, 0)))
    assert "PHONE" in cats(rules.detect_line(line(1, "02-2345-6789", 0, 0)))
    assert "PHONE" in cats(rules.detect_line(line(1, "(538) 705-7201", 0, 0)))


def test_institution_contact_fields_are_not_personal_data():
    assert "PHONE" not in cats(rules.detect_line(line(1, "(02)2799-1199", 0, 0), prev_text="傳真號碼："))
    assert "EMAIL" not in cats(rules.detect_line(line(1, "records@clinic.example", 0, 0), prev_text="Facility e-mail"))
    # a patient's own number next to an ordinary label is still found, also below a hospital letterhead
    assert "PHONE" in cats(rules.detect_line(line(1, "0912-345-678", 0, 0), prev_text="Riverside Hospital 聯絡電話"))
    assert "EMAIL" in cats(rules.detect_line(line(1, "kyle.c@example.com", 0, 0), prev_text="E-mail"))
