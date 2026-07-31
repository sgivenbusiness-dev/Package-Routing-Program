 #Sean Given, Student ID: 010925184

from __future__ import annotations
import csv
from datetime import timedelta
from typing import Any, Iterable, List, Optional, Tuple

#tent
import os
import datetime as dt

#load data form csvs at import time
with open("addresses.csv", newline="") as f:
    AddressCSV: List[List[str]] = list(csv.reader(f))

with open("distances.csv", newline="") as f:
    DistanceCSV: List[List[str]] = list(csv.reader(f))

# Precompute a quick lookup: address string -> row index (int)
# address index is a dict mapping so later lookups are O(1)
ADDRESS_INDEX = {row[2]: int(row[0]) for row in AddressCSV if row and len(row) >= 3}

def address_index(address: str) -> int:
    """Return the address row index for a given address string."""
    return ADDRESS_INDEX[address]


def distance_between(idx1: int, idx2: int) -> float:
    """Distance (float miles) between two address indices, using the upper/lower triangle."""
    d = DistanceCSV[idx1][idx2]
    if d == "":
        d = DistanceCSV[idx2][idx1]
    return float(d)


# Hash table w/ chaining for key -> value (package id -> package)
class ChainHashTable:
    """Simple chaining hash table for key->value (package id -> Package)."""

    def __init__(self, initialcapacity: int = 40) -> None:
        self.table: List[List[List[Any]]] = [[] for _ in range(initialcapacity)]

    def insert(self, key: Any, item: Any) -> bool:
        bucket = hash(key) % len(self.table)
        bucket_list = self.table[bucket]

        for kv in bucket_list:
            if kv[0] == key:
                kv[1] = item  # update
                return True

        bucket_list.append([key, item])  # insert
        return True

    def search(self, key: Any) -> Optional[Any]:
        bucket = hash(key) % len(self.table)
        bucket_list = self.table[bucket]

        for kv in bucket_list:
            if kv[0] == key:
                return kv[1]
        return None

    def remove(self, key: Any) -> bool:
        """Remove key if present"""
        bucket = hash(key) % len(self.table)
        bucket_list = self.table[bucket]

        for i, kv in enumerate(bucket_list):
            if kv[0] == key:
                del bucket_list[i]
                return True
        return False

#<><><><><><><><><>
#domain -- classes
#<><><><><><><><><>

"""package class stores all attributes needed and accesed by a single package ID (found in csv),
along with departure time and delivery time"""
class Package:
    def __init__(
        self,
        ID: int,
        street: str,
        city: str,
        state: str,
        zip: str,
        deadline: str,
        weight: str,
        notes: str,
        status: str = "At Hub",
        departure_time: Optional[timedelta] = None,
        delivery_time: Optional[timedelta] = None,
        carrier: Optional[int] = None ###################
    ) -> None:
        self.ID = ID
        self.street = street
        self.city = city
        self.state = state
        self.zip = zip
        self.deadline = deadline
        self.weight = weight
        self.notes = notes
        self.status = status
        self.departureTime = departure_time
        self.deliveryTime = delivery_time
        self.carrier = carrier ###################


    #csv styule snapshot of the truck state
    def __str__(self) -> str:
        return (
            f"ID: {self.ID}, "
            f"{self.street:<20}, {self.city}, {self.state}, {self.zip}, "
            f"Deadline: {self.deadline}, {self.weight}, {self.status}, "
            f"Departure Time: {self.departureTime}, Delivery Time: {self.deliveryTime}, "
            f"Truck: {self.carrier}"
    )


    def status_update(self, t: timedelta) -> None:
        """Update status based on provided time-of-day (as timedelta since midnight)."""
        if self.ID in {6, 25, 28, 32} and t < timedelta(hours=9, minutes=5):
            self.status = "In the air"
        elif self.deliveryTime is None:
            self.status = "At the hub"
        elif t < (self.departureTime or timedelta(0)):
            self.status = "At the hub"
        elif t < self.deliveryTime:
            self.status = "En route"
        else:
            self.status = "Delivered"

        # Address correction for package 9 after 10:20
        if self.ID == 9:
            if t > timedelta(hours=10, minutes=20):
                self.street = "410 S State St"
                self.zip = "84111"
            else:
                self.street = "300 State St"
                self.zip = "84103"


 # Read packages.csv and insert each package into the hash table.
def load_package_data(filename: str, table: ChainHashTable) -> None:

    with open(filename, newline="") as f:
        reader = csv.reader(f, delimiter=",")
        next(reader, None)  # skip header
        for row in reader:
            p = Package(
                ID=int(row[0]),
                street=row[1],
                city=row[2],
                state=row[3],
                zip=row[4],
                deadline=row[5],
                weight=row[6],
                notes=row[7],
                status="At the Hub",
                departure_time=None,
                delivery_time=None,
            )
            table.insert(p.ID, p)


class Truck:
    # delivery truck w/ speed (mph), miles driven, current location, start time, and assigned packages.
    def __init__(
        self,
        truck_id: int,
        speed_mph: float,
        miles: float,
        current_location: str,
        depart_time: timedelta,
        package_ids: list[int],
    ) -> None:
        self.truck_id = truck_id
        self.speed = speed_mph
        self.miles = miles
        self.currentLocation = current_location
        self.time = depart_time
        self.departTime = depart_time
        self.packages = list(package_ids)

    @property
    def mileage(self) -> float:
        return self.miles

    def __str__(self) -> str:
        return (
            f"{self.speed},{self.miles},{self.currentLocation},"
            f"{self.time},{self.departTime},{self.packages}"
        )
    
#<><><><><><><><><>
# domain -- methods
#<><><><><><><><><>

PRIORITY_IDS = {25, 6}  # preserve special-case priority

# package delivery, nearest neighbor implementation. the moment we've all been waiting for.
def deliver_packages(truck: Truck, package_table: ChainHashTable) -> None:

    # Load package objects for this truck
    enroute: List[Package] = []
    for pid in truck.packages:
        pkg = package_table.search(pid)
        if pkg is not None:
            pkg.carrier = truck.truck_id 
            enroute.append(pkg)

    # clear the original list; order will be rebuilt
    truck.packages.clear()

    while enroute:
        next_pkg: Optional[Package] = None
        next_dist = float("inf")

        for pkg in enroute:
            # priority rule: deliver 25 or 6 as soon as encountered
            if pkg.ID in PRIORITY_IDS:
                next_pkg = pkg
                next_dist = distance_between(
                    address_index(truck.currentLocation), address_index(pkg.street)
                )
                break

            d = distance_between(
                address_index(truck.currentLocation), address_index(pkg.street)
            )
            if d <= next_dist:
                next_dist = d
                next_pkg = pkg

        # Move truck to next_pkg
        truck.packages.append(next_pkg.ID)  # record delivered order
        enroute.remove(next_pkg)
        truck.miles += next_dist
        truck.currentLocation = next_pkg.street
        travel_hours = next_dist / truck.speed
        truck.time += timedelta(hours=travel_hours)

        # set times on the package
        next_pkg.deliveryTime = truck.time
        next_pkg.departureTime = truck.departTime




#parsing funciton allows for correction of ambiguous times
def parse_time_hhmm(s: str) -> timedelta:
    s = s.strip().upper()
    fmts = ["%I:%M %p", "%I:%M%p", "%H:%M"]
    for fmt in fmts:
        try:
            t = dt.datetime.strptime(s, fmt).time()
            return timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
        except ValueError:
            continue
    raise ValueError("Invalid time. Use formats like '09:45' or '09:45 AM'.")


#print error if an incorrect pid is inputted by user. 
def print_package_status(package_table: ChainHashTable, q_time: timedelta, only_id: int | None) -> None:
    ids = [only_id] if only_id is not None else range(1, 41)
    for pid in ids:
        pkg = package_table.search(pid)
        if pkg is None:
            print(f"Package {pid} not found.")
            continue
        pkg.status_update(q_time)
        print(pkg)


#Execution in main.

'''
1: build package table our hash table using respective functions
2: instantiate three trucks with ID's 1-2, all
having a starting address at the hub and packages and departure times are assigned to them
3: Run deliveries'''

def main() -> None:
    # build packages
    package_table = ChainHashTable()
    load_package_data("packages.csv", package_table)

    # trucks (IDs 1..3 so the CLI print looks nice)
    t1 = Truck(1, 18, 0.0, "4001 South 700 East", timedelta(hours=8),
               [1, 13, 14, 15, 16, 19, 20, 27, 29, 30, 31, 34, 37, 40])
    t2 = Truck(2, 18, 0.0, "4001 South 700 East", timedelta(hours=11),
               [2, 3, 4, 5, 9, 18, 26, 28, 32, 35, 36, 38])
    t3 = Truck(3, 18, 0.0, "4001 South 700 East", timedelta(hours=9, minutes=5),
               [6, 7, 8, 10, 11, 12, 17, 21, 22, 23, 24, 25, 33, 39])

    # run deliveries
    deliver_packages(t1, package_table)
    deliver_packages(t3, package_table)
    t2.departTime = min(t1.time, t3.time)  # wait for earliest returning truck
    t2.time = t2.departTime
    deliver_packages(t2, package_table)

    # precompute totals for option [1]
    total_miles = t1.mileage + t2.mileage + t3.mileage
    extras = [t3]  # sample loop prints "Truck 3 miles: ..."

    # Intuitive
    while True:
        print("\nWGUPS Routing Program")
        print("[1] Total mileage")
        print("[2] Status of ALL packages at time")
        print("[3] Status of ONE package at time")
        print("[0] Exit")
        choice = input("Select: ").strip()

        if choice == "1":
            print(f"\nTruck 1 miles: {t1.mileage:.2f}")
            print(f"Truck 2 miles: {t2.mileage:.2f}")
            for t in extras:
                print(f"Truck {t.truck_id} miles: {t.mileage:.2f}")
            print(f"TOTAL miles:  {total_miles:.2f}")

        elif choice == "2":
            try:
                q = parse_time_hhmm(input("Enter time (e.g., 09:45 AM): "))
            except ValueError as e:
                print(e)
                continue
            print_package_status(package_table, q, None)

        elif choice == "3":
            try:
                q = parse_time_hhmm(input("Enter time (e.g., 10:30 AM): "))
            except ValueError as e:
                print(e)
                continue
            try:
                pid = int(input("Enter Package ID: ").strip())
            except ValueError:
                print("Please enter a valid integer Package ID.")
                continue
            print_package_status(package_table, q, pid)

        elif choice == "0":
            break
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)
    main()