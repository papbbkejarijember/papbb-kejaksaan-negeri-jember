const MAX_IMAGE_BYTES = 2_800_000;
const MAX_IMAGE_DIMENSION = 1800;

const SUPPORTED_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function readBlobAsDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Foto tidak dapat dibaca."));
    reader.readAsDataURL(blob);
  });
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Foto tidak dapat diproses."));
    };
    image.src = url;
  });
}

export async function prepareImage(file: File, label = "Foto"): Promise<{ dataUrl: string; fileName: string }> {
  if (!SUPPORTED_TYPES.has(file.type)) {
    throw new Error(`${label} harus JPG, PNG, atau WEBP.`);
  }
  if (file.size > MAX_IMAGE_BYTES) {
    // We still try to resize/compress oversized source files instead of rejecting them.
  }

  const image = await loadImage(file);
  const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(image.naturalWidth, image.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
  canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Browser tidak mendukung pemrosesan foto.");
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  let quality = 0.88;
  let blob: Blob | null = null;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
    if (blob && blob.size <= MAX_IMAGE_BYTES) break;
    quality -= 0.10;
  }

  if (!blob || blob.size > MAX_IMAGE_BYTES) {
    throw new Error(`${label} terlalu besar setelah dikompresi. Gunakan foto dengan resolusi lebih kecil.`);
  }

  return {
    dataUrl: await readBlobAsDataUrl(blob),
    fileName: file.name.replace(/\.[^.]+$/, "") + ".jpg",
  };
}

export const MAX_IMAGE_UPLOAD_BYTES = MAX_IMAGE_BYTES;
