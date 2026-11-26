# -*- coding: utf-8 -*-
"""根据 URL / 文件名 猜测模型类型，决定放入 ComfyUI/models 下的哪个子目录。

匹配优先级：
  1. model_table.json —— ComfyUI 官方工作流模板的「模型文件名 -> 目录」对照表（精确匹配）
  2. 关键词规则（自上而下，先匹配者胜出），全部未命中时默认 checkpoints
界面上每个任务仍可手动双击修改分类，以手动结果为准。
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

# 分类目录 key（语言无关）—— 显示名由 i18n 提供: tr("cat." + key)；下拉顺序即此顺序
# 与 ComfyUI 官方 models 子目录对齐（含旧版别名目录 clip / unet 与常用扩展 ipadapter）
CATEGORIES = [
    "checkpoints", "diffusion_models", "text_encoders", "loras", "vae",
    "vae_approx", "clip_vision", "controlnet", "embeddings",
    "upscale_models", "latent_upscale_models", "model_patches",
    "style_models", "ipadapter", "clip", "unet", "gligen", "hypernetworks",
    "photomaker", "classifiers", "detection", "geometry_estimation",
    "optical_flow", "frame_interpolation", "background_removal",
    "audio_encoders", "other",
]

_TABLE_FILE = Path(__file__).with_name("model_table.json")


@lru_cache(maxsize=1)
def _official_table():
    """官方模型对照表（小写文件名 -> 目录），缺失时优雅降级（空表则只走关键词规则）。

    内置表（随程序分发）先加载；APP_DIR（源码=仓库根 / EXE=EXE 同目录）下如放同名
    model_table.json，则外置条目优先，方便用户不改源码/不重打包直接覆盖扩充。
    """
    from .settings import APP_DIR
    table = {}
    for path in (_TABLE_FILE, APP_DIR / "model_table.json"):
        try:
            raw = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict):
            table.update({k.lower(): v for k, v in raw.items()
                          if not k.startswith("_") and isinstance(v, str)})
    return table


def _fname_from_url(url):
    """取 URL 对应的目标文件名（含 civitai ?filename= 参数），小写。"""
    try:
        parts = urlsplit(url)
    except ValueError:
        return ""
    if parts.query:
        for kv in parts.query.split("&"):
            k, _, v = kv.partition("=")
            if k.lower() == "filename" and v:
                return unquote(v).strip().lower()
    return unquote(parts.path.rstrip("/").rsplit("/", 1)[-1]).lower()

# (目录名, [匹配模式, ...])，按顺序尝试
_RULES = [
    ("loras", [
        r"lora", r"lyco", r"locon",
    ]),
    ("ipadapter", [
        r"ip[-_ ]?adapter",
    ]),
    ("controlnet", [
        r"control[-_ ]?net", r"/control_v\d", r"^control_v",
        r"\bcn[-_](openpose|canny|depth|lineart|tile|seg|normal)",
    ]),
    ("clip_vision", [
        r"clip[-_ ]?vision", r"clip[-_]vit", r"siglip",
        r"image[-_]encoder", r"vision[-_]model",
    ]),
    ("vae", [
        r"\bvae", r"vae[-_]", r"ft-mse", r"ft-safe", r"ft-ema", r"ft_mse",
        r"ae\.safetensors", r"taesd", r"taesdxl", r"taesx",
    ]),
    ("upscale_models", [
        r"upscal", r"esrgan", r"ultrasharp", r"remacri", r"lollypop",
        r"\b\d+x[a-z]", r"\bx4+\b",
    ]),
    ("embeddings", [
        r"embedding", r"textual[-_]inversion", r"\be[45]c\b", r"\be[45]cs?[-_]",
    ]),
    ("clip", [
        r"open[-_]?clip", r"\bt5\b", r"t5[-_.]?xxl", r"t5xxl", r"umt5",
        r"maclip", r"\bbert\b", r"text[-_]encoder", r"clip[-_]?(bigg|l|g)\b",
        r"\bclip\b",
    ]),
    ("diffusion_models", [
        r"\bflux", r"flux\.1", r"\bsd3(\.5|_5|5\b|[-_])", r"stable[-_]diffusion[-_]3",
        r"z[-_]?image", r"\billum", r"ltx[-_]?v", r"hunyuan", r"wan2", r"cogvideo",
        r"diffusion_pytorch_model", r"\bunet\b",
        r"hyper[-_]?(sd|xl)",
        # 量化底模特征（int8/int4/fp8/nvfp4/convrot 等；勿用单独的 pruned，
        # SD1.5 官方名 v1-5-pruned-emaonly 会误伤）
        r"int8", r"int4", r"fp8", r"nvfp4", r"convrot",
        r"gguf", r"awq", r"blockint",
    ]),
    ("checkpoints", [
        r"checkpoint", r"sd[-_]?xl", r"sdxl", r"v1[-_.]5", r"sd[-_]1[-_.]5",
        r"dreamshaper", r"animagine", r"\bpony", r"anything[-_]v", r"meinheld",
        r"majic", r"realistic[-_]vision", r"juggernaut", r"darksushi",
        r"counterfeit", r"official[-_]final", r"full[-_]fp16", r"deliberate",
        r"inkpunk", r"rev-animated", r"novelai",
    ]),
    # 第二轮兜底前的 LoRA 特征：速度类 LoRA 常不含 “lora” 字样
    ("loras", [
        r"turbo", r"\d+step", r"lightning", r"lightx2v", r"litza",
    ]),
]


def classify_url(url):
    """返回 (category, why)。

    why is None  -> 命中官方模型对照表（精确文件名）；
    why == ""    -> 未命中任何特征，默认 checkpoints；
    其他         -> 命中的关键词模式串。
    """
    hit = _official_table().get(_fname_from_url(url))
    if hit:
        return hit, None
    text = url.lower()
    try:
        text = unquote(text)
    except Exception:
        pass
    for cat, patterns in _RULES:
        for pat in patterns:
            if re.search(pat, text):
                return cat, pat.replace("\\b", "")
    return "checkpoints", ""
