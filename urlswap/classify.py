# -*- coding: utf-8 -*-
"""根据 URL / 文件名 猜测模型类型，决定放入 ComfyUI/models 下的哪个子目录。

规则按优先级从上到下匹配（先匹配到的胜出），全部未命中时默认 checkpoints。
界面上每个任务仍可手动双击修改分类，以手动结果为准。
"""
import re
from urllib.parse import unquote

# (目录名, 中文说明) —— UI 下拉框顺序即此顺序
CATEGORIES = [
    ("checkpoints", "大模型 / Checkpoint"),
    ("diffusion_models", "Diffusion / UNet 底模"),
    ("loras", "LoRA"),
    ("vae", "VAE"),
    ("controlnet", "ControlNet"),
    ("clip", "CLIP / 文本编码器"),
    ("clip_vision", "CLIP Vision"),
    ("unet", "UNet（旧版目录）"),
    ("upscale_models", "放大模型"),
    ("ipadapter", "IP-Adapter"),
    ("embeddings", "Embedding / Textual Inversion"),
    ("other", "其他（自行建子目录）"),
]

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
    """返回 (category, reason)。"""
    text = url.lower()
    try:
        text = unquote(text)
    except Exception:
        pass
    for cat, patterns in _RULES:
        for pat in patterns:
            if re.search(pat, text):
                return cat, "命中关键词: " + pat.replace("\\b", "")
    return "checkpoints", "未识别特征, 默认放 checkpoints（可双击任务修改）"
