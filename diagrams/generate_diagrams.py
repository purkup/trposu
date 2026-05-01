from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent
WIDTH = 1800
HEIGHT = 1273
INK = "#1f2933"
MUTED = "#52616b"
LINE = "#2f3a45"
BLUE = "#dbeafe"
GREEN = "#dcfce7"
YELLOW = "#fef9c3"
RED = "#fee2e2"
GRAY = "#f7f7f7"
WHITE = "#ffffff"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE = font(42, True)
SUBTITLE = font(24)
BODY = font(26)
BODY_BOLD = font(26, True)
SMALL = font(22)
SMALL_BOLD = font(22, True)
TINY = font(18)


def canvas(title: str, subtitle: str = "") -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)
    draw.text((70, 52), title, font=TITLE, fill=INK)
    if subtitle:
        draw.text((72, 104), subtitle, font=SUBTITLE, fill=MUTED)
    draw.line((70, 152, WIDTH - 70, 152), fill="#d9dee3", width=2)
    return image, draw


def text_width(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> int:
    return int(draw.textlength(text, font=fnt))


def wrap_line(draw: ImageDraw.ImageDraw, line: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = line.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width(draw, candidate, fnt) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont, max_width: int) -> list[str]:
    wrapped: list[str] = []
    for raw in text.split("\n"):
        wrapped.extend(wrap_line(draw, raw, fnt, max_width))
    return wrapped


def center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.ImageFont = BODY,
    fill: str = INK,
    max_lines: int | None = None,
) -> None:
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, fnt, x2 - x1 - 28)
    if max_lines:
        lines = lines[:max_lines]
    line_h = fnt.size + 8
    total_h = len(lines) * line_h - 8
    y = y1 + ((y2 - y1) - total_h) / 2
    for line in lines:
        tw = text_width(draw, line, fnt)
        draw.text((x1 + ((x2 - x1) - tw) / 2, y), line, font=fnt, fill=fill)
        y += line_h


def left_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.ImageFont = SMALL,
    fill: str = INK,
    pad: int = 18,
) -> None:
    x1, y1, x2, _ = box
    lines = wrap_text(draw, text, fnt, x2 - x1 - pad * 2)
    y = y1 + pad
    for line in lines:
        draw.text((x1 + pad, y), line, font=fnt, fill=fill)
        y += fnt.size + 8


def rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str = "",
    fill: str = GRAY,
    outline: str = LINE,
    width: int = 3,
    radius: int = 0,
    fnt: ImageFont.ImageFont = BODY,
) -> None:
    if radius:
        draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(box, fill=fill, outline=outline, width=width)
    if text:
        center_text(draw, box, text, fnt=fnt)


def ellipse(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str = "",
    fill: str = GRAY,
    outline: str = LINE,
    width: int = 3,
    fnt: ImageFont.ImageFont = BODY,
) -> None:
    draw.ellipse(box, fill=fill, outline=outline, width=width)
    if text:
        center_text(draw, box, text, fnt=fnt)


def diamond(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str = "",
    fill: str = YELLOW,
    outline: str = LINE,
    width: int = 3,
    fnt: ImageFont.ImageFont = SMALL,
) -> None:
    x1, y1, x2, y2 = box
    points = [
        ((x1 + x2) // 2, y1),
        (x2, (y1 + y2) // 2),
        ((x1 + x2) // 2, y2),
        (x1, (y1 + y2) // 2),
    ]
    draw.polygon(points, fill=fill, outline=outline)
    draw.line(points + [points[0]], fill=outline, width=width, joint="curve")
    if text:
        center_text(draw, box, text, fnt=fnt)


def process(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    number: str,
    name: str,
    fill: str = BLUE,
) -> None:
    rect(draw, box, fill=fill, outline=LINE, radius=22)
    x1, y1, x2, y2 = box
    draw.text((x1 + 20, y1 + 14), number, font=SMALL_BOLD, fill=MUTED)
    center_text(draw, (x1 + 18, y1 + 28, x2 - 18, y2 - 8), name, fnt=BODY_BOLD)


def store(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    title: str,
    text: str,
) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill=WHITE, outline=LINE, width=3)
    draw.line((x1 + 14, y1, x1 + 14, y2), fill=LINE, width=3)
    draw.text((x1 + 28, y1 + 16), title, font=SMALL_BOLD, fill=INK)
    left_text(draw, (x1 + 16, y1 + 48, x2, y2), text, fnt=SMALL, pad=12)


def component(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fill: str = GRAY,
) -> None:
    rect(draw, box, fill=fill, outline=LINE)
    x1, y1, _, _ = box
    draw.rectangle((x1 - 22, y1 + 22, x1 + 16, y1 + 50), fill=WHITE, outline=LINE, width=3)
    draw.rectangle((x1 - 22, y1 + 64, x1 + 16, y1 + 92), fill=WHITE, outline=LINE, width=3)
    center_text(draw, box, text, fnt=BODY_BOLD)


def class_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    name: str,
    attrs: list[str],
    methods: list[str],
    fill: str = WHITE,
) -> None:
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill=fill, outline=LINE, width=3)
    header_h = 52
    attr_h = 38 + len(attrs) * 28
    draw.rectangle((x1, y1, x2, y1 + header_h), fill=BLUE, outline=LINE, width=3)
    center_text(draw, (x1, y1, x2, y1 + header_h), name, fnt=BODY_BOLD)
    draw.line((x1, y1 + header_h + attr_h, x2, y1 + header_h + attr_h), fill=LINE, width=2)
    y = y1 + header_h + 14
    for attr in attrs:
        draw.text((x1 + 18, y), attr, font=TINY, fill=INK)
        y += 28
    y = y1 + header_h + attr_h + 14
    for method in methods:
        draw.text((x1 + 18, y), method, font=TINY, fill=INK)
        y += 28


def arrowhead(draw: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int], fill: str = LINE) -> None:
    angle = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    length = 18
    spread = math.pi / 7
    points = [
        p2,
        (
            int(p2[0] - length * math.cos(angle - spread)),
            int(p2[1] - length * math.sin(angle - spread)),
        ),
        (
            int(p2[0] - length * math.cos(angle + spread)),
            int(p2[1] - length * math.sin(angle + spread)),
        ),
    ]
    draw.polygon(points, fill=fill)


def arrow(
    draw: ImageDraw.ImageDraw,
    p1: tuple[int, int],
    p2: tuple[int, int],
    label: str = "",
    fill: str = LINE,
    width: int = 3,
    label_offset: tuple[int, int] = (0, -34),
) -> None:
    draw.line((p1, p2), fill=fill, width=width)
    arrowhead(draw, p1, p2, fill=fill)
    if label:
        lx = (p1[0] + p2[0]) // 2 + label_offset[0]
        ly = (p1[1] + p2[1]) // 2 + label_offset[1]
        label_box(draw, (lx, ly), label)


def poly_arrow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    label: str = "",
    fill: str = LINE,
    width: int = 3,
    label_pos: tuple[int, int] | None = None,
) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    arrowhead(draw, points[-2], points[-1], fill=fill)
    if label:
        pos = label_pos if label_pos else points[len(points) // 2]
        label_box(draw, pos, label)


def dashed_line(draw: ImageDraw.ImageDraw, p1: tuple[int, int], p2: tuple[int, int], fill: str = LINE, width: int = 2) -> None:
    total = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    if total == 0:
        return
    dash = 18
    gap = 10
    dx = (p2[0] - p1[0]) / total
    dy = (p2[1] - p1[1]) / total
    distance = 0
    while distance < total:
        start = distance
        end = min(distance + dash, total)
        draw.line(
            (
                (p1[0] + dx * start, p1[1] + dy * start),
                (p1[0] + dx * end, p1[1] + dy * end),
            ),
            fill=fill,
            width=width,
        )
        distance += dash + gap


def label_box(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    fnt: ImageFont.ImageFont = TINY,
    fill: str = INK,
) -> None:
    lines = wrap_text(draw, text, fnt, 300)
    w = max(text_width(draw, line, fnt) for line in lines) + 16
    h = len(lines) * (fnt.size + 5) + 10
    x, y = pos
    draw.rounded_rectangle((x - w // 2, y - h // 2, x + w // 2, y + h // 2), radius=6, fill=WHITE, outline="#e5e7eb")
    ty = y - h // 2 + 6
    for line in lines:
        draw.text((x - text_width(draw, line, fnt) / 2, ty), line, font=fnt, fill=fill)
        ty += fnt.size + 5


def save(image: Image.Image, filename: str) -> None:
    image.save(OUT_DIR / filename, optimize=True)


def dfd_context() -> None:
    image, draw = canvas("DFD: контекстная диаграмма", "Система бронирования мест в ресторане")
    rect(draw, (120, 480, 430, 650), "Клиент", fill=WHITE, fnt=BODY_BOLD)
    process(draw, (680, 420, 1120, 710), "0", "Управлять бронированием столов")
    rect(draw, (1350, 470, 1660, 660), "Администратор\n(локальный пользователь)", fill=WHITE, fnt=BODY_BOLD)
    arrow(draw, (430, 535), (680, 520), "Заявка на бронь,\nзапрос отмены,\nзапрос занятости")
    arrow(draw, (680, 615), (430, 615), "Номер брони,\nстатус мест,\nошибка")
    arrow(draw, (1350, 540), (1120, 535), "Управление через GUI")
    arrow(draw, (1120, 625), (1350, 625), "Сообщения программы")
    save(image, "01_dfd_context.png")


def dfd_level_1() -> None:
    image, draw = canvas("DFD: декомпозиция процесса", "Потоки данных без логических операторов")
    rect(draw, (90, 535, 330, 685), "Клиент", fill=WHITE, fnt=BODY_BOLD)
    process(draw, (480, 245, 820, 405), "1.1", "Проверить данные заявки")
    process(draw, (980, 245, 1320, 405), "1.2", "Подобрать столы")
    process(draw, (980, 575, 1320, 735), "1.3", "Сохранить бронь")
    process(draw, (480, 785, 820, 945), "1.4", "Показать занятость")
    process(draw, (980, 835, 1320, 995), "1.5", "Удалить бронь")
    store(draw, (1440, 500, 1710, 650), "D1", "bookings.txt\nсписок броней")
    store(draw, (1440, 250, 1710, 400), "D2", "Конфигурация\nстолы и интервалы")

    arrow(draw, (330, 575), (480, 325), "Данные заявки")
    arrow(draw, (820, 325), (980, 325), "Проверенная заявка")
    arrow(draw, (1320, 325), (1440, 325), "Запрос конфигурации")
    arrow(draw, (1440, 365), (1320, 365), "Данные столов")
    arrow(draw, (1320, 620), (1440, 570), "Новая бронь")
    arrow(draw, (1440, 610), (1320, 665), "Сохраненные данные")
    poly_arrow(draw, [(330, 640), (410, 640), (410, 865), (480, 865)], "Запрос занятости", label_pos=(405, 760))
    arrow(draw, (820, 865), (1440, 610), "Брони интервала", label_offset=(25, 0))
    arrow(draw, (480, 910), (330, 675), "Информация о местах", label_offset=(-20, 20))
    poly_arrow(draw, [(330, 610), (910, 610), (910, 915), (980, 915)], "Данные отмены", label_pos=(690, 575))
    arrow(draw, (1320, 915), (1440, 610), "Удаленная бронь", label_offset=(15, 10))
    poly_arrow(draw, [(980, 650), (900, 650), (900, 555), (330, 555)], "Номер брони / ошибка", label_pos=(610, 520))
    save(image, "02_dfd_level_1.png")


def idef0_context() -> None:
    image, draw = canvas("IDEF0: контекст A-0", "Функция верхнего уровня и ICOM-стрелки")
    main = (610, 430, 1190, 760)
    rect(draw, main, "Управлять бронированием\nстолов ресторана", fill=BLUE, fnt=BODY_BOLD)
    draw.text((1120, 720), "A-0", font=SMALL_BOLD, fill=MUTED)

    arrow(draw, (120, 520), (610, 520), "Заявка клиента")
    arrow(draw, (120, 660), (610, 660), "Запрос просмотра\nили отмены")
    arrow(draw, (750, 185), (750, 430), "Правила вместимости\nи быстрый ужин")
    arrow(draw, (1020, 185), (1020, 430), "Интервалы времени")
    arrow(draw, (1190, 515), (1670, 515), "Номер брони")
    arrow(draw, (1190, 650), (1670, 650), "Состояние мест,\nсообщение об ошибке\nили отмене")
    arrow(draw, (760, 1080), (760, 760), "Tkinter GUI")
    arrow(draw, (1030, 1080), (1030, 760), "BookingSystem\nи bookings.txt")

    draw.text((90, 450), "Входы", font=SMALL_BOLD, fill=MUTED)
    draw.text((715, 165), "Управление", font=SMALL_BOLD, fill=MUTED)
    draw.text((1510, 455), "Выходы", font=SMALL_BOLD, fill=MUTED)
    draw.text((760, 1110), "Механизмы", font=SMALL_BOLD, fill=MUTED)
    save(image, "03_idef0_context_a0.png")


def idef1x_erd() -> None:
    image, draw = canvas("IDEF1X: логическая модель данных", "Структура JSON-хранилища и констант приложения")
    class_box(
        draw,
        (130, 275, 520, 560),
        "BOOKING",
        ["PK id: int", "client_name: str", "visitors: int", "quick_dinner: bool"],
        ["interval: str"],
        fill=WHITE,
    )
    class_box(
        draw,
        (705, 270, 1095, 560),
        "BOOKING_TABLE",
        ["FK booking_id: int", "FK table_id: str", "half: 0 | 1 | 2"],
        ["назначенный стол"],
        fill=WHITE,
    )
    class_box(
        draw,
        (1285, 260, 1675, 555),
        "RESTAURANT_TABLE",
        ["PK table_id: str", "capacity: 2 | 4", "movable: bool"],
        ["T2-1..T2-4", "T4-1..T4-4"],
        fill=WHITE,
    )
    class_box(
        draw,
        (130, 735, 520, 1060),
        "TIME_INTERVAL",
        ["PK value: str", "start_time: time", "end_time: time"],
        ["17:00-19:00", "19:00-21:00", "21:00-23:00"],
        fill=WHITE,
    )

    arrow(draw, (520, 415), (705, 415), "1 : M")
    arrow(draw, (1095, 415), (1285, 415), "M : 1")
    poly_arrow(draw, [(325, 735), (325, 630), (325, 560)], "1 : M", label_pos=(390, 650))
    draw.text((560, 390), "содержит", font=TINY, fill=MUTED)
    draw.text((1135, 390), "использует", font=TINY, fill=MUTED)
    draw.text((360, 595), "выбран для", font=TINY, fill=MUTED)

    rect(
        draw,
        (720, 800, 1535, 950),
        "Примечание: дата рождения, кулинарные предпочтения и суммы заказов\nв текущем коде и bookings.txt не хранятся.",
        fill=YELLOW,
        fnt=SMALL_BOLD,
    )
    save(image, "04_idef1x_erd.png")


def use_case() -> None:
    image, draw = canvas("UML: диаграмма вариантов использования", "Актер: клиент локального приложения")
    x1, y1, x2, y2 = (420, 220, 1610, 1030)
    rect(draw, (x1, y1, x2, y2), fill=WHITE, outline="#9aa5b1")
    draw.text((x1 + 22, y1 + 18), "Система бронирования ресторана", font=SMALL_BOLD, fill=MUTED)
    ellipse(draw, (130, 470, 240, 580), fill=WHITE)
    draw.line((185, 580, 185, 720), fill=LINE, width=4)
    draw.line((120, 625, 250, 625), fill=LINE, width=4)
    draw.line((185, 720, 130, 820), fill=LINE, width=4)
    draw.line((185, 720, 240, 820), fill=LINE, width=4)
    center_text(draw, (85, 830, 285, 900), "Клиент", fnt=BODY_BOLD)

    cases = {
        "view": (560, 295, 940, 405, "Посмотреть места"),
        "book": (560, 515, 940, 625, "Забронировать стол"),
        "cancel": (560, 735, 940, 845, "Отменить бронь"),
        "validate": (1110, 405, 1490, 515, "Проверить ввод"),
        "select": (1110, 555, 1490, 665, "Подобрать столы"),
        "persist": (1110, 705, 1490, 815, "Записать или удалить бронь"),
    }
    for x_a, y_a, x_b, y_b, text in cases.values():
        ellipse(draw, (x_a, y_a, x_b, y_b), text, fill=BLUE, fnt=SMALL_BOLD)

    for key in ("view", "book", "cancel"):
        cx = 560
        cy = (cases[key][1] + cases[key][3]) // 2
        arrow(draw, (250, 640), (cx, cy), "", width=2)
    dashed_line(draw, (940, 570), (1110, 460))
    label_box(draw, (1030, 495), "<<include>>")
    dashed_line(draw, (940, 570), (1110, 610))
    label_box(draw, (1030, 610), "<<include>>")
    dashed_line(draw, (940, 790), (1110, 760))
    label_box(draw, (1030, 735), "<<include>>")
    dashed_line(draw, (940, 350), (1110, 760))
    label_box(draw, (1045, 555), "<<read>>")
    save(image, "05_uml_use_case.png")


def uml_class() -> None:
    image, draw = canvas("UML: диаграмма классов", "Классы и концептуальные записи, выделенные из restaurant_booking.py")
    class_box(
        draw,
        (80, 245, 610, 775),
        "RestaurantApp",
        ["- root: Tk", "- system: BookingSystem", "- interval_var: StringVar", "- message_text: Text"],
        [
            "+ create_main_window()",
            "+ show_places()",
            "+ open_booking_dialog()",
            "+ confirm_booking(...)",
            "+ open_cancel_dialog()",
            "+ confirm_cancel(...)",
        ],
    )
    class_box(
        draw,
        (760, 220, 1310, 860),
        "BookingSystem",
        ["- two_seat_tables: list[str]", "- four_seat_tables: list[str]", "- bookings: list[dict]"],
        [
            "+ load_bookings()",
            "+ save_bookings()",
            "+ create_booking(...)",
            "+ cancel_booking(...)",
            "+ get_interval_info(interval)",
            "+ choose_tables(...)",
            "+ choose_quick_tables(...)",
            "+ get_table_state(...)",
        ],
    )
    class_box(
        draw,
        (1380, 255, 1710, 585),
        "BookingRecord",
        ["+ id: int", "+ name: str", "+ visitors: int", "+ interval: str", "+ quick_dinner: bool"],
        ["+ tables: list[TableAssignment]"],
    )
    class_box(
        draw,
        (1380, 730, 1710, 960),
        "TableAssignment",
        ["+ id: str", "+ half: int"],
        ["0 - полный интервал", "1/2 - полуинтервал"],
    )
    arrow(draw, (610, 510), (760, 510), "использует")
    arrow(draw, (1310, 420), (1380, 420), "1 : 0..*")
    arrow(draw, (1545, 585), (1545, 730), "1 : 1..*")
    store(draw, (760, 970, 1310, 1125), "Файл", "bookings.txt\nJSON-массив BookingRecord")
    arrow(draw, (1035, 860), (1035, 970), "читает / записывает")
    save(image, "06_uml_class.png")


def uml_sequence() -> None:
    image, draw = canvas("UML: диаграмма последовательности", "Основной поток создания брони и альтернативы ошибок")
    names = ["Клиент", "RestaurantApp", "BookingSystem", "bookings.txt", "Popup"]
    xs = [160, 520, 900, 1260, 1600]
    top = 245
    bottom = 1055
    for x, name in zip(xs, names):
        rect(draw, (x - 115, top, x + 115, top + 70), name, fill=WHITE, fnt=SMALL_BOLD)
        dashed_line(draw, (x, top + 70), (x, bottom), fill="#9aa5b1", width=2)

    y = 360
    arrow(draw, (160, y), (520, y), "1. нажать «Забронировать стол»")
    y += 80
    arrow(draw, (520, y), (160, y), "2. открыть диалог")
    y += 80
    arrow(draw, (160, y), (520, y), "3. имя, количество,\nинтервал, быстрый ужин")
    y += 85
    arrow(draw, (520, y), (900, y), "4. create_booking(...)")
    y += 80
    arrow(draw, (900, y), (900, y + 1), "5. проверить ввод\nи подобрать столы")
    y += 80
    arrow(draw, (900, y), (1260, y), "6. save_bookings()")
    y += 70
    arrow(draw, (1260, y), (900, y), "7. JSON сохранен")
    y += 70
    arrow(draw, (900, y), (520, y), "8. booking{id}")
    y += 75
    arrow(draw, (520, y), (1600, y), "9. show_success_dialog")
    y += 70
    arrow(draw, (1600, y), (160, y), "10. имя и номер брони")

    rect(draw, (440, 930, 1510, 1115), fill=RED, outline="#b91c1c")
    draw.text((462, 945), "alt", font=SMALL_BOLD, fill="#b91c1c")
    left_text(
        draw,
        (500, 965, 1480, 1095),
        "Неверные данные или нет свободных столов: BookingSystem возвращает ошибку, RestaurantApp показывает messagebox, диалог бронирования остается открытым.",
        fnt=SMALL,
    )
    save(image, "07_uml_sequence.png")


def uml_state() -> None:
    image, draw = canvas("UML: диаграмма состояний", "Жизненный цикл заявки на бронь")
    ellipse(draw, (135, 545, 185, 595), fill=LINE)
    states = {
        "input": (310, 490, 590, 650, "Вводится"),
        "check": (730, 490, 1010, 650, "Проверяется"),
        "active": (1150, 300, 1450, 460, "Активна"),
        "rejected": (1150, 680, 1450, 840, "Отклонена"),
        "cancel": (1530, 300, 1740, 460, "Отменена"),
    }
    for key, box_data in states.items():
        x1, y1, x2, y2, text = box_data
        rect(draw, (x1, y1, x2, y2), text, fill=BLUE if key != "rejected" else RED, radius=18, fnt=BODY_BOLD)
    arrow(draw, (185, 570), (310, 570), "открыт диалог")
    arrow(draw, (590, 570), (730, 570), "подтвердить")
    arrow(draw, (1010, 540), (1150, 395), "данные верны,\nстол найден", label_offset=(15, -10))
    arrow(draw, (1010, 610), (1150, 760), "ошибка", label_offset=(10, 25))
    arrow(draw, (1450, 380), (1530, 380), "отмена по имени\nи номеру")
    arrow(draw, (1450, 760), (730, 615), "исправить ввод", label_offset=(-15, 40))
    ellipse(draw, (1665, 655, 1740, 730), fill=WHITE, outline=LINE, width=4)
    ellipse(draw, (1685, 675, 1720, 710), fill=LINE)
    arrow(draw, (1635, 460), (1700, 655), "закрыть")
    arrow(draw, (1325, 460), (1700, 655), "день брони завершен", label_offset=(30, -20))
    save(image, "08_uml_state.png")


def uml_activity() -> None:
    image, draw = canvas("UML: диаграмма деятельности", "Основные действия главного окна")
    ellipse(draw, (850, 190, 900, 240), fill=LINE)
    rect(draw, (710, 295, 1040, 395), "Выбрать действие", fill=BLUE, radius=12, fnt=SMALL_BOLD)
    diamond(draw, (750, 470, 1000, 610), "Тип действия?")

    rect(draw, (155, 690, 455, 805), "Показать занятость\nпо интервалу", fill=GREEN, radius=12, fnt=SMALL_BOLD)
    rect(draw, (660, 690, 1020, 805), "Ввести имя,\nколичество и интервал", fill=BLUE, radius=12, fnt=SMALL_BOLD)
    rect(draw, (1260, 690, 1605, 805), "Ввести имя\nи номер брони", fill=BLUE, radius=12, fnt=SMALL_BOLD)
    diamond(draw, (710, 875, 970, 1015), "Данные корректны\nи стол есть?")
    rect(draw, (1060, 895, 1345, 995), "Сохранить бронь\nи показать номер", fill=GREEN, radius=12, fnt=SMALL_BOLD)
    rect(draw, (390, 895, 625, 995), "Показать ошибку", fill=RED, radius=12, fnt=SMALL_BOLD)
    rect(draw, (1390, 895, 1660, 995), "Удалить бронь\nили показать ошибку", fill=YELLOW, radius=12, fnt=SMALL_BOLD)
    ellipse(draw, (850, 1120, 925, 1195), fill=WHITE, outline=LINE, width=4)
    ellipse(draw, (870, 1140, 905, 1175), fill=LINE)

    arrow(draw, (875, 240), (875, 295))
    arrow(draw, (875, 395), (875, 470))
    arrow(draw, (750, 540), (455, 745), "посмотреть")
    arrow(draw, (875, 610), (840, 690), "бронь")
    arrow(draw, (1000, 540), (1260, 745), "отмена")
    arrow(draw, (840, 805), (840, 875))
    arrow(draw, (970, 945), (1060, 945), "да")
    arrow(draw, (710, 945), (625, 945), "нет")
    arrow(draw, (1530, 805), (1530, 895))
    poly_arrow(draw, [(305, 805), (305, 1155), (850, 1155)])
    poly_arrow(draw, [(1205, 995), (1205, 1155), (925, 1155)])
    poly_arrow(draw, [(510, 995), (510, 1155), (850, 1155)])
    poly_arrow(draw, [(1525, 995), (1525, 1155), (925, 1155)])
    save(image, "09_uml_activity.png")


def uml_component() -> None:
    image, draw = canvas("UML: диаграмма компонентов", "Физические компоненты программного комплекса")
    component(draw, (150, 335, 545, 520), "RestaurantApp\nTkinter GUI", fill=BLUE)
    component(draw, (730, 335, 1125, 520), "BookingSystem\nbusiness logic", fill=GREEN)
    component(draw, (1310, 335, 1660, 520), "JSON persistence", fill=YELLOW)
    store(draw, (1310, 720, 1660, 880), "Artifact", "bookings.txt\nтекущие брони")
    rect(draw, (150, 735, 545, 880), "tkinter.messagebox\nи ttk widgets", fill=WHITE, fnt=SMALL_BOLD)
    arrow(draw, (545, 430), (730, 430), "create/cancel/show")
    arrow(draw, (1125, 430), (1310, 430), "load/save JSON")
    arrow(draw, (1485, 520), (1485, 720), "read/write")
    arrow(draw, (350, 735), (350, 520), "GUI events")
    save(image, "10_uml_component.png")


def uml_deployment() -> None:
    image, draw = canvas("UML: диаграмма развертывания", "Локальное настольное приложение")
    rect(draw, (120, 300, 1680, 1020), fill=WHITE, outline=LINE)
    draw.text((150, 328), "node: компьютер пользователя", font=BODY_BOLD, fill=INK)
    rect(draw, (205, 435, 730, 620), "ОС с Python 3\nи Tkinter", fill=BLUE, fnt=BODY_BOLD)
    rect(draw, (875, 435, 1485, 620), "artifact:\nrestaurant_booking.py", fill=GREEN, fnt=BODY_BOLD)
    rect(draw, (875, 750, 1485, 900), "artifact:\nbookings.txt", fill=YELLOW, fnt=BODY_BOLD)
    rect(draw, (205, 750, 730, 900), "Устройства ввода/вывода:\nэкран, клавиатура, мышь", fill=WHITE, fnt=BODY_BOLD)
    arrow(draw, (730, 525), (875, 525), "запускает")
    arrow(draw, (1180, 620), (1180, 750), "локальный доступ\nк файлу")
    arrow(draw, (730, 825), (875, 525), "действия пользователя", label_offset=(-40, -20))
    save(image, "11_uml_deployment.png")


def uml_timing() -> None:
    image, draw = canvas("UML: временная диаграмма", "Интервал 17:00-19:00 и быстрый ужин как половина интервала")
    x0, x1, x2 = 330, 1030, 1730
    y_base = 300
    for x, label in [(x0, "17:00"), (x1, "18:00"), (x2, "19:00")]:
        draw.line((x, 230, x, 1020), fill="#cbd5e1", width=3)
        draw.text((x - 36, 200), label, font=SMALL_BOLD, fill=MUTED)
    rows = [
        (335, "T2-1", [("бронь #1\nполный интервал", x0, x2, BLUE)]),
        (555, "T2-2", [("быстрый ужин #2", x0, x1, GREEN), ("быстрый ужин #3", x1, x2, GREEN)]),
        (775, "BookingSystem", [("подбор", 520, 700, YELLOW), ("сохранение", 700, 860, YELLOW)]),
    ]
    for y, name, segments in rows:
        draw.text((80, y + 32), name, font=BODY_BOLD, fill=INK)
        draw.line((x0, y + 70, x2, y + 70), fill=LINE, width=3)
        draw.text((x0 - 120, y + 42), "свободно", font=TINY, fill=MUTED)
        for label, sx, ex, color in segments:
            draw.rounded_rectangle((sx, y + 20, ex, y + 120), radius=8, fill=color, outline=LINE, width=3)
            center_text(draw, (sx, y + 20, ex, y + 120), label, fnt=SMALL_BOLD)
    arrow(draw, (690, 895), (690, 675), "выбран полуинтервал")
    arrow(draw, (850, 895), (850, 675), "запись в файл")
    rect(
        draw,
        (330, 1060, 1730, 1165),
        "Ограничение: обычная бронь занимает весь двухчасовой интервал; быстрый ужин занимает одну половину, поэтому второй быстрый заказ может использовать тот же стол в другой половине.",
        fill=WHITE,
        fnt=SMALL_BOLD,
    )
    save(image, "12_uml_timing.png")


def uml_object() -> None:
    image, draw = canvas("UML: диаграмма объектов", "Снимок состояния по bookings.txt")
    class_box(
        draw,
        (130, 285, 580, 580),
        "booking1: BookingRecord",
        ["id = 1", "name = Никита", "visitors = 2", "interval = 17:00-19:00", "quick_dinner = false"],
        ["tables = [assign1]"],
        fill=WHITE,
    )
    class_box(
        draw,
        (735, 285, 1135, 555),
        "assign1: TableAssignment",
        ["id = T2-1", "half = 0"],
        ["полный интервал"],
        fill=WHITE,
    )
    class_box(
        draw,
        (1290, 285, 1690, 555),
        "t2_1: RestaurantTable",
        ["table_id = T2-1", "capacity = 2", "movable = false"],
        ["тип: стол на 2 места"],
        fill=WHITE,
    )
    class_box(
        draw,
        (130, 760, 580, 1015),
        "system: BookingSystem",
        ["two_seat_tables = 4", "four_seat_tables = 4", "bookings = [booking1]"],
        ["DATA_FILE = bookings.txt"],
        fill=WHITE,
    )
    class_box(
        draw,
        (735, 760, 1135, 1015),
        "file: bookings.txt",
        ["format = JSON", "records = 1"],
        ["хранит текущие брони"],
        fill=WHITE,
    )
    arrow(draw, (580, 425), (735, 425), "tables")
    arrow(draw, (1135, 420), (1290, 420), "id")
    arrow(draw, (580, 890), (735, 890), "save/load")
    poly_arrow(draw, [(355, 760), (355, 650), (355, 580)], "bookings", label_pos=(430, 665))
    save(image, "13_uml_object.png")


def readme() -> None:
    (OUT_DIR / "README.md").write_text(
        """# Диаграммы курсового проекта

Диаграммы построены по `restaurant_booking.py`, `bookings.txt` и требованиям разделов 3.2, 3.3, 3.4 методического пособия.

## Состав

1. `01_dfd_context.png` - контекстная DFD.
2. `02_dfd_level_1.png` - DFD декомпозиции процессов.
3. `03_idef0_context_a0.png` - IDEF0 A-0.
4. `04_idef1x_erd.png` - IDEF1X / ERD.
5. `05_uml_use_case.png` - UML Use Case.
6. `06_uml_class.png` - UML Class.
7. `07_uml_sequence.png` - UML Sequence.
8. `08_uml_state.png` - UML State.
9. `09_uml_activity.png` - UML Activity.
10. `10_uml_component.png` - UML Component.
11. `11_uml_deployment.png` - UML Deployment.
12. `12_uml_timing.png` - UML Timing.
13. `13_uml_object.png` - UML Object.

## Проверка

- DFD содержит внешнюю сущность, процессы с глагольными названиями, именованные потоки данных и хранилища.
- IDEF0 оформлена как контекст A-0 с входами, управлениями, выходами и механизмами.
- IDEF1X показывает сущности, атрибуты и связи текущего JSON-хранилища.
- UML-набор покрывает варианты использования, классы, главный сценарий бронирования, состояния, деятельность, компоненты, развертывание, временные ограничения и снимок объектов.

## Замечание по требованиям

В текущем коде и `bookings.txt` не реализовано хранение даты рождения клиента, кулинарных предпочтений и суммы заказов. Эти поля не включены в диаграммы как действующая часть системы, чтобы графический материал соответствовал фактической реализации.
""",
        encoding="utf-8",
    )


def main() -> None:
    dfd_context()
    dfd_level_1()
    idef0_context()
    idef1x_erd()
    use_case()
    uml_class()
    uml_sequence()
    uml_state()
    uml_activity()
    uml_component()
    uml_deployment()
    uml_timing()
    uml_object()
    readme()


if __name__ == "__main__":
    main()
