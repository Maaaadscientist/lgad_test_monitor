from dash import html, dcc

from iv_control.config import load_config  # 用于更新全局 config

def generate_layout():
    return html.Div([
        html.H2("Keithley 2470 I–V Measurement"),
#        # 图表显示区域
        # 控制按钮
        html.Button("Start Measurement", id="start-button"),
        html.Button("Stop Measurement", id="stop-button", disabled=True),
        html.Button("Config Parameters", id='config-button', n_clicks=0),
        html.Button("Plot IV Curve", id='plot-iv-button'),
        # 容器：IV 绘图配置区域（初始隐藏）
        html.Div(id='iv-config-panel', style={'display': 'none'}, children=[
            dcc.Dropdown(
                id='iv-directory-dropdown',
                placeholder="Select IV result folder",
                value=None,
                style={'width': '60%', 'marginTop': '10px'}
            ),
                        # 新增一个“隐藏”按钮
            html.Button(
                'Hide Options',
                id='iv-hide-button',
                n_clicks=0,
                style={'marginLeft': '10px', 'display': 'inline-block', 'verticalAlign': 'middle'}
            )
        ]),

        
        # 弹出配置参数区域
        html.Div(id='config-panel', style={'display': 'none'}, children=[
            html.H4("Measurement Configuration"),
        
            html.Div([html.Label("Start Voltage:"), dcc.Input(id='input-start-voltage', type='number')]),
            html.Div([html.Label("Stop Voltage:"), dcc.Input(id='input-stop-voltage', type='number')]),
            html.Div([html.Label("Step Voltage:"), dcc.Input(id='input-step-voltage', type='number')]),
            html.Div([html.Label("Measurement Duration (s):"), dcc.Input(id='input-measurement-duration', type='number')]),
            html.Div([html.Label("Sample Interval (s):"), dcc.Input(id='input-sample-interval', type='number')]),
            html.Div([html.Label("Stabilization Time (s):"), dcc.Input(id='input-stabilization-time', type='number')]),
            html.Div([html.Label("Maximum Current (A):"), dcc.Input(id='input-maximum-current', type='number')]),
        
            html.Br(),
            html.Button("Confirm", id='confirm-config', n_clicks=0, style={'marginRight': '10px'}),
            html.Button("Cancel", id='cancel-config', n_clicks=0),
            html.Div(id='config-status', style={'color': 'green', 'marginTop': '10px'})
        ]),

#        # 状态显示文本
        html.Div(id='env-status', style={
            'margin': '15px',
            'fontSize': 20,
            'fontWeight': 'bold',
            'color': 'blue',
            'textAlign': 'center'
        }),
        html.Div(id='live-status', style={
         'margin': '15px', 'fontSize': 18, 'fontWeight': 'bold', 'color': '#003366'}),
        dcc.Graph(
            id='live-graph',
            style={'width': '90vw', 'height': '36vh',}  # 使用视口单位
        ),
        html.Hr(),
        #html.H4("Plot I-V Curve"),
        dcc.Graph(id='iv-graph', 
                  style={'width': '90vw', 'height': '36vh'}
                 ),
        # 定时器组件
        dcc.Interval(id='interval', interval=1000, n_intervals=0),
        #
        dcc.Store(id='config-store', data=load_config()),
    ])
