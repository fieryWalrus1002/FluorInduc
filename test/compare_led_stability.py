import time
import sys, os        
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.io_controller import IOController


def calculate_mean_current(fullscale_range_value, filename="record.csv"):
    """ calculate the mean current from the CSV file and return it """
    data = pd.read_csv(filename)

    # "Value" is 0-2V, representing 0-500nA
    # Convert to {current_unit}
    # 2V = 500nA, so each step is 2V / 500nA = 4mV/{current_unit}
    data["Current"] = (
        data["Value"] * fullscale_range_value / 2
    )  # Convert to {current_unit}
    mean_current = data["Current"].mean()
    std_current = data["Current"].std()

    return round(mean_current, 2), round(std_current, 2)

if __name__ == "__main__":
    test_name = "red_led_calibration"
    channel = 0
    experiment_time = 1.0 # seconds
    hz_acq = 1000000
    n_samples = hz_acq * experiment_time
    filename = f"./output/{test_name}.csv"
    current_unit = "uA"  # or "uA", "mA", etc.
    fullscale_range_value = 50 # the full scale range value in nA/uA, whatever you want to use

    controller = IOController()

    # from 0 to 3.3V, 0.1V steps
    num_steps = 5.0 / 0.1 + 1
    voltage_ladder = [round(i * 0.1, 2) for i in range(int(num_steps))]
    values = []
    print(f"Voltage (V), Current ({current_unit})")
    print("===================================")

    for voltage in voltage_ladder:
        controller.set_act_led(voltage)

        # delete the file to save space
        if os.path.exists(filename):
            os.remove(filename)

        controller.record_and_save(channel, n_samples, hz_acq, filename)

        mean_current, std_current = calculate_mean_current(
            fullscale_range_value=fullscale_range_value, filename=filename
        )
        print(f"{voltage} V, {mean_current} {current_unit}, {std_current}")

        values.append((voltage, mean_current, std_current))

    print("===================================")
    controller.cleanup()

# create a dataframe from the values
df = pd.DataFrame(values, columns=["Voltage", "Current", "StdDev"])
df.to_csv(f"{test_name}.csv", index=False)
print(f"Data saved to {test_name}.csv")

# plot the data with error bars
plt.errorbar(
    df["Voltage"],
    df["Current"],
    yerr=df["StdDev"],
    fmt="o",
    capsize=5,
    label="Measured Current",
)
plt.xlabel("Voltage (V)")
plt.ylabel(f"Current ({current_unit})")
plt.title(f"{test_name}")
plt.legend()
plt.savefig(f"{test_name}.png", dpi=300)
plt.show()
