"""Private, optional missing-person photos. No interview answers or GPS uploaded."""
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel
from requests import HTTPError

from fir_storage import download_evidence, upload_evidence

MAX_BYTES = 5 * 1024 * 1024


class PhotoOut(BaseModel):
    file_id: str
    filename: str
    size: int


def normalize_photo(data):
    try:
        with Image.open(io.BytesIO(data)) as original:
            if original.format not in ('JPEG', 'PNG', 'WEBP'):
                raise HTTPException(415, 'Choose a JPG, PNG or WebP photo.')
            if original.width * original.height > 25_000_000:
                raise HTTPException(413, 'Photo resolution is too large. Choose a smaller photo.')
            image = ImageOps.exif_transpose(original).convert('RGB')
            image.thumbnail((1600, 1600))
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=85)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(415, 'This is not a supported photo.') from exc


def create_missing_media_router(db, current_user):
    router = APIRouter(prefix='/api/missing')

    def bundle_key(user, draft_id):
        if not re.fullmatch(r'[A-Za-z0-9-]{8,80}', draft_id):
            raise HTTPException(422, 'Invalid draft identifier.')
        return f"{user['id']}:{draft_id}"

    @router.get('/{draft_id}/photos', response_model=list[PhotoOut])
    async def list_photos(draft_id: str, user=Depends(current_user)):
        bundle = await db.missing_media.find_one(
            {'_id': bundle_key(user, draft_id)}, {'_id': 0, 'photos': 1})
        return [PhotoOut(**p) for p in (bundle or {}).get('photos', [])]

    @router.post('/{draft_id}/photos', response_model=PhotoOut)
    async def add_photo(draft_id: str, file: UploadFile = File(...), user=Depends(current_user)):
        key = bundle_key(user, draft_id)
        raw = await file.read(MAX_BYTES + 1)
        await file.close()
        if len(raw) > MAX_BYTES:
            raise HTTPException(413, 'Each photo must be under 5 MB.')
        if not raw:
            raise HTTPException(415, 'The selected photo is empty.')
        image = await run_in_threadpool(normalize_photo, raw)
        await db.missing_media.update_one({'_id': key}, {'$setOnInsert': {
            'user_id': user['id'], 'photos': [], 'count': 0,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }}, upsert=True)
        reserved = await db.missing_media.update_one(
            {'_id': key, 'count': {'$lt': 3}}, {'$inc': {'count': 1}})
        if not reserved.modified_count:
            raise HTTPException(409, 'A maximum of 3 photos can be attached.')
        try:
            photo = await upload_evidence(user['id'], draft_id, 'missing-person.jpg', image, 'image/jpeg')
            await db.missing_media.update_one({'_id': key}, {'$push': {'photos': photo}})
            return PhotoOut(**photo)
        except Exception as exc:
            await db.missing_media.update_one({'_id': key}, {'$inc': {'count': -1}})
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status == 402:
                raise HTTPException(402, 'Photo storage is unavailable. Continue without a photo or try later.') from exc
            raise HTTPException(503, 'Photo upload failed. Please try again.') from exc

    @router.get('/{draft_id}/photos/{file_id}')
    async def read_photo(draft_id: str, file_id: str, user=Depends(current_user)):
        bundle = await db.missing_media.find_one(
            {'_id': bundle_key(user, draft_id)}, {'_id': 0, 'photos': 1})
        photo = next((p for p in (bundle or {}).get('photos', []) if p['file_id'] == file_id), None)
        if not photo:
            raise HTTPException(404, 'Photo not found.')
        try:
            data, _ = await download_evidence(photo['storage_path'])
        except HTTPError as exc:
            raise HTTPException(503, 'Photo could not be loaded. Please retry.') from exc
        return Response(data, media_type='image/jpeg', headers={
            'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})

    @router.delete('/{draft_id}/photos/{file_id}', status_code=204)
    async def detach_photo(draft_id: str, file_id: str, user=Depends(current_user)):
        # Storage has no delete API: detach and revoke reads; do not claim erasure.
        result = await db.missing_media.update_one(
            {'_id': bundle_key(user, draft_id), 'photos.file_id': file_id},
            {'$pull': {'photos': {'file_id': file_id}}, '$inc': {'count': -1}})
        if not result.matched_count:
            raise HTTPException(404, 'Photo not found.')
        return Response(status_code=204)

    return router