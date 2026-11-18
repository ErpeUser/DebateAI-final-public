"""Download ONNX models for speaker diarization (Silero VAD + WeSpeaker ResNet152-LM).

Default run fetches only what the app needs at runtime. Pass --optional to also
fetch the evaluation-only models used by scripts/diarizer_ab.py.
"""

import argparse
import hashlib
import os
from pathlib import Path
import urllib.request

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

MODEL_SPECS = {
    "silero_vad.onnx": {
        "url": "https://github.com/snakers4/silero-vad/raw/5cd7945676eb32225748052e2e6a0580e4686a08/src/silero_vad/data/silero_vad.onnx",
        "revision": "5cd7945676eb32225748052e2e6a0580e4686a08",
        "sha256": "1a153a22f4509e292a94e67d6f9b85e8deb25b4988682b7e174c65279d8788e3",
        "license": "MIT",
        "size_bytes": 2327524,
    },
    # WeSpeaker ResNet152-LM speaker embedding (VoxCeleb, EER 0.495% vox1-O).
    # Replaces the legacy ecapa_tdnn.onnx file, which actually contained
    # WeSpeaker ResNet34-LM (EER 0.723%) under a misleading name.
    "voxceleb_resnet152_LM.onnx": {
        "url": "https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet152-LM/resolve/4adba1525a6c9d5fff74b6df43a6ec97a86c4112/voxceleb_resnet152_LM.onnx",
        "revision": "4adba1525a6c9d5fff74b6df43a6ec97a86c4112",
        "sha256": "5b734353b4b410e222bbd124dd095537642237ad895727d18a3b9fee330262a8",
        "license": "Apache-2.0",
        "size_bytes": 79158228,
    },
}

# Keep the old URL mapping available to callers that only display sources.
MODELS = {filename: model["url"] for filename, model in MODEL_SPECS.items()}

# Opt-in downloads. Not fetched by a normal install; nothing at runtime reads
# them. scripts/diarizer_ab.py uses these to A/B embedding models offline.
OPTIONAL_MODEL_SPECS = {
    # WeSpeaker ResNet34-LM (VoxCeleb, EER 0.723% vox1-O), ~25 MB against the
    # ResNet152-LM's ~75 MB. This is the same architecture the legacy
    # ecapa_tdnn.onnx file held, published here under its true name.
    "voxceleb_resnet34_LM.onnx": {
        "url": "https://huggingface.co/openspeech/wespeaker-models/resolve/ee89d24b81a8b2940305c258b8829ea9b0a4679f/voxceleb_resnet34_LM.onnx",
        "revision": "ee89d24b81a8b2940305c258b8829ea9b0a4679f",
        "sha256": "7bb2f06e9df17cdf1ef14ee8a15ab08ed28e8d0ef5054ee135741560df2ec068",
        "license": "Apache-2.0",
        "size_bytes": 27787264,
    },
}

OPTIONAL_MODELS = {
    filename: model["url"] for filename, model in OPTIONAL_MODEL_SPECS.items()
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fetch(models: dict) -> None:
    for filename, model in models.items():
        # Accept the historical {filename: url} shape for external tooling, but
        # only the checked-in specs can satisfy the integrity contract.
        if isinstance(model, str):
            raise ValueError(f"unversioned model spec for {filename}")
        url = model["url"]
        dest = Path(MODELS_DIR) / filename
        if os.path.exists(dest):
            actual = _sha256(dest)
            if actual != model["sha256"]:
                raise RuntimeError(
                    f"sha256 mismatch for {filename}: expected {model['sha256']}, got {actual}"
                )
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  {filename} already exists ({size_mb:.1f} MB), verified, skipping")
            continue

        print(f"  Downloading {filename} ...")
        partial = Path(f"{dest}.download")
        try:
            urllib.request.urlretrieve(url, partial)
            actual = _sha256(partial)
            if actual != model["sha256"]:
                raise RuntimeError(
                    f"sha256 mismatch for {filename}: expected {model['sha256']}, got {actual}"
                )
            partial.replace(dest)
        finally:
            partial.unlink(missing_ok=True)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Saved {filename} ({size_mb:.1f} MB)")


def download_models(include_optional: bool = False):
    os.makedirs(MODELS_DIR, exist_ok=True)
    _fetch(MODEL_SPECS)
    if include_optional:
        print("Optional evaluation models:")
        _fetch(OPTIONAL_MODEL_SPECS)
    print("All models ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download diarization ONNX models")
    parser.add_argument(
        "--optional",
        action="store_true",
        help="also fetch evaluation-only models (WeSpeaker ResNet34-LM)",
    )
    download_models(include_optional=parser.parse_args().optional)
