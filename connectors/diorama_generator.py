import os
import re
import io
import base64
import logging
from typing import Optional

from PIL import Image

logger = logging.getLogger("diorama")

ATMOSPHERE_DESCRIPTIONS = {
    "sunny": "Bright, crisp sunny daylight with warm golden sunlight, soft light rays, clear pastel blue sky, and gentle bright highlights.",
    "partly": "Pleasant partly-cloudy daylight with soft puffy white clouds in a smooth pastel blue sky and gentle balanced illumination.",
    "cloudy": "Soft overcast daylight with layered muted gray-pastel clouds, diffused shadowless global illumination, and cool slate tones.",
    "rainy": "Rainy atmospheric scene with soft volumetric rain clouds, visible gentle rain streaks, glossy wet cobblestone and roof surfaces, and tiny reflective puddles.",
    "stormy": "Dramatic moody thunderstorm atmosphere with deep indigo-violet storm clouds, heavy rain atmosphere, wet reflective rooftops, and a subtle warm glow inside windows.",
    "snowy": "Crisp winter snowfall scene with soft snow blanketing rooftops, castle walls, and trees, gentle falling snowflakes, and cool pale-blue pastel lighting.",
    "foggy": "Serene misty morning fog hugging the lower terrain and wrapping softly around the base of the buildings, cool muted sage-pastel backdrop.",
    "night": "Peaceful starry clear night with deep twilight-indigo backdrop, soft moonlight grazing the architecture, and tiny warm golden lights glowing in building windows.",
}


def _slugify(value: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ ", "cgiosucgiosu_")
    cleaned = value.translate(tr_map).lower()
    return re.sub(r"[^a-z0-9_]+", "_", cleaned).strip("_")


class DioramaGenerator:
    """
    Generates 45-degree isometric 3D miniature city landmark weather dioramas using
    Google Gemini Nano Banana 2.1 (`gemini-nano-banana-2.1`) via the official Interactions SDK,
    caching compact WebP outputs locally and optionally in Google Cloud Storage.
    """

    def __init__(self):
        self.model = "gemini-nano-banana-2.1"
        self.local_cache_dir = os.environ.get("DIORAMA_CACHE_DIR", "/tmp/diorama_cache")
        if os.name == "nt" and self.local_cache_dir == "/tmp/diorama_cache":
            self.local_cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dioramas_cache")
        os.makedirs(self.local_cache_dir, exist_ok=True)
        self.gcs_bucket_name = os.environ.get("DIORAMA_GCS_BUCKET", "").strip()
        self.last_error: Optional[str] = None

    def is_enabled(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    def build_prompt(self, province: str, district: Optional[str], landmark: Optional[str], atmosphere: str) -> str:
        atmo_desc = ATMOSPHERE_DESCRIPTIONS.get(atmosphere, ATMOSPHERE_DESCRIPTIONS["partly"])
        subject = landmark or (f"{district}, {province}" if district and district != "__MERKEZ__" else province)
        place_ctx = f"{district} ({province})" if district and district != "__MERKEZ__" else province

        return (
            f"16:9 widescreen 45-degree top-down isometric miniature 3D cartoon diorama of {place_ctx}, Turkey, "
            f"featuring its iconic landmark **{subject}** as the unmistakable centerpiece. "
            "Composition: a compact, floating diamond-oriented square cutaway terrain island positioned slightly right-of-center "
            "so the left third remains calm, clean pastel sky negative space for overlaid text. "
            "Show realistic, tactile PBR materials (carved stone masonry, terracotta roof tiles, cobblestone, trees/water where fitting), "
            "gentle global illumination, and a subtle soft contact shadow beneath the cleanly sliced earth-and-stone base. "
            f"Weather & atmosphere: {atmo_desc} "
            "Color palette: soothing pastel-adjacent background with richer restrained accent tones on the architecture. "
            "STRICT RULES: full-bleed edge-to-edge composition with NO frames or borders; "
            "ABSOLUTELY NO text, NO city names, NO letters, NO numbers, NO weather icons, NO UI panels, and NO watermarks anywhere in the image."
        )

    def _cache_filename(self, province: str, district: Optional[str], landmark: Optional[str], atmosphere: str) -> str:
        atmo_safe = atmosphere if atmosphere in ATMOSPHERE_DESCRIPTIONS else "partly"
        key = landmark or (f"{province}_{district}" if district and district != "__MERKEZ__" else province)
        return f"{_slugify(key)}_{atmo_safe}.webp"

    def _read_gcs(self, blob_name: str) -> Optional[bytes]:
        if not self.gcs_bucket_name:
            return None
        try:
            from google.cloud import storage
            client = storage.Client()
            blob = client.bucket(self.gcs_bucket_name).blob(f"dioramas/{blob_name}")
            if blob.exists():
                return blob.download_as_bytes()
        except Exception as e:
            logger.warning("GCS diorama read failed (%s): %s", blob_name, e)
        return None

    def _write_gcs(self, blob_name: str, data: bytes) -> None:
        if not self.gcs_bucket_name:
            return
        try:
            from google.cloud import storage
            client = storage.Client()
            blob = client.bucket(self.gcs_bucket_name).blob(f"dioramas/{blob_name}")
            blob.upload_from_string(data, content_type="image/webp")
        except Exception as e:
            logger.warning("GCS diorama write failed (%s): %s", blob_name, e)

    @staticmethod
    def _to_optimized_webp(raw_bytes: bytes, max_width: int = 1280, quality: int = 82) -> bytes:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            if img.width > max_width:
                new_h = int(img.height * (max_width / img.width))
                img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=quality, method=6)
            return out.getvalue()

    def get_or_generate(
        self,
        province: str,
        district: Optional[str] = None,
        landmark: Optional[str] = None,
        atmosphere: str = "partly",
    ) -> Optional[bytes]:
        filename = self._cache_filename(province, district, landmark, atmosphere)
        local_path = os.path.join(self.local_cache_dir, filename)

        # 1. Local disk cache
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()

        # 2. GCS persistent cache
        gcs_bytes = self._read_gcs(filename)
        if gcs_bytes:
            with open(local_path, "wb") as f:
                f.write(gcs_bytes)
            return gcs_bytes

        # 3. Generate live via Gemini Nano Banana 2.1
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            self.last_error = "GEMINI_API_KEY ortam değişkeni tanımlı değil."
            return None

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = self.build_prompt(province, district, landmark, atmosphere)
            interaction = client.interactions.create(
                model=self.model,
                input=prompt,
                response_format={
                    "type": "image",
                    "aspect_ratio": "16:9",
                    "image_size": "1K",
                },
            )
            if not interaction.output_image or not interaction.output_image.data:
                self.last_error = "Gemini görsel çıktısı boş döndü."
                return None

            raw_bytes = base64.b64decode(interaction.output_image.data)
            webp_bytes = self._to_optimized_webp(raw_bytes)

            with open(local_path, "wb") as f:
                f.write(webp_bytes)
            self._write_gcs(filename, webp_bytes)
            self.last_error = None
            return webp_bytes
        except Exception as e:
            self.last_error = str(e)
            logger.exception("Gemini diorama generation failed: %s", e)
            return None
