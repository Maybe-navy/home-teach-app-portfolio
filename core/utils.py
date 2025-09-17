import random, secrets, string
from typing import Tuple
from django.contrib.auth.models import User
from django.core.cache import cache

# パスワード要件：10文字以上、4カテゴリ（大/小/数/記号）のうち少なくとも3カテゴリを含む
LOWER = string.ascii_lowercase
UPPER = string.ascii_uppercase
DIGIT = string.digits
SYMB  = "!@#$%^&*()-_=+[]{};:,.?/"

#ユーザーID自動生成（接頭辞＋数字6桁）
def generate_user_id(prefix):
    while True:
        rand_id = f"{prefix}{random.randint(100000, 999999)}"
        if not User.objects.filter(username=rand_id).exists():
            return rand_id
        
def generate_compliant_password(length: int = 12) -> str:
    """
    要件を必ず満たす初期パスワードを生成。
    デフォルトは12文字。必要なら length=14 などに。
    """
    if length < 10:
        length = 10

    # 最低限の保証：4カテゴリすべてから1文字ずつ（3カテゴリ以上必須だが4カテゴリ全部入れておく方が安全）
    pool = [
        secrets.choice(LOWER),
        secrets.choice(UPPER),
        secrets.choice(DIGIT),
        secrets.choice(SYMB),
    ]

    # 残りは全カテゴリからランダム
    all_chars = LOWER + UPPER + DIGIT + SYMB
    pool += [secrets.choice(all_chars) for _ in range(length - len(pool))]

    # シャッフル（secrets には shuffle がないので Fisher–Yates 風に）
    for i in range(len(pool) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pool[i], pool[j] = pool[j], pool[i]

    return "".join(pool)

def check_password_policy(pw: str) -> Tuple[bool, str]:
    """ 追加の自己チェック（任意）。要件を満たすかを返す """
    if len(pw) < 10:
        return False, "10文字未満です。"
    cats = 0
    cats += any(c in LOWER for c in pw)
    cats += any(c in UPPER for c in pw)
    cats += any(c in DIGIT for c in pw)
    cats += any(c in SYMB  for c in pw)
    if cats < 3:
        return False, "大文字/小文字/数字/記号のうち3種類以上を含めてください。"
    return True, ""


def cached_count(qs, key: str, ttl: int = 60):
    v = cache.get(key)
    if v is not None:
        return v
    v = qs.count()
    cache.set(key, v, ttl)
    return v