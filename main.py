import requests
import locale
from datetime import datetime
# EMAIL 
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ================= Locations =========
LOCATIONS = { 
    # "CDMX": {
    #     "lat": 19.433050,
    #     "lon": -99.141453
    # },
    "Naucalpan": {
        "lat": 19.478484,
        "lon": -99.235030
    },
    "Coacalco": {
        "lat": 19.633914,
        "lon": -99.099352
    }
}

# ================== CONFIG =====================
OPEN_WEATHER_MAP_ENDPOINT = "https://api.openweathermap.org/data/3.0/onecall"
API_KEY = "963a817a3513548eacab6f12c708bd99"
# Set locale for date formatting
locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

# Email service 
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "senderreminder@gmail.com"
EMAIL_PASS = "pqjj ssda njfl luil"  

# ================= HELPERS =====================
def unix_to_datetime(ts: int) -> str:
    """Convert Unix timestamp to human-readable date and time."""
    return datetime.fromtimestamp(ts).strftime('%d - %B - %Y %I:%M %p')

def unix_to_hour(ts: int) -> str:
    """Convert Unix timestamp to human-readable hour (AM/PM)."""
    return datetime.fromtimestamp(ts).strftime('%I:%M %p')

def get_weather_message(weather_id):
    """Return a weather message based on weather condition code."""
    # Mapping for weather codes
    mapping = [
        (lambda weather_id: weather_id < 300, " ⚡ Tormenta eléctrica. ¡Mantente a salvo y evita áreas abiertas!"),
        (lambda weather_id: weather_id < 400, " 🌦️ Llovizna ligera. Revisa el clima futuro."),
        (lambda weather_id: weather_id == 500, " 🌧️ Lluvia ligera. Cambios de clima en próximas horas."),
        (lambda weather_id: weather_id == 501, " 🌧️ Lluvia moderada. Cambios de clima en próximas horas."),
        (lambda weather_id: weather_id == 502, " 🌧️ Lluvia intensa. Lleva paraguas y ropa impermeable."),
        (lambda weather_id: weather_id == 503, " 🌧️ Lluvia muy intensa. Mejor no salgas."),
        (lambda weather_id: weather_id == 504, " 🌧️ Lluvia extrema. ¡No salgas!"),
        (lambda weather_id: weather_id == 511, " ❄️ Lluvia helada. Cuidado con superficies resbaladizas."),
        (lambda weather_id: weather_id == 520, " 🌦️ Lluvia ligera corta. Cambios de clima en próximas horas."),
        (lambda weather_id: weather_id == 521, " 🌦️ Lluvia moderada corta. Cambios de clima en próximas horas."),
        (lambda weather_id: weather_id == 522, " 🌧️ Lluvia intensa corta. Lleva paraguas y ropa impermeable."),
        (lambda weather_id: weather_id == 531, " 🌧️ Lluvia irregular. Lleva paraguas y ropa impermeable."),
        (lambda weather_id: 600 <= weather_id <= 622, " ❄️ Nieve. Mantente abrigado y ten cuidado al conducir."),
        (lambda weather_id: 701 <= weather_id < 800, " 🌫️ Condiciones atmosféricas adversas. Precaución al conducir."),
        (lambda weather_id: weather_id == 800, " ☀️ Cielo despejado. ¡Disfruta tu día!"),
        (lambda weather_id: weather_id == 801, " 🌤️ Algunas nubes. Probablemente no necesites paraguas."),
        (lambda weather_id: weather_id == 802, " ⛅ Parcialmente nublado. Probablemente no necesites paraguas."),
        (lambda weather_id: weather_id == 803, " 🌥️ Mayormente nublado. Puede que necesites paraguas."),
        (lambda weather_id: weather_id == 804, " ☁️ Completamente nublado. Lleva paraguas."),
    ]
    for cond, msg in mapping:
        if cond(weather_id):
            return msg
    return "No hay recomendaciones disponibles."

def get_pressure_message(pressure):
    if pressure > 1020:
        return "Alta presión atmosférica. Día seco."
    elif pressure < 1013:
        return "Baja presión atmosférica. Puede haber mal tiempo."
    return "Presión atmosférica normal. El clima suele ser estable."

def get_humidity_message(humidity):
    if humidity > 70:
        return "Humedad alta. Puede sentirse más caliente de lo normal."
    elif humidity < 30:
        return "Humedad baja. Aire seco, poca probabilidad de lluvia."
    return "Humedad normal. El clima es cómodo."

def get_uvi_message(uvi):
    if uvi > 7:
        return "Índice UV alto. Usa protector solar y evita el sol directo."
    elif uvi > 3:
        return "Índice UV moderado. Usa protector solar si estarás mucho tiempo afuera."
    return "Índice UV bajo. Puedes disfrutar del sol sin preocupaciones."

def get_clouds_message(clouds):
    if clouds < 20:
        return "Cielo despejado. Disfruta del sol y el aire fresco."
    elif clouds < 50:
        return "Cielo parcialmente nublado. Probablemente no necesites paraguas."
    elif clouds < 80:
        return "Cielo nublado. Puede que necesites paraguas."
    return "Cielo muy nublado. Lleva paraguas por si acaso."

def get_dewpoint_message(dewpoint):
    if dewpoint > 20:
        return "Punto de rocío alto. Puede sentirse más caliente de lo normal."
    elif dewpoint > 10:
        return "Punto de rocío normal. El clima es cómodo."
    elif dewpoint > 0:
        return "Punto de rocío bajo. Aire seco, poca probabilidad de lluvia."
    return "Punto de rocío muy bajo. Aire muy seco, poca probabilidad de lluvia."

def get_dewpoint_temp_diff_message(temp, dewpoint):
    if temp is None or dewpoint is None:
        return ""
    diff = temp - dewpoint
    if diff > 10:
        return "El clima es seco y cómodo."
    elif diff < 5:
        return "El clima es húmedo y puede sentirse más caliente de lo normal."
    return "El clima es ligeramente húmedo."

def get_pop_message(pop: int) -> str:
    """Return a message based on the probability of precipitation."""
    if pop >= 0.8:
        return "Muy alta probabilidad de lluvia. Lleva paraguas y ropa impermeable."
    elif pop >= 0.5:
        return "Probabilidad moderada de lluvia. Considera llevar paraguas."
    elif pop >= 0.2:
        return "Baja probabilidad de lluvia. Probablemente no necesites paraguas."
    else:
        return "Muy baja probabilidad de lluvia. Disfruta tu día."

# ============= API & DATA =============
def fetch_weather(location: str = "Naucalpan") -> dict:
    """Fetch weather data from OpenWeatherMap API for a given location."""
    WEATHER_PARAMS = {
        "lat": LOCATIONS[location]["lat"],
        "lon": LOCATIONS[location]["lon"],
        "appid": API_KEY,
        "units": "metric",
        "exclude": "minutely",
        "lang": "es"
    }
    try:
        response = requests.get(OPEN_WEATHER_MAP_ENDPOINT, params=WEATHER_PARAMS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error al obtener datos del clima para {location}: {e}")
        return {}

def body_current_weather(current: dict, location: str) -> str:
    """Generate HTML for current weather information for a location."""
    temp = current.get("temp")
    feels_like = current.get("feels_like")
    pressure = current.get("pressure")
    desc = current.get("weather", [{}])[0].get("description", "Sin descripción")
    weather_id = current.get("weather", [{}])[0].get("id")
    humidity = current.get("humidity", 0)
    uvi = current.get("uvi", 0)
    clouds = current.get("clouds", 0)
    dewpoint = current.get("dew_point")
    time = unix_to_datetime(current.get("dt", 0))

    current_weather_html = f"""
    <div style='border:1px solid #ccc; border-radius:8px; padding:12px; margin-bottom:16px;'>
        <h2 style='color:#2d6cdf;'>Clima actual en {location} {time}</h2>
        <ul>
            <li>🌡️ <b>Temperatura:</b> {temp}°C | <b>Sensación térmica:</b> {feels_like}°C</li>
            <li>📝 <b>Descripción:</b> {desc.capitalize()}</li>
            <li>💡 <b>Recomendación:</b> {get_weather_message(weather_id)}</li>
            <li>🧭 <b>Presión:</b> {pressure} hPa - {get_pressure_message(pressure)}</li>
            <li>💧 <b>Humedad:</b> {humidity}% - {get_humidity_message(humidity)}</li>
            <li>☀️ <b>Índice UV:</b> {uvi} - {get_uvi_message(uvi)}</li>
            <li>☁️ <b>Nubes:</b> {clouds}% - {get_clouds_message(clouds)}</li>
            <li>🧊 <b>Punto de rocío:</b> {dewpoint}°C - {get_dewpoint_message(dewpoint)}</li>
            <li>🔎 <b>Diferencia temp/punto de rocío:</b> {get_dewpoint_temp_diff_message(temp, dewpoint)}</li>
        </ul>
    </div>
    """
    return current_weather_html

def body_hourly_weather(hourly: list, location: str, hours_limit: int = 6) -> str:
    """Generate HTML for hourly weather forecast for a location."""
    html = f"<div style='margin-bottom:24px;'><h3 style='color:#2d6cdf;'>Pronóstico horario para {location} próximas {hours_limit} horas</h3>"
    for i, hour in enumerate(hourly[:hours_limit]):
        hour_time = unix_to_hour(hour.get("dt", 0))
        temp = hour.get("temp")
        feels_like = hour.get("feels_like")
        desc = hour.get("weather", [{}])[0].get("description", "Sin descripción")
        weather_id = hour.get("weather", [{}])[0].get("id")
        pressure = hour.get("pressure")
        humidity = hour.get("humidity", 0)
        uvi = hour.get("uvi", 0)
        clouds = hour.get("clouds", 0)
        dewpoint = hour.get("dew_point")
        pop = hour.get("pop", 0)
        html += f"""
        <div style='border:1px solid #eee; border-radius:6px; padding:8px; margin-bottom:8px;'>
            <b>🕒 {hour_time}</b><br>
            🌡️ <b>Temp:</b> {temp}°C | <b>Sensación:</b> {feels_like}°C<br>
            📝 <b>Desc:</b> {desc.capitalize()}<br>
            💡 <b>Recomendación:</b> {get_weather_message(weather_id)}<br>
            🧭 <b>Presión:</b> {pressure} hPa - {get_pressure_message(pressure)}<br>
            💧 <b>Humedad:</b> {humidity}% - {get_humidity_message(humidity)}<br>
            ☀️ <b>UV:</b> {uvi} - {get_uvi_message(uvi)}<br>
            ☁️ <b>Nubes:</b> {clouds}% - {get_clouds_message(clouds)}<br>
            🧊 <b>Punto de rocío:</b> {dewpoint}°C - {get_dewpoint_message(dewpoint)}<br>
            🔎 <b>Dif. temp/punto de rocío:</b> {get_dewpoint_temp_diff_message(temp, dewpoint)}<br>
            ☔ <b>Prob. de precipitación:</b> {pop*100}% - {get_pop_message(pop)}
        </div>
        """
    html += "</div>"
    return html

# =========== SEND EMAIL ==============
def send_email(subject: str, body: str, to: str) -> None:
    """Send an email with the weather report."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print("✅ Email enviado correctamente.")
    except Exception as e:
        print(f"❌ Error al enviar el email: {e}")

# ============= MAIN ===================
def main() -> None:
    """Main process: fetch weather for all locations, build HTML, and send email."""
    full_body = "<html><body>"
    for location in LOCATIONS:
        weather_data = fetch_weather(location=location)
        if not weather_data:
            print(f"\n❌ No se pudo obtener información para {location}.")
            continue
        current = weather_data.get("current")
        hourly = weather_data.get("hourly", [])
        if not current:
            print(f"\n❌ Información actual no disponible para {location}.")
            continue
        full_body += body_current_weather(current, location=location)
        if not hourly:
            print(f"\n❌ Información horaria no disponible para {location}.")
            continue
        full_body += body_hourly_weather(hourly=hourly, location=location, hours_limit=6)
    full_body += "</body></html>"

    if full_body == "<html><body></body></html>":
        print("\n❌ No se pudo generar ningún informe de clima.")
        return
    send_email(subject="Informe del clima", body=full_body, to="ulmo.closable569@passinbox.com")

if __name__ == "__main__":
    main()
