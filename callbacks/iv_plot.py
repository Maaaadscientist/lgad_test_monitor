import os
import pandas as pd
import plotly.graph_objs as go
import dash
from dash import Input, Output, State, ctx, dcc
from iv_control.config import load_config

font_family='Raleway'
def register_iv_plot_callback(app):

   # # Step 1: 点击按钮 ⇒ 显示路径下拉菜单 + 动态读取 outputs/
   # @app.callback(
   #     Output('iv-config-panel', 'style'),
   #     Output('iv-directory-dropdown', 'options'),
   #     Input('plot-iv-button', 'n_clicks'),
   #     prevent_initial_call=True
   # )
   # def show_iv_dropdown(n_clicks):
   #     if not n_clicks:
   #         return {'display': 'none'},[]
   #     else:
   #         folders = sorted([
   #             f"outputs/{d}" for d in os.listdir("outputs")
   #             if d.startswith("iv_results_") and os.path.isdir(os.path.join("outputs", d))
   #         ],reverse=True)
   #         options = [{'label': f, 'value': f} for f in folders]
   #         return {'display': 'block'}, options
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


#    # Step 2: 选定路径 ⇒ 读取数据绘图 ⇒ 自动关闭菜单
#    @app.callback(
#        Output('iv-graph', 'figure'),
#        Output('iv-config-panel', 'style'),
#        Input('iv-directory-dropdown', 'value'),
#        prevent_initial_call=True
#    )
#    def plot_iv_curve(selected_path):
#        fig = go.Figure()
#        fig.update_layout(
#            title='I–V Curve',
#            title_font=dict(color='black', size=28, weight=300, shadow='1px 1px 2px midnightblue', family=font_family),
#            margin=dict(l=20, r=80, t=50, b=20),
#            plot_bgcolor='midnightblue',
#            paper_bgcolor='darkturquoise',
#            xaxis_title='Voltage (V)',
#            yaxis_title='Current (A)',
#            autosize=True
#        )
#        fig.update_yaxes(
#            linewidth=2,
#            title_font=dict(family=font_family, size=20, shadow='0 0 3px #ff6600', weight=500),
#            tickfont=dict(family=font_family, size=18, weight=400)
#        )
#        fig.update_xaxes(
#            linewidth=2,
#            title_font=dict(family=font_family, size=20, shadow='0 0 3px #ff6600', weight=500),
#            tickfont=dict(family=font_family, size=18, weight=400)
#        )
#
#        if not selected_path:
#            return fig, {'display': 'none'}
#
#        try:
#            # 修正前缀拼写
#            files = sorted([
#                f for f in os.listdir(selected_path)
#                if f.endswith(".csv") and f.startswith("results_")
#            ])
#
#            cfg = load_config()
#            stab_time = cfg.get("stabilization_time", 2)
#            data_points = []
#
#            for fname in files:
#                voltage_str = fname.split('_')[-1].replace('V.csv', '')
#                voltage = float(voltage_str)
#
#                df = pd.read_csv(os.path.join(selected_path, fname))
#                last_seconds = df[df["Time(s)"] > df["Time(s)"].max() - stab_time]
#                avg_current = last_seconds["Current(A)"].mean()
#                data_points.append((voltage, avg_current))
#
#            # 如果根本没拿到数据，直接返回隐藏面板
#            if not data_points:
#                return fig, {'display': 'none'}
#
#            data_points.sort()
#            voltages, currents = zip(*data_points)
#
#            fig.add_trace(go.Scatter(
#                x=voltages,
#                y=currents,
#                mode='markers+lines',
#                name='I–V Curve',
#                marker=dict(color='red', symbol='square', size=5),
#                marker_line=dict(color='lightpink', width=3),
#            ))
#
#            fig.update_layout(
#                yaxis_type='log' if max(currents)/min(currents) > 1e2 else 'linear',
#            )
#            return fig, {'display': 'none'}
#
#        except Exception as e:
#            print(f"⚠️ Plot error: {e}")
#            return go.Figure(), {'display': 'none'}

    @app.callback(
        Output('iv-graph', 'figure'),
        Input('iv-directory-dropdown', 'value')
    )
    def plot_iv_curve(selected_path):
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
        data_points = []
        if not selected_path:
            return fig
        try:
            files = sorted([
                f for f in os.listdir(selected_path)
                if f.endswith(".csv") and f.startswith("reuslts_")
            ])
            cfg = load_config()
            stab_time = cfg.get("stabilization_time", 2)
            for fname in files:
                voltage_str = fname.split('_')[-1].replace('V.csv', '')
                voltage = float(voltage_str)
                df = pd.read_csv(os.path.join(selected_path, fname))
                stabilization_time = stab_time
                
                last_seconds = df[df["Time(s)"] > df["Time(s)"].max() - stabilization_time]
                avg_current = last_seconds["Current(A)"].mean()
                data_points.append((voltage, avg_current))

            data_points.sort()
            voltages, currents = zip(*data_points)

            fig.add_trace(go.Scatter(
                x=voltages,
                y=currents,
                mode='markers+lines',
                name='I–V Curve',
                marker=dict(color='gold',symbol='square',size=10),
                marker_line=dict(color='orange',width=4),
                line=dict(color='orange',width=4),
            ))

            fig.update_layout(
                yaxis_type='log' if max(currents)/min(currents) > 1e2 else 'linear',
            )
            return fig

        except Exception as e:
            print(f"⚠️ Plot error: {e}")
            return go.Figure()
