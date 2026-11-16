# -*- coding: utf-8 -*-
"""无界面冒烟测试：分类 / 域名替换 / 断点续传 / 任务恢复。
用法: py tools/smoke_test.py
"""
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from urlswap.classify import classify_url          # noqa: E402
from urlswap import project                        # noqa: E402
from urlswap.downloader import (                   # noqa: E402
    DownloadManager, filename_from_url, normalize_url, to_mirror)
import urlswap.downloader as dlmod                # noqa: E402

FAILS = []


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        FAILS.append(msg)


# ---------------------------------------------------------------- 分类测试
CASES = [
    ("https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/resolve/main/v1-5-pruned-emaonly-fp16.safetensors", "checkpoints"),
    ("https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors", "diffusion_models"),
    ("https://huggingface.co/AnyLoRA_epochV1/AnyLoRA/resolve/main/anyloRA.safetensors", "loras"),
    ("https://civitai.com/api/download/models/12345?filename=Ghibli_v6.safetensors&type=LoRA", "loras"),
    ("https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors", "vae"),
    ("https://huggingface.co/comfyanonymous/ControlNet-v1-1_fp16_safetensors/resolve/main/control_v11f1p_sd15_depth.pth", "controlnet"),
    ("https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors", "clip"),
    ("https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors", "clip"),
    ("https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl_vit-h.safetensors", "ipadapter"),
    ("https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/image_encoder/pytorch_model.bin", "ipadapter"),
    ("https://huggingface.co/2nt/Esgrgan_aqualibria/resolve/main/2xAni44_v30.pth", "upscale_models"),
    ("https://huggingface.co/lllyasviel/misc/resolve/main/clip_vision_vit_h.safetensors", "clip_vision"),
    ("https://huggingface.co/jcjohnson/sd-textual-inversion-embeds-test/resolve/main/bad_prompt_version2-neg.pt", "embeddings"),
    ("https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors", "checkpoints"),
    # —— v1.1.1 分类修复案例 ——
    ("https://hf-mirror.com/x/y/resolve/main/minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors", "loras"),
    ("https://hf-mirror.com/x/y/resolve/main/minimax_h3_fl2va_pruned_int8_convrot.safetensors", "diffusion_models"),
    ("https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_turbo_1.0.safetensors", "checkpoints"),
    ("https://hf-mirror.com/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors", "diffusion_models"),
    ("https://hf-mirror.com/Comfy-Org/Hyper-SD/resolve/main/Hyper-SD15-8steps-FP8.safetensors", "diffusion_models"),
    ("https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "clip"),
]
print("== 分类测试 ==")
for url, want in CASES:
    got, why = classify_url(url)
    check(got == want, "classify %s -> %s (%s)" % (url.rsplit("/", 1)[-1][:48], got, why))

print("\n== 域名替换 / 文件名 ==")
check(to_mirror("https://huggingface.co/a/b/resolve/main/x.safetensors")
      == "https://hf-mirror.com/a/b/resolve/main/x.safetensors", "huggingface.co -> hf-mirror.com")
check(to_mirror("https://www.huggingface.co/a/b/resolve/main/x.safetensors")
      == "https://hf-mirror.com/a/b/resolve/main/x.safetensors", "www.huggingface.co -> hf-mirror.com")
check(to_mirror("https://civitai.com/api/download/models/1") == "https://civitai.com/api/download/models/1",
      "非 HF 域名不变")
check(filename_from_url("https://hf-mirror.com/a/b/resolve/main/flux1-dev%20fp16.safetensors")
      == "flux1-dev fp16.safetensors", "文件名解析 + URL 解码")
check(normalize_url("https://hf-mirror.com/Comfy-Org/MiniMax-H3/blob/main/text_encoders/x.safetensors")
      == "https://hf-mirror.com/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/x.safetensors",
      "blob 网页地址自动转 resolve 直链")
check(normalize_url("https://huggingface.co/a/b/blob/main/f.bin")
      == "https://huggingface.co/a/b/resolve/main/f.bin", "huggingface.co 的 blob 也转换")
check(normalize_url("https://civitai.com/api/download/models/1?x=1")
      == "https://civitai.com/api/download/models/1?x=1", "非 HF 地址不动")
check(normalize_url("https://hf-mirror.com/a/b/resolve/main/f.safetensors")
      == "https://hf-mirror.com/a/b/resolve/main/f.safetensors", "resolve 直链保持不变")

print("\n== 项目自动检测（打印，不判定） ==")
found = project.auto_detect()
for f in found:
    print("   找到项目:", f, "-> models:", project.models_dir_of(f))
if not found:
    print("   （本机未检测到，属正常，可手动浏览选择）")

# ------------------------------------------------------- 本地断点续传测试
print("\n== 本地服务器 断点续传/暂停/恢复/跳过 测试 ==")
DATA = bytes((i * 7 + 13) & 0xFF for i in range(2 * 1024 * 1024))  # 2MB


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/page"):
            body = b"<!DOCTYPE html><html><body>sign in</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        pos = 0
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            try:
                pos = int(rng[6:].split("-")[0] or 0)
            except ValueError:
                pos = 0
        self.count = getattr(self, "count", 0) + 1
        H.RANGE_SEEN = H.RANGE_SEEN or pos > 0
        if pos:
            self.send_response(206)
            self.send_header("Content-Range",
                             "bytes %d-%d/%d" % (pos, len(DATA) - 1, len(DATA)))
        else:
            self.send_response(200)
        body = DATA[pos:]
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", '"test-etag"')
        self.end_headers()
        try:
            for i in range(0, len(body), 64 * 1024):
                self.wfile.write(body[i:i + 64 * 1024])
                time.sleep(0.045)   # 限速方便中途暂停
        except (ConnectionError, OSError):
            pass

    def log_message(self, *a):
        pass


H.RANGE_SEEN = False
srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]
url = "http://127.0.0.1:%d/big_test_model.safetensors" % port

tmp = Path(__file__).resolve().parent / "_tmp_test"
if tmp.exists():
    for p in tmp.rglob("*"):
        if p.is_file():
            p.unlink()
tmp.mkdir(exist_ok=True)
dlmod.TASKS_FILE = tmp / "tasks.json"

settings = {"skip_existing": True}
mgr = DownloadManager(settings, lambda: str(tmp),
                      on_event=lambda m: print("   [log]", m.splitlines()[0]))
mgr.add_tasks([url], auto_mirror=False)
check(mgr.snapshot()[0]["category"] == "checkpoints", "未识别文件默认 checkpoints")
mgr.start(1)

# 下载中途暂停
deadline = time.time() + 15
while time.time() < deadline:
    s = mgr.snapshot()[0]
    if s["status"] == "downloading" and s["downloaded"] > 300 * 1024:
        break
    time.sleep(0.05)
mgr.stop()
time.sleep(0.6)
s = mgr.snapshot()[0]
check(s["status"] == "paused", "暂停后状态为 paused (实际 %s)" % s["status"])
sub = tmp / "checkpoints"          # add_tasks 默认分类 checkpoints 子目录
part = sub / ("big_test_model.safetensors.part")
check(part.exists(), ".part 断点文件已保留 (%d 字节)" % (part.stat().st_size if part.exists() else -1))
check((sub / "big_test_model.safetensors.part.meta.json").exists(), "断点 meta 已写入")

# 模拟程序重启：新管理器从 tasks.json 恢复并续传
mgr2 = DownloadManager(settings, lambda: str(tmp),
                       on_event=lambda m: print("   [log]", m.splitlines()[0]))
mgr2.load()
check(len(mgr2.snapshot()) == 1 and mgr2.snapshot()[0]["status"] in ("paused", "pending"),
      "重启后任务已恢复待续传")
mgr2.start(1)
deadline = time.time() + 30
while time.time() < deadline:
    s = mgr2.snapshot()[0]
    if s["status"] in ("done", "failed"):
        break
    time.sleep(0.1)
check(s["status"] == "done", "断点续传完成 (状态 %s)" % s["status"])
dest = sub / "big_test_model.safetensors"
check(dest.exists() and dest.read_bytes() == DATA, "落盘文件内容完整正确")
check(H.RANGE_SEEN, "续传确实使用了 Range 请求 (206)")
check(not part.exists(), ".part 已清理")

# 再次添加同一任务 -> 已存在跳过
mgr3 = DownloadManager(settings, lambda: str(tmp),
                       on_event=lambda m: print("   [log]", m.splitlines()[0]))
mgr3.add_tasks([url], auto_mirror=False)
mgr3.start(1)
time.sleep(1.2)
s = mgr3.snapshot()[-1]
check(s["status"] == "skipped", "已存在文件被跳过 (状态 %s)" % s["status"])
mgr3.stop()

# HTML 页面地址（非直链）应直接失败且不留残片
mgr5 = DownloadManager(settings, lambda: str(tmp),
                       on_event=lambda m: print("   [log]", m.splitlines()[0]))
mgr5.add_tasks(["http://127.0.0.1:%d/page.safetensors" % port], auto_mirror=False)
mgr5.start(1)
time.sleep(1.5)
s5 = mgr5.snapshot()[-1]
check(s5["status"] == "failed", "HTML 页面任务直接判失败 (状态 %s)" % s5["status"])
check("HTML" in (s5["error"] or ""), "失败原因提示了 HTML 网页")
check(not (tmp / "checkpoints" / "page.safetensors.part").exists(), "HTML 页面任务未留残片")
mgr5.stop()
srv.shutdown()

# ------------------------------------------------------------ 真实镜像测试
print("\n== hf-mirror.com 真实下载测试（网络失败不算 FAIL） ==")
try:
    live_url = ("https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5"
                "/resolve/main/feature_extractor/preprocessor_config.json")
    mgr4 = DownloadManager(settings, lambda: str(tmp),
                           on_event=lambda m: print("   [log]", m.splitlines()[0]))
    mgr4.add_tasks([live_url], auto_mirror=True)
    t = mgr4.snapshot()[-1]
    check(t["url"].startswith("https://hf-mirror.com/"), "真实测试地址已替换为 hf-mirror")
    mgr4.start(1)
    deadline = time.time() + 60
    while time.time() < deadline:
        t = mgr4.snapshot()[-1]
        if t["status"] in ("done", "failed", "skipped"):
            break
        time.sleep(0.3)
    if t["status"] == "done":
        check(True, "hf-mirror 真实下载成功 (%d 字节)" % t["total"])
    elif t["status"] == "skipped":
        check(True, "hf-mirror 测试文件已存在，跳过（视为通过）")
    else:
        print("   SKIP  网络不可达: %s" % t.get("error", t["status"]))
    mgr4.stop()
except Exception as e:
    print("   SKIP  跳过真实下载测试:", e)

# 用户实测案例：hf-mirror 的 blob 网页地址（15GB 大文件，只验证前段流正常）
try:
    big_url = ("https://hf-mirror.com/Comfy-Org/MiniMax-H3/blob/main/text_encoders/"
               "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
    bigdir = tmp / "bigtest"
    bigdir.mkdir(exist_ok=True)
    mgr6 = DownloadManager({"skip_existing": False}, lambda: str(bigdir),
                           on_event=lambda m: print("   [log]", m.splitlines()[0]))
    mgr6.add_tasks([big_url], auto_mirror=True)
    t6 = mgr6.snapshot()[-1]
    check("/resolve/" in t6["url"], "blob 地址已自动转 resolve 直链（用户案例）")
    check(t6["category"] == "clip", "MiniMax-H3 text_encoders 归类为 clip")
    mgr6.start(1)
    deadline = time.time() + 30
    ok6 = False
    while time.time() < deadline:
        t6 = mgr6.snapshot()[0]
        if t6["status"] == "downloading" and t6["downloaded"] > 1024 * 1024:
            ok6 = True
            break
        if t6["status"] in ("done", "failed"):
            break
        time.sleep(0.3)
    if ok6:
        check(t6["total"] > 10_000_000_000,
              "用户案例 15GB 大文件真实开始下载 (%d 字节)" % t6["total"])
    else:
        print("   SKIP  用户案例网络异常: %s" % t6.get("error", t6["status"]))
    mgr6.stop()
    time.sleep(0.5)
    for p in bigdir.rglob("*"):
        if p.is_file():
            p.unlink()
except Exception as e:
    print("   SKIP  跳过大文件案例测试:", e)

print()
if FAILS:
    print("共 %d 项失败:" % len(FAILS))
    for f in FAILS:
        print(" -", f)
    sys.exit(1)
print("全部测试通过 ✔")
