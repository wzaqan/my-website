import cv2
import numpy as np
import logging
import os
import json
import time

def _get_app_dir() -> str:
    """يُرجع مجلد EXE في PyInstaller أو مجلد السكريبت في وضع التطوير."""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_app_dir()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("output.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("OMREngine")

A4_RATIO = 11.69 / 8.27  # نسبة A4 الثابتة


class OMREngine:
    """
    محرك OMR عام — يعمل مع أي نموذج وأي ماسح.
    الإحداثيات في القالب = نسب مئوية (rx, ry) من أبعاد صورة المعايرة.
    المحرك يحوّلها لبكسلات بعد معرفة أبعاد الصورة الفعلية.
    يدعم أيضاً القوالب القديمة (إحداثيات مطلقة) للتوافق.
    """

    # ── ثوابت قواعد القرار — تُطبَّق على جميع الاختبارات ──
    NOISE_THRESHOLD_ABS = 8             # حد أدنى مطلق لـ (best-second) بوحدة darkness
    Z_BEST_MIN          = 1.0           # z-score الفقاعة الأفضل — أقل = لا تظليل
    Z_SECOND_MAX        = 1.0           # z-score الثانية — فوقه = مزدوجة
    GAP_PCT_MIN         = 0.15          # نسبة الفرق عند التضليل المزدوج — فوقه = DUPLICATE

    def __init__(self):
        self.pixel_threshold = 0.12
        self.debug_mode      = False   # وضع التشخيص — معطّل افتراضياً لأقصى سرعة
        self.paper_type      = "color" # نوع الورق: "color"=ملون | "bw"=أبيض وأسود
        if os.path.exists(os.path.join(BASE_DIR, "settings.json")):
            try:
                with open(os.path.join(BASE_DIR, "settings.json"), "r", encoding="utf-8") as f:
                    s = json.load(f)
                    self.pixel_threshold = float(s.get("mark_threshold", 12)) / 100.0
                    self.debug_mode      = bool(s.get("debug_mode", False))
                    self.paper_type      = s.get("paper_type", "color")
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
        logger.info(f"OMREngine جاهز. (عتبة: {self.pixel_threshold*100:.1f}% | ورق: {self.paper_type})")

    # ═══════════════════════════════════════════════
    # تحميل الصورة
    # ═══════════════════════════════════════════════
    def _load_image(self, src):
        if isinstance(src, str):
            img = cv2.imread(src)
            if img is None:
                logger.error(f"تعذّر قراءة: {src}")
            return img
        return src

    # ═══════════════════════════════════════════════
    # تحضير الصورة
    # ═══════════════════════════════════════════════
    def preprocess_image(self, image, hsv_range=None):
        image = self.smart_crop_whitespace(image)
        image = self._crop_page_region(image)
        # إذا لم يُمرَّر hsv_range → اكتشف لون الخلفية تلقائياً
        # حتى يحصل deskew (شريط التوقيت) على dropout صحيح للورق الملون.
        if hsv_range is None:
            hsv_range = self.detect_background_color(image)
        image = self.deskew_image(image, hsv_range=hsv_range)
        return image

    def get_warped_image(self, src, hsv_range=None):
        image = self._load_image(src)
        if image is None: return None
        return self.preprocess_image(image, hsv_range=hsv_range)

    def pre_calibrate_master_sheet(self, src, hsv_range=None):
        image = self._load_image(src)
        if image is None: return None
        return self.preprocess_image(image, hsv_range=hsv_range)

    # ═══════════════════════════════════════════════
    # قص الفراغ والحواف
    # ═══════════════════════════════════════════════
    def smart_crop_whitespace(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        a4_h = int(w * A4_RATIO)
        crop_y = min(a4_h, h)
        if crop_y < h:
            logger.info(f"smart_crop: {w}×{h} → {w}×{crop_y}")
            return image[:crop_y, :]
        return image

    def _find_page_contour(self, image):
        """
        البحث عن أكبر كنتور يمثل حدود الورقة.
        يحاول عدة عتبات بالترتيب — مهم للماسحات ذات الخلفيات البيضاء
        التي لا تعطي تبايناً واضحاً مع الورقة:
          1. Otsu التلقائي (يعمل مع معظم الخلفيات الداكنة/المتوسطة)
          2. عتبة منخفضة 240 (يلتقط حواف الورقة على خلفية بيضاء قليلة الرمادي)
          3. عتبة 200 الافتراضية (سابقاً 180 — رُفعت لتشمل ورق فاتح الطباعة)
        يُعيد أول كنتور صالح ≥ 25% من مساحة الصورة، وإلا None.
        """
        gray    = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        min_area = image.shape[0] * image.shape[1] * 0.25

        for method in ("otsu", "low", "fixed"):
            if method == "otsu":
                _, binary = cv2.threshold(blurred, 0, 255,
                                          cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            elif method == "low":
                _, binary = cv2.threshold(blurred, 240, 255, cv2.THRESH_BINARY)
            else:
                _, binary = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)

            cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                continue
            valid = [c for c in cnts if cv2.contourArea(c) >= min_area]
            if valid:
                return max(valid, key=cv2.contourArea)
        return None

    def _crop_page_region(self, image):
        contour = self._find_page_contour(image)
        if contour is not None:
            x, y, w, h = cv2.boundingRect(contour)
            m = 2
            image = image[max(0,y-m):min(image.shape[0],y+h+m),
                          max(0,x-m):min(image.shape[1],x+w+m)]
        return image

    # ═══════════════════════════════════════════════
    # تصحيح الميلان
    # ═══════════════════════════════════════════════
    def _normalize_line_angle(self, angle):
        """
        تطبيع زاوية خط إلى نطاق [-45, 45] درجة.
        الخطوط الأطول من العمودية تُعاد كزاوية من الأفق (والعكس بالعكس)
        لأن الورقة قد تكون أفقية أو عمودية — كلتاهما "غير مائلة".
        """
        # حصر في (-90, 90]
        while angle <= -90: angle += 180
        while angle >   90: angle -= 180
        # تحويل أي زاوية > 45° إلى مقابلها داخل ±45° (الإسقاط الأقصر)
        if   angle >  45: angle -= 90
        elif angle < -45: angle += 90
        return float(angle)

    def _estimate_skew_from_page_border(self, image):
        """
        تقدير زاوية الميل من حدود الورقة باستخدام minAreaRect.
        تستخدم زاوية OpenCV الرسمية لـ minAreaRect (وليس تحليل أطول ضلع)،
        ثم تطبَّع إلى ±45°. هذا أكثر ثباتاً من التحليل اليدوي للأركان
        الذي قد يقلب الإشارة قرب الزوايا الحادة (مشكلة Afgen).
        """
        contour = self._find_page_contour(image)
        if contour is None or len(contour) < 5:
            return None
        rect = cv2.minAreaRect(contour)
        # rect = ((cx, cy), (w, h), angle_deg) ؛ angle ∈ (-90, 0]
        (cx, cy), (rw, rh), angle = rect
        # OpenCV ≥ 4.5: angle ∈ [0, 90) وهي زاوية الضلع الأول
        # العمل الموحَّد: نضع زاوية الضلع الأطول (طول الورقة)
        if rw < rh:
            angle += 90.0
        # الآن angle ≈ 0 لورقة قائمة، وقد تكون قرب 90° إذا كانت الورقة أفقية
        angle = self._normalize_line_angle(angle)
        return 0.0 if abs(angle) < 0.05 else float(angle)

    def _estimate_skew_from_timing(self, image, hsv_range=None):
        """
        يستخرج زاوية الميل من شريط التوقيت — يعمل مع كلا المحورين:
          • عمودي (يمين/يسار): يفيت X كدالة في Y → arctan(dx/dy).
          • أفقي  (أعلى/أسفل): يفيت Y كدالة في X → arctan(dy/dx) بإشارة موجبة.
        لا يعتمد على لون خلفية الماسح.
        hsv_range: نطاق HSV المكتشف من القالب (اختياري) — يُمرَّر لـ hsv_color_dropout.
        """
        try:
            thresh   = self.hsv_color_dropout(image, hsv_range=hsv_range,
                                              paper_type=self.paper_type)
            marks_xy, direction, axis = self.detect_timing_track(thresh)
            if len(marks_xy) < 4:
                return None

            xs = np.array([m[0] for m in marks_xy], dtype=np.float64)
            ys = np.array([m[1] for m in marks_xy], dtype=np.float64)

            if axis == "vertical":
                # شريط عمودي: Y يتغير كثيراً، X يتغير قليلاً
                # نفيت X = slope * Y + b ؛ slope = dx/dy = tan(زاوية الميل من العمودي)
                if float(np.ptp(ys)) < 1e-6:
                    return None
                coeffs = np.polyfit(ys, xs, 1)
                slope  = float(coeffs[0])
                angle  = float(np.degrees(np.arctan(slope)))
            else:
                # شريط أفقي: X يتغير كثيراً، Y يتغير قليلاً
                # نفيت Y = slope * X + b ؛ slope = dy/dx
                # زاوية ميل خط أفقي تساوي arctan(dy/dx) بنفس الإشارة
                # لكن دوران cv2 يستخدم -angle، فنُعيد إشارة مطابقة لاتفاقية العمودي
                if float(np.ptp(xs)) < 1e-6:
                    return None
                coeffs = np.polyfit(xs, ys, 1)
                slope  = float(coeffs[0])
                angle  = float(np.degrees(np.arctan(slope)))

            angle = self._normalize_line_angle(angle)
            logger.info(f" Timing skew [{axis}|{direction}]: "
                        f"slope={slope:.5f}  angle={angle:.3f}°")
            return angle if abs(angle) >= 0.05 else 0.0
        except Exception as e:
            logger.warning(f"_estimate_skew_from_timing: {e}")
            return None

    def deskew_image(self, image, hsv_range=None):
        """
        تصحيح الميل بخطتين:
          1. حواف الورقة  (سريعة، تفشل مع خلفيات بعض الماسحات)
          2. شريط التوقيت (احتياطية، دقيقة دائماً)
        hsv_range: نطاق HSV المكتشف من القالب — يُمَرَّر للخطة الاحتياطية.
        """
        angle = self._estimate_skew_from_page_border(image)

        if angle is None or abs(angle) < 0.1:
            # الخطة الاحتياطية: شريط التوقيت
            angle_t = self._estimate_skew_from_timing(image, hsv_range=hsv_range)
            if angle_t is not None and abs(angle_t) >= 0.1:
                logger.info(f" Deskew fallback  timing track: {angle_t:.2f}°")
                angle = angle_t
            else:
                return image   # لا ميل مكتشف

        logger.info(f" الميلان: {angle:.2f}°")
        h, w = image.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), -angle, 1.0)
        return cv2.warpAffine(image, M, (w, h),
                              flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(255, 255, 255))

    def get_skew_angle(self, src):
        image = self._load_image(src)
        if image is None: return 0.0
        image = self.smart_crop_whitespace(image)
        image = self._crop_page_region(image)
        angle = self._estimate_skew_from_page_border(image)
        return float(angle) if angle is not None else 0.0

    # ═══════════════════════════════════════════════
    # تحويل الإحداثيات — النظام الجديد
    # ═══════════════════════════════════════════════
    def abs_to_rel(self, x, y, w, h, img_w, img_h):
        """مطلق → نسبة مئوية (للمعايرة)."""
        return {
            "rx": round(x / img_w, 6), "ry": round(y / img_h, 6),
            "rw": round(w / img_w, 6), "rh": round(h / img_h, 6),
        }

    def _bx(self, b, img_w, cal_w):
        """X بالبكسل — يستخدم النسبة rx إذا وُجدت، وإلا يحوّل x المطلق."""
        if "rx" in b: return b["rx"] * img_w
        return b.get("x", 0) * img_w / cal_w

    def _by(self, b, img_h, cal_h):
        """Y بالبكسل — يستخدم النسبة ry إذا وُجدت، وإلا يحوّل y المطلق."""
        if "ry" in b: return b["ry"] * img_h
        return b.get("y", 0) * img_h / cal_h

    def _bsize(self, b, img_w, img_h, cal_w, cal_h):
        """(w, h) بالبكسل."""
        if "rw" in b:
            return b["rw"] * img_w, b["rh"] * img_h
        return b.get("w", 20) * img_w / cal_w, b.get("h", 20) * img_h / cal_h

    # ═══════════════════════════════════════════════
    # كشف لون خلفية الورقة (المصدر الموحَّد)
    # ═══════════════════════════════════════════════
    def detect_background_color(self, image):
        """
        يكتشف لون خلفية الورقة تلقائياً ويُعيد نطاق HSV.
        المصدر الموحَّد لكشف اللون — يستخدمه:
          • preprocess_image للحصول على dropout صحيح أثناء deskew.
          • _update_template_preview في الواجهة.
          • omr_calibrator أثناء المعايرة.

        استراتيجية أخذ العينات:
          1. منطقة الوسط (15%-85% أفقياً، 10%-90% عمودياً) — تتجنّب الحواف
             حيث يوجد شريط التوقيت وحدود الورقة.
          2. شرائح أفقية متناوبة لالتقاط الصفوف الملونة بين الأسئلة.
          3. استبعاد البكسلات الداكنة (S<40 أو V<50) والبيضاء/الرمادية الفاتحة
             (V>230) لعزل لون الورق فقط.

        يُعيد قاموس فيه h_low/h_high/s_low/s_high/v_low/v_high/hue_center/detected.
        إذا لم يُكتشف لون واضح → detected=False (يستخدم المسار الافتراضي).
        """
        if image is None or image.size == 0:
            return {"h_low": 0, "h_high": 18, "s_low": 30, "s_high": 255,
                    "v_low": 30, "v_high": 255, "hue_center": 0,
                    "detected": False}

        h, w = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        x0, x1 = int(w * 0.15), int(w * 0.85)
        y0, y1 = int(h * 0.10), int(h * 0.90)
        if x1 <= x0 or y1 <= y0:
            return {"h_low": 0, "h_high": 18, "s_low": 30, "s_high": 255,
                    "v_low": 30, "v_high": 255, "hue_center": 0,
                    "detected": False}

        center_region = hsv[y0:y1, x0:x1]

        stripe_height = max(int((y1 - y0) * 0.05), 10)
        stripes = []
        y = y0
        while y + stripe_height <= y1:
            stripes.append(hsv[y: y + stripe_height, x0:x1])
            y += stripe_height * 2

        all_patches = [center_region] + stripes
        sample = np.concatenate([p.reshape(-1, 3) for p in all_patches], axis=0)

        s_vals = sample[:, 1].astype(np.float32)
        v_vals = sample[:, 2].astype(np.float32)
        colored_mask = (s_vals >= 40) & (v_vals >= 50) & (v_vals <= 230)
        colored = sample[colored_mask]

        if len(colored) < 50:
            logger.info("detect_background_color: ورقة بيضاء/غير ملوَّنة")
            return {"h_low": 0, "h_high": 18, "s_low": 30, "s_high": 255,
                    "v_low": 30, "v_high": 255, "hue_center": 0,
                    "detected": False}

        h_vals = colored[:, 0].astype(np.int32)
        hist = np.bincount(h_vals, minlength=180).astype(np.float32)
        kernel_size = 7
        kernel = np.ones(kernel_size) / kernel_size
        hist_padded = np.concatenate([hist[-kernel_size//2:], hist,
                                       hist[:kernel_size//2]])
        hist_smooth = np.convolve(hist_padded, kernel, mode='valid')[:180]
        peak_h = int(np.argmax(hist_smooth))

        H_MARGIN = 22
        h_low  = (peak_h - H_MARGIN) % 180
        h_high = (peak_h + H_MARGIN) % 180

        if h_low <= h_high:
            in_range = colored[(h_vals >= h_low) & (h_vals <= h_high)]
        else:
            in_range = colored[(h_vals >= h_low) | (h_vals <= h_high)]

        if len(in_range) >= 10:
            s_low  = max(0,   int(np.percentile(in_range[:, 1], 10)) - 20)
            s_high = min(255, int(np.percentile(in_range[:, 1], 90)) + 20)
            v_low  = max(0,   int(np.percentile(in_range[:, 2], 10)) - 20)
            v_high = min(255, int(np.percentile(in_range[:, 2], 90)) + 20)
        else:
            s_low, s_high = 30, 255
            v_low, v_high = 30, 255

        logger.info(f"detect_background_color: peak_h={peak_h} "
                    f"H=[{h_low},{h_high}] S=[{s_low},{s_high}] V=[{v_low},{v_high}]")

        return {
            "h_low":      h_low,
            "h_high":     h_high,
            "s_low":      s_low,
            "s_high":     s_high,
            "v_low":      v_low,
            "v_high":     v_high,
            "hue_center": peak_h,
            "detected":   True,
        }

    # ═══════════════════════════════════════════════
    # HSV color dropout + thresh
    # ═══════════════════════════════════════════════
    def hsv_color_dropout(self, image, hsv_range=None, paper_type=None):
        """
        إسقاط لون خلفية الورقة باستخدام نطاق HSV.

        hsv_range:  قاموس يحتوي على h_low/h_high/s_low/s_high/v_low/v_high
                    يُقرأ من حقل background_hsv_range في ملف القالب JSON.
                    إذا لم يُعطَ → يستخدم النطاق الافتراضي (وردي/أحمر).
        paper_type: "color" = ورق ملون  (الافتراضي — يستخدم مسار HSV كاملاً)
                    "bw"    = ورق أبيض وأسود — يتخطى HSV ويذهب مباشرة للـ threshold
                    إذا لم يُمرَّر → يُستخدم self.paper_type
        """
        # تحديد نوع الورق — المُمرَّر يأخذ الأولوية ثم self.paper_type
        _paper = paper_type if paper_type is not None else getattr(self, 'paper_type', 'color')

        # ── مسار الورق الأبيض والأسود — تخطي HSV كلياً ──────────────────
        if _paper == "bw":
            gray   = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            # blockSize=51 أصغر من 99 لأنه لا يوجد لون يُزعج الـ threshold
            # C=15 أعلى من 10 لتجاهل ظلال الطي والضوضاء الخفيفة في الورق الأبيض
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                51, 15
            )
            kernel = np.ones((2, 2), np.uint8)
            return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # ── مسار الورق الملون — HSV dropout ثم threshold ─────────────────
        # تسريع: تصغير الصورة 50% للمعالجة ثم تكبير الـ thresh للحجم الأصلي
        # الإحداثيات لا تتأثر لأن الـ thresh يعود لحجمه الأصلي قبل الخروج
        orig_h, orig_w = image.shape[:2]
        small = cv2.resize(image, (orig_w // 2, orig_h // 2),
                           interpolation=cv2.INTER_AREA)

        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        if hsv_range and hsv_range.get("detected", False):
            h_low  = int(hsv_range["h_low"])
            h_high = int(hsv_range["h_high"])
            s_low  = int(hsv_range.get("s_low", 25))
            s_high = int(hsv_range.get("s_high", 255))
            v_low  = int(hsv_range.get("v_low", 30))
            v_high = int(hsv_range.get("v_high", 255))

            lower1 = np.array([h_low,  s_low, v_low])
            upper1 = np.array([h_high, s_high, v_high])

            if h_low <= h_high:
                # نطاق عادي لا يتجاوز 179
                mask = cv2.inRange(hsv, lower1, upper1)
            else:
                # لون يلتف حول 180/0 (مثل الأحمر)
                mask = cv2.bitwise_or(
                    cv2.inRange(hsv, np.array([h_low,  s_low, v_low]),
                                     np.array([179,    s_high, v_high])),
                    cv2.inRange(hsv, np.array([0,      s_low, v_low]),
                                     np.array([h_high, s_high, v_high]))
                )
        else:
            # ── النطاق الافتراضي (وردي/أحمر) — للتوافق مع القوالب القديمة ──
            # s_low=25: يشمل الألوان الفاتحة (S=25+) ويتجنب ضوضاء السكانر (S<15)
            # هامش الأمان: 15 وحدة بين الضوضاء (S≈10) والألوان الحقيقية (S≈25+)
            mask = cv2.bitwise_or(
                cv2.inRange(hsv, np.array([0,   25, 30]), np.array([18,  255, 255])),
                cv2.inRange(hsv, np.array([158,  25, 30]), np.array([180, 255, 255]))
            )

        mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)

        dropped = small.copy()
        dropped[mask > 0] = [255, 255, 255]

        gray   = cv2.cvtColor(dropped, cv2.COLOR_BGR2GRAY)
        # blockSize=51 يعادل ~102 على الصورة الأصلية — قريب من الـ 99 السابق
        binary = cv2.adaptiveThreshold(gray, 255,
                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                     cv2.THRESH_BINARY_INV, 51, 10)
        kernel = np.ones((2, 2), np.uint8)
        binary_small = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # تكبير الـ thresh للحجم الأصلي قبل الخروج من الدالة
        return cv2.resize(binary_small, (orig_w, orig_h),
                          interpolation=cv2.INTER_NEAREST)

    # ═══════════════════════════════════════════════════════════════
    # شريط التوقيت الديناميكي + map_y / map_x
    # ═══════════════════════════════════════════════════════════════

    def _scan_margin(self, thresh, direction):
        """
        يبحث عن شريط التوقيت في هامش واحد بخوارزمية عامة:
        - يبدأ من هامش ضيق جداً (3%) ويوسّع تدريجياً
        - يتوقف عند أول هامش يعطي ≥4 علامات بـ X_std < X_TIGHT_THRESHOLD
        - X_std الصغير = علامات في عمود رأسي واحد = شريط توقيت حقيقي
        - X_std الكبير = دوائر أسئلة منتشرة = نتجاهل ونضيّق
        هذا المنطق عام لأي ورقة بغض النظر عن موقع الأسئلة.
        """
        h, w = thresh.shape

        if direction in ("right", "left"):
            primary_axis = "y"
        elif direction in ("top", "bottom"):
            primary_axis = "x"
        else:
            return []

        # ── الحد الأقصى لـ X_std لاعتبار العلامات في عمود واحد ──
        # 1.5% من بُعد الصورة العمودي — ثابت نسبي يعمل مع أي DPI
        X_TIGHT = w * 0.015 if primary_axis == "y" else h * 0.015

        # ── توسيع تدريجي للهامش وجمع كل النتائج الصالحة ──
        # ─ ملاحظة على المنطق ─
        # الإصدار السابق كان يُرجع عند أول margin يعطي ≥4 علامات،
        # لكن الهوامش الضيقة جداً (3%) قد تقطع العلامة وتترك حافة 9px
        # تمر بفلتر الشكل صدفة (Afgen: 4 حواف بدل 52 علامة كاملة).
        # الآن نجرّب كل القيم ونحتفظ بأطول سلسلة منتظمة — سلوك ثابت
        # للحالات السهلة ومنقذ للحالات التي يقطع فيها الهامش الضيق العلامات.
        best_result = []
        best_x_std = 0.0
        best_margin = 0
        for margin_pct in [3, 5, 7, 10]:

            margin = margin_pct / 100.0

            if direction == "right":
                roi_x = int(w * (1.0 - margin))
                roi   = thresh[:, roi_x:]
                off   = (roi_x, 0)
            elif direction == "left":
                roi   = thresh[:, :int(w * margin)]
                off   = (0, 0)
            elif direction == "top":
                roi   = thresh[:int(h * margin), :]
                off   = (0, 0)
            else:  # bottom
                roi_y = int(h * (1.0 - margin))
                roi   = thresh[roi_y:, :]
                off   = (0, roi_y)

            rh, rw = roi.shape

            # جمع المرشحين بفلتر شكل مرن
            # ─ ملاحظة على الفلاتر ─
            # العتبات السابقة (ratio≥1.5, ch<rh*0.025) كانت صارمة جداً وترفض:
            #   • علامات شبه مربعة (Afgen ≈ 1.0-1.3)
            #   • علامات كبيرة على المسح عالي الدقة (600 DPI)
            # الفلاتر الجديدة تسمح بـ:
            #   • ratio ≥ 1.1 (مستطيلات قليلة الميل)
            #   • ارتفاع حتى 6% من ROI (يستوعب 600 DPI)
            # ثم يأتي فحص X_std (المُحكَم) لفصل العلامات الحقيقية عن الضوضاء
            # وأي علامات منتشرة (دوائر أسئلة) تُرفض بسبب التشتت العمودي.
            candidates = []
            cnts, _ = cv2.findContours(roi.copy(), cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                x, y, cw, ch = cv2.boundingRect(c)
                if cw * ch < 30:
                    continue
                ratio = cw / float(ch) if ch > 0 else 0

                if primary_axis == "y":
                    # مستطيل أفقي (عرض ≥ ارتفاع)، ارتفاع معقول داخل الهامش
                    if ratio >= 1.1 and ch < rh * 0.06 and cw >= 5:
                        candidates.append((x+cw//2+off[0], y+ch//2+off[1]))
                else:
                    # مستطيل عمودي (ارتفاع ≥ عرض)، عرض معقول داخل الهامش
                    if ratio <= 0.91 and cw < rw * 0.06 and ch >= 5:
                        candidates.append((x+cw//2+off[0], y+ch//2+off[1]))

            if len(candidates) < 4:
                continue

            # ── فحص X_std: هل هي في عمود رأسي ضيق؟ ──
            sec_coords = np.array([c[0] if primary_axis == "y"
                                   else c[1] for c in candidates],
                                  dtype=np.float64)
            x_std = float(np.std(sec_coords))

            if x_std > X_TIGHT:
                # التباين كبير → ليس شريط توقيت خالصاً
                # نحاول تضييق: نأخذ العلامات حول الوسيط فقط
                med = float(np.median(sec_coords))
                tight = [c for c in candidates
                         if abs((c[0] if primary_axis == "y" else c[1]) - med)
                         <= X_TIGHT]
                if len(tight) < 4:
                    continue
                candidates = tight
                sec_coords = np.array([c[0] if primary_axis == "y"
                                       else c[1] for c in candidates],
                                      dtype=np.float64)
                if float(np.std(sec_coords)) > X_TIGHT:
                    continue

            # ── ترتيب حسب المحور الرئيسي ──
            if primary_axis == "y":
                candidates.sort(key=lambda c: c[1])
                coords = [c[1] for c in candidates]
            else:
                candidates.sort(key=lambda c: c[0])
                coords = [c[0] for c in candidates]

            # ── تقدير الوسيط الأولي من الفجوات الكبيرة ──
            gaps_raw = [coords[i+1] - coords[i] for i in range(len(coords)-1)]
            if not gaps_raw:
                continue
            large_gaps = [g for g in gaps_raw if g > float(np.max(gaps_raw)) * 0.3]
            med_gap_est = float(np.median(large_gaps)) if large_gaps else float(np.median(gaps_raw))
            if med_gap_est < 3:
                continue

            # ── دمج العلامات المتشظية (gap < 30% من الوسيط = علامة مشطورة) ──
            # بعض الماسحات تُنتج علامة التوقيت كقطعتين منفصلتين
            merged = [candidates[0]]
            for i, g in enumerate(gaps_raw):
                if g < 0.30 * med_gap_est:
                    # دمج: حدّث Y للنقطة الأخيرة إلى متوسط القطعتين
                    mx = (merged[-1][0] + candidates[i+1][0]) // 2
                    my = (merged[-1][1] + candidates[i+1][1]) // 2
                    merged[-1] = (mx, my)
                else:
                    merged.append(candidates[i+1])
            candidates = merged

            if primary_axis == "y":
                coords = [c[1] for c in candidates]
            else:
                coords = [c[0] for c in candidates]

            gaps = [coords[i+1] - coords[i] for i in range(len(coords)-1)]
            if not gaps:
                continue
            med_gap = float(np.median(gaps))
            if med_gap < 3:
                continue

            # أطول سلسلة بفجوات منتظمة ±50% (مرونة للتعامل مع اختلاف الماسحات)
            best_chain, cur_chain = [0], [0]
            for i, g in enumerate(gaps):
                if 0.45 * med_gap <= g <= 1.55 * med_gap:
                    cur_chain.append(i + 1)
                else:
                    if len(cur_chain) > len(best_chain):
                        best_chain = cur_chain
                    cur_chain = [i + 1]
            if len(cur_chain) > len(best_chain):
                best_chain = cur_chain

            if len(best_chain) < 4:
                continue

            result = [(candidates[i][0], candidates[i][1])
                      for i in best_chain]
            cur_x_std = float(np.std(sec_coords))
            logger.info(f"   _scan_margin[{direction}@{margin_pct}%]: "
                        f"{len(result)} علامة  X_std={cur_x_std:.1f}")
            # نحتفظ بأفضل نتيجة عبر كل الهوامش — ليس فقط الأول
            if len(result) > len(best_result):
                best_result = result
                best_x_std  = cur_x_std
                best_margin = margin_pct

        if best_result:
            logger.info(f"   _scan_margin[{direction}] BEST: "
                        f"{len(best_result)} علامة @ {best_margin}% "
                        f"(X_std={best_x_std:.1f})")
        return best_result

    # ═══════════════════════════════════════════════
    # دوال النواة الاصطناعية والتصحيح المجهري
    # ═══════════════════════════════════════════════

    def _make_synthetic_bubble_kernel(self, radius):
        """نواة دائرية ناعمة تحاكي فقاعة بعد مسح ضوئي."""
        size = int(radius * 2) + 1
        kernel = np.zeros((size, size), dtype=np.float32)
        cx = cy = size / 2.0
        for y in range(size):
            for x in range(size):
                d = np.hypot(x - cx, y - cy)
                if d <= radius - 1.5:
                    kernel[y, x] = 1.0
                elif d <= radius + 1.5:
                    kernel[y, x] = max(0.0, (radius + 1.5 - d) / 3.0)
        kernel = cv2.GaussianBlur(kernel, (3, 3), 0.6)
        kernel = (kernel * 255).astype(np.uint8)
        return kernel

    def _refine_with_synthetic_kernel(self, gray_roi, cx_local, cy_local, synth_kernel, win_size):
        """تصحيح مجهري باستخدام نواة مع درجة ثقة موحّدة."""
        k_h, k_w = synth_kernel.shape
        if gray_roi.shape[0] < k_h or gray_roi.shape[1] < k_w:
            return cx_local, cy_local, 0.0
        res = cv2.matchTemplate(gray_roi, synth_kernel, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        grad_x = cv2.Sobel(gray_roi, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray_roi, cv2.CV_64F, 0, 1, ksize=3)
        mag = cv2.magnitude(grad_x, grad_y)
        mean_mag = mag.mean()
        stability = min(1.0, mean_mag / 25.0)
        confidence = max_val * stability
        if confidence < 0.5:
            return cx_local, cy_local, confidence
        cx_new = max_loc[0] + k_w // 2
        cy_new = max_loc[1] + k_h // 2
        return cx_new, cy_new, confidence

    def _compute_real_kernel(self, gray_img, marks_xy, radius, max_samples=4):
        """ينتج النواة المتوسطة من العلامات الحقيقية."""
        h, w = gray_img.shape
        patch_size = int(radius * 2.5)
        patches = []
        for cx, cy in marks_xy[:max_samples]:
            x1 = max(0, int(cx) - patch_size // 2)
            y1 = max(0, int(cy) - patch_size // 2)
            x2 = min(w, x1 + patch_size)
            y2 = min(h, y1 + patch_size)
            if x2 - x1 < patch_size // 2 or y2 - y1 < patch_size // 2:
                continue
            patch = gray_img[y1:y2, x1:x2].copy()
            patch = 255 - patch
            patch = cv2.normalize(patch, None, 0, 255, cv2.NORM_MINMAX)
            M = cv2.moments(patch)
            if M["m00"] < 50:
                continue
            cx_local = int(M["m10"] / M["m00"])
            cy_local = int(M["m01"] / M["m00"])
            shift_x = patch_size // 2 - cx_local
            shift_y = patch_size // 2 - cy_local
            M_shift = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
            patch = cv2.warpAffine(patch, M_shift, (patch_size, patch_size),
                                   flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            patches.append(patch.astype(np.float32))
        if not patches:
            return None
        kernel = np.mean(patches, axis=0)
        kernel = cv2.GaussianBlur(kernel, (3, 3), 0.5)
        kernel = np.clip(kernel, 0, 255).astype(np.uint8)
        return kernel

    def _evaluate_kernel_alignment(self, gray_img, marks_xy, kernel):
        """يُعيد الانحراف المعياري لمحور العلامات بعد التصحيح بالنواة."""
        refined = []
        h, w = gray_img.shape
        k_h, k_w = kernel.shape
        refine_win = max(k_h, k_w) + 4
        for (cx, cy) in marks_xy:
            rx1 = max(0, cx - refine_win // 2)
            ry1 = max(0, cy - refine_win // 2)
            rx2 = min(w, rx1 + refine_win)
            ry2 = min(h, ry1 + refine_win)
            if rx2 <= rx1 or ry2 <= ry1:
                continue
            patch = gray_img[ry1:ry2, rx1:rx2]
            local_cx = cx - rx1
            local_cy = cy - ry1
            new_cx, new_cy, conf = self._refine_with_synthetic_kernel(
                patch, local_cx, local_cy, kernel, refine_win)
            if conf >= 0.5:
                refined.append((rx1 + new_cx, ry1 + new_cy))
            else:
                refined.append((cx, cy))
        if len(refined) < 2:
            return None
        coords = [y for (x, y) in refined]
        return float(np.std(coords))

    def _learn_real_bubble_kernel(self, gray_img, marks_xy, radius, max_samples=4):
        """يتعلم نواة حقيقية فقط إذا أثبتت تحسناً > 15% مقارنة بالنواة الاصطناعية."""
        if len(marks_xy) < 4:
            return None
        synth_kernel  = self._make_synthetic_bubble_kernel(radius)
        baseline_std  = self._evaluate_kernel_alignment(gray_img, marks_xy, synth_kernel)
        if baseline_std is None:
            return None
        real_kernel = self._compute_real_kernel(gray_img, marks_xy, radius, max_samples)
        if real_kernel is None:
            return None
        learned_std = self._evaluate_kernel_alignment(gray_img, marks_xy, real_kernel)
        if learned_std is None:
            return None
        improvement = (baseline_std - learned_std) / baseline_std
        logger.info(f"Kernel eval: baseline_std={baseline_std:.2f} "
                    f"learned_std={learned_std:.2f} imp={improvement:.2%}")
        if improvement > 0.15:
            logger.info("Real kernel accepted")
            return real_kernel
        logger.info("Real kernel rejected, using synthetic")
        return None

    def _template_driven_timing(self, thresh, template_json, gray_img=None):
        """
        المسار الحتمي: يستخرج العلامات من إحداثيات القالب مباشرةً،
        ثم يصحّح موضعها بنواة اصطناعية (أو حقيقية إذا أثبتت تحسناً).
        """
        h, w = thresh.shape
        pos      = template_json["track_position"].lower()
        axis     = "vertical" if pos in ("right", "left") else "horizontal"
        tmpl_rel = template_json["timing_marks_rel"]

        # حساب نصف قطر الفقاعة
        cal       = template_json.get("calibration", {})
        cal_w     = cal.get("image_w", template_json.get("target_w", w))
        brel      = template_json.get("bubble_size_rel", 0.0)
        if not brel and template_json.get("bubble_size"):
            brel = template_json["bubble_size"] / cal_w
        if brel <= 0:
            brel = 0.015
        bubble_radius = max(4, int(brel * w * 0.5))

        # الإحداثي الثانوي (X للشريط العمودي، Y للأفقي)
        x_rel_list = template_json.get("timing_marks_x_rel", [])
        if axis == "vertical":
            sec_ref = int(x_rel_list[0] * w) if x_rel_list else int(w * 0.92)
        else:
            y_rel_list = template_json.get("timing_marks_y_rel", [])
            sec_ref = int(y_rel_list[0] * h) if y_rel_list else int(h * 0.08)

        # المرحلة 1 — استخراج خشن بفلتر contour
        marks = []
        win   = max(int(bubble_radius * 2.5), 8)
        for ry in tmpl_rel:
            exp_y = int(ry * h) if axis == "vertical" else sec_ref
            exp_x = sec_ref     if axis == "vertical" else int(ry * w)
            x1 = max(0, exp_x - win);  y1 = max(0, exp_y - win)
            x2 = min(w, exp_x + win);  y2 = min(h, exp_y + win)
            roi_th = thresh[y1:y2, x1:x2]
            if roi_th.size == 0:
                continue
            cnts, _ = cv2.findContours(roi_th, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                continue
            largest = max(cnts, key=cv2.contourArea)
            M = cv2.moments(largest)
            if M["m00"] < 3:
                continue
            marks.append((x1 + int(M["m10"] / M["m00"]),
                           y1 + int(M["m01"] / M["m00"])))

        if len(marks) < 0.8 * len(tmpl_rel):
            logger.warning(f"Template-driven timing: only {len(marks)}/{len(tmpl_rel)} marks found")
            return None, None, None

        # المرحلة 2 — تعلم النواة (اصطناعية أو حقيقية)
        refine_kernel = self._make_synthetic_bubble_kernel(bubble_radius)
        if gray_img is not None and len(marks) >= 4:
            real_kernel = self._learn_real_bubble_kernel(gray_img, marks, bubble_radius)
            if real_kernel is not None:
                refine_kernel = real_kernel

        # المرحلة 3 — تصحيح مجهري لجميع العلامات
        refined_marks = []
        k_h, k_w  = refine_kernel.shape
        refine_win = max(k_h, k_w) + 4
        for (cx, cy) in marks:
            if gray_img is not None:
                rx1 = max(0, cx - refine_win // 2)
                ry1 = max(0, cy - refine_win // 2)
                rx2 = min(w, rx1 + refine_win)
                ry2 = min(h, ry1 + refine_win)
                if rx2 > rx1 and ry2 > ry1:
                    patch = gray_img[ry1:ry2, rx1:rx2]
                    new_cx, new_cy, conf = self._refine_with_synthetic_kernel(
                        patch, cx - rx1, cy - ry1, refine_kernel, refine_win)
                    if conf >= 0.5:
                        cx = rx1 + new_cx
                        cy = ry1 + new_cy
            refined_marks.append((cx, cy))

        logger.info(f"Template-driven timing [{pos}]: {len(refined_marks)} marks")
        return refined_marks, pos, axis

    def detect_timing_track(self, thresh, template_json=None, gray_img=None):
        """
        اكتشاف شريط التوقيت ديناميكياً:

        الأولوية:
          1. إذا وُجد 'track_position' في القالب → يفحص الهامش المحدد مباشرةً.
          2. إذا لم يوجد → يفحص الهوامش الأربعة ويختار الأكثر علامات منتظمة.

        يُعيد: (marks_xy, direction, axis)
          marks_xy  : قائمة (x,y) للعلامات
          direction : 'right'|'left'|'top'|'bottom'
          axis      : 'vertical'|'horizontal'
        """
        h, w = thresh.shape

        # ── 1. المسار الحتمي: قالب يحتوي timing_marks_rel + track_position ──
        if (template_json
                and template_json.get("timing_marks_rel")
                and template_json.get("track_position", "").lower()
                    in ("right", "left", "top", "bottom")):
            marks, pos, axis = self._template_driven_timing(
                thresh, template_json, gray_img=gray_img)
            if marks:
                return marks, pos, axis
            logger.warning("Template-driven timing failed → fallback to dynamic")

        # ── 2. المسار الاحتياطي: فحص الهوامش الأربعة ──
        if template_json:
            pos = template_json.get("track_position", "").lower()
            if pos in ("right", "left", "top", "bottom"):
                marks = self._scan_margin(thresh, pos)
                axis  = "vertical" if pos in ("right", "left") else "horizontal"
                logger.info(f" Timing from template (fallback): {pos}  {len(marks)} marks")
                return marks, pos, axis

        best_marks, best_dir = [], "right"
        for direction in ("right", "left", "top", "bottom"):
            found = self._scan_margin(thresh, direction)
            if len(found) > len(best_marks):
                best_marks = found
                best_dir   = direction

        axis = "vertical" if best_dir in ("right", "left") else "horizontal"

        if best_marks:
            logger.info(f" Auto timing: {best_dir}  {len(best_marks)} marks  axis={axis}")
        else:
            logger.warning("لم يُرصد شريط التوقيت في أي هامش.")

        return best_marks, best_dir, axis

    # ═══════════════════════════════════════════════
    # B1: التحقق الدفاعي من توافق شريط التوقيت مع القالب
    # ═══════════════════════════════════════════════
    def _verify_timing_track(self, template_json, actual_marks_xy,
                             direction, axis):
        """
        يُقارن شريط التوقيت المكتشف في الورقة المُدخَلة بالشريط المتوقَّع
        في القالب، ويُرجع قائمة تحذيرات نصّية للمستخدم (عربية، جاهزة للعرض).

        الفحوصات:
          1. اتجاه: track_position محدد بالقالب لكنه لا يطابق الاتجاه المكتشف.
          2. غياب كامل: القالب يتوقع علامات لكن لم تُكتشف ولا واحدة.
          3. عدد: فرق كبير (>10%) بين عدد العلامات المكتشف والمتوقَّع.
        إذا لم يحوِ القالب معلومات توقيت → لا تحذيرات (تخطٍّ صامت).
        كل تحذير يُسجَّل أيضاً عبر logger.warning للتتبّع.
        """
        warnings_list = []
        if not template_json:
            return warnings_list

        actual_count = len(actual_marks_xy) if actual_marks_xy else 0

        # ── 1. تطابق الاتجاه ──
        tmpl_pos = (template_json.get("track_position") or "").lower()
        if tmpl_pos in ("right", "left", "top", "bottom") and tmpl_pos != direction:
            msg = (f"اتجاه شريط التوقيت المكتشف ({direction}) لا يطابق "
                   f"القالب ({tmpl_pos}) — تأكّد من اختيار القالب الصحيح "
                   f"أو من اتجاه الورقة.")
            warnings_list.append(msg)
            logger.warning(f"_verify_timing_track: direction mismatch "
                           f"actual={direction} expected={tmpl_pos}")

        # ── استخراج العدد المتوقَّع من القالب ──
        expected_count = 0
        if template_json.get("timing_marks_rel"):
            expected_count = len(template_json["timing_marks_rel"])
        elif template_json.get("timing_marks"):
            expected_count = len(template_json["timing_marks"])

        if expected_count <= 0:
            return warnings_list

        # ── 2. غياب كامل لشريط التوقيت ──
        if actual_count == 0:
            msg = (f"لم يُكتشف شريط التوقيت في الورقة — القالب يتوقع "
                   f"{expected_count} علامة. القراءة قد تكون غير موثوقة.")
            warnings_list.append(msg)
            logger.warning(f"_verify_timing_track: no marks detected, "
                           f"expected {expected_count}")
            return warnings_list

        # ── 3. فرق ملحوظ في العدد (>10%) ──
        diff_pct = abs(actual_count - expected_count) / float(expected_count)
        if diff_pct > 0.10:
            msg = (f"عدد علامات التوقيت المكتشف ({actual_count}) يختلف عن "
                   f"المتوقَّع في القالب ({expected_count}) — قد يدلّ ذلك "
                   f"على قالب خاطئ أو ورقة تالفة أو إعدادات مسح مختلفة.")
            warnings_list.append(msg)
            logger.warning(f"_verify_timing_track: count mismatch "
                           f"actual={actual_count} expected={expected_count} "
                           f"diff_pct={diff_pct:.2%}")

        return warnings_list

    # ═══════════════════════════════════════════════
    # B3: فحص توافق DPI والمقياس بين القالب والورقة
    # ═══════════════════════════════════════════════
    def _verify_scale(self, template_json, actual_marks_xy, axis,
                      orig_img_w, orig_img_h, img_w, img_h):
        """
        فحصان:
          1. نسبة العرض/الارتفاع للورقة الأصلية (قبل resize) مقابل القالب
             — يكشف ورقاً بمقاس مختلف (Letter بدل A4) أو إعدادات ماسح خاطئة
             (>5% فرق = تحذير).
          2. امتداد شريط التوقيت المُطبَّع — يكشف تكبير/تصغير عند الطباعة
             ("Fit to page"، 95%، 110%) (>10% فرق = تحذير).

        ملاحظة: لا يُمكن استنتاج DPI الفعلي من المواضع النسبية فقط، لأن
        resize يطبّع كل المقاسات تلقائياً. الفحص الفعّال هو مقارنة الامتداد
        النسبي لشريط التوقيت — يكشف الطباعة بمقياس مختلف حتى لو احتُفظ بالتناسب.
        """
        warnings_list = []
        if not template_json:
            return warnings_list

        cal   = template_json.get("calibration", {})
        cal_w = cal.get("image_w", template_json.get("target_w", 0))
        cal_h = cal.get("image_h", template_json.get("target_h", 0))

        # ── 1. نسبة العرض/الارتفاع للورقة الأصلية ──
        if (cal_w > 0 and cal_h > 0 and
                orig_img_w > 0 and orig_img_h > 0):
            tmpl_aspect = cal_w / float(cal_h)
            orig_aspect = orig_img_w / float(orig_img_h)
            diff_pct = abs(orig_aspect - tmpl_aspect) / tmpl_aspect
            if diff_pct > 0.05:
                msg = (f"نسبة عرض/ارتفاع الورقة الممسوحة ({orig_aspect:.3f}) "
                       f"تختلف عن القالب ({tmpl_aspect:.3f}) — قد تكون الورقة "
                       f"بمقاس مختلف (مثلاً Letter بدل A4) أو إعدادات الماسح "
                       f"غير صحيحة.")
                warnings_list.append(msg)
                logger.warning(f"_verify_scale: aspect mismatch "
                               f"orig={orig_aspect:.3f} tmpl={tmpl_aspect:.3f} "
                               f"diff_pct={diff_pct:.2%}")

        # ── 2. امتداد شريط التوقيت بعد التطبيع ──
        if not actual_marks_xy or len(actual_marks_xy) < 2:
            return warnings_list

        # العلامات النسبية المتوقَّعة في القالب (0..1) — على المحور الأساسي
        tmpl_rel = template_json.get("timing_marks_rel") or []
        if not tmpl_rel and template_json.get("timing_marks"):
            tm = template_json["timing_marks"]
            if tm and max(tm) <= 1.0:
                tmpl_rel = tm   # نسبية أصلاً
        if len(tmpl_rel) < 2:
            return warnings_list

        actual_primary = [m[1] if axis == "vertical" else m[0]
                          for m in actual_marks_xy]
        dim = img_h if axis == "vertical" else img_w
        if dim <= 0:
            return warnings_list

        tmpl_span_rel   = max(tmpl_rel) - min(tmpl_rel)
        actual_span_rel = (max(actual_primary) - min(actual_primary)) / float(dim)

        if tmpl_span_rel > 0:
            span_ratio = actual_span_rel / tmpl_span_rel
            if abs(span_ratio - 1.0) > 0.10:
                msg = (f"امتداد شريط التوقيت في الورقة ({actual_span_rel:.3f}) "
                       f"يختلف عن القالب ({tmpl_span_rel:.3f}) "
                       f"بنسبة {(span_ratio - 1.0) * 100:+.1f}% — قد يدلّ ذلك "
                       f"على فرق DPI أو تكبير/تصغير عند الطباعة "
                       f"(مثل 'Fit to page').")
                warnings_list.append(msg)
                logger.warning(f"_verify_scale: span mismatch "
                               f"actual={actual_span_rel:.3f} "
                               f"tmpl={tmpl_span_rel:.3f} "
                               f"ratio={span_ratio:.3f}")

        return warnings_list

    def _build_timing_mappers(self, template_json, actual_marks_xy,
                               img_w, img_h,
                               direction="right", axis="vertical"):
        """
        بناء دالتي التصحيح الهندسي بناءً على اتجاه الشريط المكتشف.
        تمت إضافة Scale Ratio لتعويض التمدد/الانضغاط الناتج عن الفراغ الأبيض.
        """
        cal   = template_json.get("calibration", {})
        cal_w = cal.get("image_w", template_json.get("target_w", img_w))
        cal_h = cal.get("image_h", template_json.get("target_h", img_h))

        # ── إحداثيات القالب ──
        if axis == "vertical":
            if template_json.get("timing_marks_rel"):
                tmpl_primary = [ry * img_h for ry in template_json["timing_marks_rel"]]
            elif template_json.get("timing_marks"):
                # القيم قد تكون نسبية (<1) أو مطلقة - نتحقق من النوع
                tm = template_json["timing_marks"]
                if tm and max(tm) <= 1.0:
                    tmpl_primary = [y * img_h for y in tm]  # نسبية
                else:
                    tmpl_primary = [y * img_h / cal_h for y in tm]  # مطلقة
            else:
                tmpl_primary = []

            if template_json.get("timing_marks_x_rel"):
                avg_t_secondary = float(np.mean(
                    [rx * img_w for rx in template_json["timing_marks_x_rel"]]))
            elif template_json.get("timing_marks_x"):
                tm_x = template_json["timing_marks_x"]
                if tm_x and max(tm_x) <= 1.0:
                    avg_t_secondary = float(np.mean([x * img_w for x in tm_x]))
                else:
                    avg_t_secondary = float(np.mean(tm_x)) * img_w / cal_w
            else:
                avg_t_secondary = img_w * (0.92 if direction == "right" else 0.08)

            actual_primary   = [m[1] for m in actual_marks_xy]   # Y
            actual_secondary = [m[0] for m in actual_marks_xy]   # X

        else:
            if template_json.get("timing_marks_rel"):
                tmpl_primary = [rx * img_w for rx in template_json["timing_marks_rel"]]
            elif template_json.get("timing_marks"):
                tm = template_json["timing_marks"]
                if tm and max(tm) <= 1.0:
                    tmpl_primary = [x * img_w for x in tm]  # نسبية
                else:
                    tmpl_primary = [x * img_w / cal_w for x in tm]  # مطلقة
            else:
                tmpl_primary = []

            if template_json.get("timing_marks_x_rel"):
                avg_t_secondary = float(np.mean(
                    [ry * img_h for ry in template_json["timing_marks_x_rel"]]))
            elif template_json.get("timing_marks_x"):
                tm_x = template_json["timing_marks_x"]
                if tm_x and max(tm_x) <= 1.0:
                    avg_t_secondary = float(np.mean([y * img_h for y in tm_x]))
                else:
                    avg_t_secondary = float(np.mean(tm_x)) * img_h / cal_h
            else:
                avg_t_secondary = img_h * (0.08 if direction == "top" else 0.92)

            actual_primary   = [m[0] for m in actual_marks_xy]   # X
            actual_secondary = [m[1] for m in actual_marks_xy]   # Y

        if not actual_primary:
            logger.warning("لم يُرصد شريط التوقيت — معطّلتان.")
            return (lambda y, x=None: int(round(y)),
                    lambda x, cy:    int(round(x)))

        logger.info(f"المسطرة [{direction}|{axis}]: {len(actual_primary)} نقطة.")

        t_arr  = (np.array(tmpl_primary,    dtype=np.float64)
                  if tmpl_primary else
                  np.array(actual_primary,  dtype=np.float64))
        a_arr  = np.array(actual_primary,   dtype=np.float64)
        as_arr = np.array(actual_secondary, dtype=np.float64)

        # ── ميل الشريط → يقيس Shear الماسح ──
        shear_slope = 0.0
        s_slope     = 0.0
        s_intercept = avg_t_secondary
        if len(actual_primary) >= 4:
            c = np.polyfit(a_arr, as_arr, 1)
            shear_slope = float(c[0])
            s_slope     = shear_slope
            s_intercept = float(c[1])
            logger.info(f"   Shear slope={shear_slope:.5f}  "
                        f"avg_t_secondary={avg_t_secondary:.1f}px")

        if axis == "vertical":
            # ── بناء جدول الاستيفاء المثالي (مطابقة مرتّبة + np.interp) ──
            # الخوارزمية:
            #   1. كلٌّ من t_arr و a_arr مرتّبان تصاعدياً (مضمون من _scan_margin)
            #   2. مطابقة DP بالترتيب: لكل علامة حقيقية نجد أقرب علامة قالب
            #      غير مُطابَقة بعد، في نافذة ضيّقة للأمام → O(n)
            #   3. np.interp على الأزواج المُطابَقة → استيفاء خطي دقيق بين كل علامتين
            #   4. خارج النطاق: extrapolation خطي بانحدار آخر فجوة (وليس scale_ratio كلي)
            # هذا يتفوق على scale_ratio لأنه يعالج التمدد غير المنتظم وعلامات مفقودة
            _t_s = np.sort(t_arr)
            _a_s = np.sort(a_arr)
            _pairs_t, _pairs_a = [], []
            _j = 0
            for _a_val in _a_s:
                if _j >= len(_t_s): break
                _best_j, _best_d = _j, abs(_t_s[_j] - _a_val)
                for _jj in range(_j + 1, min(_j + 6, len(_t_s))):
                    _d = abs(_t_s[_jj] - _a_val)
                    if _d < _best_d:
                        _best_d, _best_j = _d, _jj
                    elif _d > _best_d:
                        break
                _pairs_t.append(_t_s[_best_j])
                _pairs_a.append(_a_val)
                _j = _best_j + 1
            _pt = np.array(_pairs_t, dtype=np.float64)
            _pa = np.array(_pairs_a, dtype=np.float64)

            if len(_pt) >= 2:
                _l_slope = (_pa[1]-_pa[0]) / (_pt[1]-_pt[0]) if _pt[1] != _pt[0] else 1.0
                _r_slope = (_pa[-1]-_pa[-2]) / (_pt[-1]-_pt[-2]) if _pt[-1] != _pt[-2] else 1.0
            else:
                _l_slope = _r_slope = 1.0

            # Scale Ratio للتسجيل فقط
            if len(a_arr) > 1 and len(t_arr) > 1:
                t_span = np.max(t_arr) - np.min(t_arr)
                a_span = np.max(a_arr) - np.min(a_arr)
                scale_ratio = a_span / t_span if t_span != 0 else 1.0
            else:
                scale_ratio = 1.0
            logger.info(f"   Vertical interp: {len(_pt)} أزواج  scale≈{scale_ratio:.4f}")
            logger.info(f"   _pt (template) = {_pt[:5]}...{_pt[-5:]}")
            logger.info(f"   _pa (actual)   = {_pa[:5]}...{_pa[-5:]}")

            def map_y(y, x=None):
                # استيفاء خطي من جدول الأزواج المُطابَقة
                if len(_pt) == 0:
                    base_y = float(y)
                elif y <= _pt[0]:
                    base_y = float(_pa[0] + (y - _pt[0]) * _l_slope)
                elif y >= _pt[-1]:
                    base_y = float(_pa[-1] + (y - _pt[-1]) * _r_slope)
                else:
                    base_y = float(np.interp(y, _pt, _pa))
                if x is not None and shear_slope != 0.0:
                    base_y -= shear_slope * (float(x) - avg_t_secondary)
                return int(round(base_y))

            def map_x(x, cy):
                x_off = (s_slope * cy + s_intercept) - avg_t_secondary
                return int(round(x + x_off))

        else:
            # شريط أفقي: المحور الرئيسي هو X، والـ Shear يؤثر على Y
            # نفس خوارزمية الاستيفاء المثالية للمحور الأفقي
            _t_sx = np.sort(t_arr)
            _a_sx = np.sort(a_arr)
            _pairs_tx, _pairs_ax = [], []
            _jx = 0
            for _a_val in _a_sx:
                if _jx >= len(_t_sx): break
                _best_jx, _best_dx = _jx, abs(_t_sx[_jx] - _a_val)
                for _jjx in range(_jx + 1, min(_jx + 6, len(_t_sx))):
                    _d = abs(_t_sx[_jjx] - _a_val)
                    if _d < _best_dx:
                        _best_dx, _best_jx = _d, _jjx
                    elif _d > _best_dx:
                        break
                _pairs_tx.append(_t_sx[_best_jx])
                _pairs_ax.append(_a_val)
                _jx = _best_jx + 1
            _ptx = np.array(_pairs_tx, dtype=np.float64)
            _pax = np.array(_pairs_ax, dtype=np.float64)

            if len(_ptx) >= 2:
                _lsx = (_pax[1]-_pax[0])/(_ptx[1]-_ptx[0]) if _ptx[1]!=_ptx[0] else 1.0
                _rsx = (_pax[-1]-_pax[-2])/(_ptx[-1]-_ptx[-2]) if _ptx[-1]!=_ptx[-2] else 1.0
            else:
                _lsx = _rsx = 1.0

            if len(a_arr) > 1 and len(t_arr) > 1:
                t_span = np.max(t_arr) - np.min(t_arr)
                a_span = np.max(a_arr) - np.min(a_arr)
                scale_ratio = a_span / t_span if t_span != 0 else 1.0
            else:
                scale_ratio = 1.0
            logger.info(f"   Horizontal interp: {len(_ptx)} أزواج  scale≈{scale_ratio:.4f}")

            def map_y(y, x=None):
                y_off = (s_slope * (float(x) if x else 0) + s_intercept) - avg_t_secondary
                return int(round(y + y_off))

            def map_x(x, cy):
                if len(_ptx) == 0:
                    base_x = float(x)
                elif x <= _ptx[0]:
                    base_x = float(_pax[0] + (x - _ptx[0]) * _lsx)
                elif x >= _ptx[-1]:
                    base_x = float(_pax[-1] + (x - _ptx[-1]) * _rsx)
                else:
                    base_x = float(np.interp(x, _ptx, _pax))
                if shear_slope != 0.0:
                    base_x -= shear_slope * (float(cy) - avg_t_secondary)
                return int(round(base_x))

        return map_y, map_x

    # ═══════════════════════════════════════════════
    # استثناء منطقة التعليمات
    # ═══════════════════════════════════════════════
    def _blank_instructions_region(self, thresh, template_json, img_w, img_h):
        r = template_json.get("instructions_region", None)
        if r is None:
            # افتراضي: منطقة وسط يسار الورقة
            r = {"rx1":0.0,"ry1":0.46,"rx2":0.50,"ry2":0.75}
        if "rx1" in r:
            x1,y1 = int(r["rx1"]*img_w), int(r["ry1"]*img_h)
            x2,y2 = int(r["rx2"]*img_w), int(r["ry2"]*img_h)
        else:
            cal = template_json.get("calibration",{})
            cw = cal.get("image_w", template_json.get("target_w", img_w))
            ch = cal.get("image_h", template_json.get("target_h", img_h))
            x1,y1 = int(r.get("x1",0)*img_w/cw),   int(r.get("y1",780)*img_h/ch)
            x2,y2 = int(r.get("x2",600)*img_w/cw), int(r.get("y2",1260)*img_h/ch)
        thresh[max(0,y1):min(img_h,y2), max(0,x1):min(img_w,x2)] = 0
        return thresh

    # ═══════════════════════════════════════════════
    # قراءة الرقم الجامعي (gray)
    # ═══════════════════════════════════════════════
    def _find_id_x_offset(self, gray, id_cols, img_w, img_h, cal_w, cal_h,
                           map_y=None, map_x=None):
        """
        يجد أفضل X offset للشبكة مع تطبيق map_y/map_x إذا أُعطيتا.
        هذا يضمن أن الرقم الجامعي يُقرأ من الموقع المصحَّح فعلاً.
        """
        _my = map_y if map_y is not None else (lambda y, x=None: int(round(y)))
        _mx = map_x if map_x is not None else (lambda x, cy: int(round(x)))

        best_x, best_c = 0, 0
        for x_off in range(-10, 11):
            total = 0
            for bubbles in id_cols.values():
                means = []
                for b in bubbles:
                    raw_y = self._by(b, img_h, cal_h)
                    raw_x = self._bx(b, img_w, cal_w) + x_off
                    cy    = _my(raw_y, raw_x)
                    cx    = _mx(raw_x, cy)
                    bw, bh = self._bsize(b, img_w, img_h, cal_w, cal_h)
                    sw = max(int(bw * 0.40), 6)
                    roi = gray[max(0, cy-sw):cy+sw, max(0, cx-sw):cx+sw]
                    if roi.size > 0:
                        means.append(roi.mean())
                if len(means) >= 2:
                    total += max(means) - min(means)
            if total > best_c:
                best_c = total; best_x = x_off
        logger.info(f"ID X offset: {best_x:+d}px")
        return best_x

    def _read_id_column(self, gray, bubbles, img_w, img_h, cal_w, cal_h,
                        x_off=0, map_y=None, map_x=None):
        """
        يقرأ عمود واحد من شبكة الرقم الجامعي/الشعبة/المقرر.
        القيم المُعادة:
          "0"-"9" : رقم مقروء
          "#"     : خانة فارغة (لم تُظلَّل)
          "?"     : تضليل مزدوج (أكثر من دائرة مظللة)

        ─ ملاحظة على المنطق (B2) ─
        الإصدار السابق استخدم FILL_THRESHOLD=200.0 ثابتاً وفجوة 20 ثابتة.
        كان يفشل عند:
          • ورق ملوّن (mean الخلفية ينخفض دون 200 طبيعياً)
          • تظليل خفيف بقلم رصاص HB (mean ≈ 180-210)
          • مسح بإضاءة عالية (كل الـ means ترتفع لكن العتبة ثابتة)
        المنطق الجديد يستخدم z-score داخل العمود الواحد (نفس أسلوب
        _read_questions) — يعمل تلقائياً مع أي خلفية وأي ماسح وأي
        شدّة تظليل، ويُعيد استخدام نفس ثوابت قواعد القرار.
        """
        if not bubbles: return "#"
        _my = map_y if map_y is not None else (lambda y, x=None: int(round(y)))
        _mx = map_x if map_x is not None else (lambda x, cy: int(round(x)))

        bw, bh = self._bsize(bubbles[0], img_w, img_h, cal_w, cal_h)
        sw = max(int(bw * 0.40), 6)
        sh = max(int(bh * 0.40), 6)

        # ── أفضل Y offset (مرحلة محاذاة — لا علاقة لها بالعتبة) ──
        best_y, best_c = 0, 0
        for y_off in range(-2, 17):
            means = []
            for b in bubbles:
                raw_y = self._by(b, img_h, cal_h) + y_off
                raw_x = self._bx(b, img_w, cal_w) + x_off
                cy = _my(raw_y, raw_x)
                cx = _mx(raw_x, cy)
                roi = gray[max(0, cy-sh):cy+sh, max(0, cx-sw):cx+sw]
                if roi.size > 0:
                    means.append(roi.mean())
            if len(means) >= 2:
                c = max(means) - min(means)
                if c > best_c: best_c = c; best_y = y_off

        # ── قياس darkness لكل دائرة بأفضل محاذاة ──
        # darkness = 255 - mean → قيم عالية = أغمق (يطابق دلالة _read_questions)
        row = []          # darkness per bubble
        digits = []       # digit string per bubble (بنفس ترتيب row)
        for b in bubbles:
            raw_y = self._by(b, img_h, cal_h) + best_y
            raw_x = self._bx(b, img_w, cal_w) + x_off
            cy = _my(raw_y, raw_x)
            cx = _mx(raw_x, cy)
            roi = gray[max(0, cy-sh):cy+sh, max(0, cx-sw):cx+sw]
            if roi.size > 0:
                row.append(255.0 - float(roi.mean()))
                digits.append(str(b["digit"]))

        n_ch = len(row)
        if n_ch == 0:
            return "#"

        if n_ch == 1:
            # حالة نادرة: عمود بفقاعة واحدة — نسقط لعتبة مطلقة محافِظة
            # (z-score غير معرّفة لعنصر واحد). darkness > 45 تظليل واضح
            # تقريباً يعادل mean < 210.
            return digits[0] if row[0] > 45.0 else "#"

        # ── إحصائيات العمود ──
        best_val = max(row)
        best_i   = row.index(best_val)
        row_mean = sum(row) / n_ch
        stdev    = (sum((v - row_mean) ** 2 for v in row) / n_ch) ** 0.5
        sec_val  = sorted(row, reverse=True)[1]
        gap_abs  = best_val - sec_val
        gap_pct  = (best_val - sec_val) / best_val if best_val > 0 else 0.0
        min_val  = min(row)
        rel_contrast = (best_val - min_val) / (best_val + 1e-6)
        z_best   = (best_val - row_mean) / stdev if stdev > 0 else 0.0
        z_second = (sec_val  - row_mean) / stdev if stdev > 0 else 0.0

        # ── لوج تشخيصي (بعد حساب جميع المتغيرات) ───────────────────────────
        _top3 = sorted(zip(row, digits), reverse=True)[:3]
        logger.info(
            f"ID_COL: digits={digits} "
            f"top3={[(d,f'{v:.1f}') for v,d in _top3]} "
            f"best={best_val:.1f}({digits[best_i]}) sec={sec_val:.1f} "
            f"z_best={z_best:.2f} gap_abs={gap_abs:.1f} gap_pct={gap_pct:.2f} "
            f"rel_contrast={rel_contrast:.2f}"
        )

        # ── شجرة القرار المُحدّثة (rel_contrast بدل gap_pct الثابت) ──
        if rel_contrast < 0.30:
            logger.info(f"ID_COL: => '#' (rel_contrast={rel_contrast:.2f} < 0.30 — عمود فارغ)")
            return "#"
        if z_best < self.Z_BEST_MIN or gap_abs < self.NOISE_THRESHOLD_ABS:
            logger.info(f"ID_COL: => '#' (z_best={z_best:.2f}<{self.Z_BEST_MIN} أو gap_abs={gap_abs:.1f}<{self.NOISE_THRESHOLD_ABS})")
            return "#"
        if z_second < self.Z_SECOND_MAX:
            return digits[best_i]   # إجابة واحدة واضحة ✅
        # تضليل مزدوج — في حقل الرقم نأخذ الأثقل دائماً
        return digits[best_i]

    # ═══════════════════════════════════════════════
    # قراءة النموذج (thresh)
    # ═══════════════════════════════════════════════
    def _read_version(self, thresh, bubbles, img_w, img_h, cal_w, cal_h, map_y, map_x,
                      gray_image=None):
        """
        يقرأ النموذج المظلل من فقاعات VERSION.
        يستخدم نفس مقياس darkness من gray_image كـ _read_id_column و_read_questions
        حتى تكون قيم gap_abs متوافقة مع NOISE_THRESHOLD_ABS (نطاق 0-255).
        """
        if not bubbles:
            logger.info("VERSION read: '#'  (no bubbles)")
            return "#"

        # ── مرحلة 1: قياس darkness من gray — نفس مقياس _read_id_column ──
        # darkness = 255 - mean → نطاق 0-255 → متوافق مع NOISE_THRESHOLD_ABS
        src = gray_image if gray_image is not None else cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        if len(src.shape) == 3:
            src = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

        scores = []   # [(darkness, label_str)]
        for b in bubbles:
            raw_x = self._bx(b, img_w, cal_w)
            cy    = map_y(self._by(b, img_h, cal_h), raw_x)
            cx    = map_x(raw_x, cy)
            bw, bh = self._bsize(b, img_w, img_h, cal_w, cal_h)
            sw = max(int(bw * 0.40), 6)
            sh = max(int(bh * 0.40), 6)
            roi = src[
                max(0, int(cy) - sh):min(int(cy) + sh, src.shape[0]),
                max(0, int(cx) - sw):min(int(cx) + sw, src.shape[1])
            ]
            darkness = (255.0 - float(roi.mean())) if roi.size > 0 else 0.0
            bubble_label = str(b.get("label") or b.get("digit") or (len(scores) + 1))
            scores.append((darkness, bubble_label))

        # ── DEBUG مؤقت — احذفه بعد التشخيص ──────────────────────────────
        logger.info(f"VERSION raw scores: {[(lbl, f'{drk:.1f}') for drk, lbl in scores]}")
        # ─────────────────────────────────────────────────────────────────

        if not scores:
            logger.info("VERSION read: '#'  (empty scores)")
            return "#"

        # ── مرحلة 2: z-score داخل فقاعات VERSION ────────────────────────
        # نفس منطق _read_id_column و_read_questions — يتكيف مع أي خلفية وأي ماسح
        intensities = [s[0] for s in scores]
        n_ch        = len(intensities)

        best_val  = max(intensities)
        best_i    = intensities.index(best_val)
        row_mean  = sum(intensities) / n_ch
        stdev     = (sum((v - row_mean) ** 2 for v in intensities) / n_ch) ** 0.5
        sec_val   = sorted(intensities, reverse=True)[1] if n_ch >= 2 else 0.0

        z_best   = (best_val - row_mean) / stdev if stdev > 0 else 0.0
        z_second = (sec_val  - row_mean) / stdev if stdev > 0 else 0.0
        gap_abs  = best_val - sec_val
        gap_pct  = (best_val - sec_val) / best_val if best_val > 0 else 0.0

        scores_sorted = sorted(scores, key=lambda x: x[0], reverse=True)
        best_val, best_d = scores_sorted[0]

        logger.info(
            f"VERSION scores: {[(d, f'{v:.4f}') for v, d in scores]} | "
            f"mean={row_mean:.4f} std={stdev:.4f} "
            f"z_best={z_best:.2f} z_sec={z_second:.2f} "
            f"gap_abs={gap_abs:.4f} gap_pct={gap_pct:.3f}"
        )

        # ── مرحلة 3: شجرة القرار — نفس ثوابت قواعد القرار الموحّدة ──────
        if z_best < self.Z_BEST_MIN or gap_abs < self.NOISE_THRESHOLD_ABS:
            logger.info(f"VERSION read: '#'  z_best={z_best:.2f} < {self.Z_BEST_MIN} أو gap_abs={gap_abs:.4f} < {self.NOISE_THRESHOLD_ABS}")
            return "#"

        # ── بوابة وضوح القرار — ديناميكية لجميع الماسحات ───────────────
        # بدل 0.30 ثابت: نحسب العتبة من توزيع فقاعات VERSION نفسها
        # ماسح هادئ (أفيجين) → تباين أقل → عتبة أقل تلقائياً
        _ver_range  = max(intensities) - min(intensities)
        _dyn_thresh = max(0.10, min(0.30, _ver_range / (best_val + 1e-6) * 0.60))
        if gap_pct < _dyn_thresh:
            logger.info(
                f"VERSION read: '#'  gap_pct={gap_pct:.3f} < {_dyn_thresh:.3f} (إشارة غير حاسمة)"
            )
            return "#"

        if z_second >= self.Z_SECOND_MAX and gap_pct < self.GAP_PCT_MIN:
            logger.warning(
                f"VERSION conflict (مزدوج): best={best_d} z_sec={z_second:.2f} gap_pct={gap_pct:.3f}"
            )
            return "#"

        logger.info(f"VERSION read: '{best_d}'  z_best={z_best:.2f}  gap_pct={gap_pct:.3f}")
        return best_d

    # ═══════════════════════════════════════════════
    # تقييم فقاعة واحدة
    # ═══════════════════════════════════════════════
    def _validate_and_score_bubble(self, thresh, gray_img, cx, cy, half_r, fill_threshold=0.25):
        """
        يُقيّم فقاعة واحدة ويُعيد درجة darkness (0-100) أو None إذا كانت فارغة هندسياً.
        يجمع بين فلترة نسبة الامتلاء (من الصورة الثنائية) وشدة التظليل (من الصورة الرمادية).
        """
        # 1. حساب حدود ROI
        x1 = max(0, int(cx) - half_r)
        y1 = max(0, int(cy) - half_r)
        x2 = min(thresh.shape[1], int(cx) + half_r)
        y2 = min(thresh.shape[0], int(cy) + half_r)
        if x2 <= x1 or y2 <= y1:
            return None

        # 2. المرحلة الهندسية: فلترة بنسبة الامتلاء (Hard Reject)
        roi_th = thresh[y1:y2, x1:x2]
        white_pixels = cv2.countNonZero(roi_th)
        fill_ratio = white_pixels / roi_th.size if roi_th.size > 0 else 0
        if fill_ratio < fill_threshold:   # استخدم العتبة الديناميكية الممررة
            return None

        # 3. المرحلة الإحصائية: حساب شدة التظليل (Intensity Score)
        roi_gray = gray_img[y1:y2, x1:x2]
        darkness = 255.0 - float(roi_gray.mean()) if roi_gray.size > 0 else 0.0
        intensity = min(100.0, darkness)  # نحتفظ بالمقياس 0-100 للتوافق مع باقي النظام

        # 4. المرحلة الإحصائية: عقوبة التباين الشديد (Std Penalty)
        std_val = float(np.std(roi_gray)) if roi_gray.size > 0 else 0
        if std_val > 60:
            intensity *= 0.85
        elif std_val > 40:
            intensity *= 0.92

        return intensity

    # ═══════════════════════════════════════════════
    # قراءة الإجابات
    # ═══════════════════════════════════════════════
            def _read_questions(self, thresh, questions, img_w, img_h,
                        cal_w, cal_h, map_y, map_x,
                        bubble_size_rel, offsets_rel, num_choices,
                        gray_image=None):
        """
        قراءة إجابات الأسئلة — Data-Driven Architecture.
        كل سؤال يحمل choices بإحداثيات rx/ry منفردة لكل خيار.
        المحرك يقرأ مباشرة — لا horizontal_offsets، لا حسابات.
        """
        half_r    = max(int(bubble_size_rel * img_w * 0.5 * 1.20), 8)
        sorted_qs = sorted(questions, key=lambda q: q["id"])
        use_gray  = gray_image is not None

        if use_gray:
            # ── مرحلة 1: قياس darkness لكل فقاعة ──────────────────────
            q_dark_cache = []

            for q in sorted_qs:
                choices = q.get("choices", [])
                n_ch = len(choices)
                if n_ch == 0:
                    q_dark_cache.append([])
                    continue

                # ── المرحلة 1: حساب عتبة الامتلاء الديناميكية للسؤال ──
                fill_ratios = []
                for ch in choices:
                    raw_x = ch["rx"] * img_w
                    raw_y = ch["ry"] * img_h
                    my = map_y(raw_y, raw_x)
                    mx = map_x(raw_x, my)
                    x1 = max(0, int(mx) - half_r)
                    y1 = max(0, int(my) - half_r)
                    x2 = min(img_w, int(mx) + half_r)
                    y2 = min(img_h, int(my) + half_r)
                    if x2 > x1 and y2 > y1:
                        roi_th = thresh[y1:y2, x1:x2]
                        white_pixels = cv2.countNonZero(roi_th)
                        fill_ratios.append(white_pixels / roi_th.size if roi_th.size > 0 else 0)
                    else:
                        fill_ratios.append(0.0)

                if len(fill_ratios) >= 3:
                    sorted_fr = sorted(fill_ratios)
                    trim = int(len(sorted_fr) * 0.2)
                    trimmed = sorted_fr[trim:-trim] if trim > 0 else sorted_fr
                    median_fill = np.median(trimmed) if trimmed else 0.0
                else:
                    median_fill = np.median(fill_ratios) if fill_ratios else 0.0

                fill_threshold = max(0.18, median_fill * 0.35)

                # ── المرحلة 2: تقييم الفقاعات بالعتبة الديناميكية ──
                row = []
                for ch in choices:
                    raw_x = ch["rx"] * img_w
                    raw_y = ch["ry"] * img_h
                    my = map_y(raw_y, raw_x)
                    mx = map_x(raw_x, my)

                    score = self._validate_and_score_bubble(
                        thresh, gray_image, mx, my, half_r,
                        fill_threshold=fill_threshold
                    )
                    if score is None:
                        row.append(0.0)
                    else:
                        row.append(score)
                q_dark_cache.append(row)

            # ── مرحلة 2: تحديد الإجابة لكل سؤال ────────────────────────
            results = []
            for q, row in zip(sorted_qs, q_dark_cache):
                choices = q.get("choices", [])
                n_ch    = len(row)

                if n_ch == 0:
                    result = "EMPTY"
                    results.append(result)
                    logger.info(f"Q{q['id']}: n_ch=0 decision=EMPTY")
                    continue

                best_val = max(row)
                best_i   = row.index(best_val)
                row_mean = sum(row) / n_ch

                stdev    = (sum((v - row_mean)**2 for v in row) / n_ch) ** 0.5 if n_ch >= 2 else 0.0
                sec_val  = sorted(row, reverse=True)[1] if n_ch >= 2 else 0.0

                z_best   = (best_val - row_mean) / stdev if stdev > 0 else 0.0
                z_second = (sec_val  - row_mean) / stdev if stdev > 0 else 0.0
                gap_abs  = best_val - sec_val
                gap_pct  = (best_val - sec_val) / best_val if best_val > 0 else 0.0

                fill_min = -1.0
                filled   = []
                result   = "?"

                if z_best < self.Z_BEST_MIN or gap_abs < self.NOISE_THRESHOLD_ABS:
                    fill_min = max(best_val * 0.60, row_mean * 1.05, 8.0)
                    filled   = [i for i, v in enumerate(row) if v > fill_min]
                    if len(filled) >= 2:
                        lbl_1  = choices[filled[0]]["label"]
                        lbl_2  = choices[filled[1]]["label"]
                        result = f"DUPLICATE:{lbl_1},{lbl_2}"
                    elif len(filled) == 1:
                        result = choices[filled[0]]["label"]
                    else:
                        result = "EMPTY"
                    results.append(result)
                elif z_second < self.Z_SECOND_MAX:
                    fill_min = max(best_val * 0.60, row_mean * 1.05, 8.0)
                    filled   = [i for i, v in enumerate(row) if v > fill_min]
                    if len(filled) >= 2:
                        lbl_1  = choices[filled[0]]["label"]
                        lbl_2  = choices[filled[1]]["label"]
                        result = f"DUPLICATE:{lbl_1},{lbl_2}"
                    else:
                        result = choices[best_i]["label"]
                    results.append(result)
                elif gap_pct >= self.GAP_PCT_MIN:
                    sec_i  = sorted(range(n_ch), key=lambda x: row[x], reverse=True)[1]
                    lbl_1  = choices[best_i]["label"]
                    lbl_2  = choices[sec_i]["label"]
                    result = f"DUPLICATE:{lbl_1},{lbl_2}"
                    results.append(result)
                else:
                    sec_i  = sorted(range(n_ch), key=lambda x: row[x], reverse=True)[1]
                    lbl_1  = choices[best_i]["label"]
                    lbl_2  = choices[sec_i]["label"]
                    result = f"DUPLICATE:{lbl_1},{lbl_2}"
                    results.append(result)

                # ── لوج تشخيصي واحد لكل سؤال ──
                best_lbl = (
                    choices[best_i].get("label", "?")
                    if 0 <= best_i < len(choices)
                    else "?"
                )
                filled_lbls = [
                    choices[i].get("label", "?")
                    for i in filled
                    if 0 <= i < len(choices)
                ]
                logger.info(
                    f"Q{q['id']}: "
                    f"row={np.round(row, 1).tolist()} "
                    f"best={best_val:.1f}({best_lbl}) "
                    f"sec={sec_val:.1f} "
                    f"mean={row_mean:.1f} "
                    f"std={stdev:.1f} "
                    f"z_b={z_best:.2f} "
                    f"z_s={z_second:.2f} "
                    f"gap_abs={gap_abs:.1f} "
                    f"gap_pct={gap_pct:.2f} "
                    f"fill_min={fill_min:.1f} "
                    f"filled={filled_lbls} "
                    f"decision={result}"
                )

            return results

        else:
            # ── مسار thresh (احتياطي) ──────────────────────────────────
            results = []
            for q in sorted_qs:
                best_label = None
                best_score = -1
                for ch in q.get("choices", []):
                    raw_x = ch["rx"] * img_w
                    raw_y = ch["ry"] * img_h
                    my = map_y(raw_y, raw_x)
                    mx = map_x(raw_x, my)
                    y1 = max(0,     int(my) - half_r)
                    y2 = min(img_h, int(my) + half_r)
                    x1 = max(0,     int(mx) - half_r)
                    x2 = min(img_w, int(mx) + half_r)
                    roi   = thresh[y1:y2, x1:x2]
                    score = float(roi.mean()) / 255.0 if roi.size > 0 else 0.0
                    if score > best_score:
                        best_score = score
                        best_label = ch["label"]
                results.append(best_label if (best_label and best_score >= 0.05)
                               else "EMPTY")
            return results


 def _save_debug(self, thresh, template_json, actual_marks_xy,
                    img_w, img_h, cal_w, cal_h, map_y, map_x):
        try:
            os.makedirs(os.path.join(BASE_DIR, "omr_debug"), exist_ok=True)
            ts  = int(time.time())
            dbg = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)

            r = template_json.get("instructions_region",
                                  {"rx1":0.0,"ry1":0.46,"rx2":0.50,"ry2":0.75})
            if "rx1" in r:
                x1,y1=int(r["rx1"]*img_w),int(r["ry1"]*img_h)
                x2,y2=int(r["rx2"]*img_w),int(r["ry2"]*img_h)
            else:
                cw=cal_w; ch=cal_h
                x1,y1=int(r.get("x1",0)*img_w/cw),int(r.get("y1",780)*img_h/ch)
                x2,y2=int(r.get("x2",600)*img_w/cw),int(r.get("y2",1260)*img_h/ch)
            cv2.rectangle(dbg,(x1,y1),(x2,y2),(0,255,255),2)
            cv2.putText(dbg,"EXCLUDED",(x1+5,y1+30),cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,255),2)

            for mx,my in actual_marks_xy:
                cv2.circle(dbg,(int(mx),int(my)),5,(255,0,0),-1)

            for b in template_json.get("id_grid",[]):
                raw_x=self._bx(b,img_w,cal_w)
                my=map_y(self._by(b,img_h,cal_h), raw_x)
                mx=map_x(raw_x, my)
                bw,bh=self._bsize(b,img_w,img_h,cal_w,cal_h)
                cv2.rectangle(dbg,(int(mx-bw//2),int(my-bh//2)),
                              (int(mx+bw//2),int(my+bh//2)),(0,165,255),1)

            cv2.imwrite(os.path.join(BASE_DIR, "omr_debug", f"full_{ts}.png"), dbg)
            cv2.imwrite("debug_overlay.jpg", dbg)
        except Exception as e:
            logger.warning(f"debug: {e}")

    def generate_debug_image(self, thresh, template_json, map_y, map_x):
        return "debug_overlay.jpg"

    # ═══════════════════════════════════════════════
    # process_sheet — المسار الرئيسي
    # ═══════════════════════════════════════════════
    def process_sheet(self, warped_image, template_json):
        if not template_json:
            logger.error("القالب فارغ."); return None

        import time as _t
        _t0 = _t.perf_counter()

        img_h, img_w = warped_image.shape[:2]
        # B3: التقاط الأبعاد الأصلية قبل أيّ resize — لازم لفحص نسبة الـ aspect
        orig_img_w, orig_img_h = img_w, img_h
        cal   = template_json.get("calibration", {})
        cal_w = cal.get("image_w", template_json.get("target_w", img_w))
        cal_h = cal.get("image_h", template_json.get("target_h", img_h))

        # إذا كانت أبعاد الصورة مختلفة عن القالب → resize لتطابقه
        if abs(img_w - cal_w) > 10 or abs(img_h - cal_h) > 10:
            logger.info(f"process_sheet resize: {img_w}×{img_h} → {cal_w}×{cal_h}")
            warped_image = cv2.resize(warped_image, (cal_w, cal_h),
                                      interpolation=cv2.INTER_LINEAR)
            img_h, img_w = cal_h, cal_w

        logger.info(f"process_sheet: {img_w}×{img_h} | cal: {cal_w}×{cal_h}")

        # ── تحويل ذكي للرمادي يتكيف مع لون التظليل ──────────────────────────
        # الماسحات المختلفة تُنتج ألواناً مختلفة للتظليل:
        #   كانون  → تظليل أسود/رمادي → التحويل العادي يكفي
        #   أفيجين → تظليل أحمر/وردي → القناة الخضراء تجعله أكثر قتامة
        # الكشف التلقائي: نقارن متوسط القناة الخضراء مع متوسط الرمادي العادي
        # إذا كانت القناة الخضراء أفتح بفارق واضح → الورقة حمراء/ملونة
        _gray_standard = cv2.cvtColor(warped_image, cv2.COLOR_BGR2GRAY)
        _green_channel = warped_image[:, :, 1]   # القناة الخضراء (B=0, G=1, R=2)
        _red_channel   = warped_image[:, :, 2]   # القناة الحمراء

        # إذا كان متوسط الأحمر أعلى من الأخضر بـ 15+ → ورقة ذات تظليل ملون (أفيجين)
        _red_mean   = float(_red_channel.mean())
        _green_mean = float(_green_channel.mean())
        if _red_mean - _green_mean > 15:
            # القناة الخضراء تجعل الأحمر داكناً ← تزيد darkness للتظليل الملون
            gray_for_id = _green_channel
            logger.info(f"gray_for_id: green channel (red_mean={_red_mean:.1f} > green_mean={_green_mean:.1f}+15) — ماسح ملون")
        else:
            gray_for_id = _gray_standard
            logger.info(f"gray_for_id: standard BGR2GRAY (red_mean={_red_mean:.1f} ≈ green_mean={_green_mean:.1f}) — ماسح عادي")
        hsv_range   = template_json.get("background_hsv_range", None)
        thresh      = self.hsv_color_dropout(warped_image, hsv_range=hsv_range,
                                             paper_type=self.paper_type)
        logger.info(f"  ⏱ hsv_dropout: {_t.perf_counter()-_t0:.3f}s"); _t1=_t.perf_counter()
        thresh      = self._blank_instructions_region(thresh, template_json, img_w, img_h)

        actual_marks_xy, _t_dir, _t_axis = self.detect_timing_track(
            thresh, template_json=template_json, gray_img=gray_for_id)
        logger.info(f"  ⏱ timing_track: {_t.perf_counter()-_t1:.3f}s"); _t2=_t.perf_counter()

        # B1+B3: التحقق الدفاعي — لا يوقف القراءة، فقط يولّد تحذيرات
        warnings_list = self._verify_timing_track(
            template_json, actual_marks_xy, _t_dir, _t_axis)
        warnings_list += self._verify_scale(
            template_json, actual_marks_xy, _t_axis,
            orig_img_w, orig_img_h, img_w, img_h)
        map_y, map_x = self._build_timing_mappers(
            template_json, actual_marks_xy, img_w, img_h,
            direction=_t_dir, axis=_t_axis)
        logger.info(f"  ⏱ build_mappers: {_t.perf_counter()-_t2:.3f}s"); _t3=_t.perf_counter()

        # حفظ debug فقط في وضع التشخيص — معطّل افتراضياً لأقصى سرعة
        if self.debug_mode:
            self._save_debug(thresh, template_json, actual_marks_xy,
                             img_w, img_h, cal_w, cal_h, map_y, map_x)

        components    = template_json.get("components", {})
        has_id        = components.get("has_id",        True)
        has_section   = components.get("has_section",   False)
        has_course    = components.get("has_course",    False)
        has_questions = components.get("has_questions", True)

        student_id = section_id = course_code = ""
        version    = "#"

        # ── قراءة كل شبكة بشكل مستقل ──
        # كل شبكة لها X offset خاص بها

        def _read_grid(grid_bubbles):
            """
            تقرأ شبكة كاملة (رقم/شعبة/مقرر).
            كل عمود يُعيد: رقم | "-" (فارغ) | "?" (مزدوج)
            النتيجة الكاملة: تجميع الأعمدة — إذا كل الأعمدة فارغة تُعيد ""
            """
            if not grid_bubbles:
                return ""
            cols = {}
            for b in grid_bubbles:
                cols.setdefault(b["col"], []).append(b)
            x_off = self._find_id_x_offset(
                gray_for_id, cols, img_w, img_h, cal_w, cal_h,
                map_y=map_y, map_x=map_x)
            digits = []
            for ci in sorted(cols):
                d = self._read_id_column(
                    gray_for_id, cols[ci], img_w, img_h, cal_w, cal_h,
                    x_off, map_y=map_y, map_x=map_x)
                digits.append(d)
            if all(d == "#" for d in digits):
                return ""
            return "".join(digits)

        id_grid         = template_json.get("id_grid", [])
        sec_grid        = template_json.get("sec_grid", [])
        course_grid     = template_json.get("course_grid", [])
        version_bubbles = template_json.get("version_bubbles", [])

        final_id_grid     = id_grid
        final_sec_grid    = sec_grid
        final_course_grid = course_grid

        if has_id:      student_id  = _read_grid(final_id_grid)
        if has_section: section_id  = _read_grid(final_sec_grid)
        if has_course:  course_code = _read_grid(final_course_grid)
        logger.debug(f"النتائج: الرقم={student_id}, الشعبة={section_id}, المقرر={course_code}, النموذج={version}")
        logger.info(f"  ⏱ read_grids: {_t.perf_counter()-_t3:.3f}s"); _t4=_t.perf_counter()

        # ── النموذج ──
        vb = (template_json.get("version_bubbles") or
              template_json.get("version_area") or [])
        if vb:
            d = self._read_version(thresh, vb, img_w, img_h, cal_w, cal_h, map_y, map_x,
                                   gray_image=gray_for_id)
            # d الآن يحمل label مباشرة ("1","2","A","B"...)
            version = str(d) if d and d != "#" else "#"
        else:
            version = "#"

        # ── الإجابات ──
        results = []
        if has_questions:
            questions   = template_json.get("questions", [])
            num_choices = template_json.get("num_choices", 5)

            bubble_rel = template_json.get("bubble_size_rel", 0.0)
            if not bubble_rel and template_json.get("bubble_size"):
                bubble_rel = template_json["bubble_size"] / cal_w

            logger.info(f"   questions={len(questions)} bubble_rel={bubble_rel:.4f}")
            if questions:
                results = self._read_questions(
                    thresh, questions,
                    img_w, img_h, cal_w, cal_h,
                    map_y, map_x,
                    bubble_rel, [], num_choices,
                    gray_image=gray_for_id)
                non_empty = sum(1 for r in results if r != "EMPTY")
                logger.info(f"   نتائج: {len(results)} سؤال | {non_empty} غير فارغة")

        logger.info(f"  ⏱ read_questions: {_t.perf_counter()-_t4:.3f}s")
        # ── قص منطقة اسم الطالب وحفظها ──────────────────────
        name_image_path = None
        name_area = template_json.get("name_area")
        if name_area:
            try:
                # دعم صيغتين: (rx1,ry1,rx2,ry2) أو (x,y,w,h)
                if "rx1" in name_area:
                    # صيغة النسبية (relative)
                    na_x = int(name_area.get("rx1", 0) * img_w)
                    na_y = int(name_area.get("ry1", 0) * img_h)
                    na_x2 = int(name_area.get("rx2", 0) * img_w)
                    na_y2 = int(name_area.get("ry2", 0) * img_h)
                    na_w = na_x2 - na_x
                    na_h = na_y2 - na_y
                else:
                    # الصيغة القديمة (x,y,w,h) معايرة
                    na_x = int(name_area.get("x", 0) * img_w / cal_w)
                    na_y = int(name_area.get("y", 0) * img_h / cal_h)
                    na_w = int(name_area.get("w", 0) * img_w / cal_w)
                    na_h = int(name_area.get("h", 0) * img_h / cal_h)
                # تأكد أن الإحداثيات داخل حدود الصورة
                na_x = max(0, min(na_x, img_w - 1))
                na_y = max(0, min(na_y, img_h - 1))
                na_w = max(10, min(na_w, img_w - na_x))
                na_h = max(10, min(na_h, img_h - na_y))
                crop = warped_image[na_y:na_y+na_h, na_x:na_x+na_w]
                if crop.size > 0:
                    # نُرجع الـ array مباشرة — بدون كتابة مؤقتة على الديسك
                    name_image_path = crop
                    logger.info(f" name crop ready: {crop.shape}")
            except Exception as _ne:
                logger.warning(f"name_area crop failed: {_ne}")

        return {
            "student_id":  student_id,
            "section_id":  section_id,
            "course_code": course_code,
            "version":     version,
            "answers":     results,
            "name_image":  name_image_path,
            "debug_image": "debug_overlay.jpg",
            # بيانات التوقيت — تُستخدم في UI لرسم الدوائر في مكانها الصحيح
            "timing_marks_actual": [[int(m[0]), int(m[1])] for m in actual_marks_xy],
            "timing_axis":         _t_axis,   # "vertical" | "horizontal"
            "timing_direction":    _t_dir,
            "img_w":               img_w,
            "img_h":               img_h,
            # B1: تحذيرات التحقق الدفاعي — تُعرض في UI عند وجود اختلاف مع القالب
            "warnings":            warnings_list,        }
