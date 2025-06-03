import dash
import yaml
from ui.layout import generate_layout

from callbacks.graph import register_graph_callback
from callbacks.env_status import register_env_status_callback
from callbacks.iv_control import register_iv_control_callbacks
from callbacks.iv_plot import register_iv_plot_callback
import threading

import dash_bootstrap_components as dbc

# 初始化 Dash 应用
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])  # 可替换为其他主题
app.layout = generate_layout

# 全局共享状态（可变对象）
shared_status = {
    "voltage": None,
    "current": None,
    "time": None,
    "temperature": None,   # ✅ 新增
    "humidity": None,       # ✅ 新增
}
time_series = []
current_series = []
iv_curve = []
stop_event = threading.Event()

register_iv_control_callbacks(app, shared_status, time_series, current_series, iv_curve, stop_event)
register_env_status_callback(app, shared_status)
register_graph_callback(app, shared_status, time_series, current_series)
register_iv_plot_callback(app)
# ========== 启动 App ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050)

