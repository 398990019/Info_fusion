export type Envelope<T> = {
  code: number
  msg: string
  data: T
  meta?: {
    page: number
    size: number
    total: number
    has_more: boolean
  }
}

export type V1DocListItem = {
  id: string
  title: string
  author?: string | null
  source: string
  created_at?: string | null
  updated_at?: string | null
}

export type V1DocDetail = {
  id: string
  title: string
  content?: string | null
  tags: string[]
  source: string
  created_at?: string | null
}

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:5000'

export async function fetchV1Docs(
  page = 1,
  size = 20,
  token?: string,
  etag?: string,
): Promise<{ envelope?: Envelope<V1DocListItem[]>; etag?: string; notModified?: boolean }> {
  const url = `${API_BASE}/api/v1/docs?page=${page}&size=${size}`
  const headers: Record<string, string> = {}
  if (token) headers["Authorization"] = `Bearer ${token}`
  if (etag) headers["If-None-Match"] = etag

  const res = await fetch(url, { headers, cache: 'no-store' })
  if (res.status === 304) {
    return { notModified: true, etag: res.headers.get('ETag') || etag }
  }
  if (!res.ok) {
    throw new Error(`Failed to fetch v1 docs: ${res.status}`)
  }
  const envelope = (await res.json()) as Envelope<V1DocListItem[]>
  const newEtag = res.headers.get('ETag') || undefined
  return { envelope, etag: newEtag }
}

export async function fetchV1DocDetail(id: string, token?: string): Promise<Envelope<V1DocDetail>> {
  // 直接路径式；若包含 ? 可使用 query 版本
  const detailUrl = `${API_BASE}/api/v1/docs/${encodeURI(id)}`
  const res = await fetch(detailUrl, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: 'no-store',
  })
  if (res.status === 404) {
    // 回退到 query 版本（适配带 ? 的 ID）
    const q = `${API_BASE}/api/v1/doc?id=${encodeURIComponent(id)}`
    const res2 = await fetch(q, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      cache: 'no-store',
    })
    if (!res2.ok) throw new Error(`Failed to fetch v1 doc by query: ${res2.status}`)
    return res2.json()
  }
  if (!res.ok) throw new Error(`Failed to fetch v1 doc: ${res.status}`)
  return res.json()
}

export async function searchV1Docs(q: string, token?: string): Promise<Envelope<V1DocListItem[]>> {
  const url = `${API_BASE}/api/v1/search?q=${encodeURIComponent(q)}`
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`Failed to search v1 docs: ${res.status}`)
  return res.json()
}
