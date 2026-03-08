import asyncio
from bleak import BleakClient, BleakScanner

# The UUID for the Heart Rate Measurement Characteristic
HR_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
# FC:39:32:35:50:97                        | Domyos-Bike-0191
ADDRESS = "FC:39:32:35:50:97"
BIKE_SERVICE_UUID = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
DATA_CHAR_UUID = "49535343-1e4d-4bd9-ba61-23c647249616"

def hr_notification_handler(sender, data):
    """
    Data format for Heart Rate Measurement is defined by Bluetooth SIG.
    The first byte is flags; the second byte is usually the HR value.
    """
    # Simple parsing: the second byte is the beats per minute (BPM)
    bpm = data[1]
    print(f"Heart Rate: {bpm} BPM")


async def main():
    print("Scanning for Polar H10...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and "Polar H10" in d.name
    )

    if not device:
        print("Polar H10 not found. Make sure it's nearby and on your chest.")
        return

    print(f"Found {device.name} [{device.address}]. Connecting...")

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")

        # Start receiving notifications from the HR characteristic
        await client.start_notify(HR_CHARACTERISTIC_UUID, hr_notification_handler)

        print("Reading data... Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)


async def run_scanner():
    print("Scanning for devices... (this takes 5 seconds)")
    devices = await BleakScanner.discover()

    print(f"\nFound {len(devices)} devices:\n")
    print(f"{'Address/ID':<40} | {'Name'}")
    print("-" * 60)

    for d in devices:
        # Some devices don't broadcast a name, we'll show 'Unknown' for those
        name = d.name if d.name else "Unknown/Hidden"
        print(f"{d.address:<40} | {name}")


async def explore_bike():
    print(f"Connecting to Domyos Bike at {ADDRESS}...")

    async with BleakClient(ADDRESS) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return

        print(f"Connected! Exploring services...\n")
        services = client.services

        for service in services:
            print(f"--- Service: {service.description} ({service.uuid}) ---")

            for char in service.characteristics:
                # Determine what we can do with this characteristic
                props = ", ".join(char.properties)
                print(f"  > Characteristic: {char.description} ({char.uuid})")
                print(f"    Properties: {props}")

                # If it's readable, try to fetch the current value
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    Current Value: {value.hex(':')}")
                    except Exception as e:
                        print(f"    Could not read: {e}")
            print("\n")


def handle_data(sender, data):
    if len(data) < 25:
        return

        # Mapping based on your console image vs hex dump
    distance_km = data[11] / 10.0  # 0x03 -> 0.3 km
    calories = data[15]  # 0x06 -> 6 Kcal

    # Time is stored in seconds at Byte 20
    total_seconds = data[20]
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    # Resistance Level
    level = data[24]

    # RPM and Heart Rate (usually found in Bytes 17-19)
    rpm = data[19]
    heart_rate = data[17]

    # Clear screen and print formatted info
    print("\033[H\033[J", end="")  # Clears the terminal for a "Live Dashboard" feel
    print(f"--- DOMYOS C3.2 DASHBOARD ---")
    print(f"Time:       {minutes:02d}:{seconds:02d}")
    print(f"Distance:   {distance_km:.1f} km")
    print(f"Calories:   {calories} kcal")
    print(f"RPM:        {rpm}")
    print(f"Heart Rate: {heart_rate} bpm")
    print(f"Level:      {level:02d}")
    print(f"-----------------------------")


async def main_bike():
    print(f"Connecting to {ADDRESS}...")
    async with BleakClient(ADDRESS) as client:
        print("Connected! Subscribing to data stream...")

        # Start notifications
        await client.start_notify(DATA_CHAR_UUID, handle_data)

        print("Pedal the bike to see data. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)





try:
    # asyncio.run(main())
    # asyncio.run(run_scanner())
    asyncio.run(main_bike())
except KeyboardInterrupt:
    print("\nDisconnected.")