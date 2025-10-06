# api_server.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from main import run_full_pipeline


def _normalize_text(value):
    if isinstance(value, str):
        return value.lower()
    if value is None:
        return ''
    return str(value).lower()

_WECHAT_SOURCE_ALIASES = {'wechat', '微信公众号', 'weixin', 'wx', 'mp', '公众号'}


def _normalize_source(article: dict) -> str:
    raw_source = (article.get('source') or '').strip()
    platform = (article.get('platform') or '').strip().lower()
    link = (article.get('link') or article.get('url') or '').lower()

    if raw_source:
        if raw_source.strip().lower() in _WECHAT_SOURCE_ALIASES:
            return '微信公众号'
        return raw_source

    if platform in _WECHAT_SOURCE_ALIASES or 'mp.weixin.qq.com' in link:
        return '微信公众号'
    if platform == 'yuque':
        return '语雀'

    return '未知来源'


def _build_source_tree(articles: list[dict]) -> list[dict]:
    totals: dict[str, int] = {}
    wechat_children: dict[str, int] = {}

    for article in articles:
        source_label = _normalize_source(article)
        totals[source_label] = totals.get(source_label, 0) + 1

        platform = (article.get('platform') or '').strip()
        if platform == '微信公众号':
            mp_name = (article.get('source') or '').strip() or '公众号未命名'
            wechat_children[mp_name] = wechat_children.get(mp_name, 0) + 1

    tree: list[dict] = []
    for label, count in totals.items():
        if label == '微信公众号':
            children = [
                {'label': name, 'count': child_count}
                for name, child_count in sorted(wechat_children.items(), key=lambda item: item[0])
            ]
            tree.append({'label': label, 'count': count, 'children': children})
        else:
            tree.append({'label': label, 'count': count})

    # Ensure consistent ordering: keep 微信公众号 first, others alphabetically
    tree.sort(key=lambda node: (0 if node['label'] == '微信公众号' else 1, node['label']))
    return tree


app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """获取处理后的文章数据"""
    try:
        # 读取处理后的知识库数据
        articles = []
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)

        filtered_articles = []
        if os.path.exists('filtered_articles.json'):
            with open('filtered_articles.json', 'r', encoding='utf-8') as f:
                filtered_articles = json.load(f)

        if articles:
            return jsonify({
                'success': True,
                'data': articles,
                'count': len(articles),
                'last_updated': datetime.now().isoformat(),
                'filtered': filtered_articles,
                'filtered_count': len(filtered_articles)
            })
        else:
            return jsonify({
                'success': False,
                'message': '数据文件不存在或为空',
                'data': [],
                'filtered': filtered_articles,
                'filtered_count': len(filtered_articles)
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'读取数据时出错: {str(e)}',
            'data': []
        })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    try:
        stats = {
            'total_articles': 0,
            'sources': {},
            'domains': {},
            'last_processed': None
        }
        
        filtered_articles_count = 0

        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            stats['total_articles'] = len(articles)
            
            # 统计来源
            stats['source_tree'] = _build_source_tree(articles)

            for article in articles:
                source = _normalize_source(article)
                stats['sources'][source] = stats['sources'].get(source, 0) + 1

                processed_at = article.get('processed_at')
                if processed_at:
                    if not stats['last_processed'] or processed_at > stats['last_processed']:
                        stats['last_processed'] = processed_at
        
        if os.path.exists('filtered_articles.json'):
            with open('filtered_articles.json', 'r', encoding='utf-8') as f:
                filtered_articles = json.load(f)
                filtered_articles_count = len(filtered_articles)

        return jsonify({
            'success': True,
            'data': {**stats, 'filtered_count': filtered_articles_count}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计信息时出错: {str(e)}'
        })


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """触发后端重新聚合并运行 AI 处理"""
    try:
        processed_articles = run_full_pipeline()
        return jsonify({
            'success': True,
            'message': '数据已重新聚合并处理完毕',
            'count': len(processed_articles)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'刷新数据时出错: {str(e)}'
        }), 500

@app.route('/api/search', methods=['GET'])
def search_articles():
    """搜索文章"""
    from flask import request
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({
            'success': False,
            'message': '搜索关键词不能为空',
            'data': []
        })
    
    try:
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            # 简单的文本搜索
            results = []
            for article in articles:
                title = _normalize_text(article.get('title'))
                content = _normalize_text(article.get('content'))
                author = _normalize_text(article.get('author'))
                summary_candidates = [
                    article.get('deep_summary'),
                    article.get('deep_summary_with_link'),
                    article.get('open_question')
                ]
                if isinstance(article.get('key_points'), list):
                    summary_candidates.extend(article['key_points'])

                llm_result = article.get('llm_result')
                if isinstance(llm_result, dict):
                    summary_candidates.extend([
                        llm_result.get('deep_summary'),
                        llm_result.get('deep_summary_with_link'),
                        llm_result.get('open_question')
                    ])
                    if isinstance(llm_result.get('key_points'), list):
                        summary_candidates.extend(llm_result['key_points'])

                combined_summary = ' '.join(
                    _normalize_text(item) for item in summary_candidates if item is not None
                )

                if (
                    query in title
                    or query in content
                    or query in combined_summary
                    or query in author
                ):
                    results.append(article)
            
            return jsonify({
                'success': True,
                'data': results,
                'count': len(results),
                'query': query
            })
        else:
            return jsonify({
                'success': False,
                'message': '数据文件不存在',
                'data': []
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'搜索时出错: {str(e)}',
            'data': []
        })


@app.route('/api/source-tree', methods=['GET'])
def get_source_tree():
    """返回分层的数据源结构，供前端构建折叠视图"""
    try:
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)

            tree = _build_source_tree(articles)
            return jsonify({'success': True, 'data': tree})

        return jsonify({
            'success': False,
            'message': '数据文件不存在',
            'data': []
        })
    except Exception as exc:
        return jsonify({
            'success': False,
            'message': f'获取数据源结构时出错: {exc}',
            'data': []
        }), 500

if __name__ == '__main__':
    print("启动 API 服务器...")
    print("API 地址: http://localhost:5000")
    print("文章列表: http://localhost:5000/api/articles")
    print("统计信息: http://localhost:5000/api/stats")
    print("搜索接口: http://localhost:5000/api/search?q=关键词")
    
    app.run(host='0.0.0.0', port=5000, debug=True)