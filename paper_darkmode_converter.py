"""
model.py  ─  PDF 다크모드 변환기 (Figure 보존 버전)
=====================================================
• Docling (CUDA) 으로 피규어 바운딩박스 자동 추출
• 피규어 영역은 원본 그대로 보존
• 나머지 영역(텍스트·배경·벡터)은 다크모드로 변환

사용법:
    python model.py                  # 기본값: 12.pdf → 12_dark.pdf
    python model.py input.pdf        # → input_dark.pdf
    python model.py input.pdf out.pdf
"""

import re
import sys
from collections import defaultdict

import fitz  # PyMuPDF


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  임계값
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLACK_THRESH = 0.15
WHITE_THRESH = 0.85


def _is_black(v: float) -> bool:
    return v <= BLACK_THRESH


def _is_white(v: float) -> bool:
    return v >= WHITE_THRESH


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PDF 문자열 리터럴 보호
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _protect_strings(text: str):
    protected: list = []
    out: list = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '(':
            depth = 1
            j = i + 1
            while j < n and depth > 0:
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                j += 1
            protected.append(text[i:j])
            out.append(f"\x00S{len(protected) - 1}\x00")
            i = j
        else:
            out.append(text[i])
            i += 1
    return ''.join(out), protected


def _restore_strings(text: str, protected: list) -> str:
    for idx, s in enumerate(protected):
        text = text.replace(f"\x00S{idx}\x00", s)
    return text


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  인라인 이미지 보호
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_RE_INLINE_IMG = re.compile(rb'\bBI\b.+?\bEI\b', re.DOTALL)


def _protect_inline_images(raw: bytes):
    images: list = []

    def _repl(m):
        images.append(m.group(0))
        return f"__IMG{len(images) - 1}__".encode('latin-1')

    cleaned = _RE_INLINE_IMG.sub(_repl, raw)
    return cleaned, images


def _restore_inline_images(raw: bytes, images: list) -> bytes:
    for idx, img in enumerate(images):
        raw = raw.replace(f"__IMG{idx}__".encode('latin-1'), img)
    return raw


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  색상 연산자 치환
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_NUM = r'(\d+\.?\d*|\.\d+)'


def _swap_gray(v_str: str) -> str:
    v = float(v_str)
    if _is_black(v):
        return '1'
    if _is_white(v):
        return '0'
    return v_str


def _make_gray_replacer(op: str):
    def _fn(m):
        return f'{_swap_gray(m.group(1))} {op}'
    return _fn


def _make_rgb_replacer(op: str):
    def _fn(m):
        r = float(m.group(1))
        g = float(m.group(2))
        b = float(m.group(3))
        if _is_black(r) and _is_black(g) and _is_black(b):
            return f'1 1 1 {op}'
        if _is_white(r) and _is_white(g) and _is_white(b):
            return f'0 0 0 {op}'
        return m.group(0)
    return _fn


def _make_cmyk_replacer(op: str):
    def _fn(m):
        c  = float(m.group(1))
        mm = float(m.group(2))
        y  = float(m.group(3))
        k  = float(m.group(4))
        if _is_black(c) and _is_black(mm) and _is_black(y) and _is_white(k):
            return f'0 0 0 0 {op}'
        if _is_black(c) and _is_black(mm) and _is_black(y) and _is_black(k):
            return f'0 0 0 1 {op}'
        return m.group(0)
    return _fn


def swap_stream_colors(stream: bytes, prepend_white_default: bool = False) -> bytes:
    stream, imgs = _protect_inline_images(stream)
    text = stream.decode('latin-1')
    text, strs = _protect_strings(text)

    N = _NUM
    text = re.sub(rf'(?<![.\w]){N}\s+g(?![a-zA-Z])',  _make_gray_replacer('g'), text)
    text = re.sub(rf'(?<![.\w]){N}\s+G(?![a-zA-Z])',  _make_gray_replacer('G'), text)
    text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+rg\b', _make_rgb_replacer('rg'), text)
    text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+RG\b', _make_rgb_replacer('RG'), text)
    text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{N}\s+k\b',  _make_cmyk_replacer('k'),  text)
    text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{N}\s+K\b',  _make_cmyk_replacer('K'),  text)

    for op_fill, op_stroke in [('scn', 'SCN'), ('sc', 'SC')]:
        text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{N}\s+{op_fill}\b',   _make_cmyk_replacer(op_fill),   text)
        text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{N}\s+{op_stroke}\b', _make_cmyk_replacer(op_stroke), text)
        text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{op_fill}\b',   _make_rgb_replacer(op_fill),   text)
        text = re.sub(rf'(?<![.\w]){N}\s+{N}\s+{N}\s+{op_stroke}\b', _make_rgb_replacer(op_stroke), text)
        text = re.sub(rf'(?<![.\w]){N}\s+{op_fill}\b',   _make_gray_replacer(op_fill),   text)
        text = re.sub(rf'(?<![.\w]){N}\s+{op_stroke}\b', _make_gray_replacer(op_stroke), text)

    if prepend_white_default:
        text = '1 g 1 G 1 1 1 rg 1 1 1 RG\n' + text

    text = _restore_strings(text, strs)
    result = text.encode('latin-1')
    result = _restore_inline_images(result, imgs)
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Step 1: Docling으로 피규어 바운딩박스 추출 (CUDA)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def extract_figure_bboxes(pdf_path: str) -> dict:
    """
    Returns: {page_no (1-indexed): [fitz.Rect, ...], ...}
    Docling bbox 좌표계(bottom-left 원점) → PyMuPDF 좌표계(top-left 원점) 변환 포함.
    """
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import (
        PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
    )
    from docling.datamodel.base_models import InputFormat

    print("Docling 모델 로딩 중 (CUDA)...")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4,
        device=AcceleratorDevice.CUDA,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print(f"'{pdf_path}' 피규어 분석 중...")
    result = converter.convert(pdf_path)

    # 페이지 높이 정보가 필요하므로 PyMuPDF로 PDF 열기
    tmp_doc = fitz.open(pdf_path)
    figures: dict = defaultdict(list)

    for item, _ in result.document.iterate_items():
        if item.label.name == "PICTURE":
            for prov in item.prov:
                page_no = prov.page_no
                bbox    = prov.bbox
                page_h  = tmp_doc[page_no - 1].rect.height

                # Docling: bottom-left 원점 (l, b, r, t)
                # PyMuPDF: top-left 원점 (x0, y0, x1, y1)
                x0 = bbox.l
                y0 = page_h - bbox.t
                x1 = bbox.r
                y1 = page_h - bbox.b
                rect = fitz.Rect(x0, y0, x1, y1)
                figures[page_no].append(rect)
                print(f"  [페이지 {page_no}] 피규어 발견: ({x0:.1f}, {y0:.1f}, {x1:.1f}, {y1:.1f})")

    tmp_doc.close()
    print(f"  → 총 {sum(len(v) for v in figures.values())}개 피규어 추출 완료\n")
    return dict(figures)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Step 2: 다크모드 변환 (피규어 영역 보존)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def convert_dark_preserve_figures(input_path: str, output_path: str, figures: dict) -> None:
    """
    figures: {page_no (1-indexed): [fitz.Rect, ...]}

    전략:
      1) 피규어 영역을 원본에서 고해상도 픽스맵으로 스냅샷
      2) 전체 PDF에 다크모드 적용
      3) 스냅샷을 다크모드 PDF 위에 덮어씌워 피규어 원본 복원
    """
    doc = fitz.open(input_path)

    # ── 스냅샷 저장 (다크모드 적용 전) ──────────────────────
    SNAP_DPI = 300   # 스냅샷 해상도 (높을수록 선명, 메모리 ↑)
    mat = fitz.Matrix(SNAP_DPI / 72, SNAP_DPI / 72)

    snapshots: dict = {}   # page_no -> [(rect, Pixmap), ...]
    print("피규어 영역 스냅샷 저장 중...")
    for page_no, rects in figures.items():
        page = doc[page_no - 1]
        page_snaps = []
        for rect in rects:
            # 페이지 범위를 벗어나지 않도록 클리핑
            safe_rect = rect & page.rect
            if safe_rect.is_empty:
                continue
            pix = page.get_pixmap(matrix=mat, clip=safe_rect)
            page_snaps.append((safe_rect, pix))
            print(f"  [페이지 {page_no}] 스냅샷 완료: {safe_rect}")
        if page_snaps:
            snapshots[page_no] = page_snaps

    # ── Phase 1: Form XObject 벡터 색상 치환 ─────────────────
    print("\n다크모드 변환 중...")
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(xref, "Subtype")[1] == "/Form":
                raw = doc.xref_stream(xref)
                if raw:
                    doc.update_stream(
                        xref,
                        swap_stream_colors(raw, prepend_white_default=True),
                    )
        except Exception:
            pass

    # ── Phase 2: 페이지 콘텐츠 스트림 + 검은 배경 ────────────
    for idx, page in enumerate(doc):
        page.clean_contents()
        contents = page.get_contents()
        for xref in contents:
            raw = doc.xref_stream(xref)
            if raw:
                doc.update_stream(xref, swap_stream_colors(raw, prepend_white_default=True))
        page.draw_rect(page.rect, color=None, fill=(0, 0, 0), overlay=False)
        print(f"  [다크모드] 페이지 {idx + 1}/{len(doc)} 완료")

    # ── Phase 3: 피규어 원본 복원 ────────────────────────────
    print("\n피규어 원본 복원 중...")
    for page_no, page_snaps in snapshots.items():
        page = doc[page_no - 1]
        for safe_rect, pix in page_snaps:
            # 원본 픽스맵을 원래 자리에 삽입
            page.insert_image(safe_rect, pixmap=pix, overlay=True)
            print(f"  [페이지 {page_no}] 피규어 복원 완료: {safe_rect}")

    # ── 저장 ──────────────────────────────────────────────────
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    print(f"\n[DONE] 저장 완료: '{output_path}'")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    if len(sys.argv) >= 2:
        src = sys.argv[1]
    else:
        src = "paper.pdf"

    if len(sys.argv) >= 3:
        dst = sys.argv[2]
    else:
        dst = src.replace(".pdf", "_dark.pdf")

    print(f"[INPUT]  {src}")
    print(f"[OUTPUT] {dst}\n")

    # 1) 피규어 바운딩박스 추출
    figures = extract_figure_bboxes(src)

    # 2) 다크모드 변환 (피규어 보존)
    convert_dark_preserve_figures(src, dst, figures)


if __name__ == "__main__":
    main()