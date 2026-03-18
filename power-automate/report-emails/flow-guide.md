# Power Automate Flow: Automatyczny raport zagrożonych zamówień

## Przegląd

Flow wysyła e-mail z raportem zagrożonych zamówień (marża < 5%) dla każdego `Key_Sales_CuS`.
Raport zawiera:
1. Tabelę zagrożonych zamówień z marżą
2. Ceny sprzedaży wg cennika AX
3. Ceny zakupu od dostawców

---

## Struktura Flow (krok po kroku)

### 1. Trigger — Recurrence (harmonogram)

| Ustawienie | Wartość |
|---|---|
| Frequency | Week / Day (wg potrzeb) |
| Interval | 1 |
| Time zone | (UTC+01:00) Warsaw |
| Start time | np. 07:00 |

---

### 2. Run a query against a dataset (Power BI) — Zagrożone zamówienia

- **Connector**: Power BI
- **Action**: "Run a query against a dataset"
- **Workspace**: (wybierz swój workspace)
- **Dataset**: (wybierz dataset z modelem)
- **Query**: Użyj zapytania DAX z pliku `dax-threatened-orders.dax` — sekcja **TABELA 1**

```dax
EVALUATE
VAR _MarginThreshold = 0.05
RETURN
FILTER(
    SELECTCOLUMNS(
        '04_Open_Orders',
        "Key_Sales_CuS",       '04_Open_Orders'[Key_Sales_CuS],
        "Sales_Order",         '04_Open_Orders'[Sales order],
        "Line_No",             '04_Open_Orders'[Line No],
        "Item_Number",         '04_Open_Orders'[Item number],
        "Name",                '04_Open_Orders'[Name],
        "Customer_Account",    '04_Open_Orders'[Customer account],
        "Quantity",            '04_Open_Orders'[Quantity],
        "Unit_Price",          '04_Open_Orders'[Unit price],
        "Net_Amount",          '04_Open_Orders'[Net amount],
        "Amount_EUR",          '04_Open_Orders'[Amount in EUR],
        "COGS_EUR",            '04_Open_Orders'[COGS in EUR],
        "Margin",              '04_Open_Orders'[Margin],
        "Vendor",              '04_Open_Orders'[Vendor],
        "Confirmed_Ship_Date", '04_Open_Orders'[Confirmed ship date],
        "Requested_Ship_Date", '04_Open_Orders'[Requested ship date]
    ),
    [Margin] < _MarginThreshold
)
ORDER BY [Key_Sales_CuS], [Margin] ASC
```

> Nazwij ten krok: `queryThreatenedOrders`

---

### 3. Run a query — Ceny sprzedaży

Użyj sekcji **TABELA 2** z pliku DAX.

> Nazwij ten krok: `querySalesPrices`

---

### 4. Run a query — Ceny zakupu

Użyj sekcji **TABELA 3** z pliku DAX.

> Nazwij ten krok: `queryPurchasePrices`

---

### 5. Parse JSON (x3)

Dla każdego wyniku zapytania dodaj akcję **Parse JSON**:

**Schema** (przykład dla zagrożonych zamówień):
```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "Key_Sales_CuS":    { "type": "string" },
          "Sales_Order":      { "type": "string" },
          "Line_No":          { "type": "string" },
          "Item_Number":      { "type": "string" },
          "Name":             { "type": "string" },
          "Customer_Account": { "type": "string" },
          "Quantity":         { "type": "number" },
          "Unit_Price":       { "type": "number" },
          "Net_Amount":       { "type": "number" },
          "Amount_EUR":       { "type": "number" },
          "COGS_EUR":         { "type": "number" },
          "Margin":           { "type": "number" },
          "Vendor":           { "type": "string" },
          "Confirmed_Ship_Date": { "type": "string" },
          "Requested_Ship_Date": { "type": "string" }
        }
      }
    }
  }
}
```

---

### 6. Select distinct Key_Sales_CuS

- **Action**: Select
- **From**: `body('parseThreatenedOrders')?['results']`
- **Map**: `Key_Sales_CuS` → `item()?['Key_Sales_CuS']`

Następnie **Compose** z wyrażeniem:
```
union(body('Select'), body('Select'))
```
(zwraca unikalne wartości)

> Nazwij: `distinctKeys`

---

### 7. Apply to each — Per Key_Sales_CuS

**Input**: `outputs('distinctKeys')`

Wewnątrz pętli:

#### 7a. Initialize variable `currentKeySalesCuS`
```
items('Apply_to_each_key')['Key_Sales_CuS']
```

#### 7b. Filter array — zamówienia dla bieżącego klucza
- **From**: `body('parseThreatenedOrders')?['results']`
- **Condition**: `item()?['Key_Sales_CuS']` is equal to `variables('currentKeySalesCuS')`

> Nazwij: `filteredOrders`

#### 7c. Filter array — unikalne Item numbers
Wyciągnij unikalne `Item_Number` z `filteredOrders`.

#### 7d. Filter array — ceny sprzedaży dla tych produktów
- **From**: `body('parseSalesPrices')?['results']`
- **Condition**: `item()?['Item_Number']` is in lista unikalnych items

#### 7e. Filter array — ceny zakupu dla tych produktów
Analogicznie jak 7d, ale z `parsePurchasePrices`.

#### 7f. Compose HTML — zamówienia
Użyj akcji **Select** + **Join** lub pętli **Apply to each** do zbudowania wierszy HTML:

```
<tr>
  <td>@{items('loop')['Sales_Order']}</td>
  <td>@{items('loop')['Line_No']}</td>
  <td>@{items('loop')['Item_Number']}</td>
  <td>@{items('loop')['Name']}</td>
  <td>@{items('loop')['Customer_Account']}</td>
  <td class="text-right">@{items('loop')['Quantity']}</td>
  <td class="text-right">@{items('loop')['Unit_Price']}</td>
  <td class="text-right">@{items('loop')['Amount_EUR']}</td>
  <td class="text-right">@{items('loop')['COGS_EUR']}</td>
  <td class="text-right">
    <span style="color:@{if(less(items('loop')['Margin'],0),'#c0392b','#e67e22')};font-weight:700">
      @{formatNumber(mul(items('loop')['Margin'],100),'N1')}%
    </span>
  </td>
  <td>@{items('loop')['Vendor']}</td>
</tr>
```

#### 7g. Compose HTML — ceny sprzedaży i zakupu
Analogicznie jak 7f, dla tabel cen.

#### 7h. Compose — Podsumowanie
Oblicz:
- `threatenedCount` — `length(body('filteredOrders'))`
- `minMargin` — `min(...)` z filtrowanych zamówień
- `totalAmountEUR` — `sum(...)` z Amount_EUR

#### 7i. Send an email (V2) — Outlook
- **To**: Adres e-mail powiązany z `Key_Sales_CuS` (z tabeli mapowania lub Bridge_Customer)
- **Subject**: `⚠ Zagrożone zamówienia — @{variables('currentKeySalesCuS')} — @{utcNow('dd.MM.yyyy')}`
- **Body**: Wklej zawartość `email-template.html` z podstawionymi zmiennymi
- **Is HTML**: Yes

---

## Mapowanie e-mail → Key_Sales_CuS

Potrzebujesz tabeli mapującej `Key_Sales_CuS` na adres e-mail odbiorcy.

**Opcje**:
1. **Dodatkowa tabela w Power BI** z kolumnami: `Key_Sales_CuS`, `Email`
2. **SharePoint List** jako źródło mapowania
3. **Excel Online** w OneDrive/SharePoint

---

## Diagram przepływu

```
┌─────────────┐
│  Recurrence │  (co dzień / co tydzień)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────┐
│  Power BI: Query zagrożone zam. │──┐
│  Power BI: Query ceny sprzedaży │  │  (równolegle)
│  Power BI: Query ceny zakupu    │──┘
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Parse JSON (x3)                │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Distinct Key_Sales_CuS         │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Apply to each Key_Sales_CuS            │
│  ┌────────────────────────────────────┐  │
│  │ Filter zamówienia per klucz       │  │
│  │ Filter ceny sprzedaży per items   │  │
│  │ Filter ceny zakupu per items      │  │
│  │ Build HTML tables                 │  │
│  │ Calculate summary                 │  │
│  │ Send email                        │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

## Pliki w tym katalogu

| Plik | Opis |
|---|---|
| `dax-threatened-orders.dax` | 3 zapytania DAX (zamówienia, ceny sprzedaży, ceny zakupu) |
| `email-template.html` | Szablon HTML e-maila z placeholderami Power Automate |
| `flow-guide.md` | Ten dokument — instrukcja budowy flow |
