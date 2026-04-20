import time

print("============================================================\n===================Trafic Signal System=====================\n============================================================")
class TrafficSignal:
    def __init__(self):
        self.roads = ["North", "South", "East", "West"]
        self.time_per_vehicle = 2  # Seconds allocated per vehicle
        self.min_green = 5          # Minimum green light duration
        self.max_green = 60         # Maximum green light duration

    def simulate_traffic(self, vehicle_counts):
        print(f"Current Vehicle Density: {dict(zip(self.roads, vehicle_counts))}\n")

        for i, count in enumerate(vehicle_counts):
            road_name = self.roads[i]

            # Condition 3: Check if road is empty to avoid unnecessary waiting
            if count == 0:
                print(f"🚦 Road {road_name}: No vehicles. Skipping to next road.")
                continue

            # Calculate Green light duration based on density
            green_duration = min(max(count * self.time_per_vehicle, self.min_green), self.max_green)

            self.change_light(road_name, green_duration, count)

    def change_light(self, road, duration, vehicles):
        print(f"🟢 GREEN Light: {road} Road ({vehicles} vehicles detected)")
        
        # Simulating the countdown
        for remaining in range(duration, 0, -1):
            print(f"   Time remaining: {remaining}s", end="\r")
            time.sleep(1)
        
        print(f"\n🟡 YELLOW Light: {road} Road (Clearing intersection...)")
        time.sleep(2)
        print(f"🔴 RED Light: {road} Road\n")

# --- Execution ---
if __name__ == "__main__":
    # Condition 2: Variable quantities of vehicles
    # North=15, South=3, East=0 (Empty), West=25
    current_density = [int(input("Enter Current Density in North Road:")), int(input("Enter Current Density in South Road:")), int(input("Enter Current Density in East Road:")), int(input("Enter Current Density in West Road:"))]
    
    signal_system = TrafficSignal()
    signal_system.simulate_traffic(current_density)
