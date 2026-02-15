import time
import requests
import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from api.models import FuelStation


class Command(BaseCommand):
    help = "Load fuel prices using POI Name Search (Fallbacks to City)"

    def handle(self, *args, **kwargs):
        file_path = "fuel_prices.csv"

        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File {file_path} not found."))
            return

        # Resume Capability: Filter out IDs already loaded
        existing_ids = set(FuelStation.objects.values_list("opis_id", flat=True))
        df_pending = df[~df["OPIS Truckstop ID"].isin(existing_ids)]

        remaining = len(df_pending)
        if remaining == 0:
            self.stdout.write(self.style.SUCCESS("All data loaded."))
            return

        self.stdout.write(f"Processing {remaining} rows using POI Name Search...")

        headers = {"User-Agent": "StudentFuelProject/1.0"}

        for index, row in df_pending.iterrows():
            opis_id = row["OPIS Truckstop ID"]
            city = row["City"]
            state = row["State"]
            name = row["Truckstop Name"]

            # Strategy 1: Try searching by Truckstop Name + City + State
            # Clean the name slightly (remove store numbers if needed, but usually OSM handles them)
            query_poi = f"{name}, {city}, {state}"

            # Strategy 2: Fallback to City Center (sufficient for assignment routing)
            query_city = f"{city}, {state}, USA"

            coords = self.geocode_photon(query_poi, headers)

            if not coords:
                # Fallback!
                coords = self.geocode_photon(query_city, headers)
                if coords:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  -> Fallback used for: {name} (Used City Center)"
                        )
                    )

            if coords:
                lon, lat = coords
                FuelStation.objects.create(
                    opis_id=opis_id,
                    name=name,
                    address=row["Address"],
                    city=city,
                    state=state,
                    retail_price=row["Retail Price"],
                    location=Point(lon, lat),
                )
                self.stdout.write(f"Loaded: {name}")
            else:
                self.stdout.write(self.style.ERROR(f"Failed: {name}"))

            # Polite Delay
            time.sleep(1.0)

    def geocode_photon(self, query, headers):
        """Helper to query Photon"""
        try:
            response = requests.get(
                "https://photon.komoot.io/api/",
                params={"q": query, "limit": 1},
                headers=headers,
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                if data["features"]:
                    # Photon returns [lon, lat]
                    return data["features"][0]["geometry"]["coordinates"]
        except Exception:
            pass
        return None
