# IT Navigator Backend

Bu papka IT Navigator loyihasining backend qismi uchun.

## Hozirgi birinchi qadam

`app/main.py` ichida bitta oddiy FastAPI server bor.

```python
@app.get("/")
def health_check():
    ...
```

Bu funksiya backend ishlayotganini tekshirish uchun kerak. Postman orqali `GET /`
so'rov yuborilganda `status: ok` qaytarsa, server to'g'ri ishga tushgan bo'ladi.

## Ishga tushirish

```bash
cd it_navigator_backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Postman yoki browserda:

```text
GET http://127.0.0.1:8000/
```
