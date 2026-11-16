import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from services.action_catalog import CONFIRM_EACH_TIME, WAIT_ACTION


class ActionExecutionError(RuntimeError):
    pass


class ActionCancelledError(RuntimeError):
    pass


class ActionRunner:
    def __init__(self, parent=None, reload_callback=None):
        self.parent = parent
        self.reload_callback = reload_callback
        self._pressed_mouse_button = False
        self._tray_icon = None

    @staticmethod
    def requires_confirmation(action):
        return action in CONFIRM_EACH_TIME

    def confirm(self, action, params):
        details = f"\n\nПараметри: {params}" if params else ""
        answer = QMessageBox.question(
            self.parent,
            "Підтвердження дії",
            f"Виконати дію «{action}» зараз?{details}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def execute(self, action, params=None):
        params = params or {}
        if action in ("Немає", WAIT_ACTION):
            return
        if self.requires_confirmation(action) and not self.confirm(action, params):
            raise ActionCancelledError(f"Дію «{action}» скасовано користувачем.")
        try:
            import pyautogui
        except ImportError:
            pyautogui = None
        handled_errors = (
            OSError,
            ValueError,
            TypeError,
            subprocess.SubprocessError,
        )
        if pyautogui is not None:
            handled_errors += (pyautogui.FailSafeException,)
        try:
            self._execute(action, params)
        except handled_errors as error:
            raise ActionExecutionError(f"Дія «{action}» не виконана: {error}") from error

    def _execute(self, action, params):
        if action in {
            "Відкрити Telegram",
            "Відкрити Chrome",
            "Відкрити Steam",
            "Відкрити Discord",
            "Відкрити OBS Studio",
            "Відкрити Калькулятор",
            "Відкрити Блокнот",
            "Відкрити Провідник",
            "Відкрити Диспетчер завдань",
            "Відкрити Термінал",
            "Відкрити Налаштування системи",
            "Відкрити Завантаження",
            "Відкрити Робочий стіл",
            "Відкрити Кошик",
        }:
            self._open_builtin(action)
            return
        if action == "Відкрити програму":
            self._start_path(params.get("path"))
            return
        if action == "Відкрити папку":
            self._start_path(params.get("path"))
            return
        if action == "Відкрити посилання":
            url = self._required(params, "url")
            if not webbrowser.open(url, new=2):
                raise ActionExecutionError(f"Не вдалося відкрити посилання: {url}")
            return
        if action in {
            "Відкрити нову вкладку",
            "Закрити поточну вкладку",
            "Відновити закриту вкладку",
            "Наступна вкладка",
            "Попередня вкладка",
            "Оновити сторінку (F5)",
            "Переключити програму (Alt + Tab)",
            "Закріпити вікно ліворуч",
            "Закріпити вікно праворуч",
            "Створити новий віртуальний робочий стіл",
            "Наступний віртуальний робочий стіл",
            "Попередній віртуальний робочий стіл",
            "Видалити поточний віртуальний робочий стіл",
            "Показати режим Task View (Win + Tab)",
            "Заблокувати екран (Win + L)",
            "Згорнути вікно",
            "Розгорнути вікно",
            "Відновити розмір вікна",
            "Згорнути всі вікна",
            "Закрити активну програму",
            "Закрити поточне вікно",
        }:
            self._window_action(action)
            return
        if action in {
            "Гучність +",
            "Гучність -",
            "Вимкнути/Увімкнути звук",
            "Пауза/Плей",
            "Наступний трек",
            "Попередній трек",
            "Зупинити відтворення",
            "Перемотати назад (10 сек)",
            "Перемотати вперед (10 сек)",
            "Встановити гучність на %",
        }:
            self._media_action(action, params)
            return
        if action in {
            "Яскравість +",
            "Яскравість -",
            "Встановити яскравість на %",
        }:
            self._brightness_action(action, params)
            return
        if action in {
            "Перемістити курсор у координати",
            "Лівий клік",
            "Правий клік",
            "Подвійний клік",
            "Потрійний клік",
            "Затиснути ліву кнопку",
            "Відпустити ліву кнопку",
            "Прокрутка вгору",
            "Прокрутка вниз",
            "Прокрутка вліво",
            "Прокрутка вправо",
            "Натиснути гарячі клавіші",
            "Ввести текст",
            "Натиснути Enter",
            "Натиснути Escape",
            "Натиснути Space",
            "Натиснути Backspace",
            "Натиснути Tab",
            "Скопіювати виділене",
            "Вставити з буфера",
            "Вирізати виділене",
            "Скопіювати кастомний текст у буфер",
            "Очистити буфер обміну",
        }:
            self._input_action(action, params)
            return
        if action in {
            "Скріншот всього екрана",
            "Скріншот активного вікна",
            "Скріншот області",
            "Зберегти скріншот у файл",
            "Скопіювати скріншот у буфер",
        }:
            self._screenshot_action(action, params)
            return
        if action in {
            "Перевести ПК у режим сну",
            "Перевести ПК у режим гібернації",
            "Перезавантажити ПК",
            "Вимкнути ПК",
            "Вимкнути ПК через N хвилин",
            "Скасувати таймер вимкнення",
            "Вийти з облікового запису",
        }:
            self._power_action(action, params)
            return
        if action == "Оновити конфігурацію":
            if self.reload_callback is None:
                raise ActionExecutionError("Оновлення конфігурації недоступне.")
            self.reload_callback()
            return
        if action == "Показати системне сповіщення (Toast)":
            title = str(params.get("title", "NeuralControl"))
            text = self._required(params, "text")
            if not QSystemTrayIcon.isSystemTrayAvailable():
                raise ActionExecutionError("Системний трей недоступний для Toast.")
            self._tray_icon = QSystemTrayIcon(self.parent)
            self._tray_icon.setIcon(self.parent.windowIcon())
            self._tray_icon.show()
            self._tray_icon.showMessage(
                title,
                text,
                QSystemTrayIcon.Information,
                5000,
            )
            return
        if action == "Режим Мишки":
            raise ActionExecutionError(
                "Режим Мишки потрібно запускати як правило, а не як звичайну дію."
            )
        if action == "Виконати консольну команду":
            command = self._required(params, "command")
            subprocess.Popen(command, shell=True)
            return
        if action == "Запустити Python скрипт":
            path = Path(self._required(params, "path")).expanduser()
            if not path.is_file():
                raise FileNotFoundError(f"Скрипт не знайдено: {path}")
            subprocess.Popen([sys.executable, str(path)])
            return
        if action in {"Очистити Кошик"}:
            self._require_windows()
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Clear-RecycleBin -Force",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return
        if action == "Примусово закрити програму":
            self._force_close_active_window()
            return
        if action in {
            "Вимкнути/Увімкнути мікрофон",
            "Переключити пристрій виводу звуку",
            "Почати/Зупинити запис екрана",
            "Зберегти останні N хвилин повтору",
            "Увімкнути/Вимкнути Нічний режим",
            "Увімкнути/Вимкнути Wi-Fi",
            "Увімкнути/Вимкнути Bluetooth",
            "Увімкнути/Вимкнути режим 'Не турбувати'",
            "Переключити джерело монітора",
        }:
            raise ActionExecutionError(
                f"Дію «{action}» не реалізовано для цієї системи."
            )
        raise ActionExecutionError(f"Непідтримувана дія: {action}")

    def _open_builtin(self, action):
        if action == "Відкрити Telegram":
            self._open_url("https://web.telegram.org")
        elif action == "Відкрити Chrome":
            try:
                browser = webbrowser.get("chrome")
            except webbrowser.Error as error:
                raise ActionExecutionError(
                    "Chrome не знайдено або не зареєстровано у системі."
                ) from error
            if not browser.open_new_tab("https://www.google.com"):
                raise ActionExecutionError("Chrome не відкрив сторінку.")
        elif action in {"Відкрити Завантаження", "Відкрити Робочий стіл"}:
            import ctypes

            self._require_windows()
            path = ctypes.create_unicode_buffer(260)
            result = ctypes.windll.shell32.SHGetFolderPathW(
                None,
                0x8000 if action == "Відкрити Завантаження" else 0,
                None,
                0,
                path,
            )
            if result != 0:
                raise ActionExecutionError(f"Не вдалося знайти папку {action}.")
            os.startfile(path.value)
        elif action == "Відкрити Кошик":
            self._require_windows()
            os.startfile("shell:RecycleBinFolder")
        elif action == "Відкрити Калькулятор":
            self._require_windows()
            subprocess.Popen(["calc.exe"])
        elif action == "Відкрити Блокнот":
            self._require_windows()
            subprocess.Popen(["notepad.exe"])
        elif action == "Відкрити Провідник":
            self._require_windows()
            subprocess.Popen(["explorer.exe"])
        elif action == "Відкрити Диспетчер завдань":
            self._require_windows()
            subprocess.Popen(["taskmgr.exe"])
        elif action == "Відкрити Термінал":
            self._require_windows()
            subprocess.Popen(["wt.exe"])
        elif action == "Відкрити Налаштування системи":
            self._require_windows()
            os.startfile("ms-settings:")
        elif action == "Відкрити Steam":
            self._open_url("steam://open/main")
        elif action == "Відкрити Discord":
            self._open_url("https://discord.com/app")
        elif action == "Відкрити OBS Studio":
            if sys.platform == "win32":
                subprocess.Popen(["obs64.exe"])
            else:
                subprocess.Popen(["obs"])
        else:
            raise ActionExecutionError(f"Невідома вбудована програма: {action}")

    def _window_action(self, action):
        keys = {
            "Відкрити нову вкладку": ("ctrl", "t"),
            "Закрити поточну вкладку": ("ctrl", "w"),
            "Відновити закриту вкладку": ("ctrl", "shift", "t"),
            "Наступна вкладка": ("ctrl", "tab"),
            "Попередня вкладка": ("ctrl", "shift", "tab"),
            "Оновити сторінку (F5)": ("f5",),
            "Переключити програму (Alt + Tab)": ("alt", "tab"),
            "Закріпити вікно ліворуч": ("win", "left"),
            "Закріпити вікно праворуч": ("win", "right"),
            "Створити новий віртуальний робочий стіл": ("win", "ctrl", "d"),
            "Наступний віртуальний робочий стіл": ("win", "ctrl", "right"),
            "Попередній віртуальний робочий стіл": ("win", "ctrl", "left"),
            "Видалити поточний віртуальний робочий стіл": (
                "win",
                "ctrl",
                "f4",
            ),
            "Показати режим Task View (Win + Tab)": ("win", "tab"),
            "Заблокувати екран (Win + L)": ("win", "l"),
            "Згорнути всі вікна": ("win", "d"),
            "Закрити активну програму": ("alt", "f4"),
            "Закрити поточне вікно": ("alt", "f4"),
            "Відновити розмір вікна": ("win", "down"),
            "Згорнути вікно": ("win", "down"),
            "Розгорнути вікно": ("win", "up"),
        }
        self._hotkey(*keys[action])

    def _media_action(self, action, params):
        keys = {
            "Гучність +": "volumeup",
            "Гучність -": "volumedown",
            "Вимкнути/Увімкнути звук": "volumemute",
            "Пауза/Плей": "playpause",
            "Наступний трек": "nexttrack",
            "Попередній трек": "prevtrack",
            "Зупинити відтворення": "stop",
            "Перемотати назад (10 сек)": "left",
            "Перемотати вперед (10 сек)": "right",
        }
        pyautogui = self._get_pyautogui()
        if action == "Встановити гучність на %":
            percent = int(params["percent"])
            if not 0 <= percent <= 100:
                raise ValueError("Гучність має бути від 0 до 100.")
            pyautogui.press("volumedown", presses=50, _pause=False)
            for _ in range(round(percent / 2)):
                pyautogui.press("volumeup", _pause=False)
            return
        pyautogui.press(keys[action], _pause=False)

    def _input_action(self, action, params):
        pyautogui = self._get_pyautogui()
        key_actions = {
            "Натиснути Enter": "enter",
            "Натиснути Escape": "esc",
            "Натиснути Space": "space",
            "Натиснути Backspace": "backspace",
            "Натиснути Tab": "tab",
            "Скопіювати виділене": ("ctrl", "c"),
            "Вставити з буфера": ("ctrl", "v"),
            "Вирізати виділене": ("ctrl", "x"),
        }
        if action in key_actions:
            value = key_actions[action]
            pyautogui.hotkey(*value, _pause=False) if isinstance(value, tuple) else pyautogui.press(value, _pause=False)
        elif action == "Перемістити курсор у координати":
            pyautogui.moveTo(int(params["x"]), int(params["y"]), duration=0, _pause=False)
        elif action in {"Лівий клік", "Правий клік", "Подвійний клік", "Потрійний клік"}:
            clicks = {"Подвійний клік": 2, "Потрійний клік": 3}.get(action, 1)
            button = "right" if action == "Правий клік" else "left"
            pyautogui.click(clicks=clicks, button=button, _pause=False)
        elif action == "Затиснути ліву кнопку":
            pyautogui.mouseDown(button="left", _pause=False)
            self._pressed_mouse_button = True
        elif action == "Відпустити ліву кнопку":
            pyautogui.mouseUp(button="left", _pause=False)
            self._pressed_mouse_button = False
        elif action.startswith("Прокрутка "):
            directions = {
                "Прокрутка вгору": ("scroll", 3),
                "Прокрутка вниз": ("scroll", -3),
                "Прокрутка вправо": ("hscroll", 3),
                "Прокрутка вліво": ("hscroll", -3),
            }
            method, amount = directions[action]
            getattr(pyautogui, method)(amount, _pause=False)
        elif action == "Натиснути гарячі клавіші":
            keys = [key.strip().lower() for key in params["hotkey"].split("+")]
            if not keys or any(not key for key in keys):
                raise ValueError("Вкажіть коректну комбінацію клавіш.")
            pyautogui.hotkey(*keys, _pause=False)
        elif action == "Ввести текст":
            pyautogui.write(str(params["text"]), interval=0.01, _pause=False)
        elif action == "Скопіювати кастомний текст у буфер":
            QApplication.clipboard().setText(str(params["text"]))
        elif action == "Очистити буфер обміну":
            QApplication.clipboard().clear()

    def _screenshot_action(self, action, params):
        pyautogui = self._get_pyautogui()
        region = None
        if action == "Скріншот активного вікна":
            self._require_windows()
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            window = user32.GetForegroundWindow()
            rect = wintypes.RECT()
            if not window or not user32.GetWindowRect(window, ctypes.byref(rect)):
                raise ActionExecutionError("Не вдалося визначити активне вікно.")
            region = (
                rect.left,
                rect.top,
                rect.right - rect.left,
                rect.bottom - rect.top,
            )
        elif action == "Скріншот області":
            region = tuple(
                int(params[key]) for key in ("x", "y", "width", "height")
            )
        image = pyautogui.screenshot(region=region)
        if action == "Скопіювати скріншот у буфер":
            rgb_image = image.convert("RGB")
            width, height = rgb_image.size
            clipboard_image = QImage(
                rgb_image.tobytes(),
                width,
                height,
                width * 3,
                QImage.Format_RGB888,
            ).copy()
            QApplication.clipboard().setImage(clipboard_image)
            return
        if action == "Скріншот всього екрана":
            path = self._screenshot_path()
        elif action == "Скріншот області" and not params.get("path"):
            path = self._screenshot_path()
        else:
            path = Path(self._required(params, "path")).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(path))

    def _power_action(self, action, params):
        self._require_windows()
        commands = {
            "Перезавантажити ПК": ["shutdown", "/r", "/t", "0"],
            "Вимкнути ПК": ["shutdown", "/s", "/t", "0"],
            "Скасувати таймер вимкнення": ["shutdown", "/a"],
            "Вийти з облікового запису": ["shutdown", "/l"],
            "Перевести ПК у режим сну": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            "Перевести ПК у режим гібернації": ["shutdown", "/h"],
        }
        if action == "Вимкнути ПК через N хвилин":
            minutes = int(params["minutes"])
            if minutes < 1:
                raise ValueError("Укажіть щонайменше одну хвилину.")
            commands[action] = ["shutdown", "/s", "/t", str(minutes * 60)]
        subprocess.Popen(commands[action])

    def _brightness_action(self, action, params):
        self._require_windows()
        if action == "Встановити яскравість на %":
            brightness = int(params["percent"])
            if not 0 <= brightness <= 100:
                raise ValueError("Яскравість має бути від 0 до 100.")
        else:
            query = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "(Get-WmiObject -Namespace root/WMI "
                    "-Class WmiMonitorBrightness | Select-Object -First 1 "
                    "-ExpandProperty CurrentBrightness)",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            current = int(query.stdout.strip())
            delta = 10 if action == "Яскравість +" else -10
            brightness = max(0, min(100, current + delta))

        command = (
            "$monitor = Get-WmiObject -Namespace root/WMI "
            "-Class WmiMonitorBrightnessMethods | Select-Object -First 1; "
            f"$monitor.WmiSetBrightness(1, {brightness})"
        )
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _force_close_active_window():
        ActionRunner._require_windows()
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        window = user32.GetForegroundWindow()
        process_id = wintypes.DWORD()
        if not window or not user32.GetWindowThreadProcessId(
            window, ctypes.byref(process_id)
        ):
            raise ActionExecutionError("Не вдалося визначити активний процес.")
        if process_id.value in (0, os.getpid()):
            raise ActionExecutionError(
                "Примусове закриття NeuralControl заблоковано."
            )
        subprocess.run(
            ["taskkill", "/PID", str(process_id.value), "/F"],
            check=True,
            capture_output=True,
            text=True,
        )

    def _start_path(self, raw_path):
        if not raw_path:
            raise ValueError("Не вказано шлях.")
        path = Path(str(raw_path)).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Шлях не знайдено: {path}")
        if sys.platform == "win32":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])

    @staticmethod
    def _open_url(url):
        if not webbrowser.open(url, new=2):
            raise ActionExecutionError(f"Не вдалося відкрити: {url}")

    @staticmethod
    def _required(params, key):
        value = str(params.get(key, "")).strip()
        if not value:
            raise ValueError(f"Потрібно заповнити параметр «{key}».")
        return value

    @staticmethod
    def _require_windows():
        if sys.platform != "win32":
            raise ActionExecutionError("Ця дія доступна лише у Windows.")

    @staticmethod
    def _get_pyautogui():
        try:
            import pyautogui
        except ImportError as error:
            raise ActionExecutionError(
                f"Модуль pyautogui недоступний: {error}"
            ) from error
        return pyautogui

    @staticmethod
    def _hotkey(*keys):
        ActionRunner._get_pyautogui().hotkey(*keys, _pause=False)

    @staticmethod
    def _screenshot_path():
        from datetime import datetime

        from core.types import DATA_DIR

        return DATA_DIR / "screenshots" / datetime.now().strftime(
            "screenshot_%Y%m%d_%H%M%S.png"
        )

    def release_mouse_button(self):
        if not self._pressed_mouse_button:
            return
        pyautogui = self._get_pyautogui()
        try:
            pyautogui.mouseUp(button="left", _pause=False)
        except pyautogui.FailSafeException as error:
            raise ActionExecutionError(
                f"Не вдалося відпустити ліву кнопку миші: {error}"
            ) from error
        else:
            self._pressed_mouse_button = False
