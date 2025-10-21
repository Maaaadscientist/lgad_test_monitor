import os
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import Input, Output, State, ctx, dcc
from iv_control.config import load_config

font_family='Raleway'
def register_cv_plot_callback(app):

    # —— 合并“显示”和“隐藏 iv-config-panel”到一个回调
    @app.callback(
        Output('cv-config-panel', 'style'),
        Output('cv-directory-dropdown', 'options'),
        Input('plot-cv-button', 'n_clicks'),
        Input('cv-hide-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_iv_panel(plot_nclicks, hide_nclicks):
        triggered_id = ctx.triggered_id

        # --------- 如果是“Plot I–V”按钮被按下
        if triggered_id == 'plot-cv-button':
            # 列出所有 outputs/iv_results_* 文件夹
            try:
                folders = sorted(
                    [f"outputs/{d}" for d in os.listdir("outputs")
                     if d.startswith("cv_results_") and os.path.isdir(os.path.join("outputs", d))],
                    reverse=True
                )
            except FileNotFoundError:
                folders = []
            options = [{'label': f, 'value': f} for f in folders]
            # 显示面板 + 填充下拉菜单
            return {'display': 'block'}, options

        # --------- 如果是“收起下拉菜单”按钮被按下
        elif triggered_id == 'cv-hide-button':
            # 隐藏面板，不改变 options
            return {'display': 'none'}, dash.no_update

        # --------- 其他情况（虽然 prevent_initial_call=True，但写个兜底）
        return dash.no_update, dash.no_update

    @app.callback(
        Output('cv-graph', 'figure'),
        Input('cv-directory-dropdown', 'value')
    )
    def plot_cv_curve(selected_path):
        fig = go.Figure()

        fig.update_layout(
            title='C–V Curve',
            title_font=dict(color='black',size=20,weight=300,shadow='1px 1px 2px midnightblue',family=font_family),
            margin=dict(l=20, r=80, t=40, b=20),
            plot_bgcolor='royalblue',
            paper_bgcolor='lightseagreen',
            xaxis_title='Voltage (V)',
            yaxis_title='Capacitance (pF)',
            autosize=True
        )
        fig.update_yaxes(
            linewidth=2,
            title_font=dict(family=font_family,size=20,shadow='1 1 2px midnightblue',weight=500),
            tickfont=dict(family=font_family,size=18,weight=400)
        )
        fig.update_xaxes(
            linewidth=2,
            #title_font=dict(family=font_family,size=20,weight=300),
            title_font=dict(family=font_family,size=20,shadow='1 1 2px midnightblue',weight=500),
            tickfont=dict(family=font_family,size=18,weight=400)
        )
        data_points = []
        if not selected_path:
            return fig
        try:
            files = sorted([
                f for f in os.listdir(selected_path)
                if f.endswith(".csv")
                and (f.startswith("results_") or f.startswith("reuslts_"))
            ])
            cfg = load_config()
            stab_time = cfg.get("stabilization_time", 2)
            for fname in files:
                voltage_str = fname.split('_')[-1].replace('V.csv', '')
                voltage = float(voltage_str)
                df = pd.read_csv(os.path.join(selected_path, fname))

                if "Cp(F)" in df.columns:
                    cap_series = df["Cp(F)"]
                    scale_to_pf = 1e12
                elif "Cp(uF)" in df.columns:
                    cap_series = df["Cp(uF)"]
                    scale_to_pf = 1e6
                else:
                    continue

                last_seconds = df[df["Time(s)"] > df["Time(s)"].max() - stab_time]
                window = cap_series.loc[last_seconds.index]
                if window.empty:
                    window = cap_series

                avg_cap_pf = window.mean() * scale_to_pf
                data_points.append((voltage, avg_cap_pf))

            if not data_points:
                return fig

            data_points.sort()
            voltages, capacitances = zip(*data_points)

            fig.add_trace(go.Scatter(
                x=voltages,
                y=capacitances,
                mode='markers+lines',
                name='C–V Curve',
                marker=dict(color='gold',symbol='square',size=10),
                marker_line=dict(color='orange',width=4),
                line=dict(color='orange',width=4),
            ))

            if capacitances and min(capacitances) > 0:
                ratio = max(capacitances)/min(capacitances) if min(capacitances) else 0
                fig.update_layout(
                    yaxis_type='log' if ratio > 1e2 else 'linear',
                )
            return fig

        except Exception as e:
            print(f"⚠️ Plot error: {e}")
            return go.Figure()
