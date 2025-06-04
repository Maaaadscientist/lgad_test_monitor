# callbacks/config_controls.py

import threading
import yaml
import dash
from dash import Input, Output, State, callback_context as ctx
from iv_control.measurement import perform_measurement

def register_iv_control_callbacks(app, _shared_status, _time_series, _current_series, _iv_curve, _stop_event):
    shared_status = _shared_status
    time_series = _time_series
    current_series = _current_series
    iv_curve = _iv_curve
    stop_event = _stop_event

    # 控制按钮 Start / Stop
    @app.callback(
        Output('start-button', 'disabled'),
        Output('stop-button', 'disabled'),
        Input('start-button', 'n_clicks'),
        Input('stop-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def control_buttons(start_clicks, stop_clicks):
        print("🟢 [control_buttons] triggered")
        if ctx.triggered_id == 'start-button':
            stop_event.clear()
            threading.Thread(
                target=perform_measurement,
                args=(shared_status, time_series, current_series, iv_curve, stop_event)
            ).start()
            return True, False
        elif ctx.triggered_id == 'stop-button':
            stop_event.set()
            #instr.write("OUTP OFF")
            return False, True
        return dash.no_update, dash.no_update

    # 配置面板显示开关
    @app.callback(
        Output('config-panel', 'style'),
        Input('config-button', 'n_clicks'),
        Input('confirm-config', 'n_clicks'),
        Input('cancel-config', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_config_panel(config_clicks, confirm_clicks, cancel_clicks):
        triggered = ctx.triggered_id
        if triggered == 'config-button':
            return {'display': 'block'}
        return {'display': 'none'}

    # 统一配置加载和保存逻辑
    @app.callback(
        Output('config-store', 'data'),
        Output('input-start-voltage', 'value'),
        Output('input-stop-voltage', 'value'),
        Output('input-step-voltage', 'value'),
        Output('input-measurement-duration', 'value'),
        Output('input-sample-interval', 'value'),
        Output('input-stabilization-time', 'value'),
        Output('input-maximum-current', 'value'),
        Output('input-ac-voltage', 'value'),
        Output('input-ac-frequency', 'value'),
        Input('config-button', 'n_clicks'),
        Input('confirm-config', 'n_clicks'),
        State('input-start-voltage', 'value'),
        State('input-stop-voltage', 'value'),
        State('input-step-voltage', 'value'),
        State('input-measurement-duration', 'value'),
        State('input-sample-interval', 'value'),
        State('input-stabilization-time', 'value'),
        State('input-maximum-current', 'value'),
        State('input-ac-voltage', 'value'),
        State('input-ac-frequency', 'value'),
        State('config-store', 'data'),
        prevent_initial_call=True
    )
    def unified_config_handler(config_clicks, confirm_clicks,
                               sv, ev, step, dur, si, stab, maxc, acv, acf,
                               current_store):
        triggered_id = ctx.triggered_id

        if triggered_id == 'config-button':
            return (
                current_store,
                current_store['start_voltage'],
                current_store['stop_voltage'],
                current_store['step_voltage'],
                current_store['measurement_duration'],
                current_store['sample_interval'],
                current_store['stabilization_time'],
                current_store['maximum_current'],
                current_store['ac_voltage'],
                current_store['ac_frequency'],
            )

        elif triggered_id == 'confirm-config':
            updated = {
                'start_voltage': sv,
                'stop_voltage': ev,
                'step_voltage': step,
                'measurement_duration': dur,
                'sample_interval': si,
                'stabilization_time': stab,
                'maximum_current': maxc,
                'ac_voltage' : acv,
                'ac_frequency' : acf,
            }
            with open("configs/config.yaml", "w") as f:
                print("save")
                yaml.safe_dump(updated, f)
            return (updated, sv, ev, step, dur, si, stab, maxc, acv, acf)

        return dash.no_update, *([dash.no_update] * 9)

