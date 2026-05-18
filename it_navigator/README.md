# IT Navigator REST API

Bu app IT Navigator loyihasining backend API qismi uchun.

## Birinchi endpoint

```text
GET /api/health/
```

Bu endpoint backend ishlayotganini tekshiradi.

Postman'da `GET` request yuborilganda quyidagiga o'xshash JSON qaytadi:

```json
{
  "message": "IT Navigator backend ishlayapti",
  "status": "ok"
}
```

## Hozir yozilgan funksiya

`views.py` ichida:

```python
def health_check(request):
    ...
```

Bu funksiya hozircha database, login yoki AI bilan ishlamaydi. Faqat server
so'rov qabul qilib, JSON javob qaytara olayotganini tekshiradi.
