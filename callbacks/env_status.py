# callbacks/env_status.py

from dash import Output, Input
from sensors.sht35 import read_sht35

def register_env_status_callback(app, shared_status):
    @app.callback(
        Output('env-status', 'children'),
        Input('interval', 'n_intervals')
    )
    def update_env_status(n):
        temperature, humidity = read_sht35()

        # ✅ 更新共享状态
        shared_status["temperature"] = temperature
        shared_status["humidity"] = humidity

        temperature_display = f"{temperature:.1f} °C" if temperature is not None else "N/A"
        humidity_display = f"{humidity:.1f} %" if humidity is not None else "N/A"

        return f"Temperature: {temperature_display} | Humidity: {humidity_display}"

