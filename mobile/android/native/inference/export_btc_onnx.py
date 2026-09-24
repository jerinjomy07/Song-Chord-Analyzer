"""
Export script: PyTorch BTC Checkpoint to ONNX & TorchScript for Android Mobile Inference.
Verifies numerical equivalence between PyTorch, TorchScript, and ONNX Runtime Mobile.
"""

from pathlib import Path
import sys
import os

import torch
import numpy as np

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from models.btc.btc_model import BTC_model


class MobileBTCWrapper(torch.nn.Module):
    """
    Lightweight inference wrapper eliminating training dependencies and loss computations.
    Directly maps (batch, 100, 144) CQT spectrogram frames to (batch, 100, 170) logits.
    """

    def __init__(self, btc_model: torch.nn.Module):
        super().__init__()
        self.btc = btc_model

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        batch_size = features.shape[0]
        # Pass dummy labels since probs_out=True bypasses loss calculation
        dummy_labels = torch.zeros(batch_size, 100, dtype=torch.long, device=features.device)
        return self.btc(features, dummy_labels)


def export_models(checkpoint_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = output_dir / "btc_model_170voca.onnx"
    torchscript_path = output_dir / "btc_model_170voca.ptl"

    print(f"Loading BTC checkpoint: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

    config = {
        'feature_size': 144,
        'timestep': 100,
        'num_chords': 170,
        'input_dropout': 0.0,
        'layer_dropout': 0.0,
        'attention_dropout': 0.0,
        'relu_dropout': 0.0,
        'num_layers': 8,
        'num_heads': 4,
        'hidden_size': 128,
        'total_key_depth': 128,
        'total_value_depth': 128,
        'filter_size': 128,
        'loss': 'ce',
        'probs_out': True
    }

    base_model = BTC_model(config)
    base_model.load_state_dict(checkpoint['model'])
    base_model.eval()

    model = MobileBTCWrapper(base_model)
    model.eval()

    dummy_input = torch.randn(1, 100, 144, dtype=torch.float32)

    # 1. Export ONNX
    print("Exporting ONNX model...")
    torch.onnx.export(
        model,
        dummy_input,
        str(onnx_path),
        input_names=["cqt_features"],
        output_names=["chord_logits"],
        dynamic_axes={
            "cqt_features": {0: "batch_size"},
            "chord_logits": {0: "batch_size"}
        },
        opset_version=14,
        do_constant_folding=True
    )
    onnx_size_mb = os.path.getsize(onnx_path) / (1024 * 1024)
    print(f"ONNX Model exported: {onnx_path} ({onnx_size_mb:.2f} MB)")

    # 2. Export TorchScript / PyTorch Mobile
    print("Exporting TorchScript mobile model...")
    traced = torch.jit.trace(model, dummy_input)
    traced.save(str(torchscript_path))
    ts_size_mb = os.path.getsize(torchscript_path) / (1024 * 1024)
    print(f"TorchScript Model exported: {torchscript_path} ({ts_size_mb:.2f} MB)")

    # 3. Numerical Verification with ONNX Runtime
    import onnxruntime as ort
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    ort_out = session.run(["chord_logits"], {"cqt_features": dummy_input.numpy()})[0]

    with torch.no_grad():
        pt_out = model(dummy_input).numpy()

    max_diff = np.max(np.abs(pt_out - ort_out))
    print(f"Verification: Max absolute difference between PyTorch and ONNX = {max_diff:.6e}")
    assert max_diff < 1e-4, "Export verification failed! High numerical divergence detected."
    print("SUCCESS: Both models successfully generated and numerically verified.")


if __name__ == "__main__":
    ckpt = ROOT / "models" / "btc" / "btc_model_large_voca.pt"
    out = ROOT / "mobile" / "android" / "native" / "inference"
    export_models(ckpt, out)
