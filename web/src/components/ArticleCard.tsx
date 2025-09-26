import { FC } from 'react'

interface Article {
  title: string
  content: string
  published_time: string
  llm_result: {
    deep_summary: string
    cross_disciplinary_insights: Array<{
      domain: string
      analysis: string
      connection: string
    }>
    open_question: string
  }
}

interface ArticleCardProps {
  article: Article
}

const ArticleCard: FC<ArticleCardProps> = ({ article }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <h2 className="text-xl font-semibold mb-2 text-primary">{article.title}</h2>
      <p className="text-gray-600 text-sm mb-4">{article.published_time}</p>
      
      <div className="mb-4">
        <h3 className="font-medium text-secondary mb-2">Summary</h3>
        <p className="text-gray-700">{article.llm_result.deep_summary}</p>
      </div>
      
      <div className="mb-4">
        <h3 className="font-medium text-secondary mb-2">Cross-disciplinary Insights</h3>
        {article.llm_result.cross_disciplinary_insights.map((insight, index) => (
          <div key={index} className="mb-3">
            <h4 className="text-sm font-medium text-primary">{insight.domain}</h4>
            <p className="text-gray-700 text-sm">{insight.analysis}</p>
            <p className="text-gray-600 text-sm italic">Connection: {insight.connection}</p>
          </div>
        ))}
      </div>
      
      <div>
        <h3 className="font-medium text-secondary mb-2">Open Question</h3>
        <p className="text-gray-700">{article.llm_result.open_question}</p>
      </div>
    </div>
  )
}

export default ArticleCard