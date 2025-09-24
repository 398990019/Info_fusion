from simhash import Simhash
import jieba

def get_tokens(doc_text): #针对英文的get_token
    if not isinstance(doc_text, str):
        return []
    return doc_text.lower().replace('.','').replace(',','').split()

def generate_simhash(doc_text):
    return Simhash(get_tokens(doc_text))


def get_hamming_distance(hash1,hash2):
    if not (hash1 and hash2):
        return float('inf')
    return hash1.distance(hash2)