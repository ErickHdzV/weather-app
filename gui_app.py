import tkinter as tk
from tkinter import ttk, messagebox
import requests

# Ubicaciones igual que en main.py
LOCATIONS = {
    "Naucalpan": {"lat": 19.478484, "lon": -99.235030},
    "Coacalco": {"lat": 19.633914, "lon": -99.099352},
}
API_KEY = "963a817a3513548eacab6f12c708bd99"
API_URL = "https://api.openweathermap.org/data/3.0/onecall"

def fetch_weather():
    """Fetch weather for the selected location and display results."""
    location = location_var.get()
    if not location:
        messagebox.showwarning("Ubicación no seleccionada", "Por favor, selecciona una ubicación.")
        return
    lat = LOCATIONS[location]["lat"]
    lon = LOCATIONS[location]["lon"]
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
        "exclude": "minutely",
        "lang": "es"
    }
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        display_weather(data, location)
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error de red", f"No se pudo obtener el clima.\n{e}")

def display_weather(data: dict, location: str):
    """Update labels with weather info from the API (main values), with emojis and color."""
    current = data.get("current", {})
    temp = current.get("temp", "-")
    feels_like = current.get("feels_like", "-")
    desc = current.get("weather", [{}])[0].get("description", "Sin datos").capitalize()
    humidity = current.get("humidity", "-")
    clouds = current.get("clouds", "-")
    uvi = current.get("uvi", "-")
    pressure = current.get("pressure", "-")
    dewpoint = current.get("dew_point", "-")
    wind_speed = current.get("wind_speed", "-")

    city_label.config(text=f"🌎 Ubicación: {location}")
    temp_label.config(text=f"🌡️ Temperatura: {temp} °C")
    feels_label.config(text=f"🥵 Sensación térmica: {feels_like} °C")
    desc_label.config(text=f"📝 Clima: {desc}")
    humidity_label.config(text=f"💧 Humedad: {humidity}%")
    clouds_label.config(text=f"☁️ Nubes: {clouds}%")
    uvi_label.config(text=f"☀️ Índice UV: {uvi}")
    pressure_label.config(text=f"🧭 Presión: {pressure} hPa")
    dewpoint_label.config(text=f"🧊 Punto de rocío: {dewpoint} °C")
    wind_label.config(text=f"💨 Viento: {wind_speed} m/s")

# ====== Configuración de la ventana principal ======
root = tk.Tk()
root.title("Clima actual")
root.geometry("650x550")
root.configure(bg="#e3f0ff")

mainframe = tk.Frame(root, bg="#e3f0ff", padx=30, pady=30)
mainframe.grid(row=0, column=0, sticky="NSEW")
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)

# Menú desplegable para ubicación
location_var = tk.StringVar(value=list(LOCATIONS.keys())[0])
tk.Label(mainframe, text="🌎 Ubicación:", font=("Arial", 14, "bold"), bg="#e3f0ff", fg="#1a237e").grid(row=0, column=0, sticky="W")
location_menu = ttk.OptionMenu(mainframe, location_var, list(LOCATIONS.keys())[0], *LOCATIONS.keys())
location_menu.config(width=15)
location_menu.grid(row=0, column=1, padx=10, sticky="EW")

fetch_button = tk.Button(mainframe, text="🔍 Obtener clima", font=("Arial", 12, "bold"), bg="#1976d2", fg="white", activebackground="#1565c0", activeforeground="white", command=fetch_weather)
fetch_button.grid(row=0, column=2, padx=10, pady=10)

# Marco para los resultados
result_frame = tk.Frame(mainframe, bg="#e3f0ff", padx=20, pady=20, highlightbackground="#1976d2", highlightthickness=2)
result_frame.grid(row=1, column=0, columnspan=3, pady=20, sticky="EW")

city_label = tk.Label(result_frame, text="", font=("Arial", 18, "bold"), bg="#e3f0ff", fg="#0d47a1")
city_label.grid(row=0, column=0, sticky="W", pady=5)
temp_label = tk.Label(result_frame, text="", font=("Arial", 16, "bold"), bg="#e3f0ff", fg="#e65100")
temp_label.grid(row=1, column=0, sticky="W", pady=5)
feels_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#ff9800")
feels_label.grid(row=2, column=0, sticky="W", pady=5)
desc_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#388e3c")
desc_label.grid(row=3, column=0, sticky="W", pady=5)
humidity_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#0288d1")
humidity_label.grid(row=4, column=0, sticky="W", pady=5)
clouds_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#616161")
clouds_label.grid(row=5, column=0, sticky="W", pady=5)
uvi_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#d32f2f")
uvi_label.grid(row=6, column=0, sticky="W", pady=5)
pressure_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#6d4c41")
pressure_label.grid(row=7, column=0, sticky="W", pady=5)
dewpoint_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#00897b")
dewpoint_label.grid(row=8, column=0, sticky="W", pady=5)
wind_label = tk.Label(result_frame, text="", font=("Arial", 14), bg="#e3f0ff", fg="#3949ab")
wind_label.grid(row=9, column=0, sticky="W", pady=5)

root.mainloop()