from simhash import Simhash
from diff_utils import find_diff
from yuque_fetcher import fetch_yuque_data
import json
import os
import requests
from datetime import datetime, timedelta
from simhash_utils import generate_simhash, get_hamming_distance


def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError:
            print(f"警告，无法解析文件{filename}，将重新创建。")
            return {}
    else:
        return {}


def save_data(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"错误：无法将数据保存到文件{filename}:{e}")


def get_doc_body(token, group_login, book_slug, doc_id):
    url = f"https://www.yuque.com/api/v2/repos/{group_login}/{book_slug}/docs/{doc_id}"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        doc_data = response.json().get("data")
        if doc_data and "body" in doc_data:
            return doc_data.get("body")
        else:
            print(f"警告：API 返回数据结构不完整或文档 {doc_id} 内容为空。")
            return None
    except requests.exceptions.RequestException as e:
        print(f"API 请求失败: {e}")
        return None
    except KeyError as e:
        print(f"API 返回数据结构错误，缺少键: {e}")
        return None



TOKEN = "s91TCRkU7KDHYAqy9F5ACOa4WoYUNZKvpI1hsj2S"
GROUP_LOGIN = "ph25ri"
BOOK_SLUG = "ua1c3q"
data_file = "yuque_data.json"

# 1. 加载上次运行保存的数据
last_run_data = load_data(data_file)

# 2. 从语雀 API 获取最新数据
new_yuque_data = fetch_yuque_data(TOKEN, GROUP_LOGIN, BOOK_SLUG)
new_docs_map = new_yuque_data.get("docs_map") if new_yuque_data else {}

# 一个字典，用于存储本次运行的最新数据
new_run_data = {}

if new_docs_map:
    for doc_id, new_doc_info in new_docs_map.items():
        # 注意：JSON 文件的键默认为字符串，所以这里要转换类型
        doc_id_str = str(doc_id)
        last_doc_info = last_run_data.get(doc_id_str, {})

        # 检查文档是否为新增，或更新时间是否变化
        is_new_doc = doc_id_str not in last_run_data
        is_updated = last_doc_info.get("updated_at") != new_doc_info.get("updated_at")

        # 如果文档有更新或为新增，则进行详细处理
        if is_new_doc or is_updated:
            print(f"检测到更新：{new_doc_info['title']}...")

            # 3. 按需获取文档正文
            document_body = get_doc_body(TOKEN, GROUP_LOGIN, BOOK_SLUG, doc_id)

            # 如果成功获取到正文
            if document_body:
                new_simhash_obj = generate_simhash(document_body)

                # 4. SimHash 过滤器开始：只有在文档不是新增且有旧指纹时才进行比对
                if not is_new_doc and "simhash" in last_doc_info:
                    old_simhash_value = last_doc_info["simhash"]
                    old_simhash_obj = Simhash(old_simhash_value)

                    distance = get_hamming_distance(old_simhash_obj, new_simhash_obj)

                    # 如果汉明距离小于或等于3，则认为是微小更新
                    if distance <= 3:
                        print(f"检测到微小更新，文档：{new_doc_info['title']}，汉明距离：{distance}。已跳过。")
                        # 即使是微小更新，也需要将新数据保存下来
                        new_run_data[doc_id_str] = new_doc_info
                        new_run_data[doc_id_str]["body"] = document_body
                        new_run_data[doc_id_str]["simhash"] = new_simhash_obj.value
                        continue  # 跳到下一个文档，不再进行后续处理

                # 5. 如果没有被 SimHash 过滤器跳过，则进行深入处理
                print(f"检测到实质性更新，文档：{new_doc_info['title']}。")
                old_doc_body = last_doc_info.get("body", "")
                diff_content = find_diff(old_doc_body, document_body)

                if diff_content:
                    print("--- 差异内容 ---")
                    print(diff_content)
                else:
                    print("内容无实质性变化。")

                # 6. 将所有新数据（包括正文和指纹）保存到新字典中
                new_run_data[doc_id_str] = new_doc_info
                new_run_data[doc_id_str]["body"] = document_body
                new_run_data[doc_id_str]["simhash"] = new_simhash_obj.value

        else:
            # 7. 如果文档没有更新，也要将其所有数据复制过来
            # 这样可以确保下次比对时仍有旧正文和指纹
            new_run_data[doc_id_str] = last_doc_info

    # 8. 保存本次运行的数据
    save_data(data_file, new_run_data)
    print("\n所有文档数据已保存，下次运行将以此为基准。")

else:
    print("无法获取语雀数据，请检查配置或网络连接。")

'''
if __name__ == "__main__":
    # --- 测试代码 ---
    test_data = {
        "123": {"title": "first_doc", "updated_at": "2025-09-23T10:00:00Z"},
        "456": {"title": "second_doc", "updated_at": "2025-09-23T11:00:00Z"},
    }
    filename = "test_data.json"

    save_data(filename, test_data)
    print(f"测试数据已保存到{filename}")

    loaded_data = load_data(filename)
    print("加载的数据：", loaded_data)

    if os.path.exists(filename):
        os.remove(filename)
        print(f"已删除{filename}以模拟第一次运行。")

    empty_data = load_data(filename)
    print("加载空文件夹得到的数据：", empty_data)

    print("\n--- 正在运行主程序... ---")
'''