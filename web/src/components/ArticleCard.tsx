import { FC } from 'react'
import { LinkIcon, CalendarIcon, UserIcon } from '@heroicons/react/24/outline'

interface Article {
  title: string
  link?: string
  published_time: string
  content: string
  source?: string
  llm_result?: {
    deep_summary: string
    cross_disciplinary_insights: Array<{
      domain: string
      analysis: string
      connection: string
    }>
    open_question: string
  }
  processed_at: string
}

interface ArticleCardProps {
  article: Article
}

const ArticleCard: FC<ArticleCardProps> = ({ article }) => {
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    } catch {
      return dateString
    }
  }

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow duration-300 p-6 border border-gray-200">
      {/* Article Header */}
      <div className="mb-4">
        <h3 className="text-xl font-semibold text-gray-900 mb-2 line-clamp-2">
          {article.title}
        </h3>
        
        <div className="flex items-center justify-between text-sm text-gray-500 mb-3">
          <div className="flex items-center space-x-4">
            {article.source && (
              <div className="flex items-center space-x-1">
                <UserIcon className="h-4 w-4" />
                <span>{article.source}</span>
              </div>
            )}
            <div className="flex items-center space-x-1">
              <CalendarIcon className="h-4 w-4" />
              <span>{formatDate(article.published_time)}</span>
            </div>
          </div>
          
          {article.link && (
            <a
              href={article.link}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 transition-colors"
            >
              <LinkIcon className="h-4 w-4" />
              <span>原文</span>
            </a>
          )}
        </div>
      </div>

      {/* AI Analysis Section */}
      {article.llm_result && (
        <div className="space-y-4">
          {/* Deep Summary */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
              <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
              深度总结
            </h4>
            <p className="text-sm text-gray-600 leading-relaxed">
              {truncateText(article.llm_result.deep_summary, 200)}
            </p>
          </div>

          {/* Cross-disciplinary Insights */}
          {article.llm_result.cross_disciplinary_insights && article.llm_result.cross_disciplinary_insights.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                跨学科视角
              </h4>
              <div className="space-y-2">
                {article.llm_result.cross_disciplinary_insights.slice(0, 2).map((insight, index) => (
                  <div key={index} className="bg-gray-50 rounded p-3">
                    <div className="flex items-center mb-1">
                      <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                        {insight.domain}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 leading-relaxed">
                      {truncateText(insight.analysis, 150)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Open Question */}
          {article.llm_result.open_question && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <div className="w-2 h-2 bg-purple-500 rounded-full mr-2"></div>
                开放性思考
              </h4>
              <p className="text-sm text-gray-600 italic leading-relaxed">
                {truncateText(article.llm_result.open_question, 150)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Original Content Preview */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <h4 className="text-sm font-medium text-gray-700 mb-2">原文摘要</h4>
        <p className="text-xs text-gray-500 leading-relaxed">
          {truncateText(article.content, 100)}
        </p>
      </div>
    </div>
  )
}

export default ArticleCard