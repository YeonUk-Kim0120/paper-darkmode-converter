# PDF Dark Mode Converter

논문 PDF를 다크모드로 변환하는 도구입니다.
**Docling (CUDA)** 으로 피규어 영역을 자동 감지하여, 피규어는 원본 색상 그대로 보존하고 나머지(텍스트·배경·벡터)만 다크모드로 변환합니다.

---

## 동작 방식

```
1. Docling (CUDA) → 논문 내 피규어 바운딩박스 추출
2. 피규어 영역을 원본 픽스맵으로 스냅샷 저장
3. 전체 PDF에 다크모드 적용 (검은 배경, 흰 텍스트, 벡터 반전)
4. 피규어 영역에 저장해둔 원본 스냅샷 복원
5. 결과 PDF 저장
```

---

## 요구사항

- Python 3.10 이상
- NVIDIA GPU (CUDA 지원)
- CUDA Toolkit 및 cuDNN 설치

---

## 설치

### 1. 패키지 설치

```bash
pip install pymupdf docling numpy
```

### 2. PyTorch CUDA 버전 설치

> `pip install torch`로 설치하면 CPU 전용 버전이 설치될 수 있습니다.  
> 반드시 아래 명령으로 CUDA 지원 버전을 설치하세요.

```bash
# CUDA 12.8용 (RTX 30xx/40xx 시리즈 권장)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

설치 후 CUDA 동작 확인:

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 출력 예: True  NVIDIA GeForce RTX 3060
```

---

## 사용법

```bash
# 기본값: 12.pdf → 12_dark.pdf
python model.py

# 입력 파일 지정: input.pdf → input_dark.pdf
python model.py input.pdf

# 입출력 파일 모두 지정
python model.py input.pdf output.pdf
```

---

## 결과물

| 파일 | 설명 |
|---|---|
| `{입력명}_dark.pdf` | 다크모드 변환된 PDF |

---

## 주요 설정값

[model.py](model.py) 상단에서 아래 값을 수정할 수 있습니다.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `BLACK_THRESH` | `0.15` | 이 값 이하의 밝기를 "검은색"으로 판단 |
| `WHITE_THRESH` | `0.85` | 이 값 이상의 밝기를 "흰색"으로 판단 |
| `SNAP_DPI` | `150` | 피규어 스냅샷 해상도 (높을수록 선명, 메모리↑) |

---

## 주의사항

- CUDA가 없는 환경에서는 `extract_figure_bboxes()` 내의 `AcceleratorDevice.CUDA`를 `AcceleratorDevice.CPU`로 변경하세요.
- Docling은 최초 실행 시 AI 모델 가중치를 자동으로 다운로드합니다 (수 GB, 시간 소요).
- `SNAP_DPI`를 200~300으로 올리면 피규어 화질이 더 선명해집니다.
