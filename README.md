# FluorInduc

**FluorInduc** is a prototype system for measuring fluorescence induction using a Digilent Analog Discovery device. It controls LED intensities, triggers an electronic shutter, and records data via the device's oscilloscope functionality.

Variable LED intensities are used to excite a leaf placed in the sample holder, while a Hamamatsu photomultiplier tube (PMT) detects the resulting fluorescence. The system is designed to be flexible, allowing for different LED configurations and timing sequences.

The application is built using Python and Flask, leveraging the Digilent WaveForms SDK for hardware interaction. It provides a web-based GUI for real-time control and visualization of the experiment.

A variety of 3D-printed parts were created to adapt our existing parts together with a Thor Labs optical bench setup.


---

## Requirements

### ✅ Hardware
- Digilent Analog Discovery (1, 2, or 3)
- Uniblitz shutter driver (e.g., VMM-D1)
- Thor Labs LED drivers (e.g., LEDD1B or LEDD1)
- Compatible photodetector (e.g., photomultiplier tube or photodiode) with BNC output

### ✅ Software
- Python 3.10 or later
- Digilent WaveForms SDK

> **Download the WaveForms SDK**:  
> [https://digilent.com/reference/software/waveforms/waveforms-3/start](https://digilent.com/reference/software/waveforms/waveforms-3/start)

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/FluorInduc.git
   cd FluorInduc
   ```

2. **Create a virtual environment**

   It's recommended to use a virtual environment to isolate dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure WaveForms SDK is accessible**

   The application attempts to load `dwf.dll` (Windows) or `libdwf.so` (Linux/macOS).  
   Make sure the SDK is installed and accessible through your system’s library path. I'm not sure exactly how this was set up on your system, but you may need to adjust the `io_controller.py` file to point to the correct location of the WaveForms SDK library.

---

## Usage

Run the Flask app to launch the control GUI:

```bash
python app.py
```

Once running, open your browser and go to:  
[http://localhost:5000](http://localhost:5000)

You can control LED intensities, shutter timing, and data acquisition from this interface.

---

## Project Structure

```
src/
├── recorder.py           # Handles oscilloscope sampling and data recording
├── experiment_config.py  # Timing and LED sequence configuration
├── io_controller.py      # Interfaces with WaveForms API for I/O control
app.py                    # Flask app entry point
templates/                # HTML templates for the GUI
static/                   # Static assets (CSS, JS)
requirements.txt          # Python dependencies
```

---

## Notes

- The shutter is assumed to be **normally closed (N.C.)**, with the VMM-D1 configured to open it when triggered.
- Ensure the VMM-D1 is in **Remote mode** for external triggering to function.
- The system should be tested initially with low-intensity light sources to avoid damaging sensitive photodetectors.
- Keep the shutter **closed during high-intensity actinic light exposure**, and verify all components are properly shielded.
- Timing accuracy and signal quality depend on the host computer and Analog Discovery model. A controlled environment is recommended for minimizing electrical noise and ambient light interference.

---

## Pytest

From the root directory, you can run the tests using pytest:
```
pytest                 # hardware tests skipped
pytest --run-hardware  # hardware tests run
```
To run the hardware tests, ensure that the Digilent Analog Discovery is connected and recognized by the system.

I like to run it with verbose output, like so:
```
pytest -vv --run-hardware
```
## License

This project is licensed under the MIT License.  
See the [LICENSE](LICENSE) file for full details.
