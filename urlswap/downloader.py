# -*- coding: utf-8 -*-
"""多线程下载器：断点续传、暂停/继续、失败重试、任务持久化。

仅使用 Python 标准库（urllib），无第三方依赖。
断点续传原理：
  * 下载写入 <文件名>.part，旁边记录 <文件名>.part.meta.json（ETag / 总大小）
  * 重新启动时携带 Range: bytes=<已下载>- 请求继续
  * 服务端文件变化（ETag 不一致）或不支持 Range 时自动从头重下
  * 任务列表保存在 tasks.json，程序关闭再打开自动恢复
"""
import json
import os
import queue
import re
import threading
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from . import classify
from .settings import TASKS_FILE

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 ComfyURLSwap/1.0")
CHUNK = 256 * 1024

TERMINAL = ("done", "skipped", "failed", "canceled")


class PausedSignal(Exception):
    """内部信号：任务被暂停或取消。"""


class BadUrlError(Exception):
    """URL 指向网页而非文件，重试无意义，直接判失败。"""


def normalize_url(u):
    """把 HuggingFace 的网页地址 /blob/ 自动转换为直链地址 /resolve/。

    https://hf-mirror.com/用户/仓库/blob/版本/路径/文件.safetensors
      -> https://hf-mirror.com/用户/仓库/resolve/版本/路径/文件.safetensors
    """
    try:
        parts = urlsplit(u)
        host = (parts.hostname or "").lower()
        if (host in ("huggingface.co", "hf-mirror.com")
                or host.endswith(".huggingface.co")):
            new_path = re.sub(r"^(/[^/]+/[^/]+)/blob/", r"\1/resolve/", parts.path)
            if new_path != parts.path:
                return parts._replace(path=new_path).geturl()
    except ValueError:
        pass
    return u


def to_mirror(u):
    """把 huggingface.co 域名替换为 hf-mirror.com，其它域名原样返回。"""
    try:
        parts = urlsplit(u)
        host = (parts.hostname or "").lower()
        if host == "huggingface.co" or host.endswith(".huggingface.co"):
            netloc = parts.netloc.lower().replace("huggingface.co", "hf-mirror.com")
            if netloc == "www.hf-mirror.com":
                netloc = "hf-mirror.com"
            return parts._replace(netloc=netloc).geturl()
    except ValueError:
        pass
    return u


def filename_from_url(u):
    try:
        parts = urlsplit(u)
        path = parts.path
    except ValueError:
        parts, path = None, u
    # civitai 等站点把真实文件名放在 ?filename= 查询参数里
    if parts and parts.query:
        for kv in parts.query.split("&"):
            k, _, v = kv.partition("=")
            if k.lower() == "filename" and v:
                cand = unquote(v).strip()
                if cand:
                    path = "/" + cand
                    break
    name = unquote(path.rstrip("/").rsplit("/", 1)[-1])
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name or "model.safetensors"


class Task:
    def __init__(self, source="", url="", filename="", category="checkpoints", dest=""):
        self.id = uuid.uuid4().hex[:10]
        self.source = source          # 用户输入的原始 URL
        self.url = url                # 实际下载地址（可能已换镜像域名）
        self.filename = filename
        self.category = category
        self.dest = dest              # 最终落盘完整路径
        self.status = "pending"       # pending/downloading/paused/done/failed/skipped/canceled
        self.downloaded = 0
        self.total = 0
        self.speed = 0.0
        self.error = ""
        self.retries = 0
        self.queued = False
        self.cancel_event = threading.Event()

    def to_dict(self):
        return {k: getattr(self, k) for k in
                ("id", "source", "url", "filename", "category", "dest",
                 "status", "downloaded", "total", "error", "retries")}

    @classmethod
    def from_dict(cls, d):
        t = cls()
        for k in ("id", "source", "url", "filename", "category", "dest", "error"):
            if k in d:
                setattr(t, k, d[k])
        t.downloaded = int(d.get("downloaded") or 0)
        t.total = int(d.get("total") or 0)
        t.retries = int(d.get("retries") or 0)
        status = d.get("status", "pending")
        # 上次退出时正在下载的任务 -> 视为已暂停，重新开始时自动续传
        t.status = "paused" if status == "downloading" else status
        return t


class DownloadManager:
    max_retries = 3

    def __init__(self, settings, get_models_dir, on_event=None):
        self.settings = settings if settings is not None else {}
        self.get_models_dir = get_models_dir
        self.on_event = on_event or (lambda m: None)
        self._tasks = []
        self._by_id = {}
        self._queue = queue.Queue()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._stop.set()
        self._threads = []

    # ------------------------------------------------------------------ 日志
    def _log(self, msg):
        try:
            self.on_event(msg)
        except Exception:
            pass

    # ------------------------------------------------------------ 任务持久化
    def _persist(self):
        data = [t.to_dict() for t in self._tasks]
        try:
            TASKS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
        except OSError:
            pass

    def load(self):
        """程序启动时恢复历史任务。"""
        if not TASKS_FILE.exists():
            return
        try:
            data = json.loads(TASKS_FILE.read_text("utf-8"))
        except Exception:
            return
        if not isinstance(data, list):
            return
        with self._lock:
            for d in data:
                if isinstance(d, dict):
                    t = Task.from_dict(d)
                    self._tasks.append(t)
                    self._by_id[t.id] = t
            n = len(self._tasks)
        if n:
            self._log("已恢复 %d 条历史任务（未完成任务点已保留，点击“开始/继续”自动续传）" % n)

    # ---------------------------------------------------------------- 添加任务
    def add_tasks(self, lines, auto_mirror=True):
        models_dir = self.get_models_dir()
        if not models_dir:
            raise ValueError("请先在第 1 步选择 ComfyUI 项目")
        added = []
        with self._lock:
            known = {t.url for t in self._tasks
                     if t.status in ("pending", "downloading", "paused")}
            for raw in lines:
                u = raw.strip().strip('"').strip("'")
                if not u or u.startswith("#"):
                    continue
                if not re.match(r"^https?://", u, re.I):
                    self._log("忽略无效地址: %s" % u)
                    continue
                final = to_mirror(u) if auto_mirror else u
                if final != u:
                    self._log("已替换域名 huggingface.co → hf-mirror.com\n    %s" % final)
                norm = normalize_url(final)
                if norm != final:
                    self._log("已将网页地址(/blob)自动转换为直链(/resolve):\n    %s" % norm)
                    final = norm
                if final in known:
                    self._log("已在队列中，跳过: %s" % u)
                    continue
                fname = filename_from_url(final)
                cat, reason = classify.classify_url(final)
                t = Task(source=u, url=final, filename=fname, category=cat,
                         dest=str(Path(models_dir) / cat / fname))
                self._tasks.append(t)
                self._by_id[t.id] = t
                known.add(final)
                added.append(t)
                self._log("新任务 [%s] %s —— %s" % (cat, fname, reason))
            if added:
                self._persist()
        return added

    # ------------------------------------------------------------- 启动/停止
    def start(self, workers=None):
        n = max(1, int(workers or 4))
        with self._lock:
            self._stop.clear()
            self._threads = [th for th in self._threads if th.is_alive()]
            for _ in range(max(0, n - len(self._threads))):
                th = threading.Thread(target=self._worker_loop,
                                      name="comfy-dl-%d" % len(self._threads),
                                      daemon=True)
                self._threads.append(th)
                th.start()
            for t in self._tasks:
                if t.status in ("pending", "paused"):
                    self._enqueue(t)
        self._log("下载器已启动，线程数: %d" % n)

    def stop(self):
        with self._lock:
            self._stop.set()
            drained = []
            while True:
                try:
                    drained.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            for tid in drained:
                t = self._by_id.get(tid)
                if t:
                    t.queued = False
            self._persist()

    def has_active(self):
        with self._lock:
            return any(t.status in ("downloading", "pending", "paused")
                       for t in self._tasks)

    def pending_count(self):
        with self._lock:
            return sum(1 for t in self._tasks
                       if t.status in ("pending", "paused", "downloading"))

    # ------------------------------------------------------------- 任务操作
    def cancel(self, tid):
        with self._lock:
            t = self._by_id.get(tid)
            if not t:
                return
            if t.status == "downloading":
                t.cancel_event.set()
            elif t.status in ("pending", "paused"):
                t.status = "canceled"
                self._persist()

    def retry_failed(self):
        n = 0
        with self._lock:
            for t in self._tasks:
                if t.status in ("failed", "canceled"):
                    t.status = "pending"
                    t.error = ""
                    t.retries = 0
                    t.cancel_event.clear()
                    self._enqueue(t)
                    n += 1
            if n:
                self._persist()
        return n

    def remove_completed(self):
        with self._lock:
            drop = [t for t in self._tasks
                    if t.status in ("done", "skipped", "canceled")]
            for t in drop:
                self._tasks.remove(t)
                self._by_id.pop(t.id, None)
            if drop:
                self._persist()
        return len(drop)

    def set_category(self, tid, cat):
        with self._lock:
            t = self._by_id.get(tid)
            if not t or t.status == "downloading":
                return False
            t.category = cat
            md = self.get_models_dir()
            if md:
                t.dest = str(Path(md) / cat / t.filename)
            self._persist()
            return True

    def snapshot(self):
        with self._lock:
            out = []
            for t in self._tasks:
                d = t.to_dict()
                d["speed"] = t.speed
                out.append(d)
            return out

    def find(self, tid):
        with self._lock:
            return self._by_id.get(tid)

    # ---------------------------------------------------------------- 内部
    def _enqueue(self, t):
        if not t.queued:
            t.queued = True
            self._queue.put(t.id)

    def _worker_loop(self):
        while True:
            if self._stop.is_set():
                return
            try:
                tid = self._queue.get(timeout=0.3)
            except queue.Empty:
                continue
            if self._stop.is_set():
                self._queue.put(tid)
                return
            with self._lock:
                t = self._by_id.get(tid)
                if t:
                    t.queued = False
            if not t or t.status in TERMINAL:
                continue
            t.status = "downloading"
            self._log("开始下载: %s → models/%s/" % (t.filename, t.category))
            self._run_task(t)

    def _run_task(self, t):
        while True:
            try:
                self._attempt(t)
                if t.status == "skipped":
                    self._log("已存在，跳过: %s" % t.filename)
                else:
                    t.status = "done"
                    t.error = ""
                    self._log("✔ 完成: %s 已放入 models/%s/" % (t.filename, t.category))
                break
            except PausedSignal:
                t.status = "canceled" if t.cancel_event.is_set() else "paused"
                t.speed = 0
                self._log("已%s（断点保留）: %s"
                          % ("取消" if t.status == "canceled" else "暂停", t.filename))
                break
            except BadUrlError as e:
                t.speed = 0
                t.status = "failed"
                t.error = str(e)
                self._log("✘ 失败: %s — %s" % (t.filename, e))
                break
            except Exception as e:
                t.speed = 0
                msg = "%s: %s" % (type(e).__name__, e)
                if t.cancel_event.is_set():
                    t.status = "canceled"
                    break
                if self._stop.is_set():
                    t.status = "paused"
                    break
                t.retries += 1
                if t.retries <= self.max_retries:
                    self._log("出错，%d 秒后第 %d/%d 次重试: %s — %s"
                              % (min(2 ** t.retries, 15), t.retries,
                                 self.max_retries, t.filename, msg))
                    self._stop.wait(min(2 ** t.retries, 15))
                    if self._stop.is_set():
                        t.status = "paused"
                        break
                    continue
                t.status = "failed"
                t.error = msg
                self._log("✘ 失败: %s — %s" % (t.filename, msg))
                break
        with self._lock:
            self._persist()

    # ---------------------------------------------------------------- 下载
    def _open(self, url, pos):
        headers = {"User-Agent": UA}
        if pos > 0:
            headers["Range"] = "bytes=%d-" % pos
        try:
            return urlopen(Request(url, headers=headers), timeout=60)
        except HTTPError as e:
            if e.code == 416 and pos > 0:  # 断点超出服务器文件长度，从头下
                return self._open(url, 0)
            raise

    @staticmethod
    def _read_meta(meta_path):
        try:
            m = json.loads(meta_path.read_text("utf-8"))
            return m if isinstance(m, dict) else {}
        except Exception:
            return {}

    def _attempt(self, t):
        fixed = normalize_url(t.url)
        if fixed != t.url:
            self._log("地址为网页(/blob)，自动转为直链(/resolve): %s" % t.filename)
            t.url = fixed
        dest = Path(t.dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        meta_path = dest.with_name(dest.name + ".part.meta.json")

        if dest.exists() and self.settings.get("skip_existing", True):
            t.downloaded = t.total = dest.stat().st_size
            t.status = "skipped"
            return
        if dest.exists() and part.exists():
            try:
                part.unlink()
            except OSError:
                pass

        pos = part.stat().st_size if part.exists() else 0
        if pos:
            self._log("断点续传: %s 从 %s 处继续" % (t.filename, _human(pos)))
        etag = ""
        total = t.total or 0
        bad_url = False
        try:
            resp = self._open(t.url, pos)
            try:
                code = getattr(resp, "status", 200)
                etag = resp.headers.get("ETag") or ""
                if code == 206:
                    cr = resp.headers.get("Content-Range") or ""
                    if "/" in cr:
                        try:
                            total = int(cr.rsplit("/", 1)[1])
                        except ValueError:
                            pass
                    meta = self._read_meta(meta_path)
                    old_etag = meta.get("etag") or ""
                    if old_etag and etag and old_etag != etag:
                        # 服务器上的文件更新了，断点作废，从头重下
                        self._log("服务器文件已更新，重新下载: %s" % t.filename)
                        pos = 0
                        resp.close()
                        resp = self._open(t.url, 0)
                        code = getattr(resp, "status", 200)
                        etag = resp.headers.get("ETag") or ""
                if code == 200:
                    if pos > 0:
                        self._log("服务器不支持续传，从头下载: %s" % t.filename)
                    pos = 0
                    try:
                        total = int(resp.headers.get("Content-Length") or 0)
                    except ValueError:
                        total = 0
                t.total = total
                ct = (resp.headers.get("Content-Type") or "").lower()
                first_chunk = True
                mode = "ab" if code == 206 else "wb"
                last_t = time.monotonic()
                last_b = pos
                with open(part, mode) as f:
                    while True:
                        if t.cancel_event.is_set() or self._stop.is_set():
                            raise PausedSignal()
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        if first_chunk:
                            first_chunk = False
                            head = chunk[:512].lstrip().lower()
                            is_html = (b"<!doctype html" in head
                                       or head.startswith(b"<html")
                                       or ("text/html" in ct
                                           and "octet-stream" not in ct))
                            if is_html:
                                bad_url = True
                                raise BadUrlError(
                                    "服务器返回的是网页(HTML)而不是文件，"
                                    "请使用文件直链（HF 点文件页的下载按钮或带 /resolve/ 的地址）")
                        f.write(chunk)
                        pos += len(chunk)
                        t.downloaded = pos
                        now = time.monotonic()
                        if now - last_t >= 0.5:
                            t.speed = max(0.0, (pos - last_b) / (now - last_t))
                            last_t, last_b = now, pos
                    f.flush()
                    os.fsync(f.fileno())
            finally:
                try:
                    resp.close()
                except Exception:
                    pass
            if total and pos != total:
                raise OSError("下载不完整: %d/%d" % (pos, total))
            if dest.exists():
                try:
                    dest.unlink()
                except PermissionError:
                    raise OSError("目标文件正被占用，请先关闭 ComfyUI 后重试")
            os.replace(part, dest)
            t.downloaded = t.total = pos
            t.speed = 0.0
        finally:
            if bad_url and part.exists():
                try:
                    part.unlink()
                    meta_path.unlink(missing_ok=True)
                except OSError:
                    pass
            elif part.exists():
                try:
                    meta_path.write_text(
                        json.dumps({"etag": etag, "total": total}), "utf-8")
                except OSError:
                    pass
            else:
                try:
                    meta_path.unlink(missing_ok=True)
                except OSError:
                    pass


def _human(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return ("%d%s" % (n, unit)) if unit == "B" else ("%.1f%s" % (n, unit))
        n /= 1024.0
    return "%dB" % n
