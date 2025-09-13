import requests
import copy
import time
from pathlib import Path
import pandas as pd
import json
import os

# Assuming `credentials` is defined somewhere, e.g., a dictionary
# credentials = {'OPENAQ-API-KEY': 'your_api_key_here'}
with open("credentials.json", "r") as f:
    credentials = json.load(f)


class OpenAQDataFetcher:
    """
    A class to fetch and process air quality data from the OpenAQ API.
    """

    def __init__(self, api_key: str):
        self.headers = {"X-API-Key": api_key}
        self.total_api_calls = 0
        self.start = time.time()

    def get_data(self, sensor_id: int, datetime_from: str, datetime_to: str, location_name: str,
                 latitude: str, longitude: str, country_name: str):
        """
        Fetches sensor data for a specific time range and saves it to a CSV file.
        """
        data_dict = {}
        page = 1
        limit = 1000

        print(f"\nsensor_id: {sensor_id} | Fetching data from {datetime_from} to {datetime_to}")

        while True:
            url = f"https://api.openaq.org/v3/sensors/{sensor_id}/hours?datetime_to={datetime_to}&datetime_from={datetime_from}&limit={limit}&page={page}"
            readings = requests.get(url, headers=self.headers)
            readings.raise_for_status()

            # Increment the instance variable for total API calls
            self.total_api_calls += 1

            readings = readings.json()

            if readings['meta']['found'] == 0:
                print(f"No readings found from {datetime_from} to {datetime_to}")
                break

            if page == 1:
                pollutant_name = readings['results'][0]['parameter']['name']
                unit = readings['results'][0]['parameter']['units']
                page_timestamps = [f['period']['datetimeTo']['utc'] for f in readings['results']]
                data_dict['Timestamp'] = page_timestamps
                
                for stat in ['min', 'q02', 'q25', 'median', 'q75', 'q98', 'max', 'avg', 'sd']:
                    stat_data = [f['summary'][stat] for f in readings['results'] if stat in f.get('summary', {})]
                    data_dict[stat] = stat_data
            else:
                data_dict['Timestamp'] += [f['period']['datetimeTo']['utc'] for f in readings['results']]
                
                for stat in ['min', 'q02', 'q25', 'median', 'q75', 'q98', 'max', 'avg', 'sd']:
                    stat_data = [f['summary'][stat] for f in readings['results'] if stat in f.get('summary', {})]
                    data_dict[stat] += stat_data

            print(f"sensor_id: {sensor_id} | Fetched {len(readings['results'])} readings from page {page} | Total readings - {len(data_dict['Timestamp'])}")
            
            if len(readings['results']) < limit:
                print("Reached the end of data.")
                break

            page += 1
            

        if data_dict:
            print(f"Finished Fetching all data. Total readings are {len(data_dict['Timestamp'])} for sensor {sensor_id}")
            data_df = pd.DataFrame(data_dict)
            data_df['pollutant'] = pollutant_name
            data_df['location_name'] = location_name
            data_df['latitude'] = latitude
            data_df['longitude'] = longitude
            data_df['unit'] = unit
            data_df['sensor_id'] = sensor_id
            data_df['city_name'] = "Sacremento"
            data_df['state'] = "California"
            data_df['country'] = country_name
            data_file_path = Path("AQ_data") / "Sacremento" / location_name / str(sensor_id) / datetime_from[:4] / datetime_to.split("-")[1]
            data_file_path.mkdir(exist_ok=True, parents=True)
            file_name = data_file_path / (pollutant_name + "_" + str(sensor_id) + '.csv')
            data_df.to_csv(file_name, index=False)
            print(f"saved the data to {file_name}")
        else:
            return self.total_api_calls

    def get_sensor_data(self, location_id: int, location_name: str, latitude: float, longitude: float, country_name: str):
        """
        Fetches a list of sensors for a location and iterates through them to get data.
        """
        url = f"https://api.openaq.org/v3/locations/{location_id}/sensors"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        self.total_api_calls += 1
        response = response.json()

        sensor_ids = [sensor['id'] for sensor in response['results'] if sensor.get('coverage')]
        year_first = [int(sensor['datetimeFirst']['utc'][:4]) for sensor in response['results'] if sensor.get('coverage')]
        year_last = [int(sensor['datetimeLast']['utc'][:4]) for sensor in response['results'] if sensor.get('coverage')]
        years = [list(range(year1, year2 + 1)) for year1, year2 in zip(year_first, year_last)]

    
        for k in range(len(sensor_ids)):
            sensor_id = sensor_ids[k]
            for year in years[k]:
                try:
                    self.get_data(sensor_id=sensor_id,
                                  datetime_from=f"{str(year)}-01-01",
                                  datetime_to=f"{str(year)}-06-30",
                                  location_name=location_name,
                                  latitude=latitude,
                                  longitude=longitude,
                                  country_name=country_name)

                    self.get_data(sensor_id=sensor_id,
                                  datetime_from=f"{str(year)}-07-01",
                                  datetime_to=f"{str(year)}-12-31",
                                  location_name=location_name,
                                  latitude=latitude,
                                  longitude=longitude,
                                  country_name=country_name)
                                  
                    stop = time.time()
                    time.sleep(2)
                    print(f"\ntime elapsed: {(stop-self.start):.4f} | total_api_calls = {self.total_api_calls}\n")
                    
                    # if (stop - self.start) > 540:
                    #     time.sleep(40)
                except Exception as e:
                    print(f"Ran into an error: {e}. Retrying after 2 minutes\n\n")
                    time.sleep(120)
                    self.get_data(sensor_id=sensor_id,
                                  datetime_from=f"{str(year)}-01-01",
                                  datetime_to=f"{str(year)}-06-30",
                                  location_name=location_name,
                                  latitude=latitude,
                                  longitude=longitude,
                                  country_name=country_name)
                    
                    self.get_data(sensor_id=sensor_id,
                                  datetime_from=f"{str(year)}-07-01",
                                  datetime_to=f"{str(year)}-12-31",
                                  location_name=location_name,
                                  latitude=latitude,
                                  longitude=longitude,
                                  country_name=country_name)
                    stop = time.time()
                    time.sleep(30)
                    print(f"time elapsed: {(stop-self.start):.4f} | total_api_calls = {self.total_api_calls}")

# The new main execution block
if __name__ == "__main__":
    
    # Example of a mock `loc_response`
    with open("Sacremento_response.json", "r") as f:
        loc_response = json.load(f)
    
    api_fetcher = OpenAQDataFetcher(api_key=credentials['OPENAQ-API-KEY'])
    # downloaded_locs = os.listdir("./AQ_data/New Delhi/")
    for loc in loc_response['results']:
        print(f"loc id: {loc['id']}")
        country_name = loc['country']['name']
        location_name = loc['name'].replace(":", "_").replace(" ", "_").replace(",","").replace("-","").replace("(","").replace(")","").replace(".","")
        latitude = loc['coordinates']['latitude'] if loc['coordinates'].get('latitude') else None
        longitude = loc['coordinates']['longitude'] if loc['coordinates'].get('longitude') else None
        api_fetcher.get_sensor_data(location_id=loc['id'], 
                                    location_name=location_name, 
                                    latitude=latitude, longitude=longitude, country_name=country_name)