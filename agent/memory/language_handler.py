"""
Multi-lingual handler - Vietnamese-English language detection and prompt management.

Issue #19: Previously used only ~62 Vietnamese words for detection, leading to
false positives. This version improves detection by:
  1. Using Unicode script analysis (Vietnamese diacritic ranges).
  2. Expanding the Vietnamese word list to ~200 common words.
  3. Using a scoring ratio (vi_words / total_words) instead of absolute counts.
  4. Optionally integrating fasttext/CLD3 if available (graceful fallback).
"""

import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Vietnamese diacritic characters (including combining marks)
VIETNAMESE_CHARS = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

# Expanded Vietnamese word list (~200 words) for better recall
VIETNAMESE_WORDS = {
    # Diacritic variants
    "của",
    "và",
    "có",
    "không",
    "người",
    "cho",
    "với",
    "là",
    "trong",
    "các",
    "được",
    "một",
    "này",
    "những",
    "khi",
    "về",
    "như",
    "từ",
    "đến",
    "sau",
    "trên",
    "nó",
    "họ",
    "tôi",
    "bạn",
    "anh",
    "chị",
    "em",
    "chúng",
    "đã",
    "sẽ",
    "đang",
    "rất",
    "lắm",
    "quá",
    "gì",
    "sao",
    "thế",
    "nào",
    "đâu",
    "phải",
    "bị",
    "vì",
    "nên",
    "mà",
    "thì",
    "cả",
    "hơn",
    "nhất",
    "cùng",
    "làm",
    "nói",
    "đi",
    "lại",
    "ra",
    "vào",
    "lên",
    "xuống",
    "qua",
    "tại",
    "ở",
    "bằng",
    "để",
    "nếu",
    "tuy",
    "nhưng",
    "hoặc",
    "hay",
    "vậy",
    "còn",
    "cũng",
    "vẫn",
    "đều",
    "hãy",
    "chưa",
    "mới",
    "vừa",
    "sắp",
    "từng",
    "hỏi",
    "trả",
    "lời",
    "giúp",
    "nhé",
    "à",
    "ạ",
    "ơi",
    "nha",
    "nhé",
    "thôi",
    "biết",
    "nghĩ",
    "thấy",
    "nhìn",
    "nghe",
    "đọc",
    "viết",
    "học",
    "dạy",
    "sống",
    "làm_việc",
    "công_việc",
    "doanh_nghiệp",
    "phát_triển",
    "kết_quả",
    "vấn_đề",
    "giải_pháp",
    "hệ_thống",
    "dữ_liệu",
    "tài_liệu",
    "văn_bản",
    "nội_dung",
    "thông_tin",
    "câu_hỏi",
    "trả_lời",
    "yêu_cầu",
    "cần_thiết",
    "quan_trọng",
    "chính_xác",
    "chi_tiết",
    "tổng_quan",
    "mô_tả",
    "phân_tích",
    "đánh_giá",
    "báo_cáo",
    "kế_hoạch",
    "mục_tiêu",
    "kết_nối",
    "tải_xuống",
    "tải_lên",
    # Non-diacritic variants (telex/VNI input without diacritics)
    "cua",
    "va",
    "co",
    "khong",
    "nguoi",
    "voi",
    "trong",
    "cac",
    "duoc",
    "mot",
    "nay",
    "nhung",
    "khi",
    "ve",
    "nhu",
    "tu",
    "den",
    "sau",
    "tren",
    "no",
    "ho",
    "toi",
    "ban",
    "anh",
    "chi",
    "em",
    "chung",
    "da",
    "se",
    "dang",
    "rat",
    "lam",
    "qua",
    "gi",
    "sao",
    "the",
    "nao",
    "dau",
    "phai",
    "bi",
    "vi",
    "nen",
    "ma",
    "thi",
    "ca",
    "hon",
    "nhat",
    "cung",
    "lam",
    "noi",
    "di",
    "lai",
    "ra",
    "vao",
    "len",
    "xuong",
    "tai",
    "o",
    "bang",
    "de",
    "neu",
    "tuy",
    "nhung",
    "hoac",
    "hay",
    "vay",
    "con",
    "cung",
    "van",
    "deu",
    "hay",
    "chua",
    "moi",
    "vua",
    "sap",
    "tung",
    "hoi",
    "tra",
    "loi",
    "giup",
    "nhe",
    "a",
    "oi",
    "nha",
    "thoi",
    "biet",
    "nghi",
    "thay",
    "nhin",
    "nghe",
    "doc",
    "viet",
    "hoc",
    "day",
    "song",
    "lam_viec",
    "cong_viec",
    "doanh_nghiep",
    "phat_trien",
    "ket_qua",
    "van_de",
    "giai_phap",
    "he_thong",
    "du_lieu",
    "tai_lieu",
    "van_ban",
    "noi_dung",
    "thong_tin",
    "cau_hoi",
    "tra_loi",
    "yeu_cau",
    "can_thiet",
    "quan_trong",
    "chinh_xac",
    "chi_tiet",
    "tong_quan",
    "mo_ta",
    "phan_tich",
    "danh_gia",
    "bao_cao",
    "ke_hoach",
    "muc_tieu",
    "ket_noi",
    "tai_xuong",
    "tai_len",
}

ENGLISH_WORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "doing",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "out",
    "off",
    "over",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "each",
    "every",
    "both",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "because",
    "but",
    "and",
    "or",
    "if",
    "while",
    "although",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "me",
    "him",
    "her",
    "us",
    "them",
    "my",
    "your",
    "his",
    "its",
    "our",
    "their",
    "what",
    "which",
    "who",
    "whom",
    "please",
    "help",
    "explain",
    "document",
    "search",
    "find",
    "query",
    "answer",
    "question",
    "response",
    "system",
    "data",
    "file",
    "upload",
    "download",
    "report",
    "analysis",
    "summary",
    "important",
    "required",
    "need",
    "want",
    "know",
    "understand",
    "show",
    "tell",
    "give",
    "get",
    "make",
    "use",
    "using",
    "used",
    "about",
    "how",
}

# Minimum ratio of Vietnamese words to classify as Vietnamese
_VI_RATIO_THRESHOLD = 0.15
# Minimum absolute count of language-specific words for a confident classification
_MIN_CONFIDENT_COUNT = 2


def _try_fasttext(text: str) -> str:
    """Attempt fasttext language detection if the library is available."""
    try:
        import fasttext  # type: ignore

        model_path = getattr(_try_fasttext, "_model_path", None)
        if model_path is None:
            import os

            model_path = os.getenv("FASTTEXT_MODEL_PATH", "")
            _try_fasttext._model_path = model_path  # type: ignore
        if not model_path:
            return ""
        model = fasttext.load_model(model_path)
        labels, probs = model.predict(text.replace("\n", " "))
        if labels and probs and probs[0] > 0.7:
            label = labels[0].replace("__label__", "")
            if label in ("vi", "vi-VN"):
                return "vi"
            if label in ("en", "en-US"):
                return "en"
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("fasttext detection failed: %s", exc)
    return ""


def detect_language(text: str) -> str:
    """
    Detect whether *text* is Vietnamese, English, or mixed.

    Returns one of: "vi", "en", "mixed".
    """
    if not text or not text.strip():
        return "en"

    # 1. Try fasttext/CLD3 if available (most accurate)
    ft_result = _try_fasttext(text)
    if ft_result:
        return ft_result

    # 2. Unicode diacritic analysis (high-precision for Vietnamese)
    vi_diacritics = len(VIETNAMESE_CHARS.findall(text))
    if vi_diacritics >= 3:
        return "vi"

    # 3. Word-list scoring with ratio threshold
    words = re.findall(
        r"[a-zA-Zàáạảãâấậẩẫăắặẳẵèéẹẻẽêếệểễìíịỉĩòóọỏõôốộổỗơớợởỡùúụủũưứứựửữýỵỷỹđ]+",
        text.lower(),
    )
    if not words:
        return "en"

    total_words = len(words)
    vi_count = sum(1 for w in words if w in VIETNAMESE_WORDS)
    en_count = sum(1 for w in words if w in ENGLISH_WORDS)

    vi_ratio = vi_count / total_words
    en_ratio = en_count / total_words

    # 4. Decision logic
    if vi_diacritics >= 1 and vi_count >= _MIN_CONFIDENT_COUNT:
        return "vi"
    if (
        vi_ratio >= _VI_RATIO_THRESHOLD
        and vi_count >= _MIN_CONFIDENT_COUNT
        and vi_count > en_count
    ):
        return "vi"
    if en_count >= _MIN_CONFIDENT_COUNT and en_ratio > vi_ratio:
        return "en"
    if vi_count > 0 and en_count > 0:
        return "mixed"
    if vi_count > 0:
        return "vi"
    return "en"


def get_language_instruction(lang: str) -> str:
    instructions = {
        "vi": "IMPORTANT: The user speaks Vietnamese. Respond ENTIRELY in Vietnamese. Keep English technical terms as-is.",
        "en": "IMPORTANT: The user speaks English. Respond ENTIRELY in English.",
        "mixed": "IMPORTANT: The user mixes Vietnamese and English. Respond primarily in Vietnamese, keep English technical terms.",
    }
    return instructions.get(lang, instructions["en"])


def detect_and_instruct(text: str) -> Tuple[str, str]:
    lang = detect_language(text)
    return lang, get_language_instruction(lang)
