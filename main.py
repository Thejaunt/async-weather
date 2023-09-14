import json
import os
from random import randint
import asyncio

import dotenv
import aiohttp

dotenv.load_dotenv()


class OpenWeatherMapAPI:
    def __init__(self, city, data_collector, units=None):
        self.city = city.get("city")
        self.lon = city.get("lon")
        self.lat = city.get("lat")
        self.units = units or "Metric"
        self.__api_key = os.getenv("open_weather_key")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather?"
        self.collector = data_collector

    def get_url(self, q=None) -> str:
        url = f"{self.base_url}appid={self.__api_key}&lat={self.lat}&lon={self.lon}&units={self.units}&{q}"
        return url

    async def get_response(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.get_url()) as response:
                return await response.json()

    async def collect_temperature(self):
        res = await self.get_response()
        try:
            temp = res.get("main").get("temp")
            self.collector.append_data(temp)
        except AttributeError:
            self.collector.record_failed_city(self.city)


class WeatherStackAPI:
    def __init__(self, city, data_collector):
        self.city = city.get("city")
        self.lon = city.get("lon")
        self.lat = city.get("lat")
        self.__api_key = os.getenv("weatherstack_key")
        self.base_url = "http://api.weatherstack.com/current?"
        self.collector = data_collector

    def get_url(self, q=None):
        url = f"{self.base_url}access_key={self.__api_key}&query={self.lat},{self.lon}&{q}"
        return url

    async def get_response(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.get_url()) as response:
                return await response.json()

    async def collect_temperature(self):
        resp = await self.get_response()
        try:
            temp = resp.get("current").get("temperature")
            self.collector.append_data(temp)
        except AttributeError:
            self.collector.record_failed_city(self.city)


class Data:
    def __init__(self):
        self.data = list()
        self.failed_cities = set()
        self.failed_request_counter = int()

    def append_data(self, temp):
        self.data.append(temp)

    def get_data(self):
        return self.data

    def record_failed_city(self, city):
        self.failed_request_counter += 1
        self.failed_cities.add(city)

    def get_failed_cities(self):
        return self.failed_cities


def calculate_average_temp(data=None):
    success_cities_amount = len(data)
    if (not data) or (success_cities_amount == 0):
        return "Data collection failed"
    total_temp_number = float()
    for temp in data:
        total_temp_number += float(temp)

    res = round(total_temp_number / success_cities_amount, 2)
    return res


def get_cities():
    cities = []
    with open("cities.json") as js:
        ct = json.load(js)
        for c in ct:
            cities.append(
                {
                    "city": c.get("city"),
                    "lon": c.get("lng"),
                    "lat": c.get("lat"),
                }
            )
    return cities


async def main():
    cities = get_cities()
    collector = Data()
    apis = [
        OpenWeatherMapAPI,
        WeatherStackAPI,
    ]
    async with asyncio.TaskGroup() as tg:
        for api in apis:
            for city in cities:
                tg.create_task(api(city, data_collector=collector).collect_temperature())

    cities_failed = len(collector.failed_cities)
    cities_counted = len(collector.get_data())
    average_temp = calculate_average_temp(collector.get_data())
    failed_requests = collector.failed_request_counter
    print(
        f"""
            APIs used - {len(apis)}
            Total cities participated - {len(cities)}
            Cities failed - {cities_failed}
            Cities counted - {cities_counted}
            Failed requests - {failed_requests}
            China average temperature - {average_temp}* C
        """
    )

asyncio.run(main())


