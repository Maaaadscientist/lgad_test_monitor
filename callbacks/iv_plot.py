import os
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import Input, Output, State, ctx, dcc
from iv_control.config import load_config

font_family='Raleway'
def register_iv_plot_callback(app):
    # —— 合并“显示”和“隐藏 iv-config-panel”到一个回调
    @app.callback(
        Output('iv-config-panel', 'style'),
        Output('iv-directory-dropdown', 'options'),
        Input('plot-iv-button', 'n_clicks'),
        Input('iv-hide-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def toggle_iv_panel(plot_nclicks, hide_nclicks):
        triggered_id = ctx.triggered_id

        # --------- 如果是“Plot I–V”按钮被按下
        if triggered_id == 'plot-iv-button':
            # 列出所有 outputs/iv_results_* 文件夹
            folders = sorted(
                [f"outputs/{d}" for d in os.listdir("outputs")
                 if d.startswith("iv_results_") and os.path.isdir(os.path.join("outputs", d))],
                reverse=True
            )
            options = [{'label': f, 'value': f} for f in folders]
            # 显示面板 + 填充下拉菜单
            return {'display': 'block'}, options

        # --------- 如果是“收起下拉菜单”按钮被按下
        elif triggered_id == 'iv-hide-button':
            # 隐藏面板，不改变 options
            return {'display': 'none'}, dash.no_update

        # --------- 其他情况（虽然 prevent_initial_call=True，但写个兜底）
        return dash.no_update, dash.no_update

    @app.callback(
        Output('iv-graph', 'figure'),
        Input('iv-directory-dropdown', 'value'),
        State('iv-graph', 'figure'),
    )
    def plot_iv_curve(selected_path, existing_figure):
    
        if not selected_path or not existing_figure:
            fig = go.Figure()
            fig.update_layout(
                title='I–V Curve',
                title_font=dict(color='black',size=20,weight=300,shadow='1px 1px 2px midnightblue',family=font_family),
                margin=dict(l=20, r=80, t=40, b=20),
                plot_bgcolor='royalblue',
                paper_bgcolor='lightseagreen',
                xaxis_title='Voltage (V)',
                yaxis_title='Current (A)',
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
            return fig
        fig = go.Figure(existing_figure)  # ← 从已有图像初始化
    
        try:
            files = sorted([
                f for f in os.listdir(selected_path)
                if f.endswith(".csv") and f.startswith("reuslts_")
            ])
            cfg = load_config()
            stab_time = cfg.get("stabilization_time", 2)
            data_points = []
    
            for fname in files:
                voltage_str = fname.split('_')[-1].replace('V.csv', '')
                voltage = float(voltage_str)
                df = pd.read_csv(os.path.join(selected_path, fname))
                last_seconds = df[df["Time(s)"] > df["Time(s)"].max() - stab_time]
                avg_current = last_seconds["Current(A)"].mean()
                data_points.append((abs(voltage), abs(avg_current)))
    
            data_points.sort()
            voltages, currents = zip(*data_points)
    
            color_idx = len(fig.data)
            #color_palette = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'gold']
            color_palette = ['gold','orangered','springgreen','violet','gray','blue','turquoise']
            color = color_palette[color_idx % len(color_palette)]
    
            fig.add_trace(go.Scatter(
                x=voltages,
                y=currents,
                mode='markers+lines',
                name=selected_path.split("/")[-1],
                marker=dict(color=color, symbol='square', size=8),
                line=dict(color=color, width=3),
                marker_line=dict(color=color, width=3),
            ))
    
            fig.update_layout(
                yaxis_type='log' if any(t.y and max(t.y)/min(t.y) > 1e2 for t in fig.data if t.y) else 'linear',
                autosize=True,
                legend=dict(
                    font=dict(
                        family="Raleway",
                        size=14,
                        color="black"
                    ),
                ),
            )
    
            return fig
    
        except Exception as e:
            print(f"⚠️ Plot error: {e}")
            return go.Figure(existing_figure)
    
