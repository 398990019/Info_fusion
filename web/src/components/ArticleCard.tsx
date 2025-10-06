import { FC, useMemo } from 'react'
import { LinkIcon, CalendarIcon, UserIcon, ClockIcon } from '@heroicons/react/24/outline'

interface Article {
  title: string
  link?: string
  url?: string
  published_time?: string
  published_at?: string
  content: string
  source?: string
  author?: string
  updated_at?: string
  platform?: string
  llm_result?: {
    deep_summary?: string
    deep_summary_with_link?: string
    key_points?: string[]
    open_question?: string
  }
  deep_summary?: string
  deep_summary_with_link?: string
  key_points?: string[]
  processed_at?: string
}

interface ArticleCardProps {
  article: Article
}

const ArticleCard: FC<ArticleCardProps> = ({ article }) => {
  const formatDate = (dateString?: string) => {
    if (!dateString) return null
    try {
      return new Date(dateString).toLocaleString('zh-CN', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateString
    }
  }

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  const authorName = useMemo(() => {
    if (article.author && article.author.trim()) {
      return article.author.trim()
    }

    const titleSegments = article.title?.split(/[-———]/).map(segment => segment.trim()).filter(Boolean) ?? []
    if (titleSegments.length >= 2) {
      return titleSegments[titleSegments.length - 1]
    }

    return '作者未注明'
  }, [article.author, article.title])

  const sourceDisplay = article.source && article.source.trim() ? article.source.trim() : null
  const normalizedSource = sourceDisplay?.toLowerCase()
  const platformKey = article.platform?.trim().toLowerCase()
  const isYuque = platformKey === 'yuque' || normalizedSource === 'yuque' || normalizedSource === '语雀'

  const publishedDisplay = useMemo(() => {
    return formatDate(article.published_time || article.published_at)
  }, [article.published_at, article.published_time])

  const updatedDisplay = useMemo(() => {
    if (!isYuque) return null
    return formatDate(article.processed_at || article.updated_at)
  }, [article.processed_at, article.updated_at, isYuque])

  const originalLink = article.link || article.url
  const summaryText = article.llm_result?.deep_summary ?? article.deep_summary ?? ''
  const keyPoints = article.llm_result?.key_points ?? article.key_points ?? []
  const openQuestion = article.llm_result?.open_question

  return (
    <div className="bg-white/70 backdrop-blur rounded-2xl shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300 p-5 sm:p-6 border border-white">
      {/* Article Header */}
      <div className="mb-4 space-y-3">
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900 leading-snug">
          {article.title}
        </h3>
        
        <div className="flex flex-col gap-2">
          {(authorName || sourceDisplay) && (
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
              <span className="inline-flex items-center gap-1.5">
                <UserIcon className="h-4 w-4 flex-shrink-0 text-gray-500" />
                <span className="font-medium text-gray-800 truncate max-w-xs sm:max-w-sm">
                  {authorName}
                </span>
              </span>
              {sourceDisplay && (
                <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-600 border border-blue-100 px-2 py-0.5 text-xs font-medium">
                  {sourceDisplay}
                </span>
              )}
            </div>
          )}

          {(publishedDisplay || updatedDisplay) && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-4 text-xs sm:text-sm text-gray-500">
              {publishedDisplay && (
                <div className="flex items-center gap-1.5">
                  <CalendarIcon className="h-4 w-4 flex-shrink-0" />
                  <span>发布时间：{publishedDisplay}</span>
                </div>
              )}
              {updatedDisplay && isYuque && (
                <div className="flex items-center gap-1.5 mt-1 sm:mt-0">
                  <ClockIcon className="h-4 w-4 flex-shrink-0" />
                  <span>最后更新：{updatedDisplay}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {originalLink && (
          <a
            href={originalLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-700 text-xs font-medium"
          >
            <LinkIcon className="h-4 w-4" />
            查看原文
          </a>
        )}
      </div>

      {/* AI Analysis Section */}
      {(summaryText || openQuestion) && (
        <div className="space-y-4">
          {/* Deep Summary */}
          {summaryText && (
            <div className="rounded-xl bg-white/60 border border-gray-100 p-4">
              <h4 className="text-sm font-semibold text-gray-800 mb-2 flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                深度总结
              </h4>
              <p className="text-sm text-gray-600 leading-relaxed">
                {truncateText(summaryText, 220)}
              </p>
              {!!keyPoints.length && (
                <ul className="mt-3 space-y-1">
                  {keyPoints.map((point, idx) => (
                    <li key={idx} className="text-xs text-gray-500">
                      • {point}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Open Question */}
          {openQuestion && (
            <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-4">
              <h4 className="text-sm font-semibold text-indigo-800 mb-2 flex items-center gap-2">
                <div className="w-2 h-2 bg-indigo-500 rounded-full"></div>
                开放性思考
              </h4>
              <p className="text-sm text-indigo-900/80 leading-relaxed italic">
                {truncateText(openQuestion, 160)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Original Content Preview */}
      <div className="mt-5 pt-4 border-t border-gray-100">
        <h4 className="text-sm font-semibold text-gray-800 mb-2">原文摘要</h4>
        <p className="text-xs sm:text-sm text-gray-500 leading-relaxed">
          {truncateText(article.content, 110)}
        </p>
      </div>
    </div>
  )
}

export default ArticleCard