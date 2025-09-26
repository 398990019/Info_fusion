import ArticleCard from '@/components/ArticleCard'
import { useEffect, useState } from 'react'

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

export default function Home() {
  const [articles, setArticles] = useState<Article[]>([])

  useEffect(() => {
    // In a real app, this would be an API call
    fetch('/final_knowledge_base.json')
      .then(res => res.json())
      .then(data => setArticles(data))
  }, [])

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-8 text-primary">Info Fusion</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {articles.map((article, index) => (
          <ArticleCard key={index} article={article} />
        ))}
      </div>
    </div>
  )
}