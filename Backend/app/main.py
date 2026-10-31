"""FastAPI router. Mount with: app.include_router(router)"""
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from app.ocr.parser import process_invoice
from app.ocr.schemas import Field, LineItem, OcrResult

router = APIRouter(prefix="/invoices", tags=["invoices"])
MAX_BYTES = 10 * 1024 * 1024


@router.post("/ocr", response_model=OcrResult)
async def ocr_invoice(file: UploadFile = File(...)):
    """Extract line items from an invoice image. Nothing is saved: the owner reviews first."""
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Upload a JPG, PNG or WebP image.")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image larger than 10 MB.")
    try:
        return await run_in_threadpool(process_invoice, data)
    except ValueError as e:
        raise HTTPException(422, str(e))


if __name__ == "__main__":      # python main.py  -> quick local server
    import uvicorn
    from fastapi import FastAPI
    app = FastAPI(title="StockLens OCR")
    app.include_router(router)
    uvicorn.run(app, port=8000)
