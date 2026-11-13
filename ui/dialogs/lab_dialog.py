import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from core.types import GESTURE_TRANSLATIONS


BG = "#0a0e1a"
CYAN = "#4da6ff"
VIOLET = "#8b5cf6"
TEXT = "#e2e8f0"
MUTED = "#64748b"


class LabDialog(QDialog):
    def __init__(self, training_service, parent=None):
        super().__init__(parent)
        self.training_service = training_service
        self.setWindowTitle("ЛАБОРАТОРНІ РОБОТИ")
        self.setMinimumSize(980, 760)
        self.setStyleSheet(
            f"""
            QDialog {{ background-color: {BG}; color: {TEXT}; }}
            QLabel {{ color: {TEXT}; }}
            QTabWidget::pane {{ border: 1px solid #2a3350; }}
            QTabBar::tab {{
                background-color: #131826;
                color: {MUTED};
                padding: 9px 16px;
            }}
            QTabBar::tab:selected {{ color: {CYAN}; border-bottom: 2px solid {CYAN}; }}
            QPushButton, QSpinBox {{
                background-color: #131826;
                color: {TEXT};
                border: 1px solid #2a3350;
                border-radius: 5px;
                padding: 6px 10px;
            }}
            QPushButton:hover {{ border-color: {CYAN}; color: {CYAN}; }}
            """
        )

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self._build_fuzzy_tab()
        self._build_ga_tab()
        self._build_tree_tab()
        self._build_regression_tab()

        close_button = QPushButton("ЗАКРИТИ")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button, alignment=Qt.AlignRight)

    @staticmethod
    def _create_plot(parent_layout):
        figure = Figure(figsize=(7, 4), dpi=100, facecolor=BG)
        canvas = FigureCanvasQTAgg(figure)
        canvas.setMinimumHeight(460)
        parent_layout.addWidget(canvas, 1)
        axes = figure.add_subplot(111)
        LabDialog._style_axes(axes)
        return figure, canvas, axes

    @staticmethod
    def _style_axes(axes):
        axes.set_facecolor(BG)
        axes.tick_params(colors=TEXT)
        axes.xaxis.label.set_color(TEXT)
        axes.yaxis.label.set_color(TEXT)
        axes.grid(color="#2a3350", alpha=0.7)
        axes.set_axisbelow(True)
        for spine in axes.spines.values():
            spine.set_color("#2a3350")

    def _get_data(self, minimum_samples=2, require_multiple_classes=False):
        X, y = self.training_service.get_raw_data()
        if (
            X.ndim != 2
            or X.shape[0] < minimum_samples
            or X.shape[1] == 0
            or len(y) != X.shape[0]
        ):
            QMessageBox.information(
                self, "Недостатньо даних", "Спочатку додайте приклади жестів."
            )
            return None
        if not np.isfinite(X).all():
            QMessageBox.warning(
                self, "Некоректні дані", "У наборі є нескінченні або відсутні значення."
            )
            return None
        if require_multiple_classes and len(np.unique(y)) < 2:
            QMessageBox.information(
                self, "Недостатньо класів", "Додайте приклади щонайменше двох жестів."
            )
            return None
        return X, y

    def _build_fuzzy_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Кластерів:"))
        self.cluster_spin = QSpinBox()
        self.cluster_spin.setRange(2, 20)
        self.cluster_spin.setValue(3)
        controls.addWidget(self.cluster_spin)

        run_button = QPushButton("Кластеризувати наші жести")
        run_button.clicked.connect(self._run_clustering)
        controls.addWidget(run_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.fuzzy_figure, self.fuzzy_canvas, self.fuzzy_axes = self._create_plot(layout)
        self.tabs.addTab(page, "Fuzzy Logic")

    def _run_clustering(self):
        data = self._get_data(minimum_samples=2)
        if data is None:
            return
        X, _ = data
        if X.shape[1] < 2:
            QMessageBox.information(
                self, "Недостатньо ознак", "Для PCA потрібні щонайменше дві ознаки."
            )
            return

        scaled = StandardScaler().fit_transform(X)
        projected = PCA(n_components=2).fit_transform(scaled)
        cluster_count = min(self.cluster_spin.value(), len(projected))
        cluster_labels = KMeans(
            n_clusters=cluster_count, random_state=42, n_init=10
        ).fit_predict(projected)

        self.fuzzy_axes.clear()
        self._style_axes(self.fuzzy_axes)
        points = self.fuzzy_axes.scatter(
            projected[:, 0],
            projected[:, 1],
            c=cluster_labels,
            cmap="viridis",
            edgecolors=CYAN,
            linewidths=0.4,
        )
        colorbar = self.fuzzy_figure.colorbar(points, ax=self.fuzzy_axes)
        colorbar.set_label("Кластер", color=TEXT)
        colorbar.ax.tick_params(colors=TEXT)
        self.fuzzy_axes.set_xlabel("Головна компонента 1")
        self.fuzzy_axes.set_ylabel("Головна компонента 2")
        self.fuzzy_axes.set_title("Кластеризація жестів (KMeans)", color=TEXT)
        self.fuzzy_figure.tight_layout()
        self.fuzzy_canvas.draw_idle()

    def _build_ga_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        run_button = QPushButton("Запустити відбір ознак")
        run_button.clicked.connect(self._run_genetic_algorithm)
        layout.addWidget(run_button, alignment=Qt.AlignLeft)
        self.ga_figure, self.ga_canvas, self.ga_axes = self._create_plot(layout)
        self.tabs.addTab(page, "Генетичний алгоритм")

    @staticmethod
    def _ensure_feature_selected(mask, rng):
        if not np.any(mask):
            mask[rng.integers(len(mask))] = True
        return mask

    def _run_genetic_algorithm(self):
        data = self._get_data(minimum_samples=5, require_multiple_classes=True)
        if data is None:
            return
        X, y = data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        rng = np.random.default_rng(42)
        feature_count = X.shape[1]
        population_size = 12
        generation_count = 15
        population = rng.random((population_size, feature_count)) < 0.5
        population = np.array(
            [self._ensure_feature_selected(mask, rng) for mask in population]
        )

        def fitness(mask):
            selected = np.flatnonzero(mask)
            classifier = DecisionTreeClassifier(max_depth=6, random_state=42)
            classifier.fit(X_train[:, selected], y_train)
            error = 1 - accuracy_score(
                y_test, classifier.predict(X_test[:, selected])
            )
            return error + 0.01 * len(selected) / feature_count

        best_history = []
        best_fitness = float("inf")
        best_mask = population[0].copy()
        for _ in range(generation_count):
            scores = np.array([fitness(mask) for mask in population])
            order = np.argsort(scores)
            if scores[order[0]] < best_fitness:
                best_fitness = float(scores[order[0]])
                best_mask = population[order[0]].copy()
            best_history.append(best_fitness)

            next_population = [
                population[order[0]].copy(),
                population[order[1]].copy(),
            ]
            while len(next_population) < population_size:
                parent_pool = order[: max(2, population_size // 3)]
                parent_a, parent_b = population[
                    rng.choice(parent_pool, size=2, replace=True)
                ]
                if feature_count > 1:
                    crossover = rng.integers(1, feature_count)
                    child = np.concatenate((parent_a[:crossover], parent_b[crossover:]))
                else:
                    child = parent_a.copy()

                mutation = rng.random(feature_count) < 0.05
                child[mutation] = ~child[mutation]
                next_population.append(self._ensure_feature_selected(child, rng))
            population = np.asarray(next_population, dtype=bool)

        self.ga_axes.clear()
        self._style_axes(self.ga_axes)
        self.ga_axes.plot(
            np.arange(1, generation_count + 1),
            best_history,
            color=CYAN,
            linewidth=2,
            marker="o",
            markersize=4,
        )
        self.ga_axes.set_xlabel("Покоління")
        self.ga_axes.set_ylabel("Помилка (fitness)")
        self.ga_axes.set_title(
            f"Відібрано ознак: {int(np.sum(best_mask))}", color=TEXT
        )
        self.ga_figure.tight_layout()
        self.ga_canvas.draw_idle()

    def _build_tree_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        run_button = QPushButton("Обчислити важливість ознак")
        run_button.clicked.connect(self._run_random_forest)
        layout.addWidget(run_button, alignment=Qt.AlignLeft)
        self.tree_figure, self.tree_canvas, self.tree_axes = self._create_plot(layout)
        self.tabs.addTab(page, "Дерева рішень")

    def _run_random_forest(self):
        if self._get_data(minimum_samples=2, require_multiple_classes=True) is None:
            return
        try:
            importances = self.training_service.get_feature_importance()
        except ValueError as error:
            QMessageBox.warning(self, "Помилка моделі", str(error))
            return

        names = self.training_service.get_feature_names(len(importances))
        order = np.argsort(importances)
        self.tree_axes.clear()
        self._style_axes(self.tree_axes)
        self.tree_axes.barh(
            [names[index] for index in order],
            importances[order],
            color=VIOLET,
            edgecolor=CYAN,
        )
        self.tree_axes.set_xlabel("Важливість ознаки")
        self.tree_axes.set_ylabel("Координати руки")
        self.tree_axes.set_title("Random Forest: важливість ознак", color=TEXT)
        self.tree_figure.tight_layout()
        self.tree_canvas.draw_idle()

    def _build_regression_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        run_button = QPushButton("Побудувати залежність")
        run_button.clicked.connect(self._run_regression)
        layout.addWidget(run_button, alignment=Qt.AlignLeft)
        self.regression_figure, self.regression_canvas, self.regression_axes = (
            self._create_plot(layout)
        )
        self.tabs.addTab(page, "Регресія")

    def _run_regression(self):
        data = self._get_data(minimum_samples=2)
        if data is None:
            return
        X, y = data
        if X.shape[1] % 2:
            QMessageBox.warning(
                self,
                "Некоректний формат",
                "Для регресії потрібні парні координати X та Y кожної точки.",
            )
            return

        points = X.reshape(len(X), -1, 2)
        mean_x = points[:, :, 0].mean(axis=1)
        mean_y = points[:, :, 1].mean(axis=1)
        model = LinearRegression()
        model.fit(mean_x.reshape(-1, 1), mean_y)
        order = np.argsort(mean_x)

        self.regression_axes.clear()
        self._style_axes(self.regression_axes)
        for gesture in np.unique(y):
            mask = y == gesture
            self.regression_axes.scatter(
                mean_x[mask],
                mean_y[mask],
                label=GESTURE_TRANSLATIONS.get(str(gesture), str(gesture)),
                color=VIOLET,
                edgecolors=CYAN,
                alpha=0.8,
            )
        self.regression_axes.plot(
            mean_x[order],
            model.predict(mean_x[order].reshape(-1, 1)),
            color=CYAN,
            linewidth=2,
        )
        self.regression_axes.set_xlabel("Середня координата X руки")
        self.regression_axes.set_ylabel("Середня координата Y руки")
        self.regression_axes.set_title("Лінійна регресія жестів", color=TEXT)
        self.regression_axes.legend(
            facecolor=BG, edgecolor="#2a3350", labelcolor=TEXT
        )
        self.regression_figure.tight_layout()
        self.regression_canvas.draw_idle()
