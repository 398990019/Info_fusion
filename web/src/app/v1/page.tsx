"use client"

import { useEffect, useState } from 'react'
import { fetchV1Docs, fetchV1DocDetail, searchV1Docs, type V1DocListItem, type V1DocDetail } from '../../lib/api'

export default function V1DemoPage() {
  const [list, setList] = useState<V1DocListItem[]>([])
  const [meta, setMeta] = useState<{page:number,size:number,total:number,has_more:boolean} | null>(null)
  const [selected, setSelected] = useState<V1DocDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [etag, setEtag] = useState<string | undefined>(undefined)
  const [q, setQ] = useState<string>("")

  useEffect(() => {
    const run = async () => {
      setLoading(true)
      setError(null)
      try {
        const envToken = process.env.NEXT_PUBLIC_API_TOKEN
        const { envelope, etag: newEtag } = await fetchV1Docs(1, 10, envToken)
        if (envelope) {
          setList(envelope.data)
          if (envelope.meta) setMeta(envelope.meta as any)
          if (envelope.data.length > 0) {
            const d = await fetchV1DocDetail(envelope.data[0].id, envToken)
            setSelected(d.data)
          }
        }
        if (newEtag) setEtag(newEtag)
      } catch (e:any) {
        setError(e.message || String(e))
      } finally {
        setLoading(false)
      }
    }
    run()
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto space-y-4">
        <h1 className="text-2xl font-bold">v1 API Demo</h1>
  <p className="text-sm text-gray-600">此页直接对接 /api/v1/docs 与 /api/v1/docs/{'{'}id{'}'}，用于快速联调与验证。</p>

        {process.env.NEXT_PUBLIC_API_BASE && (
          <div className="text-xs text-gray-500">API_BASE: {process.env.NEXT_PUBLIC_API_BASE}</div>
        )}

        {loading && <div className="text-gray-500">加载中...</div>}
        {error && <div className="text-red-600">错误：{error}</div>}

        {meta && (
          <div className="text-sm text-gray-700">共 {meta.total} 条，当前取 {meta.size} 条</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white p-4 rounded border md:col-span-2">
            <div className="flex gap-2 items-center">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="搜索标题/摘要/作者"
                className="border rounded px-2 py-1 w-full"
              />
              <button
                className="px-3 py-1 bg-blue-600 text-white rounded"
                onClick={async () => {
                  setLoading(true)
                  setError(null)
                  try {
                    const envToken = process.env.NEXT_PUBLIC_API_TOKEN
                    if (q.trim()) {
                      const r = await searchV1Docs(q.trim(), envToken)
                      setList(r.data)
                      setMeta(r.meta as any ?? null)
                    } else {
                      const { envelope } = await fetchV1Docs(1, 10, envToken, etag)
                      if (envelope) {
                        setList(envelope.data)
                        setMeta(envelope.meta as any ?? null)
                      }
                    }
                  } catch (e:any) {
                    setError(e.message || String(e))
                  } finally {
                    setLoading(false)
                  }
                }}
              >搜索</button>
            </div>
          </div>
          <div className="bg-white p-4 rounded border">
            <h2 className="font-semibold mb-2">列表</h2>
            <ul className="space-y-2">
              {list.map(it => (
                <li key={it.id} className="text-sm">
                  <button className="text-blue-600 hover:underline" onClick={async () => {
                    const envToken = process.env.NEXT_PUBLIC_API_TOKEN
                    const d = await fetchV1DocDetail(it.id, envToken)
                    setSelected(d.data)
                  }}>{it.title}</button>
                  <div className="text-gray-500">{it.source} · {it.author ?? '作者未注明'} · {it.created_at ?? '-'}</div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white p-4 rounded border">
            <h2 className="font-semibold mb-2">详情</h2>
            {!selected ? (
              <div className="text-gray-500 text-sm">点击左侧标题查看详情</div>
            ) : (
              <div className="space-y-2 text-sm">
                <div className="font-semibold">{selected.title}</div>
                <div className="text-gray-500">{selected.source} · {selected.created_at ?? '-'}</div>
                {selected.tags?.length > 0 && (
                  <div className="text-gray-700">标签：{selected.tags.join('、')}</div>
                )}
                {selected.content && (
                  <div className="whitespace-pre-wrap text-gray-700 border rounded p-2 max-h-96 overflow-auto">{selected.content}</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
