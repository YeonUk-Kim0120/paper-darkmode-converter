# PDF Dark Mode Converter

This Python script converts research paper PDFs to dark mode.
Using **Docling (CUDA)**, it automatically detects figure regions, preserves figures in their original colors, and converts only the rest (text, background, and vector elements) to dark mode.

---

### 3D Gaussian Splatting

| Light Mode | Dark Mode |
|:---:|:---:|
| ![3DGS Light](images/3dgs_light.png) | ![3DGS Dark](images/3dgs_dark.png) |

### Attention Is All You Need (Transformer)

| Light Mode | Dark Mode |
|:---:|:---:|
| ![Transformer Light](images/transformer_light.png) | ![Transformer Dark](images/transformer_dark.png) |

---

## How It Works

```
1. Docling (CUDA) extracts figure bounding boxes from the paper.
2. Figure regions are saved as snapshots from the original pixmap.
3. Dark mode is applied to the full PDF (black background, white text, inverted vectors).
4. The saved original figure snapshots are restored onto figure regions.
5. The final PDF is saved.
```

---

## Requirements

- Python 3.10+
- NVIDIA GPU (CUDA-supported)
- CUDA Toolkit 12.x and cuDNN installed

---

## Install and Run (Recommended: uv)

With [uv](https://docs.astral.sh/uv/), you can create a virtual environment, install dependencies, and run the script in **one line**.

### 1. Install uv

```bash
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone the repository

```bash
git clone https://github.com/YeonUk-Kim0120/paper-darkmode-converter.git
cd paper-darkmode-converter
```

### 3. Run (dependencies installed automatically)

```bash
# paper.pdf -> paper_dark.pdf (auto naming)
uv run paper_darkmode_converter.py paper.pdf

# Specify both input and output files
uv run paper_darkmode_converter.py input.pdf output.pdf
```

> On first run, `uv run` creates a virtual environment and installs all dependencies, including the CUDA build of PyTorch.
> On later runs, cached environments are reused so startup is immediate.

### 4. (Optional) Run with the CLI command

```bash
# After installing the package with uv, you can use the paper-darkmode command
uv pip install -e .
paper-darkmode paper.pdf
```

---

## Install and Run (pip)

<details>
<summary>Manual installation with pip</summary>

### 1. Clone the repository

```bash
git clone https://github.com/YeonUk-Kim0120/paper-darkmode-converter.git
cd paper-darkmode-converter
```

### 2. Install packages

```bash
pip install pymupdf docling numpy
```

### 3. Install CUDA build of PyTorch

> If you only run `pip install torch`, the **CPU-only build** is installed and CUDA will not work.
> You must install a CUDA-enabled build separately using the command below.

```bash
# For CUDA 12.8 (RTX 20xx / 30xx / 40xx series)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

### 4. Run

```bash
python paper_darkmode_converter.py paper.pdf
python paper_darkmode_converter.py input.pdf output.pdf
```

</details>

---

## Downloading Docling AI Model Weights

Docling automatically downloads the AI model weights required for figure detection **on first run**.

- Download path: `~/.cache/docling/` (Windows: `C:\Users\{username}\.cache\docling\`)
- Size: about 1-2 GB
- Internet connection required; downloaded only once (cache reused afterward)

If you want to preload weights in advance, you can trigger it before conversion with:

```bash
uv run python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"
```

---

## Notes

- **Figure quality**: Set `SNAP_DPI` to `300-400` for clearer figures when zoomed in.
- **Conversion time**: For a typical paper, conversion takes about 1-5 minutes on a GPU system.
