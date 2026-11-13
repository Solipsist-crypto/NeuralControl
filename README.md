# ⚡ NeuralControl — Neural Hand Control System

Система управління ПК жестами рук через вебкамеру.
Нейромережа (MLP) для розпізнавання жестів, дообучення,
кругове меню, режим малювання, робота у фоні.

## Вимоги

- Python 3.10+
- Вебкамера
- Windows 10/11

## Встановлення

```bash
# 1. Клонувати
git clone <url>
cd NeuralControl

# 2. venv
python -m venv venv
venv\Scripts\activate

# 3. Залежності
pip install -r requirements.txt

# 4. Модель MediaPipe → покласти hand_landmarker.task у assets/
Запуск
bash
python main.py
Структура
text
NeuralControl/
├── core/        # Логіка (MediaPipe, моделі, фільтри)
├── services/    # Контролери, потоки, диспетчер дій
├── ui/          # PySide6 інтерфейс
├── labs/        # Лабораторні роботи 4-8
├── data/        # JSON-конфіги, моделі, приклади
└── assets/      # Модель MediaPipe, іконки
Етапи
☑ Етап 0: Архітектура, структура, каркас UI
□ Етап 1: Core (features, hand_tracker, filters)
□ Етап 2: Services (camera, controller, dispatcher)
□ Етап 3: UI Вкладка 1 (управління, overlay, режими)
□ Етап 4: UI Вкладка 2 (навчання, порівняння моделей)
□ Етап 5: UI Вкладки 3-4 (лаби, довідка)
□ Етап 6: Кругове меню + Tray icon
□ Етап 7: Малювання (неон + частинки)
□ Етап 8: Динамічні жести
□ Етап 9: EXE
Ліцензія
MIT

---

## 📄 `NeuralControl/core/__init__.py`

```python
"""Ядро NeuralControl: MediaPipe, моделі, фільтри, реєстр жестів."""