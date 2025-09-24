from simhash import Simhash
from diff_utils import find_diff
from yuque_fetcher import fetch_yuque_data
import json
import os
import requests
from datetime import datetime , timedelta
from simhash_utils import generate_simhash, get_hamming_distance


base_url = "https://www.yuque.com/api/v2"
token = "s91TCRkU7KDHYAqy9F5ACOa4WoYUNZKvpI1hsj2S"
group_login = "ph25ri"
book_slug = "ua1c3q"

def load_data(filename):
    if os.path.exists(filename):
        try:
            with open(filename,'r',encoding = 'utf-8') as f:
                return json.load(f)

        except json.JSONDecodeError:
            print(f"警告，无法解析文件{filename}，将重新创建。")
            return {}
    else:
        return {}

def save_data(filename,data):
    try:
        with open(filename,'w',encoding = 'utf-8') as f:
            json.dump(data,f,ensure_ascii = False, indent = 4)
    except IOError as e:
        print(f"错误：无法将数据保存到文件{filename}:{e}")

def get_doc_body(token,group_login,book_slug,doc_id):
    base_url = "https://www.yuque.com/api/v2"
    token = "s91TCRkU7KDHYAqy9F5ACOa4WoYUNZKvpI1hsj2S"
    group_login = "ph25ri"
    book_slug = "ua1c3q"
    url = f"{base_url}/repos/{group_login}/{book_slug}/docs/{doc_id}"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        doc_data = response.json().get("data")
        if doc_data and doc_data.get("body"):
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

def find_diff():

    return


last_run_data = load_data("yuque_data.json")
new_yuque_data = fetch_yuque_data(token,group_login,book_slug)
new_docs_map = new_yuque_data.get("docs_map") if new_yuque_data else {}

new_run_data={}

if new_docs_map:
    for doc_id , new_doc_info in new_yuque_data["docs_map"].items():
        if doc_id in last_run_data and last_run_data[doc_id]["updated_at"] != new_doc_info["updated_at"]:
            doc_id_str = str(doc_id)
            last_doc_info = last_run_data.get(doc_id,{})

            is_new_doc = doc_id_str in last_run_data
            is_updated = last_doc_info.get("updated_at") != new_doc_info.get("updated_at")

            if is_new_doc or is_updated:
                print("检测到更新：{new_doc_info['title']}...")
                document_body = get_doc_body(token, group_login, book_slug, doc_id)

                if document_body:
                    new_simhash_obj = generate_simhash(document_body)

                    if not is_new_doc and "simhash" in last_doc_info:
                        old_simhash_value = last_doc_info["simhash"]
                        old_simhash_obj = Simhash(old_simhash_value)

                        distance = get_hamming_distance(old_simhash_obj, new_simhash_obj)

                        if distance <= 3:
                            print(f"检测到微小更新，文档:{new_doc_info['title']}，汉明距离为{distance}。已跳过。")
                            new_run_data[doc_id_str] = new_doc_info
                            new_run_data[doc_id_str]["body"] = document_body
                            new_run_data[doc_id_str]["simhash"] = new_simhash_obj.value
                            continue

                    print(f"检测到实质性更新，文档：{new_doc_info['title']}。")
                    old_doc_body = last_doc_info.get("body","")
                    diff_content = find_diff(old_doc_body, document_body)

                    if diff_content:
                        print("---差异内容---")
                        print(diff_content)
                    else:
                        print("内容无实质性变化。")

                    new_run_data[doc_id_str] = new_doc_info
                    new_run_data[doc_id_str]["body"] = document_body
                    new_run_data[doc_id_str]["simhash"] = new_simhash_obj.value

            else:
                new_run_data[doc_id_str] = last_doc_info
    save_data('yuque_data.json',new_yuque_data)
    print("数据已保存。")
else:
    print("无法获取语雀数据，请检查配置或网络连接。")









'''
if __name__ == "__main__" :
    test_data = {
        "doc_1":{"title":"first_doc","updated_at":"2025-09-23T10:00:00Z"},
        "doc_2":{"title":"second_doc","updated_at":"2025-09-23T11:00:00Z"},
    }
    filename = "test_data.json"

    save_data(filename,test_data)
    print(f"测试数据已保存到{filename}")

    loaded_data = load_data(filename)
    print("加载的数据：",loaded_data)

    if os.path.exists(filename):
        os.remove(filename)
        print(f"已删除{filename}以模拟第一次运行。")

    empty_data = load_data(filename)
    print("加载空文件夹得到的数据：",empty_data)
'''