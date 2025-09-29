# api_server.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # 允许跨域请求

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """获取处理后的文章数据"""
    try:
        # 读取处理后的知识库数据
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
            return jsonify({
                'success': True,
                'data': articles,
                'count': len(articles),
                'last_updated': datetime.now().isoformat()
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
        
        if os.path.exists('final_knowledge_base.json'):
            with open('final_knowledge_base.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            stats['total_articles'] = len(articles)
            
            # 统计来源
            for article in articles:
                source = article.get('source', 'WeChat')
                stats['sources'][source] = stats['sources'].get(source, 0) + 1
                
                # 统计跨学科领域
                if 'llm_result' in article and 'cross_disciplinary_insights' in article['llm_result']:
                    for insight in article['llm_result']['cross_disciplinary_insights']:
                        domain = insight.get('domain', 'Unknown')
                        stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
                
                # 更新最后处理时间
                processed_at = article.get('processed_at')
                if processed_at:
                    if not stats['last_processed'] or processed_at > stats['last_processed']:
                        stats['last_processed'] = processed_at
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计信息时出错: {str(e)}'
        })

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
                title = article.get('title', '').lower()
                content = article.get('content', '').lower()
                summary = ''
                if 'llm_result' in article:
                    summary = article['llm_result'].get('deep_summary', '').lower()
                
                if (query in title or query in content or query in summary):
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

if __name__ == '__main__':
    print("启动 API 服务器...")
    print("API 地址: http://localhost:5000")
    print("文章列表: http://localhost:5000/api/articles")
    print("统计信息: http://localhost:5000/api/stats")
    print("搜索接口: http://localhost:5000/api/search?q=关键词")
    
    app.run(host='0.0.0.0', port=5000, debug=True)