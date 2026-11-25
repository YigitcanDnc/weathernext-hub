import os
import re
import io
import base64
import logging
from typing import Optional

from PIL import Image, ImageFilter
import numpy as np

logger = logging.getLogger("diorama")

ATMOSPHERE_DESCRIPTIONS = {
    "sunny": "Bright, crisp sunny daylight directly illuminating the island with warm golden sunlight highlights and rich vibrant architecture surfaces.",
    "partly": "Balanced, cheerful daylight softly illuminating the architecture, rooftops, and greenery of the island.",
    "cloudy": "Soft diffused overcast daylight across the island's stone masonry, roofs, and greenery with cool muted shadowless lighting.",
    "rainy": "Rain-soaked island atmosphere with wet glistening rooftops, glossy damp cobblestones, tiny puddles on plazas, and cool overcast lighting on the island itself.",
    "stormy": "Dramatic moody storm lighting on the island with wet reflective stone and roof surfaces, deep cool twilight contrast on walls, and warm amber light glowing inside windows.",
    "snowy": "Crisp winter snowfall on the island with fresh soft white snow blanketing rooftops, castle walls, plazas, and trees, illuminated by cool daylight.",
    "foggy": "Serene misty morning mood with subtle wispy haze tucked tightly between the lower buildings on the island slab only (never spilling outside the island silhouette).",
    "night": "Peaceful starry night lighting on the island architecture with cool silver-blue moonlight grazing the stone facades and roofs, plus warm golden lights glowing inside windows and street lanterns.",
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
            f"1:1 square aspect ratio, 45-degree top-down isometric miniature 3D cartoon diorama of {place_ctx}, Turkey, "
            f"featuring its iconic landmark **{subject}** as the unmistakable centerpiece. "
            "Composition: a compact, floating diamond-oriented square cutaway terrain island STRICTLY CENTERED inside the 1:1 frame, "
            "with a generous 15% completely flat pure solid #FFFFFF white margin on ALL FOUR edges (top, bottom, left, right) "
            "so the entire landmark spire and the entire floating island base sit cleanly inside with zero edge touching or clipping. "
            "Show realistic, tactile PBR materials (carved stone masonry, terracotta roof tiles, cobblestone, trees/water where fitting) "
            "with crisp, well-defined silhouette edges along the cleanly sliced earth-and-stone island base. "
            f"Lighting & surface mood on the island: {atmo_desc} "
            "CRITICAL ISOLATION RULES: Place ONLY the floating 3D island on a 100% FLAT, UNIFORM, PURE SOLID #FFFFFF WHITE studio background. "
            "ABSOLUTELY NO cast shadow, NO drop shadow, NO ambient floor shadow beneath the island, NO ground plane, NO sky gradient, "
            "NO floating clouds outside the island, and NO mist or fog extending past the island silhouette. "
            "STRICT RULES: full-bleed 1:1 composition with NO frames or borders; "
            "ABSOLUTELY NO text, NO city names, NO letters, NO numbers, NO weather icons, NO UI panels, and NO watermarks anywhere in the image."
        )

    def _cache_filename(self, province: str, district: Optional[str], landmark: Optional[str], atmosphere: str) -> str:
        atmo_safe = atmosphere if atmosphere in ATMOSPHERE_DESCRIPTIONS else "partly"
        key = landmark or (f"{province}_{district}" if district and district != "__MERKEZ__" else province)
        return f"cut_{_slugify(key)}_{atmo_safe}.webp"

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
    def _border_floodfill(cand: np.ndarray) -> np.ndarray:
        """Exact 4-connected floodfill seeded from all 4 outer borders via vectorized directional sweeps."""
        h, w = cand.shape
        bg = np.zeros((h, w), dtype=bool)
        bg[0, :] = cand[0, :]
        bg[-1, :] = cand[-1, :]
        bg[:, 0] = cand[:, 0]
        bg[:, -1] = cand[:, -1]
        while True:
            prev_count = int(bg.sum())
            for y in range(1, h):
                bg[y] |= bg[y - 1] & cand[y]
            for y in range(h - 2, -1, -1):
                bg[y] |= bg[y + 1] & cand[y]
            for x in range(1, w):
                bg[:, x] |= bg[:, x - 1] & cand[:, x]
            for x in range(w - 2, -1, -1):
                bg[:, x] |= bg[:, x + 1] & cand[:, x]
            if int(bg.sum()) == prev_count:
                break
        return bg

    @staticmethod
    def remove_solid_background(img: Image.Image) -> Image.Image:
        """
        Converts a solid uniform outer background into clean RGBA transparency using
        outer-border floodfill + 2px silhouette matting + color decontamination,
        then centers the island in a padded square canvas.
        """
        rgba = img.convert("RGBA")
        arr = np.asarray(rgba, dtype=np.float32)
        rgb = arr[:, :, :3].copy()
        h, w = rgb.shape[:2]
        if h < 16 or w < 16:
            return img

        strip_top = rgb[:4, :, :].reshape(-1, 3)
        strip_bot = rgb[-4:, :, :].reshape(-1, 3)
        strip_left = rgb[4:-4, :4, :].reshape(-1, 3)
        strip_right = rgb[4:-4, -4:, :].reshape(-1, 3)
        perim = np.concatenate([strip_top, strip_bot, strip_left, strip_right], axis=0)
        bg_color = np.median(perim, axis=0)

        perim_dist = np.linalg.norm(perim - bg_color, axis=1)
        if float((perim_dist <= 30.0).mean()) < 0.85:
            return img

        dist = np.linalg.norm(rgb - bg_color, axis=2)
        outer_bg = DioramaGenerator._border_floodfill(dist <= 28.0)

        outer_u8 = Image.fromarray((outer_bg.astype(np.uint8) * 255), mode="L")
        dilated = np.asarray(outer_u8.filter(ImageFilter.MaxFilter(5))) > 0
        border_band = dilated & ~outer_bg

        alpha = np.ones((h, w), dtype=np.float32)
        alpha[outer_bg] = 0.0
        alpha[border_band] = np.clip((dist[border_band] - 14.0) / (56.0 - 14.0), 0.0, 1.0)

        decontam = border_band & (alpha > 0.02) & (alpha < 0.98)
        if np.any(decontam):
            a_exp = alpha[decontam, None]
            rgb[decontam] = np.clip(
                (rgb[decontam] - (1.0 - a_exp) * bg_color[None, :]) / np.maximum(a_exp, 0.2),
                0.0,
                255.0,
            )
        rgb[alpha == 0.0] = 0.0

        opaque_frac = float((alpha > 0.5).mean())
        if not (0.08 <= opaque_frac <= 0.90):
            return img

        fg_ys, fg_xs = np.where(alpha > 0.05)
        if len(fg_ys) == 0:
            return img

        y0, y1 = int(fg_ys.min()), int(fg_ys.max()) + 1
        x0, x1 = int(fg_xs.min()), int(fg_xs.max()) + 1

        out_arr = np.zeros((h, w, 4), dtype=np.uint8)
        out_arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
        out_arr[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
        cut_img = Image.fromarray(out_arr, mode="RGBA").crop((x0, y0, x1, y1))

        cw, ch = cut_img.size
        canvas_size = max(1, int(round(max(cw, ch) / 0.86)))
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        canvas.paste(cut_img, ((canvas_size - cw) // 2, (canvas_size - ch) // 2), cut_img)
        return canvas

    @staticmethod
    def _to_optimized_webp(raw_bytes: bytes, max_width: int = 800, quality: int = 88) -> bytes:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img = DioramaGenerator.remove_solid_background(img)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            if img.width > max_width or (img.width == img.height and img.width != max_width):
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
                    "aspect_ratio": "1:1",
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
