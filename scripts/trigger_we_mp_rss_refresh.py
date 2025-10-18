from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_path() -> None:
	script_path = Path(__file__).resolve()
	repo_root = script_path.parent.parent
	path_str = str(repo_root)
	if path_str not in sys.path:
		sys.path.insert(0, path_str)


def main() -> int:
	_ensure_repo_root_on_path()

	try:
		from we_mp_rss_sync import refresh_wechat_articles
	except ImportError as exc:  # pragma: no cover - defensive guard
		print(f"We-MP-RSS refresh: failed to import helper ({exc})")
		return 1

	success = refresh_wechat_articles()
	print(f"We-MP-RSS refresh: {success}")
	return 0 if success else 1


if __name__ == "__main__":
	sys.exit(main())
