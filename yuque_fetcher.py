import requests


def fetch_yuque_data(token,group_login,book_slug):
    base_url = "https://www.yuque.com/api/v2"
    token = "s91TCRkU7KDHYAqy9F5ACOa4WoYUNZKvpI1hsj2S"
    group_login = "ph25ri"
    book_slug = "ua1c3q"
    docs_url = f"{base_url}/repos/{group_login}/{book_slug}/docs"
    toc_url = f"{base_url}/repos/{group_login}/{book_slug}/toc"
    headers = {
        "X-Auth-Token": token,
        "Content-Type": "application/json"
    }

    params = {
        "optional_properties": "hits"
    }

    try:
        docs_response = requests.get(docs_url,headers = headers)
        docs_response.raise_for_status()
        docs_data = docs_response.json().get("data")
        docs_map = {doc["id"]:doc for doc in docs_data}

        toc_response = requests.get(toc_url,headers = headers)
        toc_response.raise_for_status()
        toc_list = toc_response.json().get("data")

        return{
            "docs_map":docs_map,
            "toc_list":toc_list
        }

    except requests.exceptions.RequestException as e:
        print(f"API 请求失败：{e}")
        return None
    except KeyError as e:
        print(f"API 返回数据结构错误，缺少键：{e}")
        return None

if __name__ == "__main__":
    TOKEN = "s91TCRkU7KDHYAqy9F5ACOa4WoYUNZKvpI1hsj2S"
    GROUP_LOGIN = "ph25ri"
    BOOKS_SLUG = "ua1c3q"

    data = fetch_yuque_data(TOKEN,GROUP_LOGIN,BOOKS_SLUG)
    if data:
        print("数据获取成功！")




