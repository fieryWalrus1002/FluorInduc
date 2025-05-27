import time
import sys, os        
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.io_controller import IOController
import random

def convert_voltage_to_current(voltage, fullscale_range_value):
    """ Convert voltage to current using the full scale range value """
    # "signal" is 0-2V, representing 0-500nA
    # Convert to {current_unit}
    # 2V = 500nA, so each step is 2V / 500nA = 4mV/{current_unit}
    return voltage * fullscale_range_value / 2


def create_voltage_ladder(start, end, step):
    """ Create a voltage ladder from start to end with the given step """
    num_steps = (end - start) / step + 1
    voltage_ladder = [round(i * step + start, 2) for i in range(int(num_steps))]

    # randomize the order of the voltages
    random.shuffle(voltage_ladder)

    return voltage_ladder

if __name__ == "__main__":
    test_name = "green"
    
    channel = 0
    time_exp = 10.0 # seconds
    hz_acq = 1000
    n_samples = int(hz_acq * time_exp)
    export_filename = f"./output/{test_name}.csv"
    
    print(f"Number of samples: {n_samples}")

    # PM100D full scale range value in nA/uA, whatever you want to use
    fullscale_range_value = 50
    current_unit = "uA"

    voltage_ladder = create_voltage_ladder(start=1.0, end=3.3, step=0.1)

    # delete the file to save space
    if os.path.exists(export_filename) == False:
        dfs = {}

        controller = IOController()

        for voltage in voltage_ladder:
            filename = f"./output/{test_name}_{time_exp}_{voltage}.csv"

            # turn on the LED
            controller.set_act_led(voltage)
            print(f"LED set to {voltage} V")

            # start the recording. It will wait 2s for the LED to stabilize
            controller.record_and_save(channel, n_samples, hz_acq, filename)

            controller.set_act_led(0.0)
            print(f"LED set to 0 V, wainting {time_exp} seconds")
            time.sleep(time_exp)

            # process the data
            data = pd.read_csv(filename)
            data[f"Current_{current_unit}"] = convert_voltage_to_current(data["signal"], fullscale_range_value)
            data["deltaCurrent"] = data[f"Current_{current_unit}"] / data[f"Current_{current_unit}"][0:1000].mean()
            
            # data["deltaCurrent"] = data[f"Current_{current_unit}"].diff().fillna(0)

            # add to the dictionary
            dfs[voltage] = data

        print("===================================")
        print(f"LED set to 0 V")
        # after the last measurement, turn off the LED
        controller.cleanup()
        
        # now we can create a single dataframe with all the data
        df = pd.DataFrame()
        for voltage, data in dfs.items():
            # add the voltage column to the dataframe
            data["Voltage"] = voltage
            df = pd.concat([df, data], ignore_index=True)

        df = df.sort_values(by="Voltage")
        df = df.reset_index(drop=True)
        df.to_csv(export_filename, index=False)
        print(f"Data saved to {export_filename}")



    df = pd.read_csv(export_filename)
    print(f"Data loaded from {export_filename}")
    
    # plot the time vs Current (uA) for each voltage
    plt.figure(figsize=(10, 6))
    for voltage in voltage_ladder:
        plt.plot(
            df[df["Voltage"] == voltage]["time"],
            df[df["Voltage"] == voltage][f"Current_{current_unit}"],
            label=f"{voltage} V",
        )
    plt.xlabel("time")
    plt.ylabel(f"Current ({current_unit})")
    plt.title("Current vs Time for different voltages")
    plt.legend()
    plt.grid()  

    plt.savefig(f"./output/{test_name}_current_vs_time.png")
    print(f"Current vs Time plot saved to {test_name}_current_vs_time.png")
    plt.close()

    # now do the same, but for delta current
    plt.figure(figsize=(10, 6))
    for voltage in voltage_ladder:
        plt.plot(
            df[df["Voltage"] == voltage]["time"],
            df[df["Voltage"] == voltage]["deltaCurrent"],
            label=f"{voltage} V",
        )
    plt.xlabel("time")
    plt.ylabel(f"Delta Current ({current_unit})")
    plt.title("Delta Current vs Time for different voltages")
    plt.legend()
    plt.grid()
    plt.savefig(f"./output/{test_name}_delta_current_vs_time.png")
    plt.close()
    print(f"Delta Current vs Time plot saved to {test_name}_delta_current_vs_time.png")
