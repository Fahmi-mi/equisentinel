# EquiSentinel
Project Plan — Revised & Detailed

*Real-Time AI-Powered Stock Market Analytics System*

Versi 2.0 — Semester Break Project

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
* [11. Evaluasi & Skor Plan (Versi Revisi)](#11-evaluasi-skor-plan-versi-revisi)
* [12. Manajemen Risiko](#12-manajemen-risiko)
* [13. Struktur Repository](#13-struktur-repository)
* [14. Fase 4 (Opsional) — Data Engineering & ETL Layer](#14-fase-4-opsional--data-engineering--etl-layer)
* [Penutup](#penutup)

---

# 1. Ringkasan Proyek
EquiSentinel adalah sistem pemantauan dan analitik pasar saham real-time berskala enterprise. Sistem ini menggunakan Agen AI otonom sebagai "Analis Keuangan Pribadi" yang secara otomatis mendeteksi anomali harga, menarik konteks berita finansial terkait, dan memberikan analisis sentimen terstruktur langsung di dashboard. Ketika terjadi pergerakan harga yang tidak wajar pada suatu emiten (misalnya saham anjlok drastis atau volume transaksi meledak), sistem secara otomatis mengkorelasikan data teknikal dengan berita finansial terbaru, lalu menyimpulkan apakah anomali tersebut didorong oleh faktor teknikal, sentimen pasar, atau aksi korporasi.

---

# 2. Strategi Pengerjaan: Phased MVP
Mengingat kompleksitas sistem, pengerjaan dibagi menjadi 3 fase bertahap agar progres dapat diukur dan risiko kegagalan diminimalkan.

| Fase | Durasi | Deliverable Utama | Status |
|---|---|---|---|
| Fase 1 — Fondasi | Minggu 1–3 | Simulator + NATS + Go WebSocket + Dashboard basic (grafik live) | Selesai |
| Fase 2 — AI Core | Minggu 4–6 | Python AI Worker + LangGraph state machine + notifikasi anomali | Selesai |
| Fase 3 — Polish | Minggu 7+ | Human-in-the-Loop feedback, historis PostgreSQL, LangSmith monitoring | Selesai |

---

# 3. Tech Stack Lengkap

## 3.1 Data Ingestion & Simulator
Bahasa: Python 3.12+ dengan uv sebagai package manager.
* Skrip generator tick-by-tick mensimulasikan data OHLCV (Open, High, Low, Close, Volume) untuk emiten BEI (BBCA, GOTO, TLKM, dll.).
* Scenario-Driven Scripts: skenario anomali telah diprogram (e.g., crash 7% dalam 5 menit, volume spike 10x) untuk keperluan testing korelasi dengan berita.
* Semua payload menggunakan Protocol Buffers (Protobuf) untuk schema enforcement dan efisiensi serialisasi.

## 3.2 Message Broker — NATS JetStream
Tulang punggung komunikasi berkecepatan tinggi antar service.
* JetStream diaktifkan untuk persistensi pesan (guaranteed delivery) — tidak ada data yang hilang saat AI worker mengalami restart atau latensi tinggi.
* Dua stream utama: stock.quotes (data harga, high-throughput) dan stock.news (berita finansial).
* Stream ketiga: stock.anomaly (output dari Go setelah filtering) dengan consumer group untuk AI worker.
* Priority Queue: anomali dengan severity tinggi (>5% dalam 1 menit) mendapat prioritas lebih tinggi dalam antrian.

## 3.3 API Gateway & Orchestrator — Go (Golang)
Service sentral yang menjadi jembatan antara semua komponen.
* Berlangganan ke NATS stream stock.quotes dan meneruskan data harga ke dashboard via WebSocket.
* Anomaly Detection Engine: menghitung Price Change >3% dalam 1 menit ATAU Volume >5x rata-rata 20 menit terakhir.
* Debouncing: anomali yang sama dari emiten yang sama dikelompokkan dalam window 30 detik untuk mencegah AI overload.
* Menyertakan Correlation ID (UUID v4) pada setiap event anomali untuk menghubungkan data harga dengan hasil analisis AI.
* Menyimpan hasil analisis AI (diterima dari NATS) ke PostgreSQL dan langsung push ke dashboard via WebSocket.

## 3.4 Historical Storage — PostgreSQL 16
Database utama untuk semua data persisten.
* Tabel stock_prices: menyimpan data OHLCV historis dengan indeks pada (ticker, timestamp).
* Tabel news_articles: arsip berita finansial termasuk ticker terkait, timestamp, dan sentiment score.
* Tabel anomaly_events: riwayat anomali yang terdeteksi beserta metadata (severity, trigger condition, correlation_id).
* Tabel ai_analyses: hasil analisis LangGraph termasuk kesimpulan, risk level, dan model yang digunakan.
* Tabel user_feedback: data Human-in-the-Loop (akurat/salah) sebagai dataset evaluasi AI.

> *Gunakan TimescaleDB extension untuk tabel time-series (stock_prices) agar query historis jauh lebih cepat.*

## 3.5 AI Engine — Python + LangGraph + DeepSeek API
* Python 3.12 dengan uv virtual environment.
* LangGraph sebagai orkestrator state machine Agen AI (bukan sequential chain).
* LangChain untuk tool integration: NATS consumer, PostgreSQL query, dan DeepSeek API call.
* DeepSeek API (mis. model `deepseek-chat`): LLM reasoning dilakukan via REST API, bukan hosting lokal. Memerlukan API key dan koneksi internet — pengembangan offline tidak lagi memungkinkan, namun tidak butuh GPU/RAM besar untuk hosting model sendiri.
* LangSmith: monitoring log pemikiran agen, latensi per state, token usage, dan alur keputusan.
* Sentiment Caching: hasil analisis per emiten disimpan dalam Redis (TTL 5 menit) untuk menghindari API call berulang — penting untuk performa maupun untuk menekan biaya panggilan API.

## 3.6 Frontend — SvelteKit
* SvelteKit (Node.js runtime standar): framework compiler-based, tanpa Virtual DOM, sehingga bundle size lebih kecil dan overhead runtime jauh lebih rendah dibanding framework berbasis React seperti Next.js.
* Svelte Stores (writable/derived): state management reaktif native untuk menangani data WebSocket real-time. Implementasi Capped Buffer (circular array, max 500 data points) dan RequestAnimationFrame untuk render grafik candlestick agar tidak terjadi memory leak.
* `+page.server.ts` / Form Actions: server-side data loading untuk halaman historis dan submit feedback Human-in-the-Loop langsung ke PostgreSQL, tanpa API layer terpisah.
* Tailwind CSS 3: styling utility-first yang konsisten.
* Lucia Auth (atau JWT custom via `+hooks.server.ts`): autentikasi token untuk semua API endpoint dan WebSocket handshake
* Charting library: TradingView Lightweight Charts (free, open-source, framework-agnostic) untuk grafik candlestick profesional.

---

# 4. Arsitektur & Alur Sistem

## 4.1 Gambaran Arsitektur
Sistem beroperasi dalam pola event-driven yang terdiri dari empat tahap:
1. Ingestion: Python Simulator → NATS (stock.quotes, stock.news)
2. Routing: Go Service → WebSocket (visual) + NATS stock.anomaly (analitik)
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
Keamanan dirancang berlapis (defense-in-depth) di setiap layer sistem:

## 5.1 Autentikasi & Otorisasi
* Lucia Auth (atau JWT custom via SvelteKit hooks): semua API endpoint dan WebSocket handshake wajib menyertakan token autentikasi yang valid.
* NATS Authentication: gunakan NATS credentials file (NKeys) untuk mengamankan koneksi antara Go service, Python Simulator, dan Python AI Worker ke NATS server.
* Role-Based Access: dua role — Admin (bisa lihat semua data + kelola user) dan Viewer (hanya bisa melihat dashboard).

## 5.2 Keamanan Jaringan
* Semua komunikasi internal service (Go ↔ NATS, Python ↔ NATS) berjalan di Docker internal network, tidak terekspos ke publik.
* WebSocket dari Go ke browser: gunakan WSS (WebSocket Secure) dengan TLS.
* CORS Policy: whitelist hanya domain frontend SvelteKit yang diizinkan mengakses Go WebSocket endpoint.
* Rate Limiting: pasang middleware rate limiter di SvelteKit (60 req/menit per user, via hooks.server.ts) dan di Go (100 WebSocket connection per IP).

## 5.3 Keamanan Data
* Secrets Management: semua kredensial (database password, NATS credentials, API keys) disimpan dalam file .env yang TIDAK di-commit ke Git. Gunakan .env.example sebagai template.
* PostgreSQL: aktifkan SSL connection untuk semua koneksi ke database.
* Input Validation: semua payload dari NATS divalidasi dengan Protobuf schema sebelum diproses. Payload AI result divalidasi dengan Pydantic.
* Log Sanitization: jangan log data sensitif (harga saham yang belum dipublikasikan, data user) dalam format plain text.

## 5.4 Secret Management di Berbagai Environment

| Jenis Secret | Development | Production |
|---|---|---|
| Database Password | .env lokal | Environment variable di server / Docker secret |
| NATS Credentials | nats.creds file lokal | Docker secret / K8s secret |
| Auth Secret (Lucia/JWT) | .env lokal (`openssl rand -base64 32`) | Set manual di server, rotasi berkala |
| DeepSeek API Key | .env lokal | Environment variable di server / Docker secret |
| LangSmith API Key | .env lokal | Environment variable di server |

---

# 6. Observability & Monitoring

## 6.1 Logging Strategy
* Go Service: gunakan zerolog untuk structured logging (JSON format). Log setiap anomali yang terdeteksi, WebSocket connection/disconnection, dan error NATS.
* Python AI Worker: gunakan structlog. Log setiap state transition LangGraph, LLM call latency, dan Pydantic validation error.
* SvelteKit: gunakan library seperti `pino` untuk structured logging di server-side hooks. Log request, auth event, dan feedback submission.
* Log Level: DEBUG di development, INFO di production. ERROR dan CRITICAL selalu di-log di semua environment.

## 6.2 Metrics & Alerting
* Prometheus + Grafana (via Docker Compose): expose /metrics endpoint dari Go service dan Python worker.
* Metrik kunci yang dipantau:
  * NATS queue depth (stock.anomaly) — alert jika >100 pesan menumpuk
  * AI Worker processing latency — alert jika >10 detik per analisis
  * WebSocket connection count — monitor jumlah client aktif
* LangSmith: monitoring khusus untuk AI engine — token usage, state transition heatmap, error rate per state.

## 6.3 Health Checks
* Go Service: endpoint GET /health mengembalikan status koneksi NATS dan jumlah WebSocket aktif.
* Python Worker: endpoint GET /health mengembalikan status koneksi NATS, status konektivitas DeepSeek API, dan queue depth.
* SvelteKit: endpoint `/api/health` (route handler) untuk cek koneksi PostgreSQL, Redis, dan storage.
* Docker Compose healthcheck: setiap service memiliki healthcheck definition agar Docker tahu kapan service siap.

---

# 7. Deployment & DevOps

## 7.1 Docker Compose (Development & Staging)
Semua service dijalankan via single docker-compose.yml agar reprodusibel di mesin mana pun:
* Service: nats (JetStream enabled), postgres (+ TimescaleDB), redis, go-gateway, python-simulator, python-ai-worker, sveltekit-app, prometheus, grafana.
* Named volumes untuk PostgreSQL dan NATS data agar data persisten saat restart.
* Internal network bridge: semua service berkomunikasi via nama service (e.g., nats:4222, postgres:5432), tidak via IP.
* Environment variables di-inject via .env file yang tidak di-commit.

## 7.2 Makefile / Task Runner
Sediakan Makefile di root project untuk mempermudah operasional:
* make up: jalankan seluruh stack (docker compose up -d)
* make down: hentikan semua service
* make migrate: jalankan database migration (mis. via Drizzle ORM atau node-pg-migrate)
* make proto: kompilasi semua file .proto menjadi kode Go dan Python
* make logs: tampilkan log dari semua service secara real-time
* make test: jalankan semua test suite

## 7.3 CI/CD Pipeline (GitHub Actions)
Tiga workflow utama:

### Workflow 1: PR Validation (trigger: pull_request)
* Lint: golangci-lint untuk Go, ruff + mypy untuk Python, eslint + svelte-check untuk SvelteKit.
* Unit Tests: go test ./... untuk Go, pytest untuk Python, vitest untuk SvelteKit.
* Protobuf Validation: cek konsistensi .proto file antara Go dan Python generator.
* Build Check: docker compose build untuk memastikan semua image berhasil dibangun.

### Workflow 2: Staging Deploy (trigger: push ke branch main)
* Build dan push Docker images ke GitHub Container Registry (ghcr.io).
* Deploy ke staging server via SSH + docker compose pull && docker compose up -d.
* Smoke test otomatis: cek health endpoint semua service setelah deploy.

### Workflow 3: Scheduled Data Backup (trigger: cron setiap hari pukul 02.00)
* pg_dump database PostgreSQL dan upload ke storage (GitHub Release atau cloud storage).
* Alert via email jika backup gagal.

## 7.4 Environment Management

| Environment | Tujuan | Data | AI Model |
|---|---|---|---|
| Development (lokal) | Coding & debugging | Simulated (Python script) | DeepSeek API (`deepseek-chat`) |
| Staging | Testing integrasi & demo | Simulated dengan skenario lengkap | DeepSeek API (`deepseek-chat`) |
| Production (opsional) | Live demo / portofolio | Simulated (tidak ada data real) | Sama dengan staging |

---

# 8. Strategi Testing

## 8.1 Unit Tests
* Go: test fungsi anomaly detection (apakah threshold >3% terdeteksi benar), debouncing logic, dan Protobuf serialization.
* Python AI Worker: test setiap state LangGraph secara terpisah dengan mock LLM response. Test Pydantic validation untuk output AI.
* SvelteKit: test alur autentikasi (Lucia/JWT), endpoint feedback submission, dan data historis query (via vitest).

## 8.2 Integration Tests
* End-to-end flow test: Python Simulator menembak anomali → Go mendeteksi → AI Worker memproses → hasil muncul di response API SvelteKit.
* Gunakan Docker Compose test environment dengan database dan NATS yang terisolasi.
* Test scenario: normal market (tidak ada alert), anomali tunggal, burst anomali (10 emiten dalam 1 menit).

## 8.3 Performance Tests
* Gunakan k6 untuk load testing WebSocket endpoint Go: simulasikan 100 concurrent client menerima data real-time.
* Ukur AI Worker throughput: berapa banyak analisis yang bisa diproses per menit dengan DeepSeek API, termasuk dampak rate limit dari sisi provider.
* Target: anomali terdeteksi dan analisis AI tersedia di dashboard dalam <15 detik dari terjadinya event.

---

# 9. Stabilitas & Strategi Skalabilitas

## 9.1 Schema Enforcement
Protocol Buffers (Protobuf) digunakan untuk semua komunikasi antar-service. Perubahan schema harus backward-compatible (aturan: hanya tambah field baru, jangan hapus atau ubah tipe field lama). Kompilasi ulang .proto file diotomasi via make proto.

## 9.2 Backpressure Management
NATS JetStream consumer group pada AI worker dengan MaxAckPending=10 memastikan worker tidak dibanjiri pesan. Anomali severity tinggi (trigger: price_change_pct >5%) diprioritaskan via dedicated subject stock.anomaly.critical.

## 9.3 LLM Optimization
* Adaptive Sampling: jika queue stock.anomaly >50 pesan, Go mengirim prompt yang lebih ringkas (compressed context) ke AI worker.
* Sentiment Caching (Redis): hasil analisis per ticker di-cache selama 5 menit. Anomali baru untuk ticker yang sama dalam window tersebut menggunakan hasil cache, menghemat LLM call.
* Model Fallback: jika DeepSeek API timeout >10 detik atau gagal (rate limit/downtime), AI worker mengembalikan analisis default ("Data tidak cukup untuk analisis, pantau secara manual") agar sistem tidak blocking.

## 9.4 State Sync via Correlation ID
Setiap AnomalyEvent memiliki correlation_id (UUID v4) yang dibuat oleh Go service. ID ini mengalir melalui semua tahap — dari anomaly detection hingga hasil AI di dashboard — sehingga setiap komponen visual di browser dapat dikorelasikan dengan data teknikal dan hasil analisis yang tepat.

---

# 10. Human-in-the-Loop & Feedback System
Setiap notifikasi anomali di dashboard menyertakan dua tombol feedback: Akurat dan Tidak Akurat. Data feedback disimpan ke tabel user_feedback di PostgreSQL dengan kolom:
* analysis_id (FK ke ai_analyses)
* feedback_value (ACCURATE / INACCURATE)
* user_id (FK ke users)
* submitted_at (timestamp)

Data ini berfungsi sebagai dataset evaluasi untuk mengukur akurasi model dari waktu ke waktu dan dapat digunakan sebagai fine-tuning dataset di masa mendatang.

---

# 11. Evaluasi & Skor Plan (Versi Revisi)
Berikut adalah penilaian plan versi revisi ini berdasarkan delapan dimensi:

| Dimensi | Skor Lama | Skor Baru | Keterangan |
|---|---|---|---|
| Arsitektur sistem | 90 | 92 | Alur Go → AI → Dashboard kini terdefinisi lengkap |
| Kelengkapan stack | 85 | 90 | Klarifikasi DeepSeek API sebagai LLM provider, tambah Redis & TimescaleDB |
| Skalabilitas & stabilitas | 88 | 91 | Adaptive sampling & model fallback ditambahkan |
| Realisme scope (Phased MVP) | 55 | 80 | Pembagian 3 fase membuat scope jauh lebih terkelola |
| Dokumentasi & alur | 85 | 93 | Kontrak data Protobuf & state machine LangGraph terinci |
| Keamanan & auth | 70 | 88 | NATS auth, CORS, rate limiting, secrets management |
| Observability & testing | 60 | 87 | Prometheus, Grafana, health checks, unit + integration test |
| Deployment & DevOps | 50 | 88 | Docker Compose, Makefile, CI/CD GitHub Actions lengkap |

**Skor Keseluruhan (Versi Revisi): 89 / 100**

> *Sisa 11 poin mencerminkan kompleksitas implementasi nyata yang hanya bisa diverifikasi saat koding berlangsung: apakah DeepSeek API cukup cepat dan stabil (dari sisi latency maupun rate limit) untuk target <15 detik, apakah LangGraph state machine bisa di-debug dengan mudah, dan apakah NATS JetStream stabil di environment lokal Docker.*
>
> *Catatan revisi: frontend diganti dari Laravel TALL Stack ke SvelteKit untuk mengeksplorasi stack baru dengan overhead runtime lebih ringan (compiler-based, tanpa Virtual DOM) dibanding alternatif seperti Next.js. Perubahan ini bersifat netral terhadap skor — bukan perbaikan kualitas plan, melainkan pertukaran teknologi yang tetap mempertahankan kelengkapan fitur (autentikasi, real-time rendering, Human-in-the-Loop) di bagian yang relevan.*

---

# 12. Manajemen Risiko

| Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|
| DeepSeek API lambat/timeout (>15 detik per analisis) | Sedang | Tinggi | Gunakan model DeepSeek yang lebih ringan, atau siapkan provider API cadangan (mis. Gemini API) sebagai fallback |
| Rate limit / downtime DeepSeek API mengganggu ketersediaan AI worker | Rendah | Sedang | Retry dengan exponential backoff, circuit breaker, dan fallback ke analisis default (State 4) agar sistem tidak blocking |
| Biaya panggilan API membengkak seiring volume anomali | Rendah | Sedang | Sentiment Caching (Redis, TTL 5 menit) dan debouncing 30 detik di Go gateway menekan jumlah panggilan API berulang |
| Scope creep: fitur bertambah sebelum Fase 1 selesai | Tinggi | Tinggi | Freeze fitur per fase; buat backlog dan tolak penambahan sampai fase selesai |
| NATS JetStream sulit dikonfigurasi lokal | Rendah | Sedang | Gunakan official NATS Docker image dengan config file minimal yang sudah terdokumentasi |
| LangGraph state machine sulit di-debug | Sedang | Sedang | Aktifkan LangSmith dari hari pertama; log setiap state transition |
| Waktu liburan habis sebelum Fase 2 | Sedang | Rendah | Fase 1 sudah merupakan proyek portofolio yang berdiri sendiri |

---

# 13. Struktur Repository
Monorepo dengan struktur berikut:
* / (root)
  * docker-compose.yml, Makefile, .env.example, README.md
  * /proto — Definisi .proto untuk semua kontrak data
  * /simulator — Python data generator (uv project)
  * /gateway — Go service (API Gateway + WebSocket + Anomaly Detector)
  * /ai-worker — Python AI Engine (uv project, LangGraph, DeepSeek API)
  * /dashboard — SvelteKit application
  * /infra — Konfigurasi NATS, Prometheus, Grafana
  * /.github/workflows — CI/CD pipeline (GitHub Actions)

---

# 14. Fase 4 (Opsional) — Data Engineering & ETL Layer
Fase ini bersifat opsional dan baru dipertimbangkan setelah Fase 1–3 selesai sepenuhnya dan stabil. Tujuannya menambahkan layer batch processing untuk analitik historis yang lebih kaya, tanpa mengganggu jalur real-time yang sudah berjalan. Disimpan sebagai referensi untuk dipertimbangkan di kemudian hari.

## 14.1 Posisi dalam Arsitektur
Fase 4 berjalan berdampingan (bukan menggantikan) jalur real-time NATS + Go yang sudah ada. NATS/Go menangani streaming per detik; ETL menangani pemrosesan batch terjadwal (per beberapa menit/jam) untuk agregasi dan analitik historis.
* Extract: menarik data dari tabel PostgreSQL existing (stock_prices, news_articles) serta opsional API eksternal untuk data historis tambahan (mis. data historis BEI).
* Transform: agregasi candle OHLCV per interval (1 menit, 5 menit, 1 jam), kalkulasi indikator teknikal (SMA, EMA, RSI, Bollinger Bands), dan data cleaning (outlier removal, gap filling).
* Load: menulis hasil ke tabel warehouse baru yang terpisah dari tabel transaksional, agar query analitik berat tidak membebani sistem real-time.

## 14.2 Tech Stack Tambahan
* Apache Airflow: orchestrator DAG untuk scheduling, dependency management, retry, dan monitoring job ETL.
* dbt (data build tool) — opsional: untuk transformasi SQL yang lebih terstruktur dan ter-versioning jika kompleksitas transform bertambah.
* pandas / polars: komputasi transform di sisi Python untuk kalkulasi indikator teknikal.
* Tabel warehouse baru di PostgreSQL: candles_1m, candles_5m, candles_1h, technical_indicators, feature_store_ai.
* pgbouncer — opsional: connection pooling terpisah agar query batch ETL tidak rebutan koneksi dengan Go gateway.

## 14.3 Dampak Terhadap Sistem Existing
Sebagian besar perubahan bersifat aditif. Berikut klasifikasinya:

**Murni tambahan (tidak menyentuh kode existing)**
* Container Airflow baru di docker-compose.yml.
* Folder /etl baru berisi DAG Python, terpisah dari codebase AI worker dan gateway.
* Tabel warehouse baru — tidak mengubah skema stock_prices, anomaly_events, atau ai_analyses yang sudah ada.
* Halaman dashboard analitik historis baru (route + komponen Svelte baru).

**Modifikasi ringan (aditif terhadap kode existing)**
* AI Worker: opsional menambah satu state baru di LangGraph untuk membaca tabel technical_indicators sebagai konteks tambahan sebelum reasoning ke LLM. Sistem tetap berfungsi penuh tanpa perubahan ini.
* Prometheus: tambah scrape target untuk metrik Airflow.
* .env: tambah variabel kredensial Airflow dan koneksi warehouse, tidak menghapus variabel lama.
* CI/CD: tambah satu workflow baru untuk lint/test DAG.

**Perlu kehati-hatian khusus**
* Resource contention: Airflow scheduler + webserver menambah overhead RAM sekitar 1–1.5GB. Perlu cek headroom mesin sebelum mengaktifkan.
* Query batch yang berat berpotensi membebani PostgreSQL real-time. Mitigasi: gunakan pgbouncer/connection pool terpisah, dan jadwalkan job di luar jam simulasi intensif.

## 14.4 Manfaat yang Diharapkan
* AI Worker mendapat konteks lebih kaya — analisis tidak hanya berdasar berita, tapi juga indikator teknikal (mis. kondisi overbought/oversold) sebagai sinyal tambahan.
* Dashboard mendapat halaman analitik historis: tren jangka panjang, perbandingan indikator antar emiten, laporan periodik.
* Query analitik berat tidak lagi membebani tabel transaksional real-time karena dipisah ke warehouse khusus.

## 14.5 Kriteria Mulai Fase 4
Fase 4 baru layak dimulai jika seluruh kondisi berikut terpenuhi:
1. Fase 1–3 berjalan stabil tanpa bug kritis selama minimal beberapa hari berturut-turut.
2. Tidak ada lagi perubahan besar yang direncanakan pada skema tabel PostgreSQL existing.
3. Tersedia waktu dan resource tambahan (waktu liburan masih cukup, atau dilanjutkan di luar masa liburan sebagai proyek iteratif).

> *Estimasi effort Fase 4 jauh lebih ringan dibanding Fase 1–3 karena tidak ada pembangunan ulang — murni menambah satu layer baru di atas fondasi yang sudah ada.*
