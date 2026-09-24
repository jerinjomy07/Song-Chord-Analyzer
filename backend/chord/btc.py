"""
BTC (Bi-directional Transformer for Chord Recognition) Recognizer.
Uses 170-chord vocabulary trained checkpoint to predict chords, probabilities, and alternative candidates.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
import librosa
import soundfile as sf

from backend.config import (
    BTC_CHECKPOINT_PATH,
    CUDA_AVAILABLE,
    CQT_N_BINS,
    CQT_BINS_PER_OCTAVE,
    CQT_HOP_LENGTH,
    BTC_TIMESTEP,
    TARGET_SAMPLE_RATE,
)
from backend.models.schemas import ChordPrediction, ChordCandidate
from backend.chord.base import ChordRecognizer
from backend.chord.vocabulary import get_btc_index_map, parse_chord_string


class BTCRecognizer(ChordRecognizer):
    def __init__(self, checkpoint_path: Path = BTC_CHECKPOINT_PATH, device: Optional[str] = None):
        self.checkpoint_path = checkpoint_path
        self.device = device or ("cuda" if CUDA_AVAILABLE else "cpu")
        self.idx_to_chord = get_btc_index_map()
        self.model = None
        self.mean = 0.0
        self.std = 1.0
        self._load_model()

    def _load_model(self):
        """Loads BTC model architecture and weights."""
        from models.btc.btc_model import BTC_model

        if not self.checkpoint_path.exists():
            raise FileNotFoundError(f"BTC Checkpoint not found at {self.checkpoint_path}")

        checkpoint = torch.load(self.checkpoint_path, map_location=self.device, weights_only=False)
        self.mean = checkpoint['mean']
        self.std = checkpoint['std']

        config = {
            'feature_size': CQT_N_BINS,
            'timestep': BTC_TIMESTEP,
            'num_chords': 170,
            'input_dropout': 0.2,
            'layer_dropout': 0.2,
            'attention_dropout': 0.2,
            'relu_dropout': 0.2,
            'num_layers': 8,
            'num_heads': 4,
            'hidden_size': 128,
            'total_key_depth': 128,
            'total_value_depth': 128,
            'filter_size': 128,
            'loss': 'ce',
            'probs_out': True  # Output raw logits for exact probabilities
        }

        self.model = BTC_model(config).to(self.device)
        self.model.load_state_dict(checkpoint['model'])
        self.model.eval()

        # Build reverse lookup for chord to index
        self.chord_to_idx = {v: k for k, v in self.idx_to_chord.items()}

    def predict_probabilities(self, audio_path: Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes CQT and predicts full posterior probability matrix across all 170 chords.
        Returns:
            (probabilities [num_frames, 170], frame_times [num_frames])
        """
        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        if sr != TARGET_SAMPLE_RATE:
            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)
            sr = TARGET_SAMPLE_RATE

        cqt = librosa.cqt(
            y,
            sr=sr,
            n_bins=CQT_N_BINS,
            bins_per_octave=CQT_BINS_PER_OCTAVE,
            hop_length=CQT_HOP_LENGTH
        )
        features = np.log(np.abs(cqt) + 1e-6).T
        features = (features - self.mean) / self.std

        time_unit = 10.0 / float(BTC_TIMESTEP)
        num_frames = features.shape[0]

        n_timestep = BTC_TIMESTEP
        num_pad = n_timestep - (num_frames % n_timestep)
        if num_pad < n_timestep:
            features_padded = np.pad(features, ((0, num_pad), (0, 0)), mode="constant", constant_values=0)
        else:
            features_padded = features

        num_instances = features_padded.shape[0] // n_timestep
        all_probs = []

        with torch.no_grad():
            inp_tensor = torch.tensor(features_padded, dtype=torch.float32).unsqueeze(0).to(self.device)
            for t in range(num_instances):
                chunk = inp_tensor[:, n_timestep * t : n_timestep * (t + 1), :]
                attn_out, _ = self.model.self_attn_layers(chunk)
                logits = self.model.output_layer(attn_out)
                probs = torch.softmax(logits.squeeze(0), dim=-1).cpu().numpy()
                all_probs.append(probs)

        probs_matrix = np.concatenate(all_probs, axis=0)[:num_frames]
        frame_times = np.arange(num_frames) * time_unit
        return probs_matrix, frame_times

    def decode_prob_vector(
        self,
        p_vector: np.ndarray,
        is_flat: bool = False
    ) -> Tuple[str, str, float, List[ChordCandidate], str]:
        """
        Decodes a probability vector with simplicity regularization:
        Prefers the base triad unless the extended chord (7, maj7, min7) has decisive evidence.
        Returns:
            (root, quality, confidence, alternatives, display)
        """
        top_idx = int(np.argmax(p_vector))
        top_chord = self.idx_to_chord.get(top_idx, 'N')
        top_prob = float(p_vector[top_idx])

        if top_chord == 'N' or top_chord == 'X':
            return ('N', 'none', top_prob, [], 'N')

        root, qual, _, _, _ = parse_chord_string(top_chord)

        # Build candidate alternatives list
        sorted_indices = np.argsort(p_vector)[::-1][:4]
        alts = []
        for a_idx in sorted_indices:
            if a_idx != top_idx and p_vector[a_idx] > 0.08:
                a_str = self.idx_to_chord.get(int(a_idx), 'N')
                _, _, _, _, a_disp = parse_chord_string(a_str)
                alts.append(ChordCandidate(chord=a_disp, probability=round(float(p_vector[a_idx]), 2)))

        # REQUIREMENT 4 & 5: Simplicity Regularization
        # If the winning chord is an extension, compare with its base triad:
        final_qual = qual
        final_prob = top_prob

        if qual in ['7', 'maj7', 'min7', 'maj6', 'min6', 'dim7', 'hdim7']:
            base_qual = 'min' if qual in ['min7', 'min6', 'hdim7'] else ('dim' if qual == 'dim7' else 'maj')
            base_str = root if base_qual == 'maj' else f"{root}:{base_qual}"
            base_idx = self.chord_to_idx.get(base_str)

            if base_idx is not None:
                base_prob = float(p_vector[base_idx])
                # Only keep extension if it has strong confidence (>= 0.60), significantly beats triad (> 1.35x),
                # and margin is not razor-thin (>= 0.15)
                keep_extension = (top_prob >= 0.60) and (top_prob > base_prob * 1.35) and (top_prob - base_prob >= 0.15)

                if not keep_extension:
                    # Simplify to base triad
                    final_qual = base_qual
                    final_prob = min(0.99, round(top_prob + base_prob, 2))
                    # Record the extension as top alternative
                    _, _, _, _, ext_disp = parse_chord_string(top_chord)
                    alts.insert(0, ChordCandidate(chord=ext_disp, probability=round(top_prob, 2)))

        from backend.chord.vocabulary import format_chord_display
        display = format_chord_display(root, final_qual, root, is_flat=is_flat)
        return (root, final_qual, final_prob, alts[:3], display)

    def predict_features(self, features: np.ndarray) -> List[ChordPrediction]:
        """Inference on precomputed normalized CQT features."""
        time_unit = 10.0 / float(BTC_TIMESTEP)
        num_frames = features.shape[0]
        n_timestep = BTC_TIMESTEP
        num_pad = n_timestep - (num_frames % n_timestep)
        if num_pad < n_timestep:
            features_padded = np.pad(features, ((0, num_pad), (0, 0)), mode="constant", constant_values=0)
        else:
            features_padded = features

        num_instances = features_padded.shape[0] // n_timestep
        all_probs = []

        with torch.no_grad():
            inp_tensor = torch.tensor(features_padded, dtype=torch.float32).unsqueeze(0).to(self.device)
            for t in range(num_instances):
                chunk = inp_tensor[:, n_timestep * t : n_timestep * (t + 1), :]
                attn_out, _ = self.model.self_attn_layers(chunk)
                logits = self.model.output_layer(attn_out)
                probs = torch.softmax(logits.squeeze(0), dim=-1).cpu().numpy()
                all_probs.append(probs)

        probs = np.concatenate(all_probs, axis=0)[:num_frames]
        frame_predictions = []
        for i in range(len(probs)):
            root, qual, conf, alts, display = self.decode_prob_vector(probs[i])
            frame_predictions.append({
                "frame": i,
                "time": i * time_unit,
                "chord": display,
                "root": root,
                "quality": qual,
                "confidence": conf,
                "alternatives": alts
            })
        return self._collapse_frames_to_segments(frame_predictions, time_unit)

    def analyze(self, audio_path: Path, is_flat: bool = False, **kwargs) -> List[ChordPrediction]:
        """Runs end-to-end CQT feature extraction and BTC inference on an audio file."""
        probs, frame_times = self.predict_probabilities(audio_path)
        time_unit = 10.0 / float(BTC_TIMESTEP)

        frame_predictions: List[Dict[str, Any]] = []
        for i in range(len(probs)):
            root, qual, conf, alts, display = self.decode_prob_vector(probs[i], is_flat=is_flat)
            frame_predictions.append({
                "frame": i,
                "time": frame_times[i],
                "chord": display,
                "root": root,
                "quality": qual,
                "confidence": conf,
                "alternatives": alts
            })

        return self._collapse_frames_to_segments(frame_predictions, time_unit)

    def _collapse_frames_to_segments(self, frames: List[Dict[str, Any]], time_unit: float) -> List[ChordPrediction]:
        """Merges contiguous identical frame predictions into ChordPrediction objects."""
        if not frames:
            return []

        segments: List[ChordPrediction] = []
        curr_chord = frames[0]["chord"]
        curr_start = frames[0]["time"]
        curr_confs = [frames[0]["confidence"]]
        curr_alts = frames[0]["alternatives"]

        for f in frames[1:]:
            if f["chord"] == curr_chord:
                curr_confs.append(f["confidence"])
            else:
                end_time = f["time"]
                dur = end_time - curr_start
                avg_conf = float(np.mean(curr_confs))
                root, qual, bass, inv, display = parse_chord_string(curr_chord)

                segments.append(ChordPrediction(
                    root=root,
                    quality=qual,
                    bass=bass,
                    inversion=inv,
                    display=display,
                    start_time=round(curr_start, 3),
                    end_time=round(end_time, 3),
                    duration=round(dur, 3),
                    confidence=round(avg_conf, 2),
                    needs_review=(avg_conf < 0.65 and display != 'N'),
                    alternatives=curr_alts
                ))

                curr_chord = f["chord"]
                curr_start = f["time"]
                curr_confs = [f["confidence"]]
                curr_alts = f["alternatives"]

        # Final segment
        end_time = frames[-1]["time"] + time_unit
        dur = end_time - curr_start
        avg_conf = float(np.mean(curr_confs))
        root, qual, bass, inv, display = parse_chord_string(curr_chord)
        segments.append(ChordPrediction(
            root=root,
            quality=qual,
            bass=bass,
            inversion=inv,
            display=display,
            start_time=round(curr_start, 3),
            end_time=round(end_time, 3),
            duration=round(dur, 3),
            confidence=round(avg_conf, 2),
            needs_review=(avg_conf < 0.65 and display != 'N'),
            alternatives=curr_alts
        ))

        return segments

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "BTCRecognizer",
            "type": "Bi-directional Transformer",
            "vocabulary_size": 170,
            "license": "MIT",
            "device": self.device
        }
