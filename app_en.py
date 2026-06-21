import pandas as pd
import numpy as np
import dash
import psycopg2
import os

from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# =====================================================
# 📌 1. DATA LOADING FROM SUPABASE
# =====================================================
def load_data():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        sslmode='require'
    )
    df = pd.read_sql("SELECT username, tokens, hour, fecha FROM tips_events", conn)
    conn.close()
    return df

df = load_data()

# Rename columns to match original logic
df = df.rename(columns={'username': 'Usuario', 'tokens': 'Tokens', 'hour': 'Hora', 'fecha': 'Fecha'})

# Parse datetime
df['Fecha'] = pd.to_datetime(df['Fecha'])
df['Hora']  = pd.to_datetime(df['Hora'], utc=True).dt.tz_convert(None)

df['fecha_hora'] = df.apply(
    lambda row: datetime.combine(row['Fecha'].date(), row['Hora'].time()), axis=1
)
df['fecha'] = df['fecha_hora'].dt.date

# Helpful time columns
df['day_of_week'] = df['fecha_hora'].dt.day_name()
df['intervalo']   = df['fecha_hora'].dt.floor('30min')
df['h']           = df['intervalo'].dt.strftime('%H:%M')
df['Usuario']     = df['Usuario'].astype(str).str.strip()

# Date range for DatePicker
min_date = df['fecha'].min()
max_date = df['fecha'].max()


# =====================================================
# 📌 2. HISTORICAL / GLOBAL AGGREGATIONS
# =====================================================

# Heatmap Data
df_intervalos_hist = df.groupby('intervalo', as_index=False)['Tokens'].sum()
df_intervalos_hist['dia_semana'] = df_intervalos_hist['intervalo'].dt.day_name()
df_intervalos_hist['h']          = df_intervalos_hist['intervalo'].dt.strftime('%H:%M')

promedios_hist = df_intervalos_hist.groupby(['dia_semana', 'h'])['Tokens'].mean().unstack().fillna(0)
conteos_hist   = df_intervalos_hist.groupby(['dia_semana', 'h'])['Tokens'].count().unstack().fillna(0)

orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
promedios_hist = promedios_hist.reindex(orden_dias)
conteos_hist   = conteos_hist.reindex(orden_dias)

# Historical Heatmap
H3_hist = go.Figure(data=go.Heatmap(
    z=promedios_hist.values, x=promedios_hist.columns, y=promedios_hist.index,
    colorscale='BuPu', showscale=True,
    hovertemplate="Day: %{y}<br>Slot: %{x}<br>Average: %{z:.0f}tk<extra></extra>"
))

anotaciones_h3 = []
shapes_h3 = []
for i, dia in enumerate(promedios_hist.index):
    for j, franja in enumerate(promedios_hist.columns):
        valor = promedios_hist.iloc[i, j]
        n     = conteos_hist.iloc[i, j]
        anotaciones_h3.append(dict(
            x=franja, y=dia, text=f"{valor:.0f}tk<br>n={n}", showarrow=False,
            font=dict(size=9, color="black" if valor < (promedios_hist.values.max() / 2) else "white")
        ))
        if n < 3:
            shapes_h3.append(dict(
                type="rect", x0=j-0.5, y0=i-0.5, x1=j+0.5, y1=i+0.5,
                line=dict(color="gray", width=1.5, dash="dash"), fillcolor="rgba(0,0,0,0)"
            ))

H3_hist.update_layout(
    title='<b>All-Time Average Tokens by Hourly Time Slot</b>',
    xaxis=dict(side='bottom', tickmode='linear', title='Time Slot'),
    yaxis=dict(autorange='reversed', title='Day of the Week'),
    annotations=anotaciones_h3, shapes=shapes_h3, height=500,
    margin=dict(l=100, r=20, t=50, b=50), plot_bgcolor='white'
)

# Global audience metrics
usuarios_unicos_totales = df['Usuario'].nunique()
ranking_df_hist = (
    df.groupby('Usuario')['Tokens'].sum()
    .reset_index()
    .sort_values(by='Tokens', ascending=False)
    .head(15)
)
ranking_df_hist['Puesto'] = range(1, len(ranking_df_hist) + 1)

total_tokens_hist = df['Tokens'].sum()
frases_porcentaje_hist = []
for n in [5, 8, 10, 15]:
    pct = df.groupby('Usuario')['Tokens'].sum().sort_values(ascending=False).head(n).sum() / total_tokens_hist * 100
    frases_porcentaje_hist.append(f"Top {n} users represent {pct:.1f}% of total tokens.")


# =====================================================
# 📌 3. HELPER FUNCTIONS
# =====================================================
def get_fortnight_filter(target_date):
    dt = pd.to_datetime(target_date)
    if dt.day <= 15:
        start_date = datetime(dt.year, dt.month, 1).date()
        end_date   = datetime(dt.year, dt.month, 15).date()
    else:
        start_date  = datetime(dt.year, dt.month, 16).date()
        next_month  = dt.month + 1 if dt.month < 12 else 1
        next_year   = dt.year if dt.month < 12 else dt.year + 1
        end_date    = (datetime(next_year, next_month, 1) - timedelta(days=1)).date()
    return start_date, end_date

def get_week_filter(target_date):
    dt     = pd.to_datetime(target_date)
    monday = (dt - timedelta(days=dt.weekday())).date()
    return [(monday + timedelta(days=i)) for i in range(7)]


# =====================================================
# 📌 4. DASH APP SETUP & LAYOUT
# =====================================================
app    = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

sidebar = html.Div(
    [
        html.H2("Token Analytics", className="display-4",
                style={'textAlign': 'center', 'font-variant': 'small-caps', 'fontSize': '1.8rem', 'marginTop': '20px'}),
        html.Hr(),
        html.H3("Select Target Date:", style={'textAlign': 'center', 'fontSize': '1.1rem', 'marginBottom': '10px'}),
        html.Div([
            dcc.DatePickerSingle(
                id='global-date-picker',
                min_date_allowed=min_date,
                max_date_allowed=max_date,
                date=max_date,
                display_format='YYYY-MM-DD',
                style={'width': '100%', 'textAlign': 'center', 'marginBottom': '30px'}
            )
        ], style={'display': 'flex', 'justifyContent': 'center'}),
        html.Hr(),
        html.H3("Analysis Perspective:", style={'textAlign': 'center', 'fontSize': '1.1rem', 'marginBottom': '20px'}),
        dbc.Nav(
            [
                dbc.NavLink("Historical View",       href="/",           active="exact"),
                dbc.NavLink("Users & Distribution",  href="/page2_url",  active="exact"),
            ],
            vertical=True, pills=True, style={"fontSize": 18, "gap": "10px"}
        ),
    ],
    style={
        "position": "fixed", "top": 0, "left": 0, "bottom": 0,
        "width": "16rem", "padding": "2rem 1rem", "background-color": "#f8f9fa",
    },
)

app.layout = dbc.Container([
    dcc.Location(id="url", refresh=False),
    dbc.Row([
        dbc.Col(sidebar, width=3),
        dbc.Col(html.Div(id="page-content", style={"padding": "2rem 1rem"}), width=9)
    ])
], fluid=True)


# =====================================================
# 📌 5. CALLBACK CONTROLLER
# =====================================================
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname"),
     Input("global-date-picker", "date")]
)
def render_page_content(pathname, selected_date):
    if not selected_date:
        return html.Div("Please pick a valid date from the sidebar controller.")

    selected_dt = pd.to_datetime(selected_date).date()

    fn_start, fn_end = get_fortnight_filter(selected_dt)
    df_fortnight     = df[(df['fecha'] >= fn_start) & (df['fecha'] <= fn_end)].copy()

    # -------------------------------------------------
    # PAGE 1: HISTORICAL VIEW
    # -------------------------------------------------
    if pathname == "/":
        if df_fortnight.empty:
            return html.Div(f"No records found for the fortnight period of {fn_start} to {fn_end}.")

        # H2: Fortnightly Performance by Day of the Week
        total_por_dia_fn = df_fortnight.groupby('fecha')['Tokens'].sum().reset_index()
        total_por_dia_fn['dia_semana'] = pd.to_datetime(total_por_dia_fn['fecha']).dt.day_name()

        resumen_por_dia_fn = total_por_dia_fn.groupby('dia_semana')['Tokens'].agg(
            promedio_diario='mean', dias_registrados='count'
        ).reset_index()
        resumen_por_dia_fn = resumen_por_dia_fn.set_index('dia_semana').reindex(orden_dias).reset_index().fillna(0)
        resumen_por_dia_fn['texto_barras'] = resumen_por_dia_fn['dias_registrados'].apply(lambda n: f'n={n}')

        H2 = px.bar(
            resumen_por_dia_fn, x='dia_semana', y='promedio_diario',
            title=f'<b>Average Tokens by Day of the Week</b><br><sub>Fortnight Period: {fn_start} to {fn_end}</sub>',
            labels={'dia_semana': 'Day of the Week', 'promedio_diario': 'Average Tokens'},
            text='texto_barras',
        )
        colores = ['gray' if n < 2 else '#7F77DD' for n in resumen_por_dia_fn['dias_registrados']]
        H2.update_traces(marker_color=colores, textposition='outside', textfont_size=10)
        H2.update_layout(
            height=400, plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showline=True, linecolor='lightgray'),
            yaxis=dict(showgrid=True, gridcolor='whitesmoke'),
            annotations=[dict(text="n = days recorded in fortnight", xref="paper", yref="paper",
                              x=1.0, y=1.1, showarrow=False, font=dict(size=11, color="gray"))]
        )

        # H1: Fortnightly Performance by Time Slot
        df_intervalos_fn   = df_fortnight.groupby('intervalo', as_index=False)['Tokens'].sum()
        df_intervalos_fn['h'] = df_intervalos_fn['intervalo'].dt.strftime('%H:%M')
        tokens_por_franja_fn  = (
            df_intervalos_fn.groupby('h', as_index=False)['Tokens']
            .mean()
            .rename(columns={'Tokens': 'tk_promedio_por_franja'})
        )

        H1 = px.bar(
            tokens_por_franja_fn, x='h', y='tk_promedio_por_franja',
            title=f'<b>Average Tokens by Time Slot</b><br><sub>Fortnight Period: {fn_start} to {fn_end}</sub>',
            labels={'h': 'Time Slot', 'tk_promedio_por_franja': 'Average Tokens'}
        )
        H1.update_layout(plot_bgcolor='rgba(0,0,0,0)')

        return html.Div([
            html.H1("Fortnightly & Historical Analytics", style={'marginBottom': '5px'}),
            html.P(f"Currently inspecting the payroll fortnight window: {fn_start} to {fn_end}",
                   className="text-muted", style={'marginBottom': '25px'}),
            dcc.Graph(figure=H2),
            dcc.Graph(figure=H1),
            dcc.Graph(figure=H3_hist)
        ])

    # -------------------------------------------------
    # PAGE 2: USERS & DISTRIBUTION VIEW
    # -------------------------------------------------
    elif pathname == "/page2_url":
        week_days = get_week_filter(selected_dt)
        df_week   = df[df['fecha'].isin(week_days)].copy()

        if not df_week.empty:
            ranking_wk        = df_week.groupby('Usuario')['Tokens'].sum().sort_values(ascending=False)
            top_usuarios_semana = ranking_wk.head(10).index.tolist()

            df_week['Usuario_agrupado'] = np.where(
                df_week['Usuario'].isin(top_usuarios_semana), df_week['Usuario'], 'Others'
            )
            tokens_dia = df_week.groupby(['fecha', 'Usuario_agrupado'])['Tokens'].sum().reset_index()
            tokens_dia['fecha_bonita'] = pd.to_datetime(tokens_dia['fecha']).dt.strftime('%a %d-%m')

            orden_leyenda = top_usuarios_semana.copy()
            if 'Others' in tokens_dia['Usuario_agrupado'].values:
                orden_leyenda.append('Others')

            lista_colores = px.colors.qualitative.T10[:len(top_usuarios_semana)]
            mapa_colores  = {user: color for user, color in zip(top_usuarios_semana, lista_colores)}
            mapa_colores['Others'] = 'lightgray'

            H4 = px.bar(
                tokens_dia, x='fecha_bonita', y='Tokens', color='Usuario_agrupado',
                title=f'<b>Daily Tokens — Week of {week_days[0].strftime("%Y-%m-%d")}</b>',
                category_orders={'Usuario_agrupado': orden_leyenda},
                color_discrete_map=mapa_colores,
                labels={'fecha_bonita': 'Date', 'Tokens': 'Total Tokens', 'Usuario_agrupado': 'User'},
            )
            H4.update_layout(barmode='stack', xaxis_tickangle=-45, plot_bgcolor='white', height=500)
        else:
            H4 = px.bar(title=f"No data available for the week of {week_days[0]}")

        if not df_fortnight.empty:
            top15_users_fn = df_fortnight.groupby('Usuario')['Tokens'].sum().nlargest(15).index

            frequency_df = (
                df_fortnight[df_fortnight['Usuario'].isin(top15_users_fn)]
                .groupby(['Usuario', 'day_of_week', 'h'])
                .size()
                .reset_index(name='interactions')
            )

            user_peak_hours = (
                frequency_df
                .sort_values(['Usuario', 'interactions'], ascending=[True, False])
                .groupby('Usuario')
                .head(2)
            )

            user_peak_hours_table = user_peak_hours.rename(columns={
                'Usuario': 'User', 'day_of_week': 'Favorite Day',
                'h': 'Time Block (30m)', 'interactions': 'Frequency (Count)'
            }).sort_values(by=['User', 'Frequency (Count)'], ascending=[True, False])

            peak_table_component = dbc.Table.from_dataframe(
                user_peak_hours_table, striped=True, bordered=True, hover=True,
                style={'marginTop': '15px', 'maxWidth': '800px', 'fontSize': '14px'}
            )
        else:
            peak_table_component = html.P("No user activity recorded in this period.")

        return html.Div([
            html.H1("User Ranking & Concentration Analysis", style={'marginBottom': '30px'}),

            dbc.Card([
                dbc.CardBody([
                    html.H5("Total Global Audience", className="text-muted"),
                    html.H2(f"{usuarios_unicos_totales} Unique Users", className="text-primary")
                ])
            ], style={'marginBottom': '30px', 'width': '400px'}),

            html.H3("Top 15 Users by Token Contribution (All-Time)"),
            dbc.Table.from_dataframe(
                ranking_df_hist[['Puesto', 'Usuario', 'Tokens']],
                striped=True, bordered=True, hover=True,
                style={'marginBottom': '30px', 'maxWidth': '600px'}
            ),

            html.H3("Concentration Analysis (Pareto Principle)"),
            html.Ul([html.Li(frase) for frase in frases_porcentaje_hist],
                    style={'fontSize': '16px', 'lineHeight': '2', 'marginBottom': '40px'}),

            html.H3("Weekly Token Distribution (Selected Date's Week)"),
            dcc.Graph(figure=H4),

            html.Hr(style={'marginTop': '40px', 'marginBottom': '40px'}),

            html.H3(f"User Peak Activity Analysis — Fortnight: {fn_start} to {fn_end}"),
            html.P("Identifies the two specific 30-minute blocks where the top performers registered highest frequency during this specific payroll fortnight.",
                   className="text-muted"),
            peak_table_component
        ])

    return html.Div([
        html.H1("404: Not Found", className="text-danger"),
        html.P(f"The path '{pathname}' was not found.")
    ])


# =====================================================
# 📌 6. RUN SERVER
# =====================================================
if __name__ == '__main__':
    app.run(debug=True)
