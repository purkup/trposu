import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


DATA_FILE = Path(__file__).with_name("bookings.txt")

TIME_INTERVALS = [
    "17:00 - 19:00",
    "19:00 - 21:00",
    "21:00 - 23:00",
]

TWO_SEAT_TABLES = 4
FOUR_SEAT_TABLES = 4


class BookingSystem:
    def __init__(self):
        self.two_seat_tables = [f"T2-{number}" for number in range(1, TWO_SEAT_TABLES + 1)]
        self.four_seat_tables = [f"T4-{number}" for number in range(1, FOUR_SEAT_TABLES + 1)]
        self.bookings = self.load_bookings()

    def load_bookings(self):
        if not DATA_FILE.exists():
            return []

        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def save_bookings(self):
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.bookings, file, ensure_ascii=False, indent=2)

    def get_next_id(self):
        if not self.bookings:
            return 1
        return max(booking["id"] for booking in self.bookings) + 1

    def get_table_state(self, table_id, interval):
        is_full_busy = False
        busy_halves = set()

        for booking in self.bookings:
            if booking["interval"] != interval:
                continue

            for table in booking["tables"]:
                if table["id"] != table_id:
                    continue

                if table["half"] == 0:
                    is_full_busy = True
                else:
                    busy_halves.add(table["half"])

        return is_full_busy, busy_halves

    def choose_tables(self, table_ids, count, interval, quick_dinner):
        if quick_dinner:
            return self.choose_quick_tables(table_ids, count, interval)

        free_tables = []
        for table_id in table_ids:
            is_full_busy, busy_halves = self.get_table_state(table_id, interval)
            if not is_full_busy and not busy_halves:
                free_tables.append({"id": table_id, "half": 0})

        if len(free_tables) < count:
            return None
        return free_tables[:count]

    def choose_quick_tables(self, table_ids, count, interval):
        best_tables = None
        best_half_busy_count = -1

        for half in (1, 2):
            candidates = []

            for table_id in table_ids:
                is_full_busy, busy_halves = self.get_table_state(table_id, interval)
                if is_full_busy or half in busy_halves:
                    continue

                has_other_half_busy = bool(busy_halves)
                candidates.append((not has_other_half_busy, table_id))

            if len(candidates) < count:
                continue

            candidates.sort()
            selected = [{"id": table_id, "half": half} for _, table_id in candidates[:count]]
            half_busy_count = sum(1 for has_no_busy_half, _ in candidates[:count] if not has_no_busy_half)

            if half_busy_count > best_half_busy_count:
                best_tables = selected
                best_half_busy_count = half_busy_count

        return best_tables

    def create_booking(self, name, visitors, interval, quick_dinner):
        name = name.strip()
        if not name:
            raise ValueError("Введите имя клиента.")

        if visitors < 1:
            raise ValueError("Количество посетителей должно быть больше нуля.")

        if interval not in TIME_INTERVALS:
            raise ValueError("Выберите корректный интервал времени.")

        if visitors <= 2:
            tables = self.choose_tables(self.two_seat_tables, 1, interval, quick_dinner)
            if tables is None:
                tables = self.choose_tables(self.four_seat_tables, 1, interval, quick_dinner)
        else:
            needed_tables = math.ceil(visitors / 4)
            tables = self.choose_tables(self.four_seat_tables, needed_tables, interval, quick_dinner)

        if tables is None:
            raise ValueError("На выбранное время нет подходящих свободных столов.")

        booking = {
            "id": self.get_next_id(),
            "name": name,
            "visitors": visitors,
            "interval": interval,
            "quick_dinner": quick_dinner,
            "tables": tables,
        }

        self.bookings.append(booking)
        self.save_bookings()
        return booking

    def cancel_booking(self, name, booking_id):
        name = name.strip()

        for booking in self.bookings:
            if booking["id"] == booking_id and booking["name"].lower() == name.lower():
                self.bookings.remove(booking)
                self.save_bookings()
                return True

        return False

    def get_interval_info(self, interval):
        lines = [
            f"Интервал: {interval}",
            f"В ресторане: {TWO_SEAT_TABLES} столов на 2 места и {FOUR_SEAT_TABLES} столов на 4 места.",
            "",
        ]

        interval_bookings = [
            booking for booking in self.bookings
            if booking["interval"] == interval
        ]

        if not interval_bookings:
            lines.append("На этот интервал броней нет.")
            return "\n".join(lines)

        two_table_ids = set()
        four_table_ids = set()
        quick_parts_2 = 0
        quick_parts_4 = 0
        full_tables_2 = 0
        full_tables_4 = 0

        for booking in interval_bookings:
            for table in booking["tables"]:
                if table["id"].startswith("T2"):
                    two_table_ids.add(table["id"])
                    if table["half"] == 0:
                        full_tables_2 += 1
                    else:
                        quick_parts_2 += 1
                else:
                    four_table_ids.add(table["id"])
                    if table["half"] == 0:
                        full_tables_4 += 1
                    else:
                        quick_parts_4 += 1

        lines.extend([
            f"Столы на 2 места: задействовано {len(two_table_ids)} из {TWO_SEAT_TABLES}; "
            f"полных броней: {full_tables_2}; быстрых полуинтервалов: {quick_parts_2}.",
            f"Столы на 4 места: задействовано {len(four_table_ids)} из {FOUR_SEAT_TABLES}; "
            f"полных броней: {full_tables_4}; быстрых полуинтервалов: {quick_parts_4}.",
            "",
            "Список броней:",
        ])

        for booking in interval_bookings:
            table_names = []
            for table in booking["tables"]:
                if table["half"] == 0:
                    table_names.append(table["id"])
                else:
                    table_names.append(f"{table['id']} половина {table['half']}")

            dinner_type = "быстрый ужин" if booking["quick_dinner"] else "обычная бронь"
            lines.append(
                f"#{booking['id']} {booking['name']}: "
                f"{booking['visitors']} чел., {dinner_type}, столы: {', '.join(table_names)}"
            )

        return "\n".join(lines)


class RestaurantApp:
    def __init__(self, root):
        self.root = root
        self.system = BookingSystem()

        self.root.title("Бронирование столов в ресторане")
        self.root.geometry("700x440")
        self.root.minsize(640, 380)

        self.interval_var = tk.StringVar(value=TIME_INTERVALS[0])

        self.create_main_window()
        self.show_places()

    def create_main_window(self):
        main_frame = ttk.Frame(self.root, padding=16)
        main_frame.pack(fill="both", expand=True)

        interval_frame = ttk.Frame(main_frame)
        interval_frame.pack(fill="x")

        ttk.Label(interval_frame, text="Интервал времени:").pack(side="left")
        interval_box = ttk.Combobox(
            interval_frame,
            textvariable=self.interval_var,
            values=TIME_INTERVALS,
            state="readonly",
            width=20,
        )
        interval_box.pack(side="left", padx=8)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=12)

        ttk.Button(
            buttons_frame,
            text="Забронировать стол",
            command=self.open_booking_dialog,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons_frame,
            text="Отменить бронь",
            command=self.open_cancel_dialog,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons_frame,
            text="Посмотреть места",
            command=self.show_places,
        ).pack(side="left")

        self.message_text = tk.Text(main_frame, height=16, wrap="word")
        self.message_text.pack(fill="both", expand=True)
        self.message_text.configure(state="disabled")

    def set_message(self, text):
        self.message_text.configure(state="normal")
        self.message_text.delete("1.0", tk.END)
        self.message_text.insert(tk.END, text)
        self.message_text.configure(state="disabled")

    def show_places(self):
        self.set_message(self.system.get_interval_info(self.interval_var.get()))

    def open_booking_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Новая бронь")
        dialog.geometry("360x240")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        name_var = tk.StringVar()
        visitors_var = tk.StringVar()
        quick_var = tk.BooleanVar(value=False)
        interval_var = tk.StringVar(value=self.interval_var.get())

        ttk.Label(frame, text="Имя клиента:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Количество посетителей:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=visitors_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Интервал:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=interval_var,
            values=TIME_INTERVALS,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Checkbutton(
            frame,
            text="Быстрый ужин",
            variable=quick_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=8)

        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=12)

        ttk.Button(buttons, text="Отменить", command=dialog.destroy).pack(side="right")
        ttk.Button(
            buttons,
            text="Подтвердить",
            command=lambda: self.confirm_booking(
                dialog,
                name_var.get(),
                visitors_var.get(),
                interval_var.get(),
                quick_var.get(),
            ),
        ).pack(side="right", padx=(0, 8))

        frame.columnconfigure(1, weight=1)

    def confirm_booking(self, dialog, name, visitors_text, interval, quick_dinner):
        try:
            visitors = int(visitors_text)
        except ValueError:
            messagebox.showerror("Ошибка", "Количество посетителей должно быть целым числом.", parent=dialog)
            return

        try:
            booking = self.system.create_booking(name, visitors, interval, quick_dinner)
        except ValueError as error:
            messagebox.showerror("Ошибка", str(error), parent=dialog)
            return

        self.show_success_dialog(dialog, booking)

    def show_success_dialog(self, booking_dialog, booking):
        popup = tk.Toplevel(booking_dialog)
        popup.title("Бронь создана")
        popup.geometry("320x130")
        popup.resizable(False, False)
        popup.transient(booking_dialog)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=16)
        frame.pack(fill="both", expand=True)

        message = f"{booking['name']}, ваша бронь создана.\nНомер брони: {booking['id']}"
        ttk.Label(frame, text=message, justify="center").pack(expand=True)

        def close_windows():
            popup.destroy()
            booking_dialog.destroy()
            self.interval_var.set(booking["interval"])
            self.show_places()

        ttk.Button(frame, text="добре", command=close_windows).pack(pady=(8, 0))

    def open_cancel_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Отмена брони")
        dialog.geometry("340x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill="both", expand=True)

        name_var = tk.StringVar()
        booking_id_var = tk.StringVar()

        ttk.Label(frame, text="Имя клиента:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=name_var).grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(frame, text="Номер брони:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=booking_id_var).grid(row=1, column=1, sticky="ew", pady=4)

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=14)

        ttk.Button(buttons, text="Отменить", command=dialog.destroy).pack(side="right")
        ttk.Button(
            buttons,
            text="добре",
            command=lambda: self.confirm_cancel(dialog, name_var.get(), booking_id_var.get()),
        ).pack(side="right", padx=(0, 8))

        frame.columnconfigure(1, weight=1)

    def confirm_cancel(self, dialog, name, booking_id_text):
        if not name.strip() or not booking_id_text.strip():
            messagebox.showwarning("Ошибка", "Заполните имя и номер брони.", parent=dialog)
            return

        try:
            booking_id = int(booking_id_text)
        except ValueError:
            messagebox.showwarning("Ошибка", "Номер брони должен быть числом.", parent=dialog)
            return

        if self.system.cancel_booking(name, booking_id):
            messagebox.showinfo("Готово", "Бронь отменена.", parent=dialog)
            dialog.destroy()
            self.show_places()
        else:
            messagebox.showwarning("Ошибка", "Бронь с такими данными не найдена.", parent=dialog)


if __name__ == "__main__":
    root_window = tk.Tk()
    app = RestaurantApp(root_window)
    root_window.mainloop()
