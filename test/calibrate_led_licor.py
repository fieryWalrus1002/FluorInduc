import time
import sys, os        
import pandas as pd
import matplotlib.pyplot as plt
import random 

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.io_controller import IOController

if __name__ == "__main__":
    test_name = "licor_red_led_calibration_random"
    channel = 0
    n_samples = 1000000
    hz_acq = 1000000
    filename = f"./{test_name}.csv"
    # current_unit = "uA"  # or "uA", "mA", etc.
    current_unit = "uE"

    controller = IOController()

    # from 0 to 3.3V, 0.1V steps
    max_voltage = 5.04
    step_value = 0.25
    num_steps = max_voltage / step_value + 1
    voltage_ladder = [round(i * step_value, 2) for i in range(int(num_steps))]
    values = []
    print(f"Voltage (V), Light Intensity ({current_unit})")
    print("===================================")

    # randomize the order of the voltages
    random.shuffle(voltage_ladder)

    for voltage in voltage_ladder:
               
        if voltage < 0.9:
            values.append((voltage, 0, 0)) # it doesn't turn on until 1.0V        
            print(f"{voltage} V, 0 {current_unit}, 0")
            continue

        controller.set_act_led(voltage)
        time.sleep(1)

        # get human console input from the manual measurement
        mean_current = float(input("Enter reading: "))
        print(f"{voltage} V, {mean_current} {current_unit}, {0}")

        values.append((voltage, mean_current, 0))

    print("===================================")
    controller.cleanup()


# create a dataframe from the values
# df = pd.DataFrame(values, columns=["Voltage", "uE", "std"])
# df.to_csv(f"{test_name}.csv", index=False)

df = pd.read_csv(f"./{test_name}.csv")

# sort the dataframe by voltage
df = df.sort_values(by="Voltage")
df = df.reset_index(drop=True)
df["uE"] = df["uE"].astype(float)  # Convert to float if necessary
print(df.head())

print(f"Data saved to {test_name}.csv")
plt.plot(df["Voltage"], df["uE"], label="Light Intensity", marker="o")
plt.xlabel("Voltage (V)")
plt.ylabel(f"Light Intenisty ({current_unit})")
plt.title(f"{test_name}")
plt.legend()
plt.savefig(f"{test_name}.png", dpi=300)
plt.show()
