import difflib


def find_diff(old_text, new_text):
    """
    比较新旧文本，找出并返回新增和修改的内容。

    参数:
    old_text (str): 旧文档的文本内容。
    new_text (str): 新文档的文本内容。

    返回:
    str: 包含新增和修改内容的文本，如果无差异则返回空字符串。
    """
    # 如果旧文档为空，直接返回新文档全部内容
    if not old_text:
        return new_text

    # 将文本按行分割，以便进行行级比对
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    # 创建一个 SequenceMatcher 对象
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

    diff_output = []
    # 遍历操作码，找出差异
    for opcode, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        # 'insert' 操作表示新文本中新增的内容
        if opcode == 'insert':
            inserted_lines = new_lines[b_start:b_end]
            diff_output.append("\n".join(inserted_lines))

        # 'replace' 操作表示新旧文本中的修改内容
        elif opcode == 'replace':
            # 只取新文本中被修改的部分
            replaced_lines = new_lines[b_start:b_end]
            diff_output.append("\n".join(replaced_lines))

    # 使用换行符连接所有差异内容，并返回
    return "\n".join(diff_output)


# --- 运行示例，帮助你测试代码是否正常工作 ---
if __name__ == "__main__":
    old_doc = """
    这是第一段内容。
    这是第二段内容，有一些小修改。
    这是第三段内容。
    """

    new_doc = """
    这是第一段内容。
    这是第二段内容，有一些重要修改。
    这是新增的第四段内容。
    """

    # 找出差异
    diff = find_diff(old_doc, new_doc)

    print("--- 检测到的差异内容 ---")
    print(diff)