# Entity–relationship overview (v1.0.0-demo)

One PostgreSQL 18 database, 24 tables, all created by the Alembic migrations in
`backend/alembic/versions/`. Column-level details: [README.md](README.md).
This page lists the entities and relationships for a report diagram;
timestamps and secondary columns are left out on purpose.

```mermaid
erDiagram
    USER ||--|| USER_PROFILE : has
    USER ||--o{ AUTH_SESSION : "signs in with"
    USER ||--o{ ADDRESS : saves
    USER ||--o| CART : owns
    CART ||--o{ CART_ITEM : contains
    CART_ITEM }o--|| PRODUCT_VARIANT : "refers to"

    CATEGORY ||--o{ PRODUCT : groups
    PRODUCT ||--o{ PRODUCT_IMAGE : shows
    PRODUCT ||--o{ PRODUCT_VARIANT : "sold as"
    PRODUCT_VARIANT ||--|| INVENTORY : "stock of"
    PRODUCT_IMAGE ||--o{ PRODUCT_IMAGE_EMBEDDING : "encoded as"

    USER ||--o{ ORDER : places
    ORDER ||--o{ ORDER_ITEM : contains
    ORDER ||--o{ ORDER_STATUS_HISTORY : records
    ORDER ||--o{ PAYMENT_STATUS_HISTORY : records
    ORDER_ITEM }o--o| PRODUCT_VARIANT : "snapshot of"

    USER ||--o{ RETURN_REQUEST : requests
    ORDER ||--o{ RETURN_REQUEST : "returned through"
    RETURN_REQUEST ||--o{ RETURN_ITEM : lists
    RETURN_ITEM }o--|| ORDER_ITEM : returns
    RETURN_REQUEST ||--o{ RETURN_STATUS_HISTORY : records

    USER ||--o{ SUPPORT_CONVERSATION : opens
    SUPPORT_CONVERSATION }o--o| ORDER : "about"
    SUPPORT_CONVERSATION }o--o| RETURN_REQUEST : "about"
    SUPPORT_CONVERSATION ||--o{ SUPPORT_MESSAGE : contains

    USER ||--o| FIT_PROFILE : confirms
    USER ||--o{ FIT_ESTIMATE : "receives (last 3)"

    USER {
        int id PK
        string email UK
        string password_hash
        enum role "customer | admin"
    }
    PRODUCT {
        int id PK
        string slug UK
        int base_price "XAF"
        bool smart_fit
        bool is_active
    }
    PRODUCT_VARIANT {
        int id PK
        string sku UK
        string size
        string color_name
    }
    INVENTORY {
        int on_hand
        int reserved
    }
    ORDER {
        int id PK
        string order_number UK "KW-..."
        enum status
        enum payment_status
        int total "XAF"
    }
    ORDER_ITEM {
        string product_name "snapshot"
        int unit_price "XAF snapshot"
        int quantity
    }
    RETURN_REQUEST {
        string return_number UK "KR-..."
        enum status
        int return_value "XAF"
    }
    RETURN_ITEM {
        int quantity
        enum reason
        bool restock
    }
    SUPPORT_CONVERSATION {
        string conversation_number UK "KS-..."
        enum subject
        enum status "open | closed"
    }
    SUPPORT_MESSAGE {
        enum sender_role "customer | store"
        text body "plain text"
        datetime read_at
    }
    FIT_PROFILE {
        int height_cm
        string top_size
        string bottom_size
        int shoe_size_eu
    }
```

## Relationships and rules

| Relationship | Cardinality | On delete | Notes |
| --- | --- | --- | --- |
| User – UserProfile | 1 : 1 | cascade | name, phone |
| User – AuthSession | 1 : n | cascade | one row per login; refresh-token id, revocation |
| User – Address | 1 : n | cascade | Cameroon delivery addresses, one default |
| User – Cart – CartItem | 1 : 0..1 : n | cascade | CartItem → ProductVariant |
| Category – Product | 1 : n | blocked (no action) | deactivation hides, nothing is hard-deleted in the admin |
| Product – ProductImage / ProductVariant | 1 : n | cascade | variant = colour × size (or one size) |
| ProductVariant – Inventory | 1 : 1 | cascade | `on_hand ≥ 0`, `reserved ≥ 0`; `available = on_hand − reserved` |
| ProductImage – ProductImageEmbedding | 1 : n (one per model) | cascade | 512-number OpenCLIP vector as bytes |
| User – Order | 1 : n | cascade | Order copies the delivery address |
| Order – OrderItem | 1 : n | cascade | immutable snapshot (name, SKU, size, colour, price); variant link set null if removed |
| Order – OrderStatusHistory / PaymentStatusHistory | 1 : n | cascade | audit trail with acting admin and notes |
| Order – ReturnRequest | 1 : n | cascade | only delivered orders; within 7 days of delivery |
| ReturnRequest – ReturnItem | 1 : n | cascade | ReturnItem → OrderItem (no catalog data copied) |
| ReturnRequest – ReturnStatusHistory | 1 : n | cascade | customer note + internal note |
| User – SupportConversation – SupportMessage | 1 : n : n | cascade | optional links to Order / ReturnRequest (set null) |
| User – FitProfile | 1 : 0..1 | cascade | confirmed sizes; estimated dimensions only if from photos |
| User – FitEstimate | 1 : n (last 3 kept) | cascade | derived numbers only, never images |
| VisualSearchIndexRun | — | — | log of index builds (not linked) |

Money is always an integer number of XAF francs. No table stores photos,
pose landmarks, payment card data or Mobile Money PINs.
