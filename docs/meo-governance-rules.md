# MEO Fabric Governance — Source Rules

> **Source:** `Fabric - Organização.pptx` (6 slides). This document is the
> machine-readable transcription of the PowerPoint and is the **authoritative
> source of truth** for naming, organization, and access-group rules for the
> Fabric Governance application in this repo.

---

## 1. Organizational Hierarchy (Slide 2 — "Estrutura Microsoft Fabric MEO")

```
Fabric Tenant (Instância Fabric)
│
├── Domain IT
│   ├── Sub Domain DEV   → Workspaces (Ws1, Ws2, Ws3)
│   ├── Sub Domain SIT   → Workspaces (Ws4, Ws5, Ws6)
│   └── Sub Domain PRD   → Workspaces (Ws7, Ws8, Ws9)
│
└── Domain BU
    ├── Sub Domain BU 1  → Workspaces (Ws10, Ws11)
    └── Sub Domain BU 2  → Workspaces (Ws12, Ws13)
```

**Key principles:**
- Two top-level domain types: **IT** (split by environment) and **BU** (split by business unit).
- Sub-domains under IT are environment-based (DEV, SIT, PRD).
- Sub-domains under BU are business-unit based.
- Workspaces always live under a sub-domain.

---

## 2. Domain Catalog (Slide 3) — 19 Approved Domains

| # | Departamento | Nome Final |
|---|---|---|
| 1 | Gestão do Segmento B2C | `dom-seg-b2c` |
| 2 | Gestão do Segmento B2B | `dom-seg-b2b` |
| 3 | Financeira | `dom-ges-fin` |
| 4 | Planeamento, Controlo e Assurance | `dom-pln-cnt` |
| 5 | Pessoas e Organização | `dom-pss-org` |
| 6 | IT - Gestão de Dados | `dom-ops-dat` |
| 7 | Engenharia e Rede | `dom-eng-net` |
| 8 | AI | `dom-ops-aic` |
| 9 | Logística | `dom-ops-lgs` |
| 10 | Field Force | `dom-ops-wfm` |
| 11 | Wholesale | `dom-ops-whs` |
| 12 | Operações Contact Center | `dom-cnt-ctr` |
| 13 | Operações Empresariais | `dom-ops-b2b` |
| 14 | Oferta | `dom-prd-ofr` |
| 15 | Operações Comerciais Consumo | `dom-ops-b2c` |
| 16 | Digital | `dom-exp-dig` |
| 17 | Compliance e Data Privacy | `dom-cmp-prv` |
| 18 | Regulação, Concorrência e Jurídico | `dom-reg-jur` |
| 19 | Auditoria | `dom-aud-int` |

---

## 3. Naming Conventions

### 3.1 Domain (Slide 3)

```
Pattern: dom-<area>-<produto>
Regex:   ^dom-[a-z]{2,4}-[a-z0-9]{2,6}$
```

### 3.2 Sub Domain (Slide 3–4)

```
Pattern: sdm-<area>-<produto>
Regex:   ^sdm-[a-z]{2,4}-[a-z0-9]{2,6}$
```

### 3.3 Workspace (Slide 4) — **STRICT 6-SEGMENT FORMAT**

```
Pattern: <country>-<area>-<subject>-<dataproducttype>-<env>-<suffix>
```

| Segment | Max Length | Description | Allowed Values / Examples |
|---|---|---|---|
| `country` | 2 | ISO 3166-1 Alpha-2 country code, lowercase | `pt`, `fr`, `es` |
| `area` | 4 | Area responsible for the product | `intl` (AI/GenAI), `nlyt` (Analytics), `fops` (FinOps), `dsci` (Data Science), `mrkt` (Marketing) |
| `subject` | 8* | Context describing what aspect of the data product is captured | `brz`, `slv`, `gld`, `ndf` |
| `dataproducttype` | 3 | Type of the data product | `brz` (bronze), `slv` (silver), `gld` (gold), `ndf` (non-differentiated) |
| `env` | 3 | Environment / context | `poc`, `dev`, `sit`, `uat`, `stg`, `prd` |
| `suffix` | 6 | Random ID for uniqueness | `12fas2` |

*Slide 4 has an internal inconsistency: the template line shows `subject{7}` but
the table description says max length 8. **Flagged for clarification with stakeholder.**
This document uses `8` (the descriptive value) until clarified.

**Constraints across all segments:** lowercase only, no special symbols, no
spaces. Numeric chars allowed only in `suffix`.

**Proposed regex (subject=8):**
```
^[a-z]{2}-[a-z]{2,4}-[a-z]{2,8}-[a-z]{2,3}-[a-z]{3}-[a-z0-9]{1,6}$
```

### 3.4 Example Workspace Names

```
pt-nlyt-customer-slv-dev-12fas2
pt-mrkt-campaign-gld-prd-a1b2c3
pt-fops-billing-brz-sit-x9y8z7
```

---

## 4. Access Groups (Slide 5) — Naming Convention

```
Pattern: grp_<service>_<environment>_<profile>
```

| Segment | Description | Allowed Values |
|---|---|---|
| `grp` | Fixed literal | `grp` |
| `service` | Fabric service | `fabric`, `powerbi` |
| `environment` | Environment | `dev`, `sit`, `uat`, `prd` |
| `profile` | Profile = `<area>_<role>` (area + role joined by `_`) | area: `aic`, `mkt`, `b2c`, `cor`, ...; role: `admin`, `member`, `contributor`, `viewer` |

### 4.1 Examples (Slide 5)

| Profile Description | Group Name |
|---|---|
| Administrator of Fabric for corporate data on development | `grp_fabric_dev_cor_admin` |
| Member of Fabric for Marketing department on production | `grp_fabric_prd_mkt_member` |
| Viewer of Power BI for AIC team on test (UAT) environment | `grp_powerbi_uat_aic_viewer` |

**Proposed regex:**
```
^grp_(fabric|powerbi)_(dev|sit|uat|prd)_[a-z]{2,5}_(admin|member|contributor|viewer)$
```

---

## 5. Gap Analysis vs Current Repo

The existing implementation in this repository was built before
these MEO rules were known. The following changes are required to align:

| Area | Current | MEO Required |
|---|---|---|
| Workspace regex | `^(prd\|stg\|dev\|sbx)-[a-z0-9]{2,6}-[a-z0-9-]{3,40}$` | 6-segment country-area-subject-type-env-suffix |
| Environment enum | `prd, stg, dev, sbx` | `poc, dev, sit, uat, stg, prd` |
| Domain field | Free text (4 hardcoded: Platform/Finance/Sales/Engineering) | 19 MEO domains (allow-list) |
| Sub-domain field | _missing_ | Required, follows `sdm-<area>-<produto>` |
| Country field | _missing_ | Required (ISO 3166-1 Alpha-2) |
| Data product type | _missing_ | Required (brz/slv/gld/ndf) |
| Access groups | UPN/Group ID only | Should validate naming `grp_<service>_<env>_<area>_<role>` |

---

## 6. Open Questions

1. **Subject length** — Slide 4 template says `{7}` but description says max 8. Which is correct?
2. **Area allow-list** — Are the 5 examples (`intl`, `nlyt`, `fops`, `dsci`, `mrkt`) exhaustive or illustrative?
3. **Subject allow-list** — Are subjects free-form or constrained to medallion layers (`brz`, `slv`, `gld`, `ndf`)?
4. **Dataproducttype duplication** — `subject` and `dataproducttype` use identical example values (`brz`, `slv`, `gld`, `ndf`). Is this intentional or a slide error?
5. **Sub-domain regex** — Pattern `sdm-<area>-<produto>` was provided but no allow-list of sub-domains. Should sub-domains be free-form or governed?
6. **Access group area code** — What is the canonical list of `area` codes for groups (`aic`, `mkt`, `b2c`, `cor`, ...)?
7. **Mapping rule** — How do organizational sub-domains (DEV/SIT/PRD/BU1/BU2) map to the workspace `env` segment?

---

## 7. Source File

- File: `Fabric - Organização.pptx`
- Slides: 6
- Dimensions: 13.33" x 7.50" (16:9)
- Layouts used: Title Slide, "2_2 lines and 2 columns text"
- Language: Portuguese (Portugal) with English technical terms
