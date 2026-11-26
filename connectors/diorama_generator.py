import os
import re
import io
import json
import base64
import logging
from typing import Optional, Tuple

from PIL import Image, ImageFilter
import numpy as np

logger = logging.getLogger("diorama")


def _slugify(value: str) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ ", "cgiosucgiosu_")
    cleaned = value.translate(tr_map).lower()
    return re.sub(r"[^a-z0-9_]+", "_", cleaned).strip("_")


class DioramaGenerator:
    """
    2-Layer Economic 3D Isometric Miniature Diorama Generator:
    - Layer 1: Uses curated province/district landmarks when provided by the catalog.
    - Layer 2: For any unmapped Turkish district (900+ districts), runs a one-time
      lightweight `gemini-3.5-flash-lite` landmark discovery call and caches the result.
    - Economic mode: Generates ONE shadowless, true-transparent (RGBA WebP) daytime
      isometric island per province/district (`eco_<slug>.webp`) and caches it locally + GCS.
    """

    def __init__(self):
        self.model = "gemini-nano-banana-2.1"
        self.discovery_model = "gemini-3.5-flash-lite"
        self.local_cache_dir = os.environ.get("DIORAMA_CACHE_DIR", "/tmp/diorama_cache")
        if os.name == "nt" and self.local_cache_dir == "/tmp/diorama_cache":
            self.local_cache_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "dioramas_cache")
        os.makedirs(self.local_cache_dir, exist_ok=True)
        self.gcs_bucket_name = os.environ.get("DIORAMA_GCS_BUCKET", "").strip()
        self.last_error: Optional[str] = None
        self._landmark_cache_path = os.path.join(self.local_cache_dir, "discovered_landmarks.json")
        self._landmark_cache: dict = self._load_landmark_cache()

    def is_enabled(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    def _load_landmark_cache(self) -> dict:
        if os.path.exists(self._landmark_cache_path):
            try:
                with open(self._landmark_cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        gcs_bytes = self._read_gcs("discovered_landmarks.json")
        if gcs_bytes:
            try:
                data = json.loads(gcs_bytes.decode("utf-8"))
                if isinstance(data, dict):
                    with open(self._landmark_cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return data
            except Exception:
                pass
        return {}

    def _save_landmark_cache(self) -> None:
        try:
            payload = json.dumps(self._landmark_cache, ensure_ascii=False, indent=2).encode("utf-8")
            with open(self._landmark_cache_path, "wb") as f:
                f.write(payload)
            self._write_gcs("discovered_landmarks.json", payload, content_type="application/json")
        except Exception as e:
            logger.warning("Failed to persist landmark discovery cache: %s", e)

    def discover_district_landmark(self, client, province: str, district: str) -> dict:
        """
        Layer 2: One-time lightweight Gemini 3.5 Flash-Lite lookup for any Turkish district
        not present in the curated catalog. Cached permanently on disk & GCS.
        """
        cache_key = f"{province}::{district}"
        if cache_key in self._landmark_cache:
            return self._landmark_cache[cache_key]

        fallback = {
            "label": f"{district} ({province})",
            "visual": f"characteristic historic town square, local architecture, and natural landscape of {district} district in {province}, Turkey",
        }
        try:
            prompt = (
                f"Identify the single most recognizable, authentic landmark, historic structure, or iconic natural feature "
                f"of the district '{district}' in '{province}' province, Turkey. "
                "If the district has no single famous monument, describe its most distinctive local square, mosque, bridge, "
                "coastal marina, lake, castle, thermal bath, pine forest, or regional architecture. "
                "Reply ONLY with valid JSON (no markdown fences) with exactly two keys:\n"
                '{"label": "Short Turkish title (max 5 words)", '
                '"visual": "Concise English architectural and landscape visual description (15-25 words) suitable for a 3D isometric miniature diorama"}'
            )
            interaction = client.interactions.create(
                model=self.discovery_model,
                input=prompt,
                store=False,
            )
            raw_text = (getattr(interaction, "output_text", None) or "").strip()
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                label = str(parsed.get("label") or "").strip()
                visual = str(parsed.get("visual") or "").strip()
                if label and visual:
                    entry = {"label": label[:72], "visual": visual[:240]}
                    self._landmark_cache[cache_key] = entry
                    self._save_landmark_cache()
                    return entry
        except Exception as e:
            logger.warning("Layer-2 landmark discovery failed for %s: %s", cache_key, e)

        self._landmark_cache[cache_key] = fallback
        self._save_landmark_cache()
        return fallback

    def build_prompt(
        self,
        province: str,
        district: Optional[str],
        landmark: Optional[str],
        visual_hint: Optional[str] = None,
    ) -> str:
        is_dist = bool(district and district != "__MERKEZ__")
        subject = landmark or (f"{district}, {province}" if is_dist else province)
        place_ctx = f"{district} ({province})" if is_dist else province
        visual_clause = f" Visual details to highlight: {visual_hint}." if visual_hint else ""

        return (
            f"1:1 square aspect ratio, 45-degree top-down isometric miniature 3D cartoon diorama of {place_ctx}, Turkey, "
            f"featuring its iconic local landmark **{subject}** as the unmistakable centerpiece.{visual_clause} "
            "Composition: a compact, floating diamond-oriented square cutaway terrain island STRICTLY CENTERED inside the 1:1 frame, "
            "with a generous 15% completely flat pure solid #FFFFFF white margin on ALL FOUR edges (top, bottom, left, right) "
            "so the entire landmark spire and the entire floating island base sit cleanly inside with zero edge touching or clipping. "
            "Show realistic, tactile PBR materials (carved stone masonry, terracotta roof tiles, cobblestone, trees/water where fitting) "
            "with crisp, well-defined silhouette edges along the cleanly sliced earth-and-stone island base. "
            "Lighting: balanced, bright, crisp studio daylight illuminating the architecture and landscape cleanly. "
            "CRITICAL ISOLATION RULES: Place ONLY the floating 3D island on a 100% FLAT, UNIFORM, PURE SOLID #FFFFFF WHITE studio background. "
            "ABSOLUTELY NO cast shadow, NO drop shadow, NO ambient floor shadow beneath the island, NO ground plane, NO sky gradient, "
            "NO floating clouds outside the island, and NO mist or fog extending past the island silhouette. "
            "STRICT RULES: full-bleed 1:1 composition with NO frames or borders; "
            "ABSOLUTELY NO text, NO city names, NO letters, NO numbers, NO weather icons, NO UI panels, and NO watermarks anywhere in the image."
        )

    def _cache_filename(self, province: str, district: Optional[str], landmark: Optional[str] = None) -> str:
        is_dist = bool(district and district != "__MERKEZ__")
        key = f"{province}_{district}" if is_dist else province
        return f"eco_{_slugify(key)}.webp"

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

    def _write_gcs(self, blob_name: str, data: bytes, content_type: str = "image/webp") -> None:
        if not self.gcs_bucket_name:
            return
        try:
            from google.cloud import storage
            client = storage.Client()
            blob = client.bucket(self.gcs_bucket_name).blob(f"dioramas/{blob_name}")
            blob.upload_from_string(data, content_type=content_type)
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
        atmosphere: str = "day",
    ) -> Tuple[Optional[bytes], str]:
        is_dist = bool(district and district != "__MERKEZ__")
        filename = self._cache_filename(province, district, landmark)
        local_path = os.path.join(self.local_cache_dir, filename)

        cache_key = f"{province}::{district}" if is_dist else f"{province}::__MERKEZ__"
        cached_meta = self._landmark_cache.get(cache_key)
        resolved_label = (
            (landmark or "").strip()
            or (cached_meta.get("label") if isinstance(cached_meta, dict) else "")
            or (f"{district} ({province})" if is_dist else province)
        )

        # 1. Local disk cache (1 economic island per province/district)
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read(), resolved_label

        # 2. GCS persistent cache
        gcs_bytes = self._read_gcs(filename)
        if gcs_bytes:
            with open(local_path, "wb") as f:
                f.write(gcs_bytes)
            return gcs_bytes, resolved_label

        # 3. Generate live via Gemini (Layer 2 discovery if unmapped district -> Nano Banana 2.1)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            self.last_error = "GEMINI_API_KEY ortam değişkeni tanımlı değil."
            return None, resolved_label

        try:
            from google import genai
            client = genai.Client(api_key=api_key)

            visual_hint = None
            clean_landmark = (landmark or "").strip()
            if not clean_landmark and is_dist:
                discovered = self.discover_district_landmark(client, province, district)
                clean_landmark = discovered.get("label") or resolved_label
                visual_hint = discovered.get("visual")
                resolved_label = clean_landmark

            prompt = self.build_prompt(province, district, clean_landmark or None, visual_hint=visual_hint)
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
                return None, resolved_label

            raw_bytes = base64.b64decode(interaction.output_image.data)
            webp_bytes = self._to_optimized_webp(raw_bytes)

            with open(local_path, "wb") as f:
                f.write(webp_bytes)
            self._write_gcs(filename, webp_bytes)
            self.last_error = None
            return webp_bytes, resolved_label
        except Exception as e:
            self.last_error = str(e)
            logger.exception("Gemini diorama generation failed: %s", e)
            return None, resolved_label
