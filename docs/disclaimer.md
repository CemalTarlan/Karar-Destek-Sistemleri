# Disclaimer / Yasal ve Etik Çerçeve

## TR

**MedSim Triage**, yalnızca **eğitim ve simülasyon** amacıyla geliştirilen bir
yazılım prototipidir. Aşağıdaki maddeler, projenin kullanım sınırlarını ve
sorumluluk reddini tanımlar.

### 1. Tıbbi cihaz değildir

Bu yazılım, hiçbir resmi otorite (örn. Türkiye İlaç ve Tıbbi Cihaz Kurumu,
CE/FDA) tarafından tıbbi cihaz olarak onaylanmamıştır ve bu kapsamda
sertifikalandırma süreçlerine tabi değildir. **Klinik karar destek sistemi
olarak kullanılamaz.**

### 2. Tanı ve tedavi sağlamaz

- Sistem, kullanıcı semptomlarını **tanı** olarak adlandırılabilecek bir
  sonuca bağlamaz.
- **İlaç adı, dozaj, uygulama yolu** veya tedavi protokolü önermez.
- Sağlık Bakanlığı'nın 3 renkli (kırmızı/sarı/yeşil) acil triyaj sistemini
  yalnızca **referans çerçeve** olarak kullanır; kuralların klinik geçerliliği
  test edilmemiştir.

### 3. Acil durum protokolü

Sistem KIRMIZI kategori belirlediğinde veya kırmızı bayrak (red-flag) örüntüsü
tespit ettiğinde, kullanıcıyı **doğrudan 112'yi aramaya** yönlendirir.
Bu yönlendirme, sistemin teknik çalışmasından bağımsız olarak her zaman
açıkça gösterilir.

### 4. Veri mahremiyeti

- Sistem **yerel olarak** çalışır (LM Studio + lokal ChromaDB). Hiçbir hasta
  verisi, semptom metni veya konuşma geçmişi varsayılan olarak harici
  servislere gönderilmez.
- Geliştirici, sistemi production ortamında konuşlandırırsa, **KVKK** ve
  ilgili sağlık verisi mevzuatına uygunluğu ayrıca sağlamak zorundadır.
  Bu iskelet KVKK uyumlu DEĞİLDİR.

### 5. LLM çıktısının doğası

Büyük dil modelleri **olasılıksal** sistemlerdir; doğru görünen ama yanlış
("hallucinated") çıktı üretebilirler. Bu nedenle:

- Triyaj rengi kararı LLM'e DEĞİL, kural motoruna bırakılmıştır.
- LLM çıktıları her zaman Pydantic şemaları ile doğrulanır.
- LLM, sistemin bir bileşenidir; otoritesi değildir.

### 6. Sorumluluk reddi

Yazarlar ve katkıda bulunanlar, bu yazılımın gerçek klinik bağlamda
kullanılması durumunda doğabilecek hiçbir doğrudan veya dolaylı zarardan
sorumlu değildir. MIT lisansının "AS IS" maddeleri geçerlidir.

### 7. Eğitim kullanımı

Bu yazılım, bilgisayar mühendisliği, sağlık bilişimi ve yapay zeka
müfredatlarında **agent mimarisi**, **structured output**, **RAG** ve
**guardrails** konularını öğretmek için kullanılabilir. Klinik personel
eğitimi için kullanılması durumunda, bu materyalin **örnek bir mühendislik
prototipi** olduğu, klinik bir kaynak olmadığı her zaman vurgulanmalıdır.

### 8. Acil durum için

> **Acil bir tıbbi durumdaysanız bu sistemi KAPATIN ve ŞİMDİ 112'yi ARAYIN.**

---

## EN — Short notice

This software (`medsim-triage`) is intended for **education and simulation
only**. It is **NOT a medical device**, does **NOT provide diagnosis,
treatment, or dosing advice**, and **MUST NOT be used in real clinical
contexts**. In a medical emergency, **call 112** (or your local emergency
number) immediately.
