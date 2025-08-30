import sys
import io
import os
from dotenv import load_dotenv

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget, QListWidgetItem, QLineEdit
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QPixmap, QIcon

from typing import Dict, List, Optional
from dataclasses import dataclass
import requests
import folium
from datetime import datetime

# =================== CONFIGURATION ===================
load_dotenv()

API_KEY = os.getenv("OPENWEATHER_API_KEY")
API_URL = os.getenv("API_URL")
EMAIL_MAP = os.getenv("EMAIL_MAP")

@dataclass
class WeatherPoint:
    dt_txt: str
    temp: float
    feels_like: float
    humidity: int
    pressure: int
    weather: str
    icon: str
    clouds: Optional[int] = None
    dew_point: Optional[float] = None
    uvi: Optional[float] = None
    pop: Optional[float] = None

class WeatherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clima Moderno")
        self.resize(1000, 700)
        self.setWindowIcon(QIcon("assets/weather_app_icon.ico"))

        self._setup_ui()
        self.hourly_data: List[WeatherPoint] = []
        self.daily_data: List[WeatherPoint] = []
        self.last_coords: Optional[Dict[str, float]] = None

    def _setup_ui(self):
        # Top bar
        top_bar = QHBoxLayout()
        location_label = QLabel("Ubicación:")
        location_label.setStyleSheet("color: #2C3E50; font-weight: bold;")
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Ciudad, dirección o lugar...")
        self.location_input.setStyleSheet(
            "QLineEdit { background: #A1C4FD; color: #2C3E50; border-radius: 6px; padding: 4px; font-size: 14px; }"
        )
        self.search_button = QPushButton("Buscar ubicación")
        self.search_button.setStyleSheet(
            "QPushButton { background: #4A90E2; color: #F5F9FF; border-radius: 8px; font-weight: bold; padding: 6px 16px; }"
            "QPushButton:hover { background: #A1C4FD; color: #2C3E50; }"
        )
        self.search_button.clicked.connect(self.handle_location_search)
        top_bar.addWidget(location_label)
        top_bar.addWidget(self.location_input)
        top_bar.addWidget(self.search_button)

        self.loader_label = QLabel()
        self.loader_label.setStyleSheet("color: #4A90E2; font-size: 15px; font-weight: bold; padding-left: 10px;")
        self.loader_label.hide()
        top_bar.addWidget(self.loader_label)
        top_bar.addStretch()

        # Sidebar tabs
        self.tabs = QTabWidget()
        self.hourly_list = QListWidget()
        self.daily_list = QListWidget()
        self.hourly_list.currentRowChanged.connect(self.show_hourly_details)
        self.daily_list.currentRowChanged.connect(self.show_daily_details)
        self.tabs.addTab(self.hourly_list, "Horas")
        self.tabs.addTab(self.daily_list, "Días")
        self.tabs.setMaximumWidth(220)

        list_style = '''
            QListWidget {
                background: #A1C4FD;
                color: #2C3E50;
                border-radius: 12px;
                font-size: 15px;
                padding: 6px;
            }
            QListWidget::item {
                border-radius: 8px;
                padding: 8px 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:selected {
                background: #4A90E2;
                color: #F5F9FF;
                font-weight: bold;
                border: 2px solid #D1D9E6;
            }
            QListWidget QScrollBar:vertical {
                width: 10px;
                background: transparent;
                margin: 2px 0 2px 0;
                border-radius: 6px;
                opacity: 0;
            }
            QListWidget:hover QScrollBar:vertical {
                opacity: 1;
                background: #EAF1FB;
            }
            QListWidget QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90E2, stop:1 #A1C4FD);
                min-height: 30px;
                border-radius: 6px;
                border: none;
            }
            QListWidget QScrollBar::add-line:vertical,
            QListWidget QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QListWidget QScrollBar::up-arrow:vertical,
            QListWidget QScrollBar::down-arrow:vertical {
                background: none;
            }
            QListWidget QScrollBar::add-page:vertical,
            QListWidget QScrollBar::sub-page:vertical {
                background: none;
            }
        '''
        self.hourly_list.setStyleSheet(list_style)
        self.daily_list.setStyleSheet(list_style)

        # Map and details
        self.map_view = QWebEngineView()
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.details_label = QLabel("Selecciona una hora o día")
        self.details_label.setAlignment(Qt.AlignCenter)
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet(
            "font-size: 16px; color: #2C3E50; background: #F5F9FF; border-radius: 10px; padding: 0 12px 12px 12px; text-align: center;"
        )

        # Matplotlib canvas
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.figure import Figure
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)

        # Layouts
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
        container.setStyleSheet("background: #F5F9FF;")
        self.setCentralWidget(container)

    # -------------------------------------------------
    # Networking and Geocoding
    # -------------------------------------------------
    def handle_location_search(self):
        location_name = self.location_input.text().strip()
        if not location_name:
            QMessageBox.warning(self, "Campo vacío", "Por favor, ingresa una ubicación.")
            return
        self.show_loader(True, "Buscando ubicación...")
        QApplication.processEvents()
        coords = self.geocode_location(location_name)
        if coords is None:
            self.show_loader(False)
            QMessageBox.critical(self, "Ubicación no encontrada", f"No se pudo encontrar la ubicación: {location_name}")
            return
        self.last_coords = coords
        self.fetch_weather(coords, location_name)
        self.show_loader(False)

    def geocode_location(self, location_name: str) -> Optional[Dict[str, float]]:
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {"q": location_name, "format": "json", "limit": 1}
            headers = {"User-Agent": f"WeatherApp/1.0 {EMAIL_MAP}"}
            resp = requests.get(url, params=params, headers=headers, timeout=8)
            resp.raise_for_status()
            results = resp.json()
            if not results:
                return None
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            return {"lat": lat, "lon": lon}
        except Exception:
            return None

    def fetch_weather(self, coords: Dict[str, float], location_name: str):
        self.show_loader(True, "Cargando clima...")
        QApplication.processEvents()
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
            self.show_loader(False)
            QMessageBox.critical(self, "Error de red", str(exc))
            return

        data = response.json()
        self.hourly_data.clear()
        self.daily_data.clear()
        self.hourly_list.clear()
        self.daily_list.clear()

        self._populate_hourly_list(data)
        self._populate_daily_list(data)

        self.update_map(coords["lat"], coords["lon"], location_name)
        self.plot_temperatures([h.temp for h in self.hourly_data], "Próximas horas")
        self.details_label.setText("Selecciona una hora o día para ver los detalles")
        self.show_loader(False)

    def show_loader(self, show: bool, text: str = ""):
        self.loader_label.setText(text if show else "")
        self.loader_label.setVisible(show)

    # -------------------------------------------------
    # Utility methods
    # -------------------------------------------------
    @staticmethod
    def unix_to_hour(ts: int) -> str:
        dt = datetime.fromtimestamp(ts)
        hour_12 = dt.strftime("%I:%M %p").lstrip("0")
        return hour_12

    def update_map(self, lat: float, lon: float, location: str):
        fmap = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker([lat, lon], tooltip=location).add_to(fmap)
        data = io.BytesIO()
        fmap.save(data, close_file=False)
        html = data.getvalue().decode()
        self.map_view.setHtml(html)

    def show_hourly_details(self, index: int):
        if 0 <= index < len(self.hourly_data):
            wp = self.hourly_data[index]
            self.update_details(wp)
            self.plot_temperatures([h.temp for h in self.hourly_data], "Próximas horas")

    def show_daily_details(self, index: int):
        if 0 <= index < len(self.daily_data):
            wp = self.daily_data[index]
            self.update_details(wp)
            self.plot_temperatures([d.temp for d in self.daily_data], "Próximos días")

    def update_details(self, wp: WeatherPoint):
        weather_emojis = {
            "01d": "☀️", "01n": "🌙",
            "02d": "🌤️", "02n": "🌤️",
            "03d": "☁️", "03n": "☁️",
            "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️",
            "10d": "🌦️", "10n": "🌦️",
            "11d": "⛈️", "11n": "⛈️",
            "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️",
        }
        emoji = weather_emojis.get(wp.icon, "❓")

        pop = wp.pop
        uvi = wp.uvi
        dew_point = wp.dew_point
        clouds = wp.clouds

        recommendations = []
        if pop is not None:
            if pop >= 0.8:
                recommendations.append("☔ Muy alta probabilidad de lluvia. Lleva paraguas y ropa impermeable.")
            elif pop >= 0.5:
                recommendations.append("🌦️ Probabilidad media de lluvia. Considera llevar paraguas.")
            elif pop >= 0.2:
                recommendations.append("🌦️ Baja probabilidad de lluvia. Probablemente no necesites paraguas.")
            else:
                recommendations.append("🌤️ Muy baja probabilidad de lluvia. Disfruta tu día.")
        else:
            recommendations.append("🌤️ No se espera lluvia. Disfruta tu día.")
        if uvi is not None and uvi >= 6:
            recommendations.append("🧴 Usa protector solar, el índice UV es alto.")
        if wp.temp >= 30:
            recommendations.append("🥵 Hace calor, mantente hidratado.")
        if wp.temp <= 5:
            recommendations.append("🧥 Hace frío, abrígate bien.")
        if wp.humidity >= 80:
            recommendations.append("💧 Humedad alta, puede sentirse bochornoso.")
        if len(recommendations) == 1:
            recommendations.append("✅ El clima es agradable, ¡disfruta tu día!")

        details_html = f'''
        <div style="display: flex; align-items: center; gap: 18px;">
            <span style="font-size: 4.5em; width:90px; height:90px; display: flex; align-items: center; justify-content: center; background: #EAF1FB; border-radius: 18px; box-shadow: 0 2px 8px #A1C4FD55;">{emoji}</span>
            <div style="flex:1;">
                <div style="font-size: 1.5em; font-weight: bold; color: #2C3E50; margin-bottom: 2px;">{wp.dt_txt}</div>
                <div style="font-size: 1.2em; color: #4A90E2; font-weight: bold;">{wp.weather.capitalize()}</div>
                <div style="margin-top: 8px;">
                    <span style="font-size: 1.1em; color: #2C3E50;">🌡️ {wp.temp} °C</span> &nbsp; 
                    <span style="color: #7B8FA1;">Sensación: {wp.feels_like} °C</span>
                </div>
                <div style="margin-top: 4px; color: #2C3E50;">
                    💧 {wp.humidity}% &nbsp; | &nbsp; ⬇️ {wp.pressure} hPa
                </div>
                <div style="margin-top: 4px; color: #2C3E50;">
                    ☁️ Nubes: {clouds if clouds is not None else '-'}% &nbsp; | &nbsp; 🧊 Punto de rocío: {dew_point if dew_point is not None else '-'}°C &nbsp; | &nbsp; ☀️ UV: {uvi if uvi is not None else '-'}
                </div>
                <div style="margin-top: 10px; font-size: 1.1em; color: #4A90E2; font-weight: bold;">
                    {'<br>'.join(recommendations)}
                </div>
            </div>
        </div>
        '''
        self.details_label.setText(details_html)
        self.icon_label.clear()

    def load_icon(self, code: str):
        try:
            url = f"https://openweathermap.org/img/wn/{code}@2x.png"
            resp = requests.get(url, timeout=5)
            pixmap = QPixmap()
            pixmap.loadFromData(resp.content)
            self.icon_label.setPixmap(pixmap)
        except Exception:
            self.icon_label.clear()

    def plot_temperatures(self, temps: List[float], title: str):
        import numpy as np
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("#F5F9FF")
        self.figure.set_facecolor("#F5F9FF")

        if title.startswith("Próximas horas") and hasattr(self, "hourly_data") and len(self.hourly_data) == len(temps):
            xlabels = [h.dt_txt for h in self.hourly_data]
        elif title.startswith("Próximos días") and hasattr(self, "daily_data") and len(self.daily_data) == len(temps):
            xlabels = [d.dt_txt for d in self.daily_data]
        else:
            xlabels = [str(i+1) for i in range(len(temps))]

        x = np.arange(len(temps))
        ax.plot(x, temps, color="#4A90E2", marker="o", markerfacecolor="#A1C4FD", markeredgecolor="#2C3E50", linewidth=2, zorder=3)
        ax.fill_between(x, temps, min(temps)-2, color="#A1C4FD", alpha=0.25, zorder=2)
        if len(temps) <= 12:
            for i, temp in enumerate(temps):
                ax.text(i, temp+0.5, f"{temp:.1f}°", ha="center", va="bottom", fontsize=10, color="#2C3E50", fontweight="bold", zorder=4)

        max_labels = 10 if len(temps) > 10 else len(temps)
        step = max(1, len(temps) // max_labels)
        shown_labels = [label if (i % step == 0 or i == len(temps)-1) else "" for i, label in enumerate(xlabels)]
        ax.set_xticks(x)
        ax.set_xticklabels(shown_labels, rotation=35, ha="right", fontsize=9)

        ax.set_title(title, color="#2C3E50", fontsize=15, fontweight="bold", pad=15)
        ax.set_ylabel("Temperatura (°C)", color="#2C3E50", fontsize=12)
        ax.set_xlabel("Hora" if title.startswith("Próximas horas") else ("Día" if title.startswith("Próximos días") else "Tiempo"), color="#2C3E50", fontsize=12)
        ax.tick_params(axis='x', colors="#2C3E50", labelsize=10)
        ax.tick_params(axis='y', colors="#2C3E50", labelsize=10)
        ax.grid(True, alpha=0.25, color="#B0C4DE", linestyle='--', zorder=1)
        for spine in ax.spines.values():
            spine.set_color("#B0C4DE")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        self.figure.tight_layout(pad=2.0)
        self.canvas.draw()

    def _populate_hourly_list(self, data: dict):
        last_day = None
        weather_emojis = {
            "01d": "☀️", "01n": "🌙",
            "02d": "🌤️", "02n": "🌤️",
            "03d": "☁️", "03n": "☁️",
            "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️",
            "10d": "🌦️", "10n": "🌦️",
            "11d": "⛈️", "11n": "⛈️",
            "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️",
        }
        days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        for hour in data.get("hourly", [])[:24]:
            dt_obj = datetime.fromtimestamp(hour.get("dt"))
            dt_txt = self.unix_to_hour(hour.get("dt"))
            icon = hour.get("weather", [{}])[0].get("icon", "01d")
            emoji = weather_emojis.get(icon, "❓")
            wp = WeatherPoint(
                dt_txt,
                hour.get("temp", 0.0),
                hour.get("feels_like", 0.0),
                hour.get("humidity", 0),
                hour.get("pressure", 0),
                hour.get("weather", [{}])[0].get("description", ""),
                icon,
                hour.get("clouds"),
                hour.get("dew_point"),
                hour.get("uvi"),
                hour.get("pop"),
            )
            if last_day != dt_obj.date():
                weekday = days[dt_obj.weekday()]
                day = dt_obj.day
                month = meses[dt_obj.month - 1]
                day_str = f"{weekday.capitalize()}, {day:02d} {month}"
                day_item = QListWidgetItem(day_str)
                day_item.setFlags(day_item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
                day_item.setTextAlignment(Qt.AlignCenter)
                day_item.setBackground(Qt.transparent)
                day_item.setForeground(Qt.darkBlue)
                day_item.setFont(self.font())
                self.hourly_list.addItem(day_item)
                last_day = dt_obj.date()
            self.hourly_data.append(wp)
            item_text = f"{dt_txt} | {wp.temp:.1f}°C | {emoji} "
            self.hourly_list.addItem(item_text)

    def _populate_daily_list(self, data: dict):
        weather_emojis = {
            "01d": "☀️", "01n": "🌙",
            "02d": "🌤️", "02n": "🌤️",
            "03d": "☁️", "03n": "☁️",
            "04d": "☁️", "04n": "☁️",
            "09d": "🌧️", "09n": "🌧️",
            "10d": "🌦️", "10n": "🌦️",
            "11d": "⛈️", "11n": "⛈️",
            "13d": "❄️", "13n": "❄️",
            "50d": "🌫️", "50n": "🌫️",
        }
        days_shorts = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
        meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
        for day in data.get("daily", [])[:7]:
            dt_obj = datetime.fromtimestamp(day.get("dt"))
            weekday = days_shorts[dt_obj.weekday()]
            day_num = dt_obj.day
            month = meses[dt_obj.month - 1]
            dt_txt = f"{weekday.capitalize()}, {day_num:02d} {month}"
            icon = day.get("weather", [{}])[0].get("icon", "01d")
            emoji = weather_emojis.get(icon, "❓")
            temp = day.get("temp", {}).get("day", 0.0)
            wp = WeatherPoint(
                dt_txt,
                temp,
                day.get("feels_like", {}).get("day", 0.0),
                day.get("humidity", 0),
                day.get("pressure", 0),
                day.get("weather", [{}])[0].get("description", ""),
                icon,
                day.get("clouds"),
                day.get("dew_point"),
                day.get("uvi"),
                day.get("pop"),
            )
            self.daily_data.append(wp)
            item_text = f"{dt_txt} {emoji}  {temp:.0f}°C"
            self.daily_list.addItem(item_text)

def main():
    app = QApplication(sys.argv)
    win = WeatherWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()