# Order & Inventory Reservation Service

dbdiagram.io havolasi: https://dbdiagram.io/d/order-backend-fastapi-6aa0d07828e65f9ec257a59a

---

## Ishga tushirish oddiyroq bo'lishi uchun make faylda komandalar yasab qo'ydim

| Buyruq         | Nima qiladi                                                 | To'liq ekvivalenti |
|----------------|-------------------------------------------------------------|--------------------|
| `make up`      | To'liq ishga tushurish (o'zgargan bo'lsa qayta build qiladi) | `docker compose up -d --build` |
| `make down`    | To'xtatadi va DB volume'ini o'chiradi                       | `docker compose down -v` |
| `make logs`    | api + worker loglar                                         | `docker compose logs -f api worker` |
| `make migrate` | alembic orqali migratsiya qilish                            | `alembic upgrade head` |
| `make test`    | Testlarni ishga tushirish                                   | `pytest` |
| `make shell`   | Konteynerda `psql` ochadi                                   | `docker compose exec db psql -U marketplace -d marketplace_db` |

---

## API

| Metod | Yo'l                  | Auth | Izoh                                                                       |
|-------|-----------------------|------|----------------------------------------------------------------------------|
| POST  | `/auth/register`      | –    | `{email, password}` → `{id, email}`                                        |
| POST  | `/auth/login`         | –    | → `{access_token, token_type}`                                             |
| POST  | `/products`           | JWT  | `{name, price, stock_quantity}`                                            |
| GET   | `/products/{id}`      | –    | Redis'da keshlanadi                                                        |
| POST  | `/orders`             | JWT  | **`Idempotency-Key` header majburiy**; `{items: [{product_id, quantity}]}` |
| GET   | `/orders/{id}`        | JWT  | faqat egasi (aks holda 404)                                                |
| POST  | `/orders/{id}/cancel` | JWT  | faqat egasi; rezerv qilingan stock qaytariladi                             |
| GET   | `/health`             | –    | db + redis tekshiriladi                                                    |

---

## Qilingan qarorlar va sabablari

### Til / framework — Python + FastAPI
Async-native, tayyor OpenAPI, Pydantic validatsiyasi. asyncpg — eng tez Postgres drayverlaridan biri.

### PostgreSQL + qo'lda yozilgan SQL, ORM yo'q
Ma'lumot bir vaqtda buzilib ketmasligi uchun ORM emas,
oddiy UPDATE ... WHERE so'rovi ishlatilgan —
chunki bu aniqroq va tekshirish oson. 
asyncpg esa tez ishlaydi va sana/son kabi ma'lumotlarni to'g'ri saqlaydi.

---

### Migratsiyalar — Alembic qo'lda yozilgan SQL'ni ishga tushiradi
Alembic ni db tablelarni generatsiya qilish uchun ishlatdim.
Chunki juda ham sodda va odatda fastapi bilan yaxshi ishlaydi.
Undan tashqari u orqali tablelarda har qanday amllarni bajarsa bo'ladi.

### Concurrency correctness — shartli UPDATE, Postgres tomonidan kafolatlanadi
Stock reserve bo'lishi:

```sql
UPDATE products
SET stock_quantity = stock_quantity - $1
WHERE id = $2 AND stock_quantity >= $1
RETURNING stock_quantity;
```

Postgresning odatiy READ COMMITTED rejimida, bitta qatorga bir vaqtda bir nechta
UPDATE kelsa, ular navbatga turadi (qulflanadi). Har biri o'z navbati kelganda,
`stock_quantity >= $1` shartini oldingi queryni commit qilingan
qiymatiga qarab qayta tekshiradi.

Masalan: omborda 10 dona tovar bor, 50 kishi bir vaqtda 1 donadan buyurtma bersa —
faqat 10 tasi muvaffaqiyatli o'tadi. Qolgan 40 tasida tekshiruv False
chiqadi va o'sha buyurtmaning hammasi bekor qilinadi (rollback).

### Idempotency — bir xil `Idempotency-Key` bilan stock ikki marta kamaymasin
`POST /orders` da `Idempotency-Key` header'ini majburiy qildim. Har bir kalitni
`idempotency_keys` jadvaliga saqladim va `(user_id, key)` unique bo'ldi.

Buyurtma yaratish jarayoni bitta transaction ichida bo'ladi:

1. avval shu `(user_id, key)` bazada bor-yo'qligini tekshiraman. Bor bo'lsa —
   yangi hech narsa qilmayman, oldin saqlangan javobni qaytaraman;
2. bo'lmasa — stock'ni kamaytiraman, buyurtmani yarataman;
3. eng oxirida `idempotency_keys` ga yozuv qo'shaman.

Agar bir xil ikkita so'rov aynan bir vaqtda kelib qolsa, ikkalasi ham 1-qadamda
"kalit yo'q" deb o'tib ketishi mumkin. Shu holatda 3-qadamdagi `INSERT` bazadagi
unique cheklovda, bittasi xato beradi. O'shada so'rovning butun
transaction'i rollback bo'ladi (ya'ni uning stock kamaytirishi ham bekor bo'ladi),
keyin u bir marta qaytadan urinadi — bu safar 1-qadamda birinchi so'rov saqlab
ulgurgan javobni topadi va o'shani qaytaradi.

Natijada: kalit bir xil bo'lsa har doim o'sha buyurtma qaytadi, stock esa faqat
bir marta kamayadi.

### Keshlash — Redis, cache-aside strategiyasi
Mahsulotni o'qish (`GET /products/{id}`) tez-tez chaqiriladi, lekin kamdan-kam
o'zgaradi — shuning uchun uni Redis'ga keshladim. **cache-aside** ishlatdim:
avval Redis'dan qidiraman, topilsa o'shani qaytaraman; topilmasa bazadan olaman
va Redis'ga 60 soniyalik TTL bilan yozib qo'yaman.

Stock o'zgarganda, buyurtma berilganda, bekor qilinganda keshdagi kalitni o'chirib
tashlayman. Sababi: yangi qiymat yozib qo'ysam-u, keyin o'sha transaction
rollback bo'lib qolsa, keshda noto'g'ri son qolib ketadi. O'chirish esa har doim
xavfsiz — keyingi o'qishda kesh bazadan qaytadan to'ladi.

TTL — shunchaki qo'shimcha xavfsizlik: bir joyda keshni o'chirishni unutib
qo'ysam muommo kelib chiqmasligi uchun.


### arq (Celery emas)
15 daqiqa ichida to'lanmagan `pending` buyurtmalarni avtomatik bekor qilish kerak
edi. Buning uchun arq'ni tanladim: u ham async, o'sha bitta Redis'ni ishlatadi va
Celery'ga o'xshab ortiqcha sozlash talab qilmaydi.

`cancel_expired_orders` funksiyasi har daqiqada bir marta ishlaydi. U `expires_at`
o'tib ketgan `pending` buyurtmalarni topib, ularni `cancelled` ga o'tkazadi va
band qilingan stock'ni omborga qaytaradi.

Ikkita nozik joy bor:

- Buyurtmalarni `SELECT ... FOR UPDATE SKIP LOCKED` bilan olaman — shunda bir
  nechta worker bir vaqtda ishlasa ham, bir buyurtmani ikkitasi bir vaqtda
  qamrab olmaydi.
- Statusni o'zgartirishda `WHERE status = 'pending'` shartini qo'yaman. Agar
  foydalanuvchi aynan o'sha payt buyurtmani qo'lda bekor qilayotgan bo'lsa,
  faqat bittasi qatorni yangilaydi — stock ikki marta qaytmaydi.

### Portlar — Postgres `5433` da
Konteyner ichida Postgres odatdagidek `5432` da turadi, faqat tashqariga (host'ga)
`5433` qilib chiqardim — kimningdir kompyuterida allaqachon `5432` da Postgres
ishlayotgan bo'lsa, to'qnashib qolmasin deb.
---
