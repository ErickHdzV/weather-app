import sys
import io
import base64
from dataclasses import dataclass
from typing import Dict, List

import requests

# Import PyQt5 modules for modern UI
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QPixmap

# Matplotlib for plotting temperature trends
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import folium

# =================== CONFIGURATION ===================
# Predefined locations for quick testing
LOCATIONS: Dict[str, Dict[str, float]] = {
    "Naucalpan": {"lat": 19.478484, "lon": -99.23503},
    "Coacalco": {"lat": 19.633914, "lon": -99.099352},
}
API_KEY = "963a817a3513548eacab6f12c708bd99"
API_URL = "https://api.openweathermap.org/data/3.0/onecall"


@dataclass
class WeatherPoint:
    """Simple container for weather details of a single point in time."""

    dt_txt: str
    temp: float
    feels_like: float
    humidity: int
    pressure: int
    weather: str
    icon: str


class WeatherWindow(QMainWindow):
    """Main application window displaying the modern weather UI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clima Moderno")
        self.resize(1000, 700)

        # ======== Widgets =========
        top_bar = QHBoxLayout()
        self.location_combo = QComboBox()
        self.location_combo.addItems(LOCATIONS.keys())
        self.fetch_button = QPushButton("Obtener clima")
        self.fetch_button.clicked.connect(self.fetch_weather)
        top_bar.addWidget(QLabel("Ubicación:"))
        top_bar.addWidget(self.location_combo)
        top_bar.addWidget(self.fetch_button)
        top_bar.addStretch()

        # Sidebar with tabs for hours and days
        self.tabs = QTabWidget()
        self.hourly_list = QListWidget()
        self.daily_list = QListWidget()
        self.hourly_list.currentRowChanged.connect(self.show_hourly_details)
        self.daily_list.currentRowChanged.connect(self.show_daily_details)
        self.tabs.addTab(self.hourly_list, "Horas")
        self.tabs.addTab(self.daily_list, "Días")
        self.tabs.setMaximumWidth(200)

        # Map using folium displayed in a QWebEngineView
        self.map_view = QWebEngineView()

        # Area for weather details and icon
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.details_label = QLabel("Selecciona una hora o día")
        self.details_label.setAlignment(Qt.AlignTop)
        self.details_label.setWordWrap(True)

        # Matplotlib canvas for temperature trends
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.map_view, stretch=3)
        right_layout.addWidget(self.icon_label, stretch=1)
        right_layout.addWidget(self.details_label, stretch=2)
        right_layout.addWidget(self.canvas, stretch=3)

        main_layout = QHBoxLayout()
        main_layout.addWidget(self.tabs)
        right_container = QWidget()
        right_container.setLayout(right_layout)
        main_layout.addWidget(right_container, stretch=1)

        container = QWidget()
        container.setLayout(QVBoxLayout())
        container.layout().addLayout(top_bar)
        container.layout().addLayout(main_layout)
        self.setCentralWidget(container)

        # Store weather data
        self.hourly_data: List[WeatherPoint] = []
        self.daily_data: List[WeatherPoint] = []

    # -------------------------------------------------
    # Networking
    # -------------------------------------------------
    def fetch_weather(self):
        """Fetch weather data from the API and update UI lists."""
        location = self.location_combo.currentText()
        coords = LOCATIONS.get(location)
        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": API_KEY,
            "units": "metric",
            "exclude": "minutely",
            "lang": "es",
        }
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            QMessageBox.critical(self, "Error de red", str(exc))
            return

        data = response.json()
        self.hourly_data = []
        self.daily_data = []
        self.hourly_list.clear()
        self.daily_list.clear()

        # --- fill hourly data ---
        for hour in data.get("hourly", [])[:24]:
            dt_txt = self.unix_to_hour(hour.get("dt"))
            wp = WeatherPoint(
                dt_txt,
                hour.get("temp", 0.0),
                hour.get("feels_like", 0.0),
                hour.get("humidity", 0),
                hour.get("pressure", 0),
                hour.get("weather", [{}])[0].get("description", ""),
                hour.get("weather", [{}])[0].get("icon", "01d"),
            )
            self.hourly_data.append(wp)
            self.hourly_list.addItem(dt_txt)

        # --- fill daily data ---
        for day in data.get("daily", [])[:7]:
            dt_txt = self.unix_to_date(day.get("dt"))
            wp = WeatherPoint(
                dt_txt,
                day.get("temp", {}).get("day", 0.0),
                day.get("feels_like", {}).get("day", 0.0),
                day.get("humidity", 0),
                day.get("pressure", 0),
                day.get("weather", [{}])[0].get("description", ""),
                day.get("weather", [{}])[0].get("icon", "01d"),
            )
            self.daily_data.append(wp)
            self.daily_list.addItem(dt_txt)

        # Display map and temperature trend for hourly by default
        self.update_map(coords["lat"], coords["lon"], location)
        self.plot_temperatures([h.temp for h in self.hourly_data], "Próximas horas")
        self.details_label.setText("Selecciona una hora o día para ver los detalles")

    # -------------------------------------------------
    # Utility methods
    # -------------------------------------------------
    @staticmethod
    def unix_to_hour(ts: int) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(ts).strftime("%H:%M")

    @staticmethod
    def unix_to_date(ts: int) -> str:
        from datetime import datetime

        return datetime.fromtimestamp(ts).strftime("%d %b")

    def update_map(self, lat: float, lon: float, location: str):
        """Render an interactive map using folium and show it in the view."""
        fmap = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker([lat, lon], tooltip=location).add_to(fmap)
        # Render map to HTML and feed into QWebEngineView
        data = io.BytesIO()
        fmap.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)

    def show_hourly_details(self, index: int):
        if index < 0 or index >= len(self.hourly_data):
            return
        wp = self.hourly_data[index]
        self.update_details(wp)
        self.plot_temperatures([h.temp for h in self.hourly_data], "Próximas horas")

    def show_daily_details(self, index: int):
        if index < 0 or index >= len(self.daily_data):
            return
        wp = self.daily_data[index]
        self.update_details(wp)
        self.plot_temperatures([d.temp for d in self.daily_data], "Próximos días")

    def update_details(self, wp: WeatherPoint):
        """Update detail area with information from a WeatherPoint."""
        self.details_label.setText(
            f"<b>{wp.dt_txt}</b><br>"
            f"Temperatura: {wp.temp} °C<br>"
            f"Sensación: {wp.feels_like} °C<br>"
            f"Humedad: {wp.humidity}%<br>"
            f"Presión: {wp.pressure} hPa<br>"
            f"{wp.weather.capitalize()}"
        )
        self.load_icon(wp.icon)

    def load_icon(self, code: str):
        """Fetch weather icon from OpenWeather and display it."""
        try:
            url = f"https://openweathermap.org/img/wn/{code}@2x.png"
            resp = requests.get(url, timeout=5)
            pixmap = QPixmap()
            pixmap.loadFromData(resp.content)
            self.icon_label.setPixmap(pixmap)
        except Exception:
            self.icon_label.clear()

    def plot_temperatures(self, temps: List[float], title: str):
        """Plot temperature trend using matplotlib."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(temps, color="tab:orange", marker="o")
        ax.set_title(title)
        ax.set_ylabel("°C")
        ax.grid(True, alpha=0.3)
        self.canvas.draw()


def main():
    app = QApplication(sys.argv)
    win = WeatherWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
