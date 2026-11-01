import { ApiError } from '../services/api'

const MAX_INPUT_BYTES = 8 * 1024 * 1024
const ALLOWED = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']

function loadImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => { URL.revokeObjectURL(url); resolve(img) }
    img.onerror = () => { URL.revokeObjectURL(url); reject(new ApiError('We could not read that image. Try a different file.')) }
    img.src = url
  })
}

/** Validates, centre-crops to a square and shrinks to `size` px. Returns { blob, dataUrl }. */
export async function processAvatar(file, size = 256) {
  if (!file) throw new ApiError('Choose an image first.')
  if (!ALLOWED.includes(file.type)) throw new ApiError('Please choose a JPG, PNG, WebP or GIF image.')
  if (file.size > MAX_INPUT_BYTES) throw new ApiError('That image is too large. Please choose one under 8 MB.')
  const img = await loadImage(file)
  const side = Math.min(img.naturalWidth, img.naturalHeight)
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, size, size)
  ctx.drawImage(img, (img.naturalWidth - side) / 2, (img.naturalHeight - side) / 2, side, side, 0, 0, size, size)
  const dataUrl = canvas.toDataURL('image/jpeg', 0.85)
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85))
  if (!blob) throw new ApiError('We could not process that image. Try a different file.')
  return { blob, dataUrl }
}
