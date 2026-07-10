"""
Trace the trained MotorFaultCNN, compile it for a Qualcomm device via
Qualcomm AI Hub, profile it, and validate its predictions against the
real labeled current-sensor data already in this repo.

This does NOT require the physical edge hardware to be in hand -- compile
and profile jobs run on Qualcomm's cloud device farm. Only a final
"run it bare-metal and confirm it still works" step needs the actual board.

Before running this, confirm two things with the team:
  1. Which checkpoint is current: models/motor_model.pth or
     models/motor_model_scratch.pth.
  2. The exact device name to target. Run this to list options and pick
     the one matching the hackathon-provided board:
       python -c "import qai_hub as hub; [print(d.name) for d in hub.get_devices()]"

Usage:
    python deploy_to_qai_hub.py --model ../models/motor_model.pth --device "<exact device name>"

Note: this has not been run end-to-end against a live Qualcomm AI Hub
account (no API token available in this environment), so double-check
the submit_inference_job/download_output_data call shapes against your
installed qai-hub version if they error.
"""
import argparse

import numpy as np
import pandas as pd
import qai_hub as hub
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

WINDOW_SIZE = 128


class MotorFaultCNN(nn.Module):
    """Must match the architecture in VigilantCascade.ipynb exactly --
    the .pth file only stores learned weights, not this class definition."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv1d(1, 32, kernel_size=5)
        self.bn1 = nn.BatchNorm1d(32)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(2)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3)
        self.bn2 = nn.BatchNorm1d(64)
        self.fc = nn.Linear(64 * 30, 2)

    def forward(self, x):
        x = self.pool(self.relu(self.bn1(self.conv1(x))))
        x = self.pool(self.relu(self.bn2(self.conv2(x))))
        x = x.view(x.size(0), -1)
        return self.fc(x)


def fit_shared_scaler(*csv_paths):
    """Fit one MinMaxScaler across all classes' data. A scaler fit
    per-file instead would hide the same scale-leakage issue raised in
    PR #1's training-notebook fix."""
    raw = np.vstack(
        [
            pd.read_csv(p, header=None, names=["raw", "baseline", "delta", "current"])[
                "current"
            ].values.reshape(-1, 1)
            for p in csv_paths
        ]
    )
    scaler = MinMaxScaler()
    scaler.fit(raw)
    return scaler


def load_windows(csv_path, scaler, window_size=WINDOW_SIZE):
    df = pd.read_csv(csv_path, header=None, names=["raw", "baseline", "delta", "current"])
    data = scaler.transform(df["current"].values.reshape(-1, 1))
    return np.array(
        [data[i : i + window_size].T for i in range(len(data) - window_size)],
        dtype=np.float32,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to the .pth checkpoint to deploy")
    parser.add_argument("--device", required=True, help="Exact qai_hub device name to target")
    parser.add_argument("--normal-csv", default="../data/normal2.csv")
    parser.add_argument("--slowed-csv", default="../data/slowed2.csv")
    parser.add_argument(
        "--num-samples", type=int, default=5, help="Validation windows to pull per class"
    )
    args = parser.parse_args()

    # 1. Load trained weights
    model = MotorFaultCNN()
    model.load_state_dict(torch.load(args.model, map_location="cpu"))
    model.eval()

    # 2. Trace to TorchScript (window of 128 samples, 1 channel)
    example_input = torch.randn(1, 1, WINDOW_SIZE)
    traced_model = torch.jit.trace(model, example_input)

    # 3. Compile for the target device
    device = hub.Device(args.device)
    print(f"Submitting compile job for device: {args.device}")
    compile_job = hub.submit_compile_job(
        model=traced_model,
        device=device,
        input_specs={"x": (1, 1, WINDOW_SIZE)},
    )
    target_model = compile_job.get_target_model()

    # 4. Profile on-device (latency/memory, runs on Qualcomm's cloud device farm)
    print("Submitting profile job...")
    hub.submit_profile_job(model=target_model, device=device)

    # 5. Validate against the real labeled data already in this repo
    scaler = fit_shared_scaler(args.normal_csv, args.slowed_csv)
    normal_windows = load_windows(args.normal_csv, scaler)
    slowed_windows = load_windows(args.slowed_csv, scaler)

    n = args.num_samples
    sample_inputs = np.concatenate([normal_windows[:n], slowed_windows[:n]])
    expected_labels = [0] * min(n, len(normal_windows)) + [1] * min(n, len(slowed_windows))

    print(f"Submitting inference job with {len(sample_inputs)} validation windows...")
    inference_job = hub.submit_inference_job(
        model=target_model,
        device=device,
        inputs={"x": [sample_inputs]},
    )
    outputs = inference_job.download_output_data()

    print("Expected labels (0=normal, 1=slowed):", expected_labels)
    print("Raw model outputs:", outputs)


if __name__ == "__main__":
    main()
