# Triyaj Kural YAML Şeması

Tüm triyaj kuralları `src/medsim/rules/data/triage_rules.yaml` dosyasında
saklanır. Kurallar `Rule` Pydantic modeli ile doğrulanır
(bkz. `src/medsim/rules/engine.py`).

## Üst seviye yapı

```yaml
version: "0.1.0-placeholder"
rules:
  - id: TR-RED-01
    color: KIRMIZI
    title: "..."
    trigger_symptoms: [...]
    required_combinations: [[...], [...]]   # opsiyonel
    age_filter: ">=35"                       # opsiyonel
    target_minutes: 0
    source_reference: "..."
```

## Alanlar

| Alan                     | Tip                       | Zorunlu | Açıklama |
| ------------------------ | ------------------------- | ------- | -------- |
| `id`                     | string                    | ✔       | Benzersiz kural kimliği. Önek konvansiyonu: `TR-{RED|YEL|GRN}-{NN}` |
| `color`                  | enum (KIRMIZI/SARI/YESIL) | ✔       | Tetiklendiğinde verilecek triyaj rengi |
| `title`                  | string                    | ✔       | İnsan tarafından okunabilir başlık (Türkçe) |
| `trigger_symptoms`       | list[string]              | ✔       | Bu kuralın tetiklenmesi için aranan semptom anahtarları (snake_case, Türkçe) |
| `required_combinations`  | list[list[string]] \| null | —     | AND-of-OR kombinasyonu: en az bir alt-listenin TÜM elemanları semptom kümesinde olmalı |
| `age_filter`             | string \| null            | —       | `">=35"`, `"<18"` gibi karşılaştırma. None ise yaş filtrelemesi yok |
| `target_minutes`         | int                       | ✔       | Hedef değerlendirme süresi (dk). KIRMIZI = 0, SARI = 30-60, YEŞİL = 240+ |
| `source_reference`       | string                    | ✔       | Kuralın kaynaklandığı klinik referans (TODO: gerçek tıbbi referansla doldurulacak) |

## Eşleştirme algoritması

`RuleEngine.match(symptoms)` şu sırayla bir kural arar:

1. `age_filter` sağlanmıyorsa kural atlanır.
2. `required_combinations` belirtilmişse, en az bir alt-listenin **tüm**
   elemanları `chief_complaint ∪ associated_symptoms` kümesinde olmalı.
3. Aksi halde, en az bir `trigger_symptoms` elemanı semptom kümesinde olmalı.
4. Adaylar **renk önceliğine** göre sıralanır (KIRMIZI > SARI > YEŞİL).
   Eşitlik durumunda en çok semptom eşleştiren ve kombinasyon kullanan kural
   tercih edilir.

## Yaş filtresi söz dizimi

Regex: `^\s*(>=|<=|>|<|==|=)\s*(\d{1,3})\s*$`

Geçerli örnekler: `">=35"`, `"<18"`, `"=65"`, `">0"`. Geçersiz biçim
yükleme sırasında `ValidationError` fırlatır.

## Tam örnek

```yaml
- id: TR-RED-01
  color: KIRMIZI
  title: "Kardiyak şüpheli göğüs ağrısı (35 yaş üstü)"
  trigger_symptoms:
    - gogus_agrisi
  required_combinations:
    - [gogus_agrisi, nefes_darligi]
    - [gogus_agrisi, kola_yayilim]
  age_filter: ">=35"
  target_minutes: 0
  source_reference: "TODO: gerçek tıbbi referansla doldurulacak"
```

Bu kuralın tetiklenmesi için:
- Hasta 35+ yaşında olmalı, **VE**
- Aşağıdaki kombinasyonlardan biri sağlanmalı:
  - `{gogus_agrisi, nefes_darligi}` ⊆ semptom kümesi, **VEYA**
  - `{gogus_agrisi, kola_yayilim}` ⊆ semptom kümesi.

## Kırmızı bayrak (red flag) YAML şeması

`src/medsim/rules/data/red_flags.yaml` dosyası **kural motorundan ayrı** bir
yapıyı izler. Bkz. `RedFlagPattern` modeli.

```yaml
patterns:
  - id: RF-CARDIAC-01
    description: "..."
    keyword_groups:
      - ["göğüs", "gogus"]            # bu sözcüklerden EN AZ BİRİ
      - ["sıkış", "ağrı", "baskı"]    # AND bu sözcüklerden EN AZ BİRİ
      - ["kol", "çene", "sırt"]       # AND bu sözcüklerden EN AZ BİRİ
```

Mantık: `keyword_groups` listesindeki gruplar arasında **AND**, her grup
içindeki sözcükler arasında **OR** uygulanır. Türkçe normalleştirme
(diyakritik yumuşatma + lowercase) detector tarafında yapılır; YAML'da
hem diyakritikli hem ASCII varyantları yazmak iyi pratiktir.
