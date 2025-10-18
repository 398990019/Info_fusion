from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class SourceMeta(BaseModel):
    # 数据来源：yuque/wechat/other
    source: Literal["yuque", "wechat", "other"] = Field(default="other")
    url: Optional[HttpUrl | str] = None
    author: Optional[str] = None
    mp_name: Optional[str] = Field(default=None, description="微信公众号名称（当 source=wechat 时可用）")
    raw_id: Optional[str] = None


class Content(BaseModel):
    title: str = ""
    # 原始正文（可为 HTML 或 Markdown）
    body: Optional[str] = None
    # 纯文本内容（可选）
    text: Optional[str] = None


class Summary(BaseModel):
    # 关键要点（来自 SimHash/LLM 处理）
    key_points: list[str] = Field(default_factory=list)
    deep_summary: Optional[str] = None
    deep_summary_with_link: Optional[str] = None
    open_question: Optional[str] = None


class Article(BaseModel):
    id: str
    content: Content
    meta: SourceMeta = Field(default_factory=SourceMeta)
    published_time: Optional[datetime] = None
    processed_at: Optional[datetime | str] = None
    tags: list[str] = Field(default_factory=list)
    summary: Summary = Field(default_factory=Summary)

    @model_validator(mode="after")
    def _normalize_times(self) -> "Article":
        # processed_at 允许传入 ISO 字符串；保持与现有 JSON 兼容
        if isinstance(self.processed_at, str):
            try:
                # 简单解析 ISO 格式
                self.processed_at = datetime.fromisoformat(self.processed_at.replace("Z", "+00:00"))
            except Exception:
                # 不可解析时保留原字符串，以兼容历史产物
                pass
        return self


# 面向 API v1 的列表项模型（与 api_server 中的 DTO 对齐，便于后续统一）
class DocListItem(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    source: Optional[str] = None
    created_at: str
    updated_at: str


class Envelope(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Any
    meta: Optional[dict[str, Any]] = None
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceMeta(BaseModel):
    """统一的来源元信息。

    platform: 数据来源平台标识，例如 "wechat"、"yuque"。
    account_id/account_name: 对应账号标识（如公众号 biz 或语雀空间等）。
    channel: 可选的栏目/分类等来源侧信息。
    """

    platform: str = Field(..., description="数据来源平台，如 wechat/yuque")
    account_id: Optional[str] = Field(None, description="来源账号 ID（如公众号 biz 等）")
    account_name: Optional[str] = Field(None, description="来源账号名称")
    channel: Optional[str] = Field(None, description="来源栏目/分类等")


class Content(BaseModel):
    """统一的内容承载结构。"""

    html: Optional[str] = Field(None, description="原始或清洗后的 HTML 内容")
    text: Optional[str] = Field(None, description="纯文本内容（用于摘要/指纹）")
    length: int = Field(0, description="内容长度（字符数），可选统计字段")


class Summary(BaseModel):
    """LLM 生成的结构化摘要信息。"""

    text: Optional[str] = Field(None, description="摘要文本")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    categories: List[str] = Field(default_factory=list, description="主题/类别标签")
    model: Optional[str] = Field(None, description="用于生成摘要的模型标识")
    updated_at: Optional[datetime] = Field(None, description="摘要最后更新时间")


class Article(BaseModel):
    """统一的文章实体模型（跨来源统一）。

    注意：为尽量减少对现有代码的影响，此模型仅作为“契约与校验”，
    目前不改变现有数据流的输入输出；后续可逐步替换到该模型。
    """

    id: str = Field(..., description="文章唯一 ID，建议使用稳定主键（如 canonical 或组合 ID）")
    title: str = Field(..., description="文章标题")
    canonical_url: Optional[str] = Field(None, description="规范化（canonical）的原文链接")
    link: Optional[str] = Field(None, description="抓取时使用的原始链接（可能与 canonical 不同）")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    authors: List[str] = Field(default_factory=list, description="作者（可能为空）")
    source: SourceMeta = Field(..., description="来源平台与账号信息")

    content: Content = Field(default_factory=Content, description="正文内容（HTML/文本）")
    summary: Summary = Field(default_factory=Summary, description="LLM 生成的摘要信息")

    raw_html: Optional[str] = Field(None, description="可选：原始 HTML，用于重解析/溯源")
    extras: dict[str, Any] = Field(default_factory=dict, description="可扩展的额外字段")

    model_config = ConfigDict(extra="ignore")


__all__ = [
    "SourceMeta",
    "Content",
    "Summary",
    "Article",
]
