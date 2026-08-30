# EquiSentinel
Project Plan — As-Built

*Real-Time AI-Powered Stock Market Analytics System*

Versi 3.0 — Personal Learning Project

> Dokumen ini merevisi Versi 2.0 agar sesuai dengan kondisi proyek yang sebenarnya setelah Fase 1–3 selesai dikerjakan. Bagian yang di Versi 2.0 bersifat enterprise/production-grade (autentikasi, TLS, Prometheus/Grafana, CI/CD multi-stage, dsb.) dihapus atau disederhanakan karena proyek ini murni untuk belajar dan dijalankan lokal, tidak ada rencana deployment publik. Fase 4 tetap dipertahankan sebagai referensi rencana ke depan.

# Daftar Isi
* [1. Ringkasan Proyek](#1-ringkasan-proyek)
* [2. Strategi Pengerjaan: Phased MVP](#2-strategi-pengerjaan-phased-mvp)
* [3. Tech Stack Lengkap](#3-tech-stack-lengkap)
* [4. Arsitektur & Alur Sistem](#4-arsitektur-alur-sistem)
* [5. Keamanan (Security)](#5-keamanan-security)
* [6. Observability & Monitoring](#6-observability-monitoring)
* [7. Deployment & DevOps](#7-deployment-devops)
* [8. Strategi Testing](#8-strategi-testing)
* [9. Stabilitas & Strategi Skalabilitas](#9-stabilitas-strategi-skalabilitas)
* [10. Human-in-the-Loop & Feedback System](#10-human-in-the-loop-feedback-system)
* [11. Manajemen Risiko](#11-manajemen-risiko)
* [12. Struktur Repository](#12-struktur-repository)
* [13. Fase 4 (Opsional) — Data Engineering & ETL Layer](#13-fase-4-opsional--data-engineering--etl-layer)

---

# 1. Ringkasan Proyek
EquiSentinel adalah sistem pemantauan dan analitik pasar saham real-time. Sistem ini menggunakan Agen AI otonom sebagai "Analis Keuangan Pribadi" yang secara otomatis mendeteksi anomali harga, menarik konteks berita finansial terkait, dan memberikan analisis sentimen terstruktur langsung di dashboard. Ketika terjadi pergerakan harga yang tidak wajar pada suatu emiten (misalnya saham anjlok drastis atau volume transaksi meledak), sistem secara otomatis mengkorelasikan data teknikal dengan berita finansial terbaru, lalu menyimpulkan apakah anomali tersebut didorong oleh faktor teknikal, sentimen pasar, atau aksi korporasi. Seluruh data (harga, berita) berasal dari simulator, bukan feed pasar nyata.

---

# 2. Strategi Pengerjaan: Phased MVP
Mengingat kompleksitas sistem, pengerjaan dibagi menjadi 3 fase bertahap agar progres dapat diukur dan risiko kegagalan diminimalkan.

| Fase | Durasi | Deliverable Utama | Status |
|---|---|---|---|
| Fase 1 — Fondasi | Minggu 1–3 | Simulator + NATS + Go WebSocket + Dashboard basic (grafik live) | Selesai |
| Fase 2 — AI Core | Minggu 4–6 | Python AI Worker + LangGraph state machine + notifikasi anomali | Selesai |
| Fase 3 — Polish | Minggu 7+ | Human-in-the-Loop feedback, historis PostgreSQL, LangSmith monitoring | Selesai |
| Fase 4 — Data Engineering (Opsional) | Iteratif | Airflow ETL + tabel warehouse (candles, indikator, feature store) + dashboard analitik + konteks teknikal AI | Selesai |

---

# 3. Tech Stack Lengkap

## 3.1 Data Ingestion & Simulator
Bahasa: Python 3.12+ dengan uv sebagai package manager.
* Skrip generator tick-by-tick mensimulasikan data OHLCV (Open, High, Low, Close, Volume) untuk emiten BEI (BBCA, BBRI, TLKM, ASII, GOTO).
* Scenario-Driven Scripts: skenario anomali telah diprogram (e.g., crash 7% dalam 5 menit, volume spike 10x) untuk keperluan testing korelasi dengan berita.
* Semua payload menggunakan Protocol Buffers (Protobuf) untuk schema enforcement dan efisiensi serialisasi.

## 3.2 Message Broker — NATS JetStream
Tulang punggung komunikasi berkecepatan tinggi antar service.
* JetStream diaktifkan untuk persistensi pesan (guaranteed delivery) — tidak ada data yang hilang saat AI worker mengalami restart atau latensi tinggi.
* Stream utama: STOCK_QUOTES (data harga), STOCK_NEWS (berita finansial), STOCK_ANOMALY (output dari Go setelah filtering), STOCK_RESULTS (hasil analisis AI).
* Anomali dengan severity tinggi (price_change_pct >5%) dipublikasikan ke subject terpisah (stock.anomaly.critical) agar tidak antre di belakang anomali non-kritis.

## 3.3 API Gateway & Orchestrator — Go (Golang)
Service sentral yang menjadi jembatan antara semua komponen.
* Berlangganan ke NATS stream stock.quotes dan meneruskan data harga ke dashboard via WebSocket.
* Anomaly Detection Engine: menghitung Price Change >3% dalam 1 menit ATAU Volume >5x rata-rata 20 menit terakhir.
* Debouncing: anomali yang sama dari emiten yang sama dikelompokkan dalam window 30 detik untuk mencegah AI overload.
* Menyertakan Correlation ID (UUID v4) pada setiap event anomali untuk menghubungkan data harga dengan hasil analisis AI.
* Menyimpan hasil analisis AI (diterima dari NATS) ke PostgreSQL dan langsung push ke dashboard via WebSocket.
* Menyediakan REST endpoint (`/history`, `/analyses`, `/feedback`) sebagai satu-satunya jalur akses ke PostgreSQL dari luar — dashboard tidak pernah connect langsung ke database (lihat §3.6).

## 3.4 Historical Storage — PostgreSQL 16 (TimescaleDB)
Database utama untuk semua data persisten. Tidak diekspos ke host machine — hanya diakses lewat jaringan internal Docker oleh gateway dan ai-worker, untuk menghindari bentrok dengan PostgreSQL native di mesin development.
* Tabel stock_prices: hypertable TimescaleDB, menyimpan data OHLCV historis dengan indeks pada (ticker, timestamp).
* Tabel news_articles: arsip berita finansial simulasi termasuk ticker terkait, headline, body, dan sumber.
* Tabel anomaly_events: riwayat anomali yang terdeteksi beserta metadata (trigger_type, price_change_pct, volume_ratio, critical, correlation_id).
* Tabel ai_analyses: hasil analisis LangGraph termasuk kesimpulan, sentiment, risk level, model yang digunakan, dan latency.
* Tabel user_feedback: data Human-in-the-Loop (ACCURATE/INACCURATE) per correlation_id, sebagai dataset evaluasi AI.
* Migration dijalankan lewat `make migrate` — runner kustom (bukan ORM) yang mencatat file yang sudah diapply ke tabel `schema_migrations`, idempotent untuk dijalankan berulang.

## 3.5 AI Engine — Python + LangGraph + DeepSeek API
* Python 3.12 dengan uv virtual environment.
* LangGraph sebagai orkestrator state machine Agen AI (bukan sequential chain).
* LangChain untuk tool integration: NATS consumer, PostgreSQL query, dan DeepSeek API call (via `langchain-openai`, DeepSeek bersifat OpenAI-compatible).
* DeepSeek API (model `deepseek-chat`): LLM reasoning dilakukan via REST API, bukan hosting lokal.
* LangSmith: monitoring log pemikiran agen, latensi per state, token usage, dan alur keputusan — aktif sejak awal Fase 2.
* Sentiment Caching: hasil analisis per emiten disimpan dalam Redis (TTL 5 menit) untuk menghindari API call berulang.

## 3.6 Frontend — SvelteKit
* SvelteKit (Node.js runtime standar): framework compiler-based, tanpa Virtual DOM, sehingga bundle size lebih kecil dan overhead runtime jauh lebih rendah dibanding framework berbasis React seperti Next.js.
* Svelte Stores berbasis runes (`$state`): state management reaktif native untuk menangani data WebSocket real-time. Implementasi Capped Buffer (circular array, max 500 data points per ticker) untuk histori quote dan AI analysis agar tidak terjadi memory leak.
* `+page.server.ts`: server-side load function yang mengambil histori harga dan AI analysis dari REST endpoint gateway (bukan connect langsung ke PostgreSQL) sehingga chart dan card AI analysis tetap terisi setelah reload halaman. Submit feedback Human-in-the-Loop juga lewat route handler (`/api/feedback`) yang meneruskan ke gateway, bukan langsung ke database.
* Tailwind CSS 4: styling utility-first yang konsisten.
* Charting library: TradingView Lightweight Charts (free, open-source, framework-agnostic) untuk grafik candlestick, termasuk marker anomali/AI analysis di atas chart.
* Tanpa sistem autentikasi — dashboard ini proyek personal yang hanya diakses lokal oleh satu pengguna, jadi Lucia Auth/JWT sengaja tidak dibangun (lihat §5.1).

---

# 4. Arsitektur & Alur Sistem

## 4.1 Gambaran Arsitektur
Sistem beroperasi dalam pola event-driven yang terdiri dari empat tahap:
1. Ingestion: Python Simulator → NATS (stock.quotes, stock.news)
2. Routing: Go Service → WebSocket (visual) + NATS stock.anomaly (analitik) + persist ke PostgreSQL
3. AI Analysis: Python Worker (LangGraph) → DeepSeek API → hasil ke NATS stock.results
4. Reporting: Go Service → SvelteKit Dashboard via WebSocket + simpan ke PostgreSQL

## 4.2 Definisi Kontrak Data (Protobuf)
Semua komunikasi antar-service menggunakan skema Protobuf yang terdefinisi:
* StockQuote: { ticker, open, high, low, close, volume, timestamp }
* NewsArticle: { id, ticker, headline, body, source, published_at }
* AnomalyEvent: { correlation_id, ticker, trigger_type, price_change_pct, volume_ratio, detected_at }
* AIAnalysis: { correlation_id, ticker, summary, sentiment (BULLISH/BEARISH/NEUTRAL), risk_level (LOW/MEDIUM/HIGH), model_used, latency_ms }

## 4.3 Alur AI State Machine (LangGraph)
Worker Python mengeksekusi state machine berikut untuk setiap AnomalyEvent:
* State 1 — Technical Check: Membaca metrik anomali (price_change_pct, volume_ratio). Jika data tidak cukup signifikan (edge case), langsung ke State 4 dengan default analysis.
* State 2 — Context Retrieval (RAG): Query PostgreSQL untuk berita terkait ticker dalam window 30 menit terakhir. Fallback ke NATS stock.news stream jika database belum punya data terbaru.
* State 3 — LLM Reasoning: Prompt ke DeepSeek API dengan konteks teknikal + berita. Template prompt: "Saham {ticker} bergerak {price_change_pct}% dalam {duration}. Berita terkait: {news_context}. Analisis sentimen dan berikan risk level (LOW/MEDIUM/HIGH) beserta alasan singkat."
* State 4 — Structured Output: LLM mengembalikan JSON terstruktur sesuai skema AIAnalysis. Validasi dengan Pydantic sebelum dikirim ke NATS stock.results.

---

# 5. Keamanan (Security)
Proyek ini berjalan lokal untuk keperluan belajar, tidak ada rencana deployment publik, sehingga sebagian besar kontrol keamanan production-grade sengaja tidak dibangun agar tidak overengineering. Yang dipertahankan hanya yang relevan untuk development lokal yang aman.

## 5.1 Autentikasi & Otorisasi
Tidak diimplementasikan. Tidak ada Lucia Auth/JWT, NATS credentials (NKeys), maupun Role-Based Access — proyek ini single-user dan hanya diakses dari localhost. Ini keputusan sadar, bukan gap: menambah sistem auth/RBAC untuk aplikasi yang tidak pernah diakses banyak orang hanya menambah kompleksitas tanpa manfaat nyata.

## 5.2 Keamanan Jaringan
* Semua komunikasi internal service (Go ↔ NATS, Python ↔ NATS, Go ↔ PostgreSQL/Redis) berjalan di Docker internal network. PostgreSQL dan Redis sengaja tidak diekspos ke host sama sekali — satu-satunya jalur ke database adalah lewat REST endpoint gateway.
* WebSocket dari Go ke browser memakai `ws://` biasa (bukan WSS/TLS) — tidak relevan tanpa deployment ke jaringan publik.
* CORS Policy: gateway melakukan origin check (`ALLOWED_ORIGINS`) pada WebSocket handshake `/ws`, default mengizinkan `http://localhost:5173` dan `http://localhost:4173`.
* Rate limiting tidak diimplementasikan — tidak relevan untuk single local client.

## 5.3 Keamanan Data
* Secrets Management: semua kredensial (database password, API keys) disimpan dalam file `.env` yang TIDAK di-commit ke Git. `.env.example` disediakan sebagai template.
* PostgreSQL: koneksi tanpa SSL — aman karena seluruh trafik berada di dalam jaringan Docker internal, tidak pernah keluar mesin.
* Input Validation: semua payload dari NATS divalidasi dengan Protobuf schema sebelum diproses. Payload AI result divalidasi dengan Pydantic.
* Tidak ada data sensitif yang diproses (seluruh data harga dan berita adalah hasil simulasi), sehingga log sanitization tidak relevan.

## 5.4 Secret Management
Satu-satunya environment yang dipakai adalah development lokal.

| Jenis Secret | Development |
|---|---|
| Database Password | `.env` lokal |
| DeepSeek API Key | `.env` lokal |
| LangSmith API Key | `.env` lokal |

---

# 6. Observability & Monitoring

## 6.1 Logging Strategy
* Go Service: zerolog untuk structured logging (JSON format). Log setiap anomali yang terdeteksi, WebSocket connection/disconnection, dan error NATS/PostgreSQL.
* Python AI Worker: structlog. Log setiap state transition LangGraph, LLM call latency, dan cache hit/miss.
* SvelteKit: `pino` untuk structured logging di server-side hooks (`hooks.server.ts`). Log method, path, status, dan durasi tiap request.
* Log Level: DEBUG di development, INFO di production. ERROR dan CRITICAL selalu di-log.

## 6.2 Metrics & Alerting
Prometheus/Grafana sengaja tidak dipasang — untuk proyek single-instance lokal ini, dashboard metrik terpisah tidak sebanding dengan overhead menjalankan 2 service tambahan.
* LangSmith dipakai sebagai monitoring khusus AI engine: token usage, state transition, latensi per state, error rate.

## 6.3 Health Checks
* Go Service: `GET /health` mengembalikan status koneksi NATS dan jumlah WebSocket aktif.
* Python Worker: `GET /health` mengembalikan status koneksi NATS, status konektivitas DeepSeek API, dan queue depth.
* SvelteKit: `GET /api/health` — health check dasar (liveness saja, tidak memeriksa downstream Postgres/Redis karena dashboard tidak pernah connect langsung ke keduanya).
* Docker Compose healthcheck: setiap service (nats, postgres, redis, gateway, simulator, ai-worker) punya healthcheck definition, dipakai oleh `docker compose up --wait` dan `make test-integration`.

---

# 7. Deployment & DevOps

## 7.1 Docker Compose
Service yang dijalankan via `docker-compose.yml`: nats (JetStream), postgres (TimescaleDB image), redis, gateway, simulator, ai-worker.
* Dashboard **tidak** dikontainerisasi — dijalankan lokal via `npm run dev` selama development, karena tidak ada kebutuhan deploy dan ini menyederhanakan hot-reload saat belajar SvelteKit.
* Named volumes (`postgres_data`, `nats_data`, `redis_data`) menjaga data persisten antar restart.
* Internal network bridge: semua service saling terhubung via nama service (nats:4222, postgres:5432, redis:6379). Hanya `nats` (4222/8222) dan `gateway` (8080) yang di-expose ke host; `postgres` dan `redis` sepenuhnya internal.
* Environment variables di-inject via `.env` (tidak di-commit).

## 7.2 Makefile
Makefile di root project untuk operasional:
* `make up` / `make down` / `make logs` — kontrol stack Docker Compose.
* `make migrate` — jalankan migration SQL secara berurutan lewat runner kustom yang mencatat file yang sudah diapply ke tabel `schema_migrations`, jadi aman dijalankan berulang kali.
* `make proto` — kompilasi semua file `.proto` menjadi kode Go dan Python.
* `make test` — jalankan seluruh unit test suite (gateway, simulator, ai-worker, dashboard).
* `make test-integration` — nyalakan stack penuh, migrate, lalu jalankan test end-to-end nyata (publish anomali sintetis → verifikasi hasil sampai ke PostgreSQL).

## 7.3 CI (GitHub Actions)
Satu workflow (`.github/workflows/ci.yml`), jalan otomatis di setiap push ke `main` dan setiap pull request:
* Empat job paralel (gateway, simulator, ai-worker, dashboard), masing-masing menjalankan unit test suite-nya (`go test`, `pytest`, `pytest`, `vitest`) plus `svelte-check`/`eslint` untuk dashboard.
* Tidak ada build/push image, deploy ke staging, maupun scheduled backup — tidak relevan karena tidak ada server staging/production, hanya development lokal.

## 7.4 Environment
Hanya ada satu environment: **Development (lokal)** — coding, testing, dan demo semuanya di mesin yang sama, dengan data simulasi dan DeepSeek API (`deepseek-chat`) yang sama. Staging dan Production tidak direncanakan.

---

# 8. Strategi Testing

## 8.1 Unit Tests
* Go: test anomaly detection (threshold >3%/>5x volume), debouncing logic, dan Protobuf round-trip.
* Python AI Worker: test setiap state LangGraph secara terpisah dengan mock LLM response, termasuk jalur cache-hit dan fallback saat LLM gagal. Test Pydantic validation untuk output AI.
* SvelteKit (vitest): test parsing pesan WebSocket (quote & AI analysis, termasuk strip prefix enum) dan capped buffer pada quote store.

## 8.2 Integration Tests
* `make test-integration`: publish anomali sintetis ke NATS, lalu poll `stock.results` dan tabel `ai_analyses` di PostgreSQL sampai hasil analisis nyata (dari DeepSeek) muncul — end-to-end tanpa mock.
* Sudah diverifikasi berulang kali dari kondisi stack yang benar-benar bersih (`docker compose down -v`).

## 8.3 Performance Tests
k6 tidak dipakai — cukup dengan script Python kustom yang mempublish banyak anomali sekaligus lalu memantau `consumer_info` NATS JetStream untuk memverifikasi backpressure (`MaxAckPending=10`) bekerja sesuai desain. Latensi end-to-end (anomali terdeteksi sampai analisis AI tersedia) yang teramati selama testing konsisten di kisaran 2–3 detik, jauh di bawah target <15 detik — belum diuji secara formal dengan ratusan concurrent client karena skalanya tidak relevan untuk single local user.

---

# 9. Stabilitas & Strategi Skalabilitas

## 9.1 Schema Enforcement
Protocol Buffers (Protobuf) digunakan untuk semua komunikasi antar-service. Perubahan schema harus backward-compatible (aturan: hanya tambah field baru, jangan hapus atau ubah tipe field lama). Kompilasi ulang `.proto` file diotomasi via `make proto`.

## 9.2 Backpressure Management
NATS JetStream consumer group pada AI worker dengan `MaxAckPending=10` memastikan worker tidak dibanjiri pesan — sudah diverifikasi lewat load test (banyak anomali sekaligus, backlog terkontrol tanpa pesan hilang). Anomali severity tinggi (price_change_pct >5%) diprioritaskan via dedicated subject `stock.anomaly.critical`.

## 9.3 LLM Optimization
* Sentiment Caching (Redis): hasil analisis per ticker di-cache selama 5 menit. Anomali baru untuk ticker yang sama dalam window tersebut menggunakan hasil cache, menghemat LLM call.
* Model Fallback: jika pemanggilan DeepSeek API gagal (exception apa pun — timeout, rate limit, error lain), AI worker langsung mengembalikan analisis default ("Data tidak cukup untuk analisis, pantau secara manual") tanpa retry, agar pipeline tidak blocking.
* Adaptive Sampling (compress prompt saat antrean panjang) sengaja tidak diimplementasikan — optimisasi prematur tanpa bukti antrean pernah jadi bottleneck nyata di skala penggunaan proyek ini.

## 9.4 State Sync via Correlation ID
Setiap AnomalyEvent memiliki correlation_id (UUID v4) yang dibuat oleh Go service. ID ini mengalir melalui semua tahap — dari anomaly detection hingga hasil AI di dashboard, termasuk feedback Human-in-the-Loop — sehingga setiap komponen visual di browser dapat dikorelasikan dengan data teknikal dan hasil analisis yang tepat.

---

# 10. Human-in-the-Loop & Feedback System
Card AI Analysis di dashboard menyertakan dua tombol feedback: Akurat dan Tidak Akurat. Data feedback disimpan ke tabel `user_feedback` di PostgreSQL dengan kolom:
* correlation_id (PRIMARY KEY, FK ke ai_analyses.correlation_id)
* feedback_value (ACCURATE / INACCURATE)
* submitted_at (timestamp)

Tidak ada kolom `user_id` — proyek ini tidak punya sistem akun (lihat §5.1), jadi feedback bersifat anonim per analysis, bukan per user. Submit ulang untuk correlation_id yang sama akan meng-update (upsert) nilai sebelumnya, bukan menambah baris baru. Data ini berfungsi sebagai dataset evaluasi untuk mengukur akurasi model dari waktu ke waktu dan dapat digunakan sebagai fine-tuning dataset di masa mendatang.

---

# 11. Manajemen Risiko

| Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|
| DeepSeek API lambat/timeout | Sedang | Tinggi | Model fallback ke analisis default saat pemanggilan gagal, agar pipeline tidak blocking |
| Rate limit / downtime DeepSeek API mengganggu ketersediaan AI worker | Rendah | Sedang | Fallback ke analisis default (State 4). Tidak ada retry/backoff otomatis — dianggap cukup mengingat volume anomali yang rendah di proyek ini |
| Biaya panggilan API membengkak seiring volume anomali | Rendah | Sedang | Sentiment Caching (Redis, TTL 5 menit) dan debouncing 30 detik di Go gateway menekan jumlah panggilan API berulang |
| Scope creep: fitur bertambah sebelum fase sebelumnya selesai | Tinggi | Tinggi | Freeze fitur per fase; tolak penambahan sampai fase selesai |
| LangGraph state machine sulit di-debug | Sedang | Sedang | LangSmith aktif dari awal Fase 2; setiap state transition ter-log |

---

# 12. Struktur Repository
Monorepo dengan struktur berikut:
* / (root)
  * docker-compose.yml, Makefile, .env.example
  * /proto — Definisi .proto untuk semua kontrak data
  * /migrations — SQL migration, diapply lewat `make migrate`
  * /simulator — Python data generator (uv project)
  * /gateway — Go service (API Gateway + WebSocket + Anomaly Detector + REST history/analytics/feedback API)
  * /ai-worker — Python AI Engine (uv project, LangGraph, DeepSeek API)
  * /etl — Python Airflow project (uv, src layout): DAG ETL, health server, extract/transform/load ke warehouse
  * /dashboard — SvelteKit application (dijalankan lokal, tidak dikontainerisasi)
  * /.github/workflows — CI (unit test + lint per push/PR)

---

# 13. Fase 4 (Opsional) — Data Engineering & ETL Layer
Fase ini bersifat opsional dan dikerjakan setelah Fase 1–3 selesai sepenuhnya dan stabil. Tujuannya menambahkan layer batch processing untuk analitik historis yang lebih kaya, tanpa mengganggu jalur real-time yang sudah berjalan. **Status: Selesai** — detail implementasi aktual dicatat di §13.6.

## 13.1 Posisi dalam Arsitektur
Fase 4 berjalan berdampingan (bukan menggantikan) jalur real-time NATS + Go yang sudah ada. NATS/Go menangani streaming per detik; ETL menangani pemrosesan batch terjadwal (per beberapa menit/jam) untuk agregasi dan analitik historis.
* Extract: menarik data dari tabel PostgreSQL existing (stock_prices, news_articles) serta opsional API eksternal untuk data historis tambahan (mis. data historis BEI).
* Transform: agregasi candle OHLCV per interval (1 menit, 5 menit, 1 jam), kalkulasi indikator teknikal (SMA, EMA, RSI, Bollinger Bands), dan data cleaning (outlier removal, gap filling).
* Load: menulis hasil ke tabel warehouse baru yang terpisah dari tabel transaksional, agar query analitik berat tidak membebani sistem real-time.

## 13.2 Tech Stack Tambahan
* Apache Airflow: orchestrator DAG untuk scheduling, dependency management, retry, dan monitoring job ETL.
* dbt (data build tool) — opsional: untuk transformasi SQL yang lebih terstruktur dan ter-versioning jika kompleksitas transform bertambah.
* pandas / polars: komputasi transform di sisi Python untuk kalkulasi indikator teknikal.
* Tabel warehouse baru di PostgreSQL: candles_1m, candles_5m, candles_1h, technical_indicators, feature_store_ai.
* pgbouncer — opsional: connection pooling terpisah agar query batch ETL tidak rebutan koneksi dengan Go gateway.

## 13.3 Dampak Terhadap Sistem Existing
Sebagian besar perubahan bersifat aditif. Berikut klasifikasinya:

**Murni tambahan (tidak menyentuh kode existing)**
* Container Airflow baru di docker-compose.yml.
* Folder /etl baru berisi DAG Python, terpisah dari codebase AI worker dan gateway.
* Tabel warehouse baru — tidak mengubah skema stock_prices, anomaly_events, atau ai_analyses yang sudah ada.
* Halaman dashboard analitik historis baru (route + komponen Svelte baru).

**Modifikasi ringan (aditif terhadap kode existing)**
* AI Worker: opsional menambah satu state baru di LangGraph untuk membaca tabel technical_indicators sebagai konteks tambahan sebelum reasoning ke LLM. Sistem tetap berfungsi penuh tanpa perubahan ini.
* .env: tambah variabel kredensial Airflow dan koneksi warehouse, tidak menghapus variabel lama.
* CI: tambah satu job baru untuk lint/test DAG.

**Perlu kehati-hatian khusus**
* Resource contention: Airflow scheduler + webserver menambah overhead RAM sekitar 1–1.5GB. Perlu cek headroom mesin sebelum mengaktifkan.
* Query batch yang berat berpotensi membebani PostgreSQL real-time. Mitigasi: gunakan pgbouncer/connection pool terpisah, dan jadwalkan job di luar jam simulasi intensif.

## 13.4 Manfaat yang Diharapkan
* AI Worker mendapat konteks lebih kaya — analisis tidak hanya berdasar berita, tapi juga indikator teknikal (mis. kondisi overbought/oversold) sebagai sinyal tambahan.
* Dashboard mendapat halaman analitik historis: tren jangka panjang, perbandingan indikator antar emiten, laporan periodik.
* Query analitik berat tidak lagi membebani tabel transaksional real-time karena dipisah ke warehouse khusus.

## 13.5 Kriteria Mulai Fase 4
Fase 4 baru layak dimulai jika seluruh kondisi berikut terpenuhi:
1. Fase 1–3 berjalan stabil tanpa bug kritis selama minimal beberapa hari berturut-turut.
2. Tidak ada lagi perubahan besar yang direncanakan pada skema tabel PostgreSQL existing.
3. Tersedia waktu dan resource tambahan untuk melanjutkan sebagai proyek iteratif.

Ketiga kriteria terpenuhi, sehingga Fase 4 dikerjakan sebagai iterasi di atas fondasi existing — hasilnya dicatat di §13.6.

## 13.6 Catatan As-Built

Implementasi aktual (deviasi dari rencana di atas, semuanya aditif):

* **Struktur /etl**: package Python `src/etl` (bukan modul flat) — DAG mengimpor `etl.*` tanpa hack sys.path. Health server ETL di-wire via `etl.entrypoint` (aiohttp + spawn `airflow standalone`), port `ETL_HTTP_PORT` (default 8083, terpisah dari simulator 8082).
* **Airflow 3.x**: CLI user management berubah — `airflow users` dihapus, diganti Simple Auth Manager. Password admin disimpan di `airflow_home/simple_auth_manager_passwords.json.generated` dan tidak dicetak ulang di log setelah run pertama.
* **DAG**: candle_aggregation (setiap 5 menit), technical_indicators (setiap 10 menit, dengan gap filling sebelum kalkulasi), data_quality (setiap jam, deteksi + log saja), feature_store (setiap 15 menit, mengisi `feature_store_ai` dari indikator terbaru per interval).
* **Data cleaning**: `fill_gaps` (forward-fill harga, volume/tick_count 0) di-wire ke DAG indikator; outlier hanya dideteksi & dilog (tidak dihapus dari warehouse) karena candle anomali adalah sinyal utama sistem.
* **Gateway**: endpoint baru `/candles`, `/indicators`, `/indicators/summary` (interval divalidasi allowlist 1m/5m/1h).
* **Dashboard**: halaman `/analytics` — chart candlestick + overlay SMA/EMA/Bollinger + panel RSI, serta tabel perbandingan indikator antar emiten.
* **AI Worker**: state LangGraph baru `technical_context` membaca `technical_indicators` (terbaru per interval via DISTINCT ON) dan menyertakannya ke prompt LLM; fallback aman jika tabel kosong.
* **Keputusan yang dilewati (opsional)**: dbt, pgbouncer, integrasi API eksternal historis (hanya stub `fetch_external_history`), laporan periodik di dashboard. `feature_store_ai` diisi tapi belum dikonsumsi AI worker (AI worker membaca `technical_indicators` langsung). Transform memakai pandas (polars tidak dipakai).

> *Estimasi effort Fase 4 jauh lebih ringan dibanding Fase 1–3 karena tidak ada pembangunan ulang — murni menambah satu layer baru di atas fondasi yang sudah ada.*
