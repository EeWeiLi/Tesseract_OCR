import os
import threading
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps, ImageFilter
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, XPreformatted, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from xml.sax.saxutils import escape as xml_escape

# ========== SETTINGS ==========
DEFAULT_OUTPUT_FOLDER = "output_files"
DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
DEFAULT_OCR_LANG = "eng+msa"   # English + Malay
DEFAULT_PDF_DPI = 300          # Good balance for speed/accuracy

# ========== PREPROCESS + OCR ==========
def _preprocess_for_ocr(img: Image.Image, upscale=1.5) -> Image.Image:
    """
    Fast, light preprocessing:
      - upscale if page small
      - grayscale + autocontrast
      - global threshold
      - light denoise + sharpen
    """
    w, h = img.size
    if min(w, h) < 1400:
        img = img.resize((int(w * upscale), int(h * upscale)), Image.LANCZOS)
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    bw = g.point(lambda x: 255 if x > 180 else 0)
    bw = bw.filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.SHARPEN)
    return bw

def _ocr_page_image(img: Image.Image, lang: str) -> str:
    # Single reliable config for documents
    cfg = "--psm 4 --oem 3 -c preserve_interword_spaces=1"
    text = pytesseract.image_to_string(img, lang=lang, config=cfg)
    return (text or "").strip()

def _render_page(doc, page_index: int, dpi: int) -> Image.Image:
    page = doc.load_page(page_index)
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

# ========== SAVE TEXT AS PDF/TXT ==========
def save_text_as_pdf(text, output_pdf_path, title=None):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
        title=title or os.path.basename(output_pdf_path)
    )
    pre_style = ParagraphStyle("Pre", fontName="Helvetica", fontSize=10, leading=14)
    safe_text = xml_escape((text or "").replace("\r\n", "\n"))

    chunks = [c.strip() for c in safe_text.split("\n\n")] or ["(No text extracted.)"]
    flow = []
    if title:
        flow.append(XPreformatted(xml_escape(title), pre_style))
        flow.append(Spacer(1, 6))
    for c in chunks:
        if c:
            flow.append(XPreformatted(c, pre_style))
            flow.append(Spacer(1, 6))
    doc.build(flow)

def save_text_as_txt(text, output_txt_path):
    with open(output_txt_path, "w", encoding="utf-8", errors="ignore") as f:
        f.write(text if text else "(No text extracted.)")

# ========== FORCE-OCR HELPERS ==========
def extract_text_pages_force_ocr(pdf_path, dpi=DEFAULT_PDF_DPI, ocr_lang=DEFAULT_OCR_LANG, log=lambda *_: None):
    """
    Minimal, force-OCR pipeline: render each page → preprocess → OCR (single config).
    Returns list[str] (one string per page).
    """
    per_page = []
    doc = fitz.open(pdf_path)  # raises if invalid
    total = len(doc)
    for i in range(total):
        pno = i + 1
        log(f"… page {pno}/{total}: OCR at {dpi} DPI")
        img = _render_page(doc, i, dpi)
        img = _preprocess_for_ocr(img)
        txt = _ocr_page_image(img, ocr_lang)
        # Optional: prefix a page marker inside the output (helps later debugging/search)
        per_page.append(f"[PAGE {pno}]\n{txt}")
    return per_page

def join_pages(pages_text, start_idx, end_idx):
    """
    Join pages_text[start_idx:end_idx] with a blank line between pages.
    start_idx inclusive, end_idx exclusive (python slicing style).
    """
    return "\n\n".join(pages_text[start_idx:end_idx]).strip()

# ========== TK GUI ==========
class OCRTextGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Force OCR → TXT or PDF (with optional page-chunking)")
        self.geometry("910x580")
        self.resizable(True, True)

        self.selected_files = []
        self.var_outdir = tk.StringVar(value=os.path.abspath(DEFAULT_OUTPUT_FOLDER))
        self.var_tesseract = tk.StringVar(value=DEFAULT_TESSERACT_PATH)
        self.var_lang = tk.StringVar(value=DEFAULT_OCR_LANG)
        self.var_dpi = tk.IntVar(value=DEFAULT_PDF_DPI)

        # Output options
        self.var_output_format = tk.StringVar(value="txt")  # "txt" or "pdf"
        self.var_chunk_enable = tk.BooleanVar(value=False)
        self.var_pages_per_chunk = tk.IntVar(value=10)      # user-defined pages per chunk

        os.makedirs(self.var_outdir.get(), exist_ok=True)
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}

        # Input PDFs
        frm_files = ttk.LabelFrame(self, text="Input PDFs"); frm_files.pack(fill="x", **pad)
        ttk.Button(frm_files, text="Select PDF(s)…", command=self.choose_pdfs).pack(side="left", padx=6, pady=8)
        ttk.Button(frm_files, text="Clear List", command=self.clear_files).pack(side="left", padx=6, pady=8)
        self.lbl_count = ttk.Label(frm_files, text="No files selected"); self.lbl_count.pack(side="left", padx=12)

        # Output folder
        frm_out = ttk.LabelFrame(self, text="Output Folder"); frm_out.pack(fill="x", **pad)
        ttk.Entry(frm_out, textvariable=self.var_outdir).pack(side="left", fill="x", expand=True, padx=6, pady=8)
        ttk.Button(frm_out, text="Browse…", command=self.choose_outdir).pack(side="left", padx=6, pady=8)

        # Settings
        frm_cfg = ttk.LabelFrame(self, text="Settings"); frm_cfg.pack(fill="x", **pad)
        ttk.Label(frm_cfg, text="Tesseract EXE:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm_cfg, textvariable=self.var_tesseract, width=60).grid(row=0, column=1, sticky="we", padx=6, pady=6)
        ttk.Button(frm_cfg, text="Browse…", command=self.browse_tesseract).grid(row=0, column=2, padx=6, pady=6)

        ttk.Label(frm_cfg, text="OCR Lang:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
        ttk.Entry(frm_cfg, textvariable=self.var_lang, width=12).grid(row=1, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(frm_cfg, text="DPI:").grid(row=1, column=2, sticky="e", padx=6, pady=6)
        ttk.Entry(frm_cfg, textvariable=self.var_dpi, width=8).grid(row=1, column=3, sticky="w", padx=6, pady=6)

        # Output format (radio)
        ttk.Label(frm_cfg, text="Output format:").grid(row=2, column=0, sticky="e", padx=6, pady=6)
        fmt_frame = ttk.Frame(frm_cfg); fmt_frame.grid(row=2, column=1, columnspan=3, sticky="w")
        ttk.Radiobutton(fmt_frame, text="Text (.txt)", variable=self.var_output_format, value="txt").pack(side="left", padx=6)
        ttk.Radiobutton(fmt_frame, text="PDF (.pdf)", variable=self.var_output_format, value="pdf").pack(side="left", padx=6)

        # Chunking controls
        chk_frame = ttk.Frame(frm_cfg); chk_frame.grid(row=3, column=1, columnspan=3, sticky="w")
        ttk.Checkbutton(chk_frame, text="Chunk output by pages", variable=self.var_chunk_enable).pack(side="left", padx=(0,12))
        ttk.Label(chk_frame, text="Pages per chunk:").pack(side="left")
        ttk.Entry(chk_frame, textvariable=self.var_pages_per_chunk, width=6).pack(side="left", padx=(6,0))

        frm_cfg.columnconfigure(1, weight=1)

        # Run
        frm_run = ttk.LabelFrame(self, text="Run"); frm_run.pack(fill="x", **pad)
        self.pb = ttk.Progressbar(frm_run, mode="determinate"); self.pb.pack(fill="x", padx=6, pady=6)

        btns = ttk.Frame(frm_run); btns.pack(fill="x")
        ttk.Button(btns, text="Start", command=self.start).pack(side="left", padx=6, pady=6)
        ttk.Button(btns, text="Open Output Folder", command=self.open_output_folder).pack(side="left", padx=6, pady=6)

        # Log
        frm_log = ttk.LabelFrame(self, text="Log"); frm_log.pack(fill="both", expand=True, **pad)
        self.txt_log = tk.Text(frm_log, height=14, wrap="word"); self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

    # --- File pickers ---
    def choose_pdfs(self):
        files = filedialog.askopenfilenames(title="Select PDF files", filetypes=[("PDF files", "*.pdf")])
        if files:
            self.selected_files = list(files)
            self.lbl_count.config(text=f"{len(self.selected_files)} file(s) selected")

    def clear_files(self):
        self.selected_files = []
        self.lbl_count.config(text="No files selected")

    def choose_outdir(self):
        d = filedialog.askdirectory(title="Choose output folder")
        if d:
            self.var_outdir.set(d); os.makedirs(d, exist_ok=True)

    def browse_tesseract(self):
        path = filedialog.askopenfilename(title="Locate tesseract.exe",
                                          filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
        if path:
            self.var_tesseract.set(path)

    # --- Utilities ---
    def log(self, msg):
        self.txt_log.insert("end", msg + "\n"); self.txt_log.see("end"); self.update_idletasks()

    def open_output_folder(self):
        outdir = self.var_outdir.get().strip()
        if os.path.isdir(outdir):
            try: os.startfile(outdir)
            except Exception: pass
        else:
            messagebox.showinfo("Output", "Output folder does not exist yet.")

    # --- Run pipeline ---
    def start(self):
        if not self.selected_files:
            messagebox.showwarning("No files", "Please select one or more PDF files.")
            return

        outdir = self.var_outdir.get().strip()
        if not outdir:
            messagebox.showwarning("No output folder", "Please choose an output folder.")
            return
        os.makedirs(outdir, exist_ok=True)

        # Configure pytesseract
        tpath = self.var_tesseract.get().strip()
        if tpath:
            pytesseract.pytesseract.tesseract_cmd = tpath
        if not os.path.isfile(pytesseract.pytesseract.tesseract_cmd):
            if not messagebox.askyesno(
                "Tesseract not found",
                "Could not find tesseract.exe at the given path. Continue anyway?"
            ):
                return

        self.pb.config(value=0, maximum=len(self.selected_files))
        self.txt_log.delete("1.0", "end")

        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self):
        ocr_lang = self.var_lang.get().strip() or DEFAULT_OCR_LANG
        dpi = int(self.var_dpi.get()); outdir = self.var_outdir.get().strip()
        fmt = self.var_output_format.get().strip().lower()
        do_chunk = bool(self.var_chunk_enable.get())
        pages_per_chunk = int(self.var_pages_per_chunk.get() or 0)

        for idx, pdf_path in enumerate(self.selected_files, start=1):
            name = os.path.basename(pdf_path)
            try:
                self.log(f"🔍 Extracting (force OCR): {name}")
                pages_text = extract_text_pages_force_ocr(pdf_path, dpi=dpi, ocr_lang=ocr_lang, log=self.log)
                total_pages = len(pages_text)
                base = os.path.splitext(name)[0]

                if do_chunk and pages_per_chunk > 0:
                    # Write multiple chunk files
                    start_page = 1
                    chunk_idx = 1
                    while start_page <= total_pages:
                        end_page = min(start_page + pages_per_chunk - 1, total_pages)
                        # zero-based indices for slice
                        chunk_text = join_pages(pages_text, start_page - 1, end_page)

                        if fmt == "pdf":
                            out_path = os.path.join(outdir, f"{base}_p{start_page:03d}-{end_page:03d}.pdf")
                            self.log(f"📝 Writing PDF chunk p{start_page}-{end_page}…")
                            title = f"{name} (pages {start_page}-{end_page})"
                            save_text_as_pdf(chunk_text, out_path, title=title)
                        else:
                            out_path = os.path.join(outdir, f"{base}_p{start_page:03d}-{end_page:03d}.txt")
                            self.log(f"📝 Writing TXT chunk p{start_page}-{end_page}…")
                            save_text_as_txt(chunk_text, out_path)

                        self.log(f"✅ Saved: {out_path}")
                        chunk_idx += 1
                        start_page = end_page + 1
                else:
                    # Single output file (all pages)
                    full_text = join_pages(pages_text, 0, total_pages)
                    if fmt == "pdf":
                        out_path = os.path.join(outdir, f"{base}_text.pdf")
                        self.log("📝 Writing PDF…")
                        save_text_as_pdf(full_text, out_path, title=name)
                    else:
                        out_path = os.path.join(outdir, f"{base}.txt")
                        self.log("📝 Writing TXT…")
                        save_text_as_txt(full_text, out_path)
                    self.log(f"✅ Saved: {out_path}")

            except Exception as e:
                self.log(f"❌ Error processing {name}: {e}")

            self.pb.config(value=idx); self.update_idletasks()

        self.log("\n✅ Done.")
        try: os.startfile(outdir)
        except Exception: pass

if __name__ == "__main__":
    app = OCRTextGUI()
    app.mainloop()
