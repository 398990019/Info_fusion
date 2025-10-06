"""Utility helpers for coordinating with the external We-MP-RSS project.

This module attempts to locate an adjacent We-MP-RSS installation and invoke
its refresh routines so that the local RSS feed stays up-to-date even when the
web UI is not opened manually.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from config import WECHAT_RSS_ROOT


# --- Internal utilities ----------------------------------------------------


def _candidate_we_rss_dirs(base_dir: Path) -> Iterator[Path]:
	"""Yield potential We-MP-RSS directories based on typical layouts."""
	if WECHAT_RSS_ROOT:
		custom_path = Path(WECHAT_RSS_ROOT).expanduser().resolve()
		if custom_path.exists():
			yield custom_path

	# Common relative locations when projects are checked out side-by-side.
	relative_candidates = [
		base_dir.parent / 'we-mp-rss',
		base_dir.parent / 'we-mp-rss-1.4.6',
		base_dir.parent.parent / 'we-mp-rss',
		base_dir.parent.parent / 'we-mp-rss-1.4.6',
	]

	for candidate in relative_candidates:
		for suffix in (candidate, candidate / 'we-mp-rss', candidate / 'we-mp-rss-1.4.6'):
			resolved = suffix.resolve()
			if (resolved / 'main.py').exists() and (resolved / 'core').is_dir():
				yield resolved


def _locate_we_rss_dir() -> Optional[Path]:
	base_dir = Path(__file__).resolve().parent
	for candidate in _candidate_we_rss_dirs(base_dir):
		return candidate
	return None


def locate_we_rss_root() -> Optional[Path]:
	"""公开获取 We-MP-RSS 项目的根目录。如果未安装则返回 None。"""

	return _locate_we_rss_dir()


@contextmanager
def _temporary_work_dir(target: Path) -> Iterator[None]:
	original = Path.cwd()
	try:
		os.chdir(target)
		yield
	finally:
		os.chdir(original)


def _ensure_scheduler_flags(cfg) -> bool:
	"""Ensure We-MP-RSS config enables scheduled refresh jobs.

	Returns True when any mutations were persisted, False otherwise.
	"""

	changed = False
	# Guarantee nested dictionaries exist.
	cfg.config.setdefault('server', {})
	cfg.config.setdefault('gather', {})

	server_cfg = cfg.config['server']
	if not server_cfg.get('enable_job'):
		server_cfg['enable_job'] = True
		changed = True

	gather_cfg = cfg.config['gather']
	if not gather_cfg.get('content', True):
		gather_cfg['content'] = True
		changed = True
	if not gather_cfg.get('content_auto_check'):
		gather_cfg['content_auto_check'] = True
		changed = True
	# Allow users to override interval via config/ENV, but default to 30 minutes.
	if not gather_cfg.get('content_auto_interval'):
		gather_cfg['content_auto_interval'] = 30
		changed = True

	if changed:
		cfg.save_config()
	return changed


# --- Public API ------------------------------------------------------------


def refresh_wechat_articles() -> bool:
	"""Trigger We-MP-RSS to pull the newest articles.

	Returns
	-------
	bool
		True if a refresh attempt was dispatched successfully, False otherwise.
	"""

	we_rss_dir = _locate_we_rss_dir()
	if we_rss_dir is None:
		print('警告: 未找到 We-MP-RSS 项目目录，跳过刷新。')
		return False

	if str(we_rss_dir) not in sys.path:
		sys.path.insert(0, str(we_rss_dir))

	try:
		with _temporary_work_dir(we_rss_dir):
			data_dir = we_rss_dir / 'data'
			try:
				data_dir.mkdir(parents=True, exist_ok=True)
				lock_file = data_dir / '.lock'
				if not lock_file.exists():
					lock_file.touch()
			except Exception as lock_exc:  # pragma: no cover - IO 权限问题走兜底
				print(f'警告: 创建 We-MP-RSS 数据目录或锁文件失败: {lock_exc}')

			import importlib

			# Lazily import to avoid paying the startup cost when功能未启用。
			core_config = importlib.import_module('core.config')
			cfg = getattr(core_config, 'cfg')

			_ensure_scheduler_flags(cfg)

			# fetch_all_article 会遍历所有订阅号并写入数据库。
			jobs_mps = importlib.import_module('jobs.mps')
			fetch_all_article = getattr(jobs_mps, 'fetch_all_article')

			# 如果缺少浏览器依赖，则提示后直接跳过，避免频繁下载 Firefox。
			controller_mod = importlib.import_module('driver.firefox_driver')
			controller = getattr(controller_mod, 'FirefoxController')()

			system = getattr(controller, 'system', 'windows')
			has_browser = True
			try:
				if system == 'windows':
					has_browser = controller._is_firefox_installed_windows()  # type: ignore[attr-defined]
				elif system == 'linux':
					has_browser = controller._is_firefox_installed_linux()  # type: ignore[attr-defined]
				elif system == 'darwin':
					has_browser = controller._is_firefox_installed_mac()  # type: ignore[attr-defined]
			except Exception as exc:  # pragma: no cover - 外部库调用
				print(f'警告: 检测 Firefox 安装状态失败，将继续尝试刷新。原因: {exc}')

			if not has_browser:
				print('警告: 未检测到 Firefox 浏览器或 geckodriver，已跳过 We-MP-RSS 刷新。请手动安装后重试。')
				return False

			print('正在调用 We-MP-RSS 刷新公众号文章数据...')
			fetch_all_article()
			print('We-MP-RSS 刷新成功完成。')
			return True
	except Exception as exc:  # pylint: disable=broad-except
		print(f"警告: 调用 We-MP-RSS 刷新失败 - {exc}")
		return False

