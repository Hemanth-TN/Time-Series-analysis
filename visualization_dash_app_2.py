import pandas as pd
from pathlib import Path
import plotly.express as px
from dash import Dash, html, dcc, Input, Output
import warnings
warnings.filterwarnings("ignore")

# Define the cities and load data once
CITIES = ['Bangalore', 'Chicago', 'New Delhi', 'Sacremento']
DATA = {city: pd.concat([pd.read_csv(f, index_col=['Timestamp'], parse_dates=True)
                        for f in Path(f"AQ_data/{city}").rglob("*.csv")])
        for city in CITIES}

def get_location_data(df):
    location_data = df.groupby('location_name').agg(
        latitude=('latitude', 'first'),
        longitude=('longitude', 'first'),
        readings_available=('pollutant', lambda x: x.unique().tolist())
    ).reset_index()
    location_data['size'] = 1
    return location_data

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Air Quality Monitoring Dashboard", style={'textAlign': 'center', 'color': 'blue'}),
    
    html.Div([
        # Left Panel for the City Map
        html.Div([
            html.Label('Select a city'),
            dcc.Dropdown(options=CITIES, value='Bangalore', id='city_dropdown'),
            html.Br(),
            html.Label('City Map'),
            dcc.Graph(id='city_map'),
        ], style={'padding': 10, 'flex': 1}),

        # Right Panel for Pollutant Trends
        html.Div([
            html.Label('Select Pollutants'),
            dcc.Dropdown(id='pollutant_dropdown', multi=False),
            html.Br(),
            html.Label('Time Series Trend'),
            dcc.Graph(id='timeseries_graph'),
        ], style={'padding': 10, 'flex': 1})

    ], style={'display': 'flex', 'flexDirection': 'row'})
], style={'width': '100%'})

# Callback to update the map
@app.callback(
    Output('city_map', 'figure'),
    Input('city_dropdown', 'value')
)
def show_city_sensors(city_name):
    df = DATA[city_name]
    unique_locations_df = get_location_data(df)
    
    fig = px.scatter_map(
        unique_locations_df,
        lat="latitude",
        lon="longitude",
        hover_name="location_name",
        size='size',
        hover_data={"size": False, "latitude": False, "longitude": False, 'readings_available': True},
        custom_data=['location_name'],
        zoom=10,
        width=1000,
        height=700
    )
    
    latitude = unique_locations_df['latitude'].mean()
    longitude = unique_locations_df['longitude'].mean()
    
    fig.update_layout(
        title=f"Locations in the {city_name} Region",
        geo=dict(
            center=dict(lat=latitude, lon=longitude),
            projection_scale=100
        )
    )
    return fig

# Callback to populate the pollutant dropdown based on map clicks
@app.callback(
    Output('pollutant_dropdown', 'options'),
    Output('pollutant_dropdown', 'value'),
    Input('city_map', 'clickData'),
    Input('city_dropdown', 'value') # Keep this to get the correct dataset
)
def update_pollutant_options(clickData, city_name):
    # Check if a point has been clicked
    if clickData is None or 'points' not in clickData:
        return [], []
    
    # Extract the location name from the clicked point
    location_name = clickData['points'][0]['customdata'][0]
    
    # Filter the main DataFrame for the selected city and location
    df = DATA[city_name]
    location_df = df[df['location_name'] == location_name]
    
    # Get the unique pollutants for that specific location
    pollutants = location_df['pollutant'].unique().tolist()
    
    options = [{'label': p, 'value': p} for p in pollutants]
    # Set the value to all available pollutants by default
    value = pollutants
    
    return options, value

# Callback to update the time series graph
@app.callback(
    Output('timeseries_graph', 'figure'),
    Input('city_map', 'clickData'),
    Input('pollutant_dropdown', 'value'),
    Input('city_dropdown', 'value')
)
def update_timeseries(clickData, selected_pollutant, city_name):
    # Check if a location and pollutants have been selected
    if clickData is None or 'points' not in clickData or not selected_pollutant:
        return {}
    
    # Extract the location name from the clicked point
    location_name = clickData['points'][0]['customdata'][0]
    
    # Filter the main DataFrame for the selected location and pollutants
    df = DATA[city_name]
    filtered_df = df[
        (df['location_name'] == location_name) & 
        (df['pollutant'] == selected_pollutant)
    ]
    
    # Plot the time series
    fig = px.scatter(
        filtered_df,
        x=filtered_df.index,
        y='avg',
        color='pollutant',
        title=f"Time Series for {selected_pollutant} in {location_name}",
        width=1000,
        height=700
    )

    fig.update_layout(xaxis_title='Timestamp', yaxis_title=filtered_df['unit'].unique()[0])
    return fig

if __name__ == '__main__':
    app.run(debug=True)