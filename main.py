import time
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.io_controller import IOController

def test_record(channel, n_samples = 1000000, hz_acq = 1000000, filename="record.csv"):
    """
    Test the recording functionality of the device.
    """
    controller = IOController()
    # Start recording
    try:
        controller.record_and_save(channel, n_samples, hz_acq, filename)

    # Cleanup after recording
    finally:
        controller.cleanup()

def test_io():
    """
    Test the analog I/O functionality of the device.
    """
    controller = IOController()

    # shutter should be closed to begin with
    controller.toggle_shutter(False)

    # turn on the ML while it is closed
    controller.toggle_measure_led(True)
    controller.set_act_led(3.3)

    time.sleep(1)

    # open the shutter
    controller.toggle_shutter(True)
    time.sleep(1)

    # now close the shutter
    controller.toggle_shutter(False)
    time.sleep(1)

    # turn off the measureing LED
    # controller.toggle_measure_led(False)
    controller.set_act_led(0)

    controller.cleanup()


def plot_data(filename="record.csv", output_img_filename="record.png"):
    """
    Plot the data from the CSV file.
    """
    import pandas as pd
    import matplotlib.pyplot as plt

    # Read the CSV file
    data = pd.read_csv(filename)

    # "Value" is 0-2V, representing 0-500nA
    # Convert to nA
    # 2V = 500nA, so each step is 2V / 500nA = 4mV/nA

    data["nA"] = data["Value"] * 500 / 2  # Convert to nA

    # Plot the data Time (s),Sample Value
    plt.plot(data["Time (s)"], data["nA"])

    mean_val = data["nA"].mean()
    std_val = data["nA"].std()
    print(f"Mean value: {mean_val} nA")
    print(f"Standard deviation: {std_val} nA")
    print(f"Max value: {data['nA'].max()} nA")
    print(f"Min value: {data['nA'].min()} nA")

    # y axis in mV, from 0 to 2V
    plt.ylim(0, 500)
    plt.xlabel("Time (s)")
    plt.ylabel("value")
    plt.title("Analog Input Data")
    plt.grid()
    plt.savefig(f"val_{round(mean_val, 0)}_{output_img_filename}", dpi=300)
    plt.show()

if __name__ == "__main__":
    test_name = "pm100d_46"
    test_record(channel=0, n_samples=100000, hz_acq=100000, filename=f"{test_name}.csv")
    plot_data(f"{test_name}.csv", output_img_filename=f"{test_name}.png")

    # voltage = 2 / full_scale_range_value * value  # Convert to voltage
    

    
    
    # max V is 2V, and the full scale range value is 500nA
    # So each step is 2V / 500nA = 4mV/nA
    # print(f"Voltage: {voltage} V")
