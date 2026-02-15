import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from api.models import FuelStation

# Ensure pygeocodio is installed: 'uv add pygeocodio'
from geocodio import GeocodioClient
from geocodio.exceptions import GeocodioAuthError


class Command(BaseCommand):
    help = "Load 1500 rows of fuel data using Geocodio"

    def handle(self, *args, **kwargs):
        # 1. Setup API Client
        api_key = os.environ.get("GEOCODIO_API_KEY")
        if not api_key:
            self.stdout.write(
                self.style.ERROR(
                    "GEOCODIO_API_KEY is missing from environment variables"
                )
            )
            return

        client = GeocodioClient(api_key)

        # 2. Read CSV
        file_path = "fuel_prices.csv"
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"{file_path} not found"))
            return

        # 3. Filter Existing Data (Resume Capability)
        # We don't want to re-geocode IDs we already have
        existing_ids = set(FuelStation.objects.values_list("opis_id", flat=True))
        df_pending = df[~df["OPIS Truckstop ID"].isin(existing_ids)]

        # 4. Limit to 1500 Rows
        # This ensures we don't exceed the daily free limit (2,500)
        LIMIT = 1500
        df_to_process = df_pending.head(LIMIT)

        count = len(df_to_process)
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No new data to load."))
            return

        self.stdout.write(f"Preparing to geocode {count} records...")

        # 5. Batch Processing
        # Geocodio accepts batches. Processing 100 at a time is optimal.
        BATCH_SIZE = 100
        records = df_to_process.to_dict("records")
        total_saved = 0

        for i in range(0, count, BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]

            # Map ID -> Address String for Geocodio
            address_map = {}
            for row in batch:
                # Construct address: "Address, City, State"
                addr = f"{row['Address']}, {row['City']}, {row['State']}"
                address_map[row["OPIS Truckstop ID"]] = addr

            try:
                self.stdout.write(f"  > Geocoding batch {i}-{i + len(batch)}...")

                # API Call
                results = client.geocode(address_map)

                new_stations = []
                for row in batch:
                    oid = row["OPIS Truckstop ID"]
                    result = results.get(oid)

                    if result and result.coords:
                        # Geocodio returns (lat, lon)
                        # PostGIS Point expects (lon, lat)
                        lat, lon = result.coords

                        new_stations.append(
                            FuelStation(
                                opis_id=oid,
                                name=row["Truckstop Name"],
                                address=row["Address"],
                                city=row["City"],
                                state=row["State"],
                                retail_price=row["Retail Price"],
                                location=Point(lon, lat),
                            )
                        )

                # Bulk Save to DB
                if new_stations:
                    FuelStation.objects.bulk_create(new_stations)
                    total_saved += len(new_stations)

            except GeocodioAuthError:
                self.stdout.write(
                    self.style.ERROR("Geocodio API Key Invalid or Quota Exceeded.")
                )
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error in batch: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully loaded {total_saved} stations.")
        )
