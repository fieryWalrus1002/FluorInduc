import pandas as pd
import numpy as np
from scipy import stats

Z = 1.96  # for 95% confidence
TOLERANCES = {
    "ared_duration": 0.01,
    "gap_ared_agreen": 0.001,
    "shutter_open": 0.001,
}
EXPECTED = {
    "ared_duration": 1.000,
    "gap_ared_agreen": 0.006,
    "shutter_open": 0.00075,
}


def generate_latex_table(csv_path):
    df = pd.read_csv(csv_path, index_col=0)
    output = []
    output.append(r"\begin{longtable}{@{}lllll@{}}")
    output.append(r"\toprule")
    output.append(
        r"\textbf{Interval} & \textbf{Expected (s)} & \textbf{Mean (s)} & \textbf{95\% CI (s)} & \textbf{Pass/Fail} \\"
    )
    output.append(r"\midrule")

    for name, row in df.iterrows():
        durations = row.values.astype(float)
        mean = np.mean(durations)
        std = np.std(durations, ddof=1)
        ci_range = stats.t.interval(
            0.95, len(durations) - 1, loc=mean, scale=stats.sem(durations)
        )
        expected = EXPECTED.get(name, 0.0)
        tolerance = TOLERANCES.get(name, 0.001)
        fail = abs(mean - expected) > tolerance
        verdict = r"\textbf{Fail}" if fail else "Pass"

        output.append(
            f"{name} & {expected:.6f} & {mean:.6f} & "
            f"[{ci_range[0]:.6f}, {ci_range[1]:.6f}] & {verdict} \\\\"
        )

    output.append(r"\bottomrule")
    output.append(r"\end{longtable}")

    return "\n".join(output)

if __name__ == "__main__":
    latex_table_code = generate_latex_table(
        "test_results/interval_durations_2025-06-23-10-30.csv"
    )

    with open("autogen_timing_table.tex", "w") as f:
        f.write(latex_table_code)

# in the tex doc you would use: \input{autogen_timing_table.tex}
