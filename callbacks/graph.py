# ========== 图形更新回调 ==========
import numpy as np
import plotly.graph_objs as go
from dash import Output, Input

font_family='Raleway'
def register_graph_callback(app, _shared_status, _time_series, _current_series):
    global shared_status, time_series, current_series
    shared_status = _shared_status
    time_series = _time_series
    current_series = _current_series

    @app.callback(
        Output('live-graph', 'figure'),
        Output('live-status', 'children'),
        Input('interval', 'n_intervals')
    )
    def update_graph(n):
        fig = go.Figure()
    
        fig.update_layout(
            title_font=dict(color='black',size=20,weight=300,shadow='1px 1px 2px midnightblue',family=font_family),
            margin=dict(l=20, r=80, t=40, b=20),
            plot_bgcolor='royalblue',
            paper_bgcolor='lightseagreen',
            xaxis_title='Time (s)',
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
        if time_series and current_series:
            y_min = np.nanmin(np.abs(current_series))
            y_max = np.nanmax(np.abs(current_series))
            span = y_max / y_min if y_min > 0 else 0
    
            yaxis_type = 'log' if span > 1e2 else 'linear'
    
            fig.add_trace(go.Scatter(
                x=time_series,
                y=current_series,
                marker=dict(color='gold',symbol='square',size=5),
                marker_line=dict(color='wheat',width=3),
                mode='lines+markers',
                name='Current',
                #line=dict(color='blue')
            ))
    
            fig.update_layout(
                title_text='Live I–t Measurement',
                autosize=True
            )
    
            #status_text = f"Voltage: {voltage_now} V Time: {time_now:.1f} s Current: {current_now:.3e} A"
            voltage_display = f"{shared_status['voltage']:.2f} V" if shared_status["voltage"] is not None else "N/A"
            time_display = f"{shared_status['time']:.1f} s" if shared_status["time"] is not None else "N/A"
            current_display = f"{shared_status['current']:.3e} A" if shared_status["current"] is not None else "N/A"
            
            status_text = f"Voltage: {voltage_display} | Time: {time_display} | Current: {current_display}"
    
        else:
            fig.update_layout(
                title_text='Waiting for measurement to start...',
            )
            status_text = "No data yet. Click 'Start Measurement' to begin."
    
    
        return fig, status_text
